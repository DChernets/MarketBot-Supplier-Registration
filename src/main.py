import logging
from logging.handlers import RotatingFileHandler
import uuid
import asyncio
import requests
from io import BytesIO
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from src.config import TELEGRAM_BOT_TOKEN, DEBUG, ENABLE_CONTENT_GENERATION, AUTO_GENERATE_CONTENT, LOCAL_ENHANCED_IMAGES_PATH
from src.google_sheets import GoogleSheetsManager
from src.gemini_service import get_gemini_service, initialize_gemini_service
from src.image_storage import get_image_storage_service, initialize_image_storage
from src.content_generation_service import get_content_generation_service
from src.utils import escape_markdown

# Создаем директорию для логов, если не существует
import os
os.makedirs('logs', exist_ok=True)

# Включаем логирование с ротацией (макс. 5 МБ, 5 файлов)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=5*1024*1024,  # 5 МБ
    backupCount=5,
    encoding='utf-8'
)
log_handler.setFormatter(log_formatter)

# Настройка основного логирования
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    handlers=[
        log_handler,
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ВАЖНО: Отключаем логирование чувствительных данных (API ключи, токены)
# httpx и telegram логируют полные URL с ключами на уровне INFO
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)
logger.info("⚠️ Sensitive data logging disabled for httpx, httpcore, telegram")

# Состояния для ConversationHandler
NAME, MARKET, PAVILION, PHONE, ADD_MORE_PHONES, ADD_MORE_PHONES_CALLBACK, ADD_LOCATION, ADD_LOCATION_CALLBACK = range(8)

# Новые состояния для распознавания изображений
PHOTO_UPLOAD, PHOTO_CONFIRMATION, LOCATION_SELECTION, QUANTITY_INPUT, PRODUCT_CONFIRMATION, PRODUCT_MANAGEMENT = range(8, 14)

# Новые состояния для управления каналами
ADD_CHANNEL_USERNAME, ADD_CHANNEL_DESCRIPTION, EDIT_CHANNEL_DESCRIPTION = range(14, 17)

class MarketBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self._sheets_manager = None  # Приватный атрибут для синглтона
        self.gemini_service = None
        self.image_storage_service = None
        self.content_generation_service = None
        self.services_initialized = False
        self.setup_handlers()

    @property
    def sheets_manager(self):
        """Ленивая инициализация GoogleSheetsManager как синглтон"""
        if self._sheets_manager is None:
            try:
                self._sheets_manager = GoogleSheetsManager()
                logger.info("GoogleSheetsManager успешно инициализирован")
            except Exception as e:
                logger.error(f"Ошибка при инициализации GoogleSheetsManager: {e}")
                self._sheets_manager = None
                raise
        return self._sheets_manager

    async def safe_edit_message_text(self, query, text, reply_markup=None, parse_mode=None):
        """Безопасное редактирование сообщения с fallback на caption"""
        message = query.message

        # Проверяем, есть ли у сообщения текст или caption
        has_text = bool(message.text) or bool(message.caption)

        # Если сообщение имеет фотографию, используем edit_message_caption
        if message.photo:
            try:
                await query.edit_message_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.warning(f"Failed to edit caption: {e}")
                # Если caption не сработал, пытаемся отправить новое сообщение
                try:
                    await message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                except Exception as e2:
                    logger.error(f"Failed to send reply message: {e2}")
        elif has_text:
            # Если сообщение без фото, но с текстом, используем edit_message_text
            try:
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.warning(f"Failed to edit text: {e}")
                # Fallback - отправляем новое сообщение
                try:
                    await message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                except Exception as e2:
                    logger.error(f"Failed to send reply message: {e2}")
        else:
            # Если сообщение не имеет ни текста, ни фото, просто отправляем новое сообщение
            logger.warning("Message has no text or photo, sending new message instead of editing")
            try:
                await message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.error(f"Failed to send reply message: {e}")
                # Последний fallback - пробуем отправить напрямую пользователю
                try:
                    await query.bot.send_message(
                        chat_id=query.from_user.id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                except Exception as e2:
                    logger.error(f"Failed to send direct message: {e2}")

  
    async def send_photo_from_telegram_url(self, chat_id: int, photo_url: str, caption: str = None, reply_markup=None):
        """Скачать фото с Telegram URL и отправить его как файл"""
        try:
            logger.info(f"Downloading photo from: {photo_url}")

            # Скачиваем фото с использованием токена бота для аутентификации
            headers = {}
            response = requests.get(photo_url, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"Photo downloaded successfully, size: {len(response.content)} bytes")

                # Создаем файл из скачанных данных
                photo_file = BytesIO(response.content)
                photo_file.name = 'product_photo.jpg'  # Устанавливаем имя файла

                # Отправляем фото в Telegram
                await self.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_file,
                    caption=caption,
                    reply_markup=reply_markup
                )
                logger.info("Photo sent successfully")
                return True
            else:
                logger.error(f"Failed to download photo, status code: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error downloading/sending photo: {e}")
            return False

    def extract_product_name(self, description: str) -> str:
        """Извлечь реальное название товара из описания"""
        if not description or description.strip() == "":
            return "Товар"

        import re

        # Сначала пытаемся извлечь из фразы "Тип товара:" (самый надежный способ)
        type_match = re.search(r'- Тип товара:\s*([^-/]+)', description)
        if type_match:
            type_name = type_match.group(1).strip()
            # Убираем лишние детали и разделители
            type_name = re.split(r'[/|-]', type_name)[0].strip()
            if type_name:
                # Укорачиваем длинные названия
                if len(type_name) > 8:  # Уменьшаем порог до 8 символов
                    # Ищем основное слово (до первого пробела или предлога)
                    main_word = re.split(r'[\s(]', type_name)[0].strip()
                    if main_word and len(main_word) > 2:
                        return main_word
                return type_name

        # Если не нашли "Тип товара:", ищем по ключевым словам
        keywords = [
            ("Бокал", "Бокал"),
            ("Термокружка", "Термокружка"),
            ("термостакан", "Термокружка"),
            ("Футболка", "Футболка"),
            ("Джинсы", "Джинсы"),
            ("Кроссовки", "Кроссовки"),
            ("Телефон", "Смартфон"),
            ("Смартфон", "Смартфон"),
            ("Наушники", "Наушники"),
            ("Шапочка", "Шапочка"),
            ("Шапка", "Шапочка"),
            ("Сахарница", "Сахарница"),
            ("Чайник", "Чайник"),
            ("Кружка", "Кружка"),
            ("Кошелек", "Кошелек"),
            ("Сумка", "Сумка"),
            ("Рюкзак", "Рюкзак"),
            ("Куртка", "Куртка"),
            ("Ботинки", "Ботинки"),
            ("Мышка", "Компьютерная мышка"),
            ("Клавиатура", "Клавиатура"),
            ("Монитор", "Монитор"),
            ("Планшет", "Планшет"),
            ("Часы", "Часы"),
            ("Очки", "Очки"),
            ("Ручка", "Ручка"),
            ("Блокнот", "Блокнот"),
            ("Книга", "Книга"),
            ("Тарелка", "Тарелка"),
            ("Вилка", "Вилка"),
            ("Ложка", "Ложка"),
            ("Нож", "Нож"),
        ]

        for keyword, result in keywords:
            if keyword.lower() in description.lower():
                return result

        # Если ничего не нашли, пробуем извлечь первое слово после маркера
        first_word_match = re.search(r'-\s*([А-Яа-яA-Za-z]+)', description)
        if first_word_match:
            first_word = first_word_match.group(1).strip()
            if len(first_word) > 2:  # Исключаем слишком короткие слова
                return first_word

        return "Товар"

    def extract_short_description(self, description: str, max_length: int = 100) -> str:
        """Извлечь краткое описание в 1 предложение"""
        if not description or description.strip() == "":
            return "Описание отсутствует"

        # Ищем первое осмысленное предложение
        import re

        # Убираем маркеры списка и лишние пробелы
        clean_desc = re.sub(r'^-\s*', '', description, flags=re.MULTILINE)
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()

        # Разбиваем на предложения и берем первое
        sentences = re.split(r'[.!?]', clean_desc)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Пропускаем слишком короткие
                # Обрезаем если слишком длинное
                if len(sentence) > max_length:
                    sentence = sentence[:max_length].rsplit(' ', 1)[0] + '...'
                return sentence

        # Если не нашли предложений, берем первые символы
        if len(clean_desc) > max_length:
            clean_desc = clean_desc[:max_length].rsplit(' ', 1)[0] + '...'
        return clean_desc if clean_desc else "Описание отсутствует"

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Простые обработчики команд
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('profile', self.profile_command))
        self.application.add_handler(CommandHandler('cancel', self.cancel))
        self.application.add_handler(CommandHandler('skip', self.skip_command))

        # Обработчики для фото
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))

        # Глобальные обработчики для текстовых сообщений и кнопок
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback, pattern=r'.*'))

    async def initialize_services(self):
        """Инициализация сервисов"""
        if self.services_initialized:
            return True

        try:
            logger.info("Инициализация сервисов распознавания изображений")

            # Инициализация Gemini сервиса
            gemini_initialized = await initialize_gemini_service()
            if gemini_initialized:
                self.gemini_service = get_gemini_service()
                logger.info("Gemini сервис успешно инициализирован")
            else:
                logger.warning("Не удалось инициализировать Gemini сервис")

            # Инициализация сервиса хранения изображений
            storage_initialized = await initialize_image_storage()
            if storage_initialized:
                self.image_storage_service = get_image_storage_service()
                logger.info("Сервис хранения изображений успешно инициализирован")
            else:
                logger.warning("Не удалось инициализировать сервис хранения изображений")

            # Инициализация сервиса генерации контента
            if ENABLE_CONTENT_GENERATION:
                try:
                    self.content_generation_service = get_content_generation_service(self.sheets_manager)
                    logger.info("Сервис генерации контента успешно инициализирован")
                except Exception as e:
                    logger.warning(f"Не удалось инициализировать сервис генерации контента: {e}")

            self.services_initialized = True
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации сервисов: {e}")
            return False

    async def start_command(self, update: Update, context):
        """Обработчик команды /start"""
        try:
            user = update.effective_user
            telegram_user_id = user.id
            telegram_username = user.username or "Нет username"

            # Проверяем, есть ли уже такой поставщик
            existing_supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

            if existing_supplier:
                await update.message.reply_text(
                    f"Добро пожаловать обратно, {existing_supplier['contact_name']}! "
                    f"Ваш профиль уже зарегистрирован. Используйте /profile для просмотра информации."
                )
            else:
                # Очищаем состояние и начинаем регистрацию
                context.user_data.clear()
                context.user_data['state'] = 'NAME'
                context.user_data['telegram_user_id'] = telegram_user_id
                context.user_data['telegram_username'] = telegram_username

                await update.message.reply_text(
                    f"Здравствуйте, {user.first_name}! 👋\n\n"
                    f"Давайте зарегистрируем вас как поставщика.\n\n"
                    f"Для начала, как вас зовут?"
                )

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text(
                "Произошла ошибка при подключении к базе данных. "
                "Пожалуйста, попробуйте позже или свяжитесь с администратором."
            )

    async def debug_callback(self, update: Update, context):
        """Отладочный обработчик для всех callback запросов"""
        query = update.callback_query
        logger.info(f"DEBUG: Callback received - data: {query.data}")
        logger.info(f"DEBUG: From user: {query.from_user.id}")

        await query.answer("Debug: received!")

        # Теперь пытаемся вызвать правильный обработчик
        if query.data.startswith('add_phone_'):
            logger.info(f"DEBUG: Redirecting to add_more_phones_callback")
            await self.add_more_phones_callback(update, context)
        elif query.data in ['add_location', 'cancel_registration']:
            logger.info(f"DEBUG: Redirecting to add_location_callback")
            await self.add_location_callback(update, context)
        elif query.data == 'add_location_post':
            logger.info(f"DEBUG: Redirecting to post_registration_callback")
            await self.post_registration_callback(update, context)
        else:
            logger.warning(f"DEBUG: Unknown callback data: {query.data}")

    async def handle_text_message(self, update: Update, context):
        """Глобальный обработчик текстовых сообщений"""
        state = context.user_data.get('state')
        edit_state = context.user_data.get('edit_state')
        message_text = update.message.text.strip() if update.message else ""

        logger.info(f"handle_text_message: state={state}, edit_state={edit_state}, message='{message_text}'")

        if state == 'NAME':
            await self.get_name(update, context)
        elif state == 'MARKET':
            await self.get_market(update, context)
        elif state == 'PAVILION':
            await self.get_pavilion(update, context)
        elif state == 'PHONE':
            await self.get_phone(update, context)
        elif state == 'ADD_MORE_PHONES':
            await self.add_more_phones_text(update, context)
        elif state == 'ADD_LOCATION':
            await self.add_location_text(update, context)
        elif state == 'market_name' or edit_state == 'market_name':
            await self.handle_market_name_edit(update, context)
        elif state == 'pavilion_number' or edit_state == 'pavilion_number':
            await self.handle_pavilion_number_edit(update, context)
        elif state == 'editing_phone' or edit_state == 'editing_phone':
            await self.handle_phone_edit(update, context)
        elif state == 'adding_phone' or edit_state == 'adding_phone':
            await self.handle_add_phone(update, context)
        elif state == PHOTO_UPLOAD:
            await self.handle_photo_upload_text(update, context)
        elif state == QUANTITY_INPUT:
            await self.handle_quantity_input(update, context)
        elif state == 'ADD_CHANNEL_USERNAME':
            await self.get_channel_username(update, context)
        elif state == 'ADD_CHANNEL_DESCRIPTION':
            await self.get_channel_description(update, context)
        elif state == 'EDIT_CHANNEL_DESCRIPTION':
            await self.update_channel_description(update, context)
        else:
            logger.info(f"handle_text_message: unhandled state '{state}' for message '{message_text}'")

    async def handle_callback(self, update: Update, context):
        """Глобальный обработчик callback кнопок"""
        query = update.callback_query
        logger.info(f"handle_callback: received callback data={query.data}")
        logger.info(f"handle_callback: from user_id={query.from_user.id}")

        try:
            await query.answer()
            logger.info(f"handle_callback: query.answer() successful")
        except Exception as e:
            logger.error(f"handle_callback: error in query.answer(): {e}")

        if query.data.startswith('add_phone_'):
            logger.info(f"handle_callback: calling add_more_phones_callback")
            await self.add_more_phones_callback(update, context)
        elif query.data in ['add_location', 'cancel_registration']:
            logger.info(f"handle_callback: calling add_location_callback")
            await self.add_location_callback(update, context)
        elif query.data.startswith('edit_location_'):
            logger.info(f"handle_callback: calling edit_location_callback")
            await self.edit_location_callback(update, context)
        elif query.data.startswith('delete_location_'):
            logger.info(f"handle_callback: calling delete_location_callback")
            await self.delete_location_callback(update, context)
        elif query.data.startswith('confirm_delete_location_'):
            logger.info(f"handle_callback: calling confirm_delete_callback")
            await self.confirm_delete_callback(update, context)
        elif query.data == 'cancel_delete' or query.data == 'cancel_edit':
            logger.info(f"handle_callback: calling cancel_action_callback")
            await self.cancel_action_callback(update, context)
        elif query.data.startswith('edit_phone_') or query.data.startswith('delete_phone_') or query.data in ['add_phone_to_location', 'finish_phones_edit']:
            logger.info(f"handle_callback: calling handle_phone_management")
            await self.handle_phone_management(update, context)
        elif query.data in ['edit_market_name', 'edit_pavilion_number', 'manage_phones']:
            logger.info(f"handle_callback: calling handle_edit_options")
            await self.handle_edit_options(update, context)
        elif query.data == 'add_location_post':
            logger.info(f"handle_callback: calling post_registration_callback")
            await self.post_registration_callback(update, context)
        elif query.data == 'photo_recognition':
            logger.info(f"handle_callback: calling start_photo_recognition")
            await self.start_photo_recognition(update, context)
        elif query.data == 'my_products':
            logger.info(f"handle_callback: calling show_my_products")
            try:
                await self.show_my_products(update, context)
                logger.info(f"handle_callback: show_my_products completed successfully")
            except Exception as e:
                logger.error(f"handle_callback: error in show_my_products: {e}")
                import traceback
                logger.error(f"handle_callback: traceback: {traceback.format_exc()}")
        elif query.data == 'my_locations':
            logger.info(f"handle_callback: calling show_my_locations")
            await self.show_my_locations(update, context)
        elif query.data == 'test_my_products':
            logger.info(f"handle_callback: calling show_my_products for TEST")
            await self.show_my_products(update, context)
        elif query.data == 'confirm_photo_recognition':
            logger.info(f"handle_callback: calling confirm_photo_recognition")
            await self.confirm_photo_recognition(update, context)
        elif query.data == 'edit_photo_recognition':
            logger.info(f"handle_callback: calling edit_photo_recognition")
            await self.edit_photo_recognition(update, context)
        elif query.data == 'back_to_photo_upload':
            logger.info(f"handle_callback: calling back_to_photo_upload")
            await self.back_to_photo_upload(update, context)
        elif query.data.startswith('select_location_for_product_'):
            logger.info(f"handle_callback: calling select_location_for_product")
            await self.select_location_for_product(update, context)
        elif query.data.startswith('edit_product_'):
            logger.info(f"handle_callback: calling edit_product")
            await self.edit_product(update, context)
        elif query.data.startswith('delete_product_'):
            logger.info(f"handle_callback: calling delete_product")
            await self.delete_product(update, context)
        elif query.data == 'back_to_profile':
            logger.info(f"handle_callback: calling back_to_profile")
            await self.back_to_profile(update, context)
        elif query.data == 'process_photos_ready':
            logger.info(f"handle_callback: calling process_photo_recognition")
            await self.process_photo_recognition(update, context)
        elif query.data == 'cancel_photo_upload':
            logger.info(f"handle_callback: calling cancel_photo_recognition")
            await self.cancel_photo_recognition(update, context)
        elif query.data.startswith('enhance_content_limit_'):
            logger.info(f"handle_callback: calling enhance_content_limit_info")
            await self.enhance_content_limit_info(update, context)
        elif query.data.startswith('enhance_content_'):
            logger.info(f"handle_callback: calling enhance_product_content")
            await self.enhance_product_content(update, context)
        elif query.data.startswith('view_enhanced_'):
            logger.info(f"handle_callback: calling view_enhanced_content")
            await self.view_enhanced_content(update, context)
        elif query.data == 'channels':
            logger.info(f"handle_callback: calling channels_callback")
            await self.channels_callback(update, context)
        elif query.data == 'add_channel':
            logger.info(f"handle_callback: calling add_channel_callback")
            await self.add_channel_callback(update, context)
        elif query.data.startswith('edit_channel_'):
            logger.info(f"handle_callback: calling edit_channel_callback")
            await self.edit_channel_callback(update, context)
        elif query.data.startswith('delete_channel_'):
            logger.info(f"handle_callback: calling delete_channel_callback")
            await self.delete_channel_callback(update, context)
        elif query.data.startswith('confirm_delete_channel_'):
            logger.info(f"handle_callback: calling confirm_delete_channel_callback")
            await self.confirm_delete_channel_callback(update, context)
        elif query.data == 'skip_description':
            logger.info(f"handle_callback: skipping channel description")
            await self.save_channel(update, context, description="", is_callback=True)
        else:
            logger.warning(f"handle_callback: unknown callback data pattern: {query.data}")

    async def get_name(self, update: Update, context):
        """Получение имени представителя"""
        context.user_data['contact_name'] = update.message.text
        context.user_data['state'] = 'MARKET'

        await update.message.reply_text(
            f"Приятно познакомиться, {context.user_data['contact_name']}!\n\n"
            "Теперь укажите название рынка, где находится ваш магазин:"
        )

    async def get_market(self, update: Update, context):
        """Получение названия рынка"""
        context.user_data['market_name'] = update.message.text
        context.user_data['state'] = 'PAVILION'

        await update.message.reply_text(
            "Отлично! Теперь укажите номер павильона:"
        )

    async def get_pavilion(self, update: Update, context):
        """Получение номера павильона"""
        context.user_data['pavilion_number'] = update.message.text
        context.user_data['state'] = 'PHONE'

        await update.message.reply_text(
            "Хорошо! Теперь укажите контактный телефон для этой точки:"
        )

    async def get_phone(self, update: Update, context):
        """Получение телефона"""
        context.user_data['contact_phones'] = [update.message.text]
        context.user_data['state'] = 'ADD_MORE_PHONES'

        keyboard = [
            [InlineKeyboardButton("Да", callback_data="add_phone_yes")],
            [InlineKeyboardButton("Нет", callback_data="add_phone_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Хотите добавить еще один телефон для этой точки?",
            reply_markup=reply_markup
        )

    async def add_more_phones_text(self, update: Update, context):
        """Добавление дополнительных телефонов - только для текстовых сообщений"""
        logger.info(f"add_more_phones_text called: update.message={update.message}")

        # Если это текстовое сообщение (дополнительный телефон)
        if update.message:
            logger.info(f"Adding phone: {update.message.text}")
            context.user_data['contact_phones'].append(update.message.text)

            keyboard = [
                [InlineKeyboardButton("Да", callback_data="add_phone_yes")],
                [InlineKeyboardButton("Нет", callback_data="add_phone_no")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Хотите добавить еще один телефон?",
                reply_markup=reply_markup
            )

    async def add_more_phones_callback(self, update: Update, context):
        """Callback обработчик для добавления телефонов"""
        query = update.callback_query
        logger.info(f"add_more_phones_callback called: data={query.data}")

        if query.data == "add_phone_yes":
            await query.edit_message_text("Введите дополнительный телефон:")
            context.user_data['state'] = 'PHONE'
        elif query.data == "add_phone_no":
            logger.info("User pressed 'Нет' - saving supplier and location")
            # Сохраняем поставщика и локацию
            await self.save_supplier_and_location(update, context)

            # После сохранения предлагаем добавить новую локацию
            keyboard = [
                [InlineKeyboardButton("Да", callback_data="add_location")],
                [InlineKeyboardButton("Нет", callback_data="cancel_registration")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "Хотите добавить еще одну торговую точку?",
                reply_markup=reply_markup
            )
            context.user_data['state'] = 'ADD_LOCATION'
        else:
            logger.warning(f"add_more_phones_callback: unknown data={query.data}")

    async def save_supplier_and_location(self, update: Update, context):
        """Сохранение поставщика и локации в Google Sheets"""
        try:
            user = update.effective_user
            telegram_user_id = user.id
            telegram_username = user.username or "Нет username"

            # Проверяем, существует ли уже поставщик
            existing_supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

            if existing_supplier:
                # Используем существующего поставщика
                internal_id = existing_supplier['internal_id']
                logger.info(f"Using existing supplier with internal_id: {internal_id}")
            else:
                # Создаем нового поставщика только если его нет
                internal_id = str(uuid.uuid4())
                logger.info(f"Creating new supplier with internal_id: {internal_id}")
                self.sheets_manager.add_supplier(
                    internal_id=internal_id,
                    telegram_user_id=telegram_user_id,
                    telegram_username=telegram_username,
                    contact_name=context.user_data['contact_name']
                )

            # Генерируем ID только для новой локации
            location_id = str(uuid.uuid4())

            # Сохраняем локацию
            contact_phones_str = ", ".join(context.user_data['contact_phones'])
            self.sheets_manager.add_location(
                location_id=location_id,
                supplier_internal_id=internal_id,
                market_name=context.user_data['market_name'],
                pavilion_number=context.user_data['pavilion_number'],
                contact_phones=contact_phones_str
            )

            logger.info(f"Saved location with location_id: {location_id}")

            # Формируем визитку
            contact_info = ""
            for i, phone in enumerate(context.user_data['contact_phones'], 1):
                contact_info += f"тел: {phone} {context.user_data['contact_name']}\n"

            if len(context.user_data['contact_phones']) > 1:
                contact_info = contact_info.replace(context.user_data['contact_name'], "").strip()
                contact_info = f"тел: {', '.join(context.user_data['contact_phones'])} {context.user_data['contact_name']}\n"

            business_card = (
                f"📋 ВАША ВИЗИТКА СОЗДАНА:\n\n"
                f"🏪 РЫНОК {context.user_data['market_name'].upper()}\n"
                f"🏢 Павильон {context.user_data['pavilion_number']}\n"
                f"{contact_info}"
                f"📱 телеграм: @{telegram_username}\n\n"
                f"✅ Регистрация завершена!"
            )

            keyboard = [
                                [InlineKeyboardButton("➕ ДОБАВИТЬ НОВУЮ ТОЧКУ", callback_data="add_location")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Используем query для callback или message для обычных сообщений
            if update.callback_query:
                await update.callback_query.edit_message_text(business_card, reply_markup=reply_markup)
            else:
                await update.message.reply_text(business_card, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error saving supplier: {e}")
            if update.callback_query:
                await update.callback_query.edit_message_text("Произошла ошибка при сохранении данных. Попробуйте позже.")
            else:
                await update.message.reply_text("Произошла ошибка при сохранении данных. Попробуйте позже.")

    async def add_location_text(self, update: Update, context):
        """Добавление новой локации - только для текстовых сообщений"""
        # Если это текстовое сообщение (ответ на вопрос)
        if update.message and update.message.text.lower() in ['да', 'yes', 'д']:
            contact_name = context.user_data.get('contact_name')
            context.user_data.clear()
            context.user_data['contact_name'] = contact_name
            context.user_data['state'] = 'MARKET'

            await update.message.reply_text(
                "Отлично! Давайте добавим новую точку.\n\n"
                "Укажите название рынка для новой точки:"
            )
        elif update.message and update.message.text.lower() in ['нет', 'no', 'н']:
            await update.message.reply_text(
                "Спасибо за регистрацию! Используйте /profile для просмотра вашей информации."
            )
            context.user_data['state'] = None
        else:
            # Если пришло что-то другое, спрашиваем уточняюще
            keyboard = [
                [InlineKeyboardButton("Да", callback_data="add_location")],
                [InlineKeyboardButton("Нет", callback_data="cancel_registration")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Хотите добавить еще одну торговую точку?",
                reply_markup=reply_markup
            )

    async def add_location_callback(self, update: Update, context):
        """Callback обработчик для добавления локации"""
        query = update.callback_query
        logger.info(f"add_location_callback called: data={query.data}")

        if query.data == "add_location":
            # Очищаем данные для новой локации, но сохраняем имя
            contact_name = context.user_data.get('contact_name')
            context.user_data.clear()
            context.user_data['contact_name'] = contact_name
            context.user_data['state'] = 'MARKET'

            await query.edit_message_text(
                "Отлично! Давайте добавим новую точку.\n\n"
                "Укажите название рынка для новой точки:"
            )
        elif query.data == "cancel_registration":
            await query.edit_message_text(
                "Спасибо за регистрацию! Используйте /profile для просмотра вашей информации."
            )
            context.user_data['state'] = None

    async def post_registration_callback(self, update: Update, context):
        """Обработка нажатий на кнопки после завершения регистрации"""
        query = update.callback_query
        logger.info(f"post_registration_callback called: data={query.data}")

        await query.answer()

        if query.data == "add_location":
            await query.edit_message_text(
                "➕ Для добавления новой точки начните регистрацию заново с /start\n"
                "В будущем будет добавлена функция добавления точек для существующих пользователей."
            )

    async def help_command(self, update: Update, context):
        """Обработчик команды /help"""
        help_text = (
            "🤖 *Справка по боту*\n\n"
            "Доступные команды:\n"
            "/start - Начать регистрацию или продолжить работу\n"
            "/profile - Посмотреть вашу информацию\n"
            "/help - Показать эту справку\n\n"
            "Бот поможет вам:\n"
            "• Зарегистрироваться как поставщик\n"
            "• Добавить несколько точек продаж\n"
            "• Создать визитку для ваших клиентов\n\n"
            "По всем вопросам пишите администратору."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def profile_command(self, update: Update, context):
        """Показать профиль пользователя"""
        try:
            # Проверяем, что update.message не равен None
            if not update.message:
                logger.error("Error in profile_command: update.message is None")
                return

            user = update.effective_user
            telegram_user_id = user.id

            supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

            if supplier:
                # Ищем все локации для этого telegram_user_id (включая от старых регистраций)
                all_locations = []
                telegram_user_id = supplier['telegram_user_id']

                # Сначала получаем все supplier_id для этого пользователя (используем кеш)
                all_suppliers = self.sheets_manager.get_all_suppliers()
                user_supplier_ids = []

                for supp_record in all_suppliers:
                    user_id_field = supp_record.get("telegram_user_id")
                    if user_id_field == telegram_user_id or str(user_id_field) == str(telegram_user_id):
                        user_supplier_ids.append(supp_record.get("internal_id"))

                # Теперь получаем все локации для всех supplier_id этого пользователя
                for supp_id in user_supplier_ids:
                    locations = self.sheets_manager.get_locations_by_supplier_id(supp_id)
                    all_locations.extend(locations)

                locations = all_locations

                # Экранируем специальные символы Markdown
                contact_name = str(supplier['contact_name']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                telegram_username = str(supplier['telegram_username']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                internal_id = str(supplier['internal_id'])

                profile_text = (
                    f"📋 *ВАШ ПРОФИЛЬ*\n\n"
                    f"👤 Имя: {contact_name}\n"
                    f"📱 Telegram: @{telegram_username}\n"
                    f"🆔 ID: {internal_id}\n\n"
                    f"🏪 *ВАШИ ТОЧКИ ПРОДАЖИ:*\n"
                )

                # Добавляем кнопки для каждой локации
                keyboard = []

                for i, location in enumerate(locations, 1):
                    # Экранируем специальные символы в данных локации
                    market_name = str(location['market_name']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    pavilion_number = str(location['pavilion_number']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    contact_phones = str(location['contact_phones']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

                    profile_text += (
                        f"\n*Точка {i}:*\n"
                        f"🏬 Рынок: {market_name}\n"
                        f"🏢 Павильон: {pavilion_number}\n"
                        f"📞 Телефоны: {contact_phones}\n"
                    )

                    # Добавляем кнопки управления для каждой локации
                    location_buttons = [
                        InlineKeyboardButton(f"✏️ Редактировать {i}", callback_data=f"edit_location_{location['location_id']}"),
                        InlineKeyboardButton(f"🗑️ Удалить {i}", callback_data=f"delete_location_{location['location_id']}")
                    ]
                    keyboard.append(location_buttons)

                # Добавляем общие кнопки управления
                keyboard.extend([
                    [InlineKeyboardButton("📺 МОИ КАНАЛЫ", callback_data="channels")],
                    [InlineKeyboardButton("➕ ДОБАВИТЬ НОВУЮ ТОЧКУ", callback_data="add_location")],
                    [InlineKeyboardButton("📸", callback_data="photo_recognition")],
                    [InlineKeyboardButton("📦", callback_data="my_products")]
                ])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(profile_text, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text(
                    "Вы еще не зарегистрированы. Используйте /start для регистрации."
                )

        except Exception as e:
            logger.error(f"Error in profile_command: {e}")
            if update.message:
                await update.message.reply_text("Произошла ошибка при загрузке профиля. Попробуйте позже.")

    async def edit_location_callback(self, update: Update, context):
        """Обработка редактирования локации"""
        query = update.callback_query
        location_id = query.data.replace('edit_location_', '')

        # Получаем информацию о локации
        user = update.effective_user
        telegram_user_id = user.id

        supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)
        if not supplier:
            await query.edit_message_text("❌ Ошибка: поставщик не найден")
            return

        # Находим все локации пользователя (используем кеш)
        all_locations = []
        all_suppliers = self.sheets_manager.get_all_suppliers()
        user_supplier_ids = []

        for supp_record in all_suppliers:
            user_id_field = supp_record.get("telegram_user_id")
            if user_id_field == telegram_user_id or str(user_id_field) == str(telegram_user_id):
                user_supplier_ids.append(supp_record.get("internal_id"))

        for supp_id in user_supplier_ids:
            locations = self.sheets_manager.get_locations_by_supplier_id(supp_id)
            all_locations.extend(locations)

        # Ищем нужную локацию
        target_location = None
        for location in all_locations:
            if location.get("location_id") == location_id:
                target_location = location
                break

        if not target_location:
            await query.edit_message_text("❌ Локация не найдена")
            return

        # Сохраняем в контекст для редактирования
        context.user_data['edit_location_id'] = location_id
        context.user_data['edit_current_market'] = target_location.get('market_name')
        context.user_data['edit_current_pavilion'] = target_location.get('pavilion_number')
        context.user_data['edit_current_phones'] = target_location.get('contact_phones')

        # Предлагаем меню редактирования
        keyboard = [
            [InlineKeyboardButton("🏬 Изменить рынок", callback_data="edit_market_name")],
            [InlineKeyboardButton("🏢 Изменить павильон", callback_data="edit_pavilion_number")],
            [InlineKeyboardButton("📞 Управлять телефонами", callback_data="manage_phones")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        edit_text = (
            f"✏️ *РЕДАКТИРОВАНИЕ ТОЧКИ*\n\n"
            f"🏬 Рынок: {target_location.get('market_name')}\n"
            f"🏢 Павильон: {target_location.get('pavilion_number')}\n"
            f"📞 Телефоны: {target_location.get('contact_phones')}\n\n"
            f"Что хотите изменить?"
        )

        await query.edit_message_text(edit_text, parse_mode='Markdown', reply_markup=reply_markup)

    async def delete_location_callback(self, update: Update, context):
        """Обработка удаления локации"""
        query = update.callback_query
        location_id = query.data.replace('delete_location_', '')

        # Запрашиваем подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_location_{location_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚠️ *УДАЛЕНИЕ ТОЧКИ*\n\n"
            "Вы уверены, что хотите удалить эту торговую точку?\n\n"
            "Это действие нельзя будет отменить!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cancel(self, update: Update, context):
        """Отмена операции"""
        context.user_data.clear()
        await update.message.reply_text(
            "Операция отменена. Используйте /start для начала.",
            reply_markup=ReplyKeyboardRemove()
        )

    async def skip_command(self, update: Update, context):
        """Пропуск текущего шага"""
        state = context.user_data.get('state')

        if state == 'ADD_CHANNEL_DESCRIPTION':
            # Пропускаем описание канала
            if update.callback_query:
                # Если вызван из callback
                await self.save_channel(update, context, description="", is_callback=True)
            else:
                # Если вызвано командой /skip
                await self.save_channel(update, context, description="", is_callback=False)
        elif state == 'EDIT_CHANNEL_DESCRIPTION':
            # Пропускаем изменение описания
            channel_id = context.user_data.get('editing_channel_id')
            if channel_id:
                # Сохраняем пустое описание
                success = self.sheets_manager.update_channel(
                    channel_id=channel_id,
                    description=""
                )

                if success:
                    await update.message.reply_text(
                        "✅ Описание оставлено пустым!",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при обновлении канала")

                # Очищаем состояние
                context.user_data.clear()

                # Показываем обновленный список каналов
                await self.show_channels_after_action(update, context)
            else:
                await update.message.reply_text("❌ Ошибка: ID канала не найден")
        else:
            await update.message.reply_text(
                "На данном шаге пропуск недоступен. Используйте /cancel для отмены операции."
            )

    async def confirm_delete_callback(self, update: Update, context):
        """Подтверждение удаления локации"""
        query = update.callback_query
        location_id = query.data.replace('confirm_delete_', '')

        try:
            if self.sheets_manager.delete_location(location_id):
                await query.edit_message_text(
                    "✅ *Локация успешно удалена!*\n\n"
                    "Используйте /profile для просмотра обновленного списка.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Ошибка при удалении локации")
        except Exception as e:
            logger.error(f"Error deleting location: {e}")
            await query.edit_message_text("❌ Произошла ошибка при удалении локации")

    async def cancel_action_callback(self, update: Update, context):
        """Отмена действия"""
        query = update.callback_query
        await query.edit_message_text("❌ Действие отменено")

    async def handle_edit_options(self, update: Update, context):
        """Обработка опций редактирования"""
        query = update.callback_query

        if query.data == 'edit_market_name':
            context.user_data['edit_state'] = 'market_name'
            await query.edit_message_text(
                "🏬 *ИЗМЕНЕНИЕ РЫНКА*\n\n"
                f"Текущее значение: {context.user_data.get('edit_current_market', 'не указано')}\n\n"
                "Введите новое название рынка:",
                parse_mode='Markdown'
            )
        elif query.data == 'edit_pavilion_number':
            context.user_data['edit_state'] = 'pavilion_number'
            await query.edit_message_text(
                "🏢 *ИЗМЕНЕНИЕ ПАВИЛЬЬОНА*\n\n"
                f"Текущее значение: {context.user_data.get('edit_current_pavilion', 'не указан')}\n\n"
                "Введите новый номер павильона:",
                parse_mode='Markdown'
            )
        elif query.data == 'manage_phones':
            phones = context.user_data.get('edit_current_phones', '')

            # Преобразуем в строку для поддержки разных типов данных
            if phones is None:
                phones = ''
            elif isinstance(phones, (int, float)):
                phones = str(phones)
            else:
                phones = str(phones)

            phones_list = [phone.strip() for phone in phones.split(',') if phone.strip()]

            keyboard = []
            for i, phone in enumerate(phones_list):
                keyboard.append([
                    InlineKeyboardButton(f"✏️ {phone}", callback_data=f"edit_phone_{i}"),
                    InlineKeyboardButton(f"🗑️ Удалить {i+1}", callback_data=f"delete_phone_{i}")
                ])

            keyboard.append([
                InlineKeyboardButton("➕ Добавить телефон", callback_data="add_phone_to_location"),
                InlineKeyboardButton("✅ Готово", callback_data="finish_phones_edit")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            text = (
                f"📞 *УПРАВЛЕНИЕ ТЕЛЕФОНАМИ*\n\n"
                f"Текущие телефоны: {', '.join(phones_list) if phones_list else 'нет'}\n\n"
                "Выберите действие:"
            )

            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_phone_management(self, update: Update, context):
        """Управление телефонами локации"""
        query = update.callback_query

        if query.data.startswith('edit_phone_'):
            phone_index = int(query.data.replace('edit_phone_', ''))
            phones = context.user_data.get('edit_current_phones', '')

            # Преобразуем в строку для поддержки разных типов данных
            if phones is None:
                phones = ''
            elif isinstance(phones, (int, float)):
                phones = str(phones)
            else:
                phones = str(phones)

            phones_list = [phone.strip() for phone in phones.split(',') if phone.strip()]

            if phone_index < len(phones_list):
                old_phone = phones_list[phone_index]
                context.user_data['edit_phone_index'] = phone_index
                context.user_data['edit_state'] = 'editing_phone'
                await query.edit_message_text(
                    f"📞 *РЕДАКТИРОВАНИЕ ТЕЛЕФОНА*\n\n"
                    f"Текущий: {old_phone}\n\n"
                    "Введите новый телефон:",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Ошибка: телефон не найден")

        elif query.data.startswith('delete_phone_'):
            phone_index = int(query.data.replace('delete_phone_', ''))
            phones = context.user_data.get('edit_current_phones', '')
            phones_list = [phone.strip() for phone in phones.split(',') if phone.strip()]

            if phone_index < len(phones_list):
                phones_list.pop(phone_index)
                context.user_data['edit_current_phones'] = ', '.join(phones_list)

                # Обновляем меню телефонов
                keyboard = []
                for i, phone in enumerate(phones_list):
                    keyboard.append([
                        InlineKeyboardButton(f"✏️ {phone}", callback_data=f"edit_phone_{i}"),
                        InlineKeyboardButton(f"🗑️ Удалить {i+1}", callback_data=f"delete_phone_{i}")
                    ])

                if phones_list:
                    keyboard.append([
                        InlineKeyboardButton("➕ Добавить телефон", callback_data="add_phone_to_location"),
                        InlineKeyboardButton("✅ Готово", callback_data="finish_phones_edit")
                    ])
                else:
                    keyboard.append([InlineKeyboardButton("➕ Добавить телефон", callback_data="add_phone_to_location")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    f"📞 *УПРАВЛЕНИЕ ТЕЛЕФОНАМИ*\n\n"
                    f"Телефон удален. Осталось: {len(phones_list)}\n"
                    "Выберите действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

        elif query.data == 'add_phone_to_location':
            context.user_data['edit_state'] = 'adding_phone'
            await query.edit_message_text(
                "📞 *ДОБАВЛЕНИЕ ТЕЛЕФОНА*\n\n"
                "Введите новый телефон:",
                parse_mode='Markdown'
            )

        elif query.data == 'finish_phones_edit':
            await self.save_location_edits(update, context)

    async def handle_phone_edit(self, update: Update, context):
        """Обработка редактирования телефона"""
        new_phone = update.message.text.strip()
        phone_index = context.user_data.get('edit_phone_index')
        phones = context.user_data.get('edit_current_phones', '')

        # Преобразуем в строку для поддержки разных типов данных
        if phones is None:
            phones = ''
        elif isinstance(phones, (int, float)):
            phones = str(phones)
        else:
            phones = str(phones)

        phones_list = [phone.strip() for phone in phones.split(',') if phone.strip()]

        if phone_index is not None and phone_index < len(phones_list):
            phones_list[phone_index] = new_phone
            context.user_data['edit_current_phones'] = ', '.join(phones_list)

            await update.message.reply_text(
                f"✅ Телефон изменен на: {new_phone}\n\n"
                "Используйте /profile для просмотра обновленных данных."
            )

            # Сохраняем изменения
            await self.save_location_edits(update, context)

    async def handle_add_phone(self, update: Update, context):
        """Обработка добавления телефона"""
        new_phone = update.message.text.strip()
        phones = context.user_data.get('edit_current_phones', '')

        # Преобразуем в строку для поддержки разных типов данных
        if phones is None:
            phones = ''
        elif isinstance(phones, (int, float)):
            phones = str(phones)
        else:
            phones = str(phones)

        phones_list = [phone.strip() for phone in phones.split(',') if phone.strip()]

        if phones_list:
            phones_list.append(new_phone)
        else:
            phones_list = [new_phone]

        context.user_data['edit_current_phones'] = ', '.join(phones_list)

        await update.message.reply_text(
            f"✅ Телефон добавлен: {new_phone}\n\n"
            f"Всего телефонов: {len(phones_list)}\n"
            "Используйте /profile для просмотра обновленных данных."
        )

        # Сохраняем изменения
        await self.save_location_edits(update, context)

    async def save_location_edits(self, update: Update, context):
        """Сохранение изменений локации"""
        try:
            location_id = context.user_data.get('edit_location_id')
            market_name = context.user_data.get('edit_current_market')
            pavilion_number = context.user_data.get('edit_current_pavilion')
            contact_phones = context.user_data.get('edit_current_phones')

            if not location_id:
                await update.message.reply_text("❌ Ошибка: данные не найдены")
                return

            # Обновляем локацию
            success = self.sheets_manager.update_location(
                location_id=location_id,
                market_name=market_name,
                pavilion_number=pavilion_number,
                contact_phones=contact_phones
            )

            if success:
                await update.message.reply_text(
                    "✅ *Изменения сохранены!*\n\n"
                    "Используйте /profile для просмотра обновленных данных.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Ошибка при сохранении изменений")

        except Exception as e:
            logger.error(f"Error saving location edits: {e}")
            await update.message.reply_text("❌ Произошла ошибка при сохранении изменений")

        # Очищаем контекст редактирования
        context.user_data.clear()

    async def handle_market_name_edit(self, update: Update, context):
        """Обработка редактирования названия рынка"""
        new_market_name = update.message.text.strip()

        # Получаем ID локации из контекста
        location_id = context.user_data.get('edit_location_id')

        if not location_id:
            await update.message.reply_text("❌ Ошибка: ID локации не найден")
            context.user_data.clear()
            return

        logger.info(f"Updating market name for location_id: {location_id} to: {new_market_name}")

        # Обновляем только название рынка, не трогая остальные данные
        success = self.sheets_manager.update_location(
            location_id=location_id,
            market_name=new_market_name  # Обновляем только рынок
        )

        if success:
            await update.message.reply_text(
                f"✅ Название рынка изменено на: {new_market_name}\n\n"
                "Используйте /profile для просмотра обновленных данных."
            )
            logger.info(f"Successfully updated market name for location {location_id}")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении изменений")
            logger.error(f"Failed to update market name for location {location_id}")

        # Очищаем только состояние редактирования, не весь контекст
        context.user_data['edit_state'] = None
        context.user_data['edit_location_id'] = None

    async def handle_pavilion_number_edit(self, update: Update, context):
        """Обработка редактирования номера павильона"""
        new_pavilion = update.message.text.strip()

        # Получаем ID локации из контекста
        location_id = context.user_data.get('edit_location_id')

        if not location_id:
            await update.message.reply_text("❌ Ошибка: ID локации не найден")
            context.user_data.clear()
            return

        logger.info(f"Updating pavilion for location_id: {location_id} to: {new_pavilion}")

        # Обновляем только павильон, не трогая остальные данные
        success = self.sheets_manager.update_location(
            location_id=location_id,
            pavilion_number=new_pavilion  # Обновляем только павильон
        )

        if success:
            await update.message.reply_text(
                f"✅ Номер павильона изменен на: {new_pavilion}\n\n"
                "Используйте /profile для просмотра обновленных данных."
            )
            logger.info(f"Successfully updated pavilion for location {location_id}")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении изменений")
            logger.error(f"Failed to update pavilion for location {location_id}")

        # Очищаем только состояние редактирования, не весь контекст
        context.user_data['edit_state'] = None
        context.user_data['edit_location_id'] = None

    async def handle_photo_message(self, update: Update, context):
        """Обработка фото сообщений"""
        try:
            state = context.user_data.get('state')

            # Обрабатываем фото только в состоянии PHOTO_UPLOAD
            if state == PHOTO_UPLOAD:
                await self.process_photo_upload(update, context)
            else:
                logger.info(f"Photo received but state is {state}, ignoring")

        except Exception as e:
            logger.error(f"Error in handle_photo_message: {e}")
            await update.message.reply_text("❌ Ошибка при обработке фото")

    async def process_photo_upload(self, update: Update, context):
        """Обработка загрузки фото"""
        try:
            # Инициализируем сервисы если необходимо
            if not self.services_initialized:
                await self.initialize_services()

            # Получаем список фото из контекста
            photos = context.user_data.get('uploaded_photos', [])

            # Проверяем лимит фото
            if len(photos) >= 10:
                await update.message.reply_text(
                    "❌ Достигнут лимит фото (максимум 10).\n"
                    "Отправьте 'Готово' для обработки или 'Отмена' для выхода."
                )
                return

            # Загружаем фото
            photo = update.message.photo[-1]  # Берем фото наивысшего качества
            file = await context.bot.get_file(photo.file_id)

            # Получаем прямой URL на файл Telegram
            bot_token = self.application.bot.token

            # Telegram API изменился - теперь file_path может возвращать полный URL
            # Нужно извлечь только относительный путь
            file_path = file.file_path

            logger.info(f"Original file_path: {file_path}")

            # Если file_path содержит полный URL, извлекаем только путь
            if file_path.startswith('http'):
                # Извлекаем путь после /file/bot{token}/
                if f'/file/bot{bot_token}/' in file_path:
                    relative_path = file_path.split(f'/file/bot{bot_token}/')[-1]

                    # Дополнительная проверка на случай дублирования URL
                    if relative_path.startswith('http'):
                        # Если остался дублирование, берем только последнюю часть пути
                        relative_path = '/'.join(relative_path.split('/')[-2:])  # photos/file_X.jpg

                    telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{relative_path}"
                else:
                    # Если формат другой, пробуем извлечь после последнего /
                    telegram_file_url = file_path
            else:
                # Если file_path только относительный путь, используем как есть
                telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

            logger.info(f"Final Telegram URL: {telegram_file_url}")

            # Скачиваем фото в память для Gemini
            photo_bytes = await file.download_as_bytearray()

            # Добавляем фото в список
            photos.append({
                'bytes': photo_bytes,
                'file_id': photo.file_id,
                'file_path': file.file_path,
                'telegram_url': telegram_file_url,
                'file_name': f"photo_{len(photos) + 1}.jpg"
            })

            context.user_data['uploaded_photos'] = photos

            # Создаем клавиатуру с кнопками
            keyboard = []

            if len(photos) > 0:
                keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="process_photos_ready")])

            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_photo_upload")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Фото {len(photos)} загружено\n"
                f"Всего загружено: {len(photos)}/10\n\n"
                "Отправьте еще фото или используйте кнопки ниже:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in process_photo_upload: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке фото")

    async def show_photo_confirmation(self, update: Update, context):
        """Показать результаты распознавания фото с поддержкой новой JSON-структуры"""
        try:
            recognition_results = context.user_data.get('recognition_results', [])

            if not recognition_results:
                await update.message.reply_text("❌ Нет результатов распознавания")
                return

            # Формируем сообщение с результатами
            message = "🖼️ *Результаты распознавания:*\n\n"

            for i, result in enumerate(recognition_results, 1):
                # Проверяем, новая ли JSON-структура или старая
                if 'название' in result and 'описание' in result:
                    # Новая JSON-структура
                    title = result.get('название', 'Неизвестный товар')
                    description = result.get('описание', 'Нет описания')

                    # Показываем улучшенное описание, если есть
                    if result.get('generated_description'):
                        description = result['generated_description']
                        message += "✨ *Улучшенное описание:*\n"

                    # Собираем дополнительную информацию
                    details = []
                    production = result.get('производство', '')
                    material = result.get('материал', '')
                    if production and production != 'Не указано':
                        details.append(f"🏭 {production}")
                    if material and material != 'Не указано':
                        details.append(f"🧪 {material}")

                    # Показываем маркетинговый текст, если есть
                    marketing_text = result.get('marketing_text', '')
                    if marketing_text:
                        details.append(f"🎯 {marketing_text}")

                    message += f"📷 *Товар {i}: {title}*\n"
                    message += f"📝 {description}\n"
                    if details:
                        message += f"🏷️ {' | '.join(details)}\n"

                    # Показываем статус улучшения изображения
                    if result.get('has_enhanced_image'):
                        message += "🖼️ *Изображение улучшено*\n"
                else:
                    # Старая структура (обратная совместимость)
                    short_desc = result.get('short_description', 'Неизвестный товар')
                    full_desc = result.get('full_description', 'Нет описания')

                    message += f"📷 *Товар {i}*\n"
                    message += f"🏷️ *Кратко:* {short_desc}\n"
                    message += f"📝 *Подробно:* {full_desc[:200]}{'...' if len(full_desc) > 200 else ''}\n"

                message += "\n"

            # Создаем клавиатуру
            keyboard = [
                [InlineKeyboardButton("✅ Верно", callback_data="confirm_photo_recognition")],
                [InlineKeyboardButton("✏️ Изменить", callback_data="edit_photo_recognition")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_photo_upload")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Определяем тип update для ответа
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in show_photo_confirmation: {e}")
            await update.message.reply_text("❌ Ошибка при показе результатов")

    async def start_photo_recognition(self, update: Update, context):
        """Начать процесс распознавания фото"""
        try:
            query = update.callback_query
            await query.answer()

            # Очищаем данные фото
            context.user_data['uploaded_photos'] = []
            context.user_data['state'] = PHOTO_UPLOAD

            # Создаем клавиатуру с кнопками
            keyboard = [
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_photo_upload")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📸 *Распознавание товаров*\n\n"
                "Пожалуйста, отправьте фотографии товаров (максимум 10 штук).\n"
                "После загрузки всех фото используйте кнопку '✅ Готово' для распознавания.\n\n"
                "Отправьте фото или используйте кнопки ниже:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in start_photo_recognition: {e}")

    async def show_my_products(self, update: Update, context):
        """Показать мои товары с фото"""
        # Инициализируем переменные перед try, чтобы они были доступны в блоке except
        user_id = None
        supplier_id = None
        products = []

        try:
            query = update.callback_query
            await query.answer()


            # Инициализируем сервисы если необходимо
            if not self.services_initialized:
                logger.info("Сервисы не инициализированы, начинаем инициализацию в show_my_products")
                await self.initialize_services()
                logger.info(f"Сервисы инициализированы. content_generation_service: {self.content_generation_service is not None}")

            user_id = query.from_user.id
            logger.info(f"show_my_products called for user_id: {user_id}")
            logger.info(f"ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")
            logger.info(f"content_generation_service available: {self.content_generation_service is not None}")

            supplier = self.sheets_manager.get_supplier_by_telegram_id(user_id)
            logger.info(f"Supplier found: {supplier is not None}")

            if not supplier:
                logger.warning(f"Supplier not found for user_id: {user_id}")
                await self.safe_edit_message_text(
                    query,
                    "❌ Вы не зарегистрированы. Используйте /start для регистрации."
                )
                return

            supplier_id = supplier['internal_id']
            logger.info(f"Supplier ID: {supplier_id}")

            # Очищаем кэш перед получением товаров, чтобы получить актуальные данные
            self.sheets_manager.invalidate_cache("products")

            products = self.sheets_manager.get_products_by_supplier_id(supplier_id)
            logger.info(f"Products returned: {products}, type: {type(products)}, length: {len(products) if products else 'N/A'}")

            if not products:
                logger.info(f"No products found for supplier {supplier_id}")
                await self.safe_edit_message_text(
                    query,
                    "Мои товары 📦\n\n"
                    "У вас пока нет сохраненных товаров.\n\n"
                    "Используйте кнопку 📸 для добавления товаров."
                )
                return

            # Сначала редактируем текущее сообщение на заголовок
            await self.safe_edit_message_text(
                query,
                f"Мои товары 📦 ({len(products)} шт.)\n\n"
                "Загружаю изображения...",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile")
                ]])
            )

            # Отправляем каждый товар отдельным сообщением с фото
            keyboard = []
            for i, product in enumerate(products, 1):
                try:
                    # Безопасное получение данных с обработкой ошибок
                    product_id = str(product.get('product_id', f'unknown_{i}'))

                    # Используем новые поля из Google Sheets
                    product_name = str(product.get('название', product.get('name', 'Без названия')))

                    # Проверяем описание и полное описание (улучшенное)
                    description_field = product.get('описание', product.get('description', ''))
                    full_description_field = product.get('full_description', '')
                    enhanced_description_field = product.get('enhanced_description', '')

                    # Приоритет: улучшенное описание AI > полное описание > базовое описание
                    if enhanced_description_field and str(enhanced_description_field).strip() and str(enhanced_description_field) != 'None':
                        description_field = str(enhanced_description_field)
                    elif full_description_field and str(full_description_field).strip() and str(full_description_field) != 'None':
                        description_field = str(full_description_field)
                    elif description_field and str(description_field).strip() and str(description_field) != 'None':
                        description_field = str(description_field)
                    else:
                        description_field = ''

                    # Если название пустое, пробуем извлечь из описания
                    if product_name == 'Без названия' or not product_name.strip():
                        product_name = self.extract_product_name(description_field)

                    # Формируем краткое описание с безопасной обработкой
                    if description_field and description_field.strip():
                        short_desc = description_field
                        # Ограничиваем длину
                        if len(short_desc) > 150:
                            short_desc = short_desc[:147] + "..."
                    else:
                        # Безопасно вызываем extract_short_description с пустой строкой
                        short_desc = self.extract_short_description('', 80)

                    # Безопасная обработка quantity
                    quantity = product.get('quantity', '0')
                    if quantity is None or quantity == '':
                        quantity_str = '0'
                    else:
                        quantity_str = str(quantity)

                    created_at = str(product.get('created_at', ''))

                    # Приоритет: улучшенное изображение > оригинальное
                    enhanced_image_url = product.get('enhanced_image_url', '')
                    photo_url = product.get('photo_urls', '')

                    # Проверяем, есть ли локальное улучшенное изображение
                    enhanced_local_path = None
                    if enhanced_image_url and str(enhanced_image_url).startswith('local:'):
                        # Извлекаем имя файла из "local:filename"
                        filename = str(enhanced_image_url).replace('local:', '')
                        enhanced_local_path = f"{LOCAL_ENHANCED_IMAGES_PATH}/{filename}"
                        # Проверяем существование файла
                        import os
                        if not os.path.exists(enhanced_local_path):
                            logger.warning(f"Enhanced image file not found: {enhanced_local_path}")
                            enhanced_local_path = None

                    # Формируем описание товара с новой структурой
                    caption = f"🏷️ {escape_markdown(product_name)}\n"

                    # Добавляем индикаторы улучшенного контента
                    has_enhanced_content = False
                    if product.get('enhanced_description') and str(product.get('enhanced_description')).strip():
                        caption += "✨ "
                        has_enhanced_content = True
                    caption += f"📝 {escape_markdown(short_desc)}\n"

                    caption += f"🆔 ID: {product_id}\n"
                    caption += f"📊 Количество: {quantity_str}\n"
                    if created_at and created_at.strip():
                        caption += f"📅 Добавлен: {created_at}\n"

                    # Показываем, если есть улучшенный контент
                    if has_enhanced_content:
                        caption += f"🎨 *Есть улучшенный контент*\n"

                    # Кнопки управления для товара
                    product_buttons = []

                    # Добавляем кнопку улучшения контента если доступна генерация
                    logger.info(f"Проверка кнопки для товара {product_id}: ENABLE_CONTENT_GENERATION={ENABLE_CONTENT_GENERATION}, content_generation_service={self.content_generation_service is not None}")
                    if ENABLE_CONTENT_GENERATION and self.content_generation_service:
                        # Проверяем, доступна ли генерация для этого товара
                        try:
                            limit_check = self.content_generation_service.usage_limits.check_daily_limit(
                                user_id, product_id, 'content_enhancement'
                            )
                            if limit_check['allowed']:
                                product_buttons.append(
                                    InlineKeyboardButton(f"✨", callback_data=f"enhance_content_{product_id}")
                                )
                            else:
                                product_buttons.append(
                                    InlineKeyboardButton(f"✨", callback_data=f"enhance_content_limit_{product_id}")
                                )
                        except Exception as e:
                            logger.warning(f"Error checking content generation limits for {product_id}: {e}")

                    # Кнопка просмотра улучшенного контента удалена

                    # Добавляем стандартные кнопки (только удалить)
                    product_buttons.append(
                        InlineKeyboardButton(f"🗑️", callback_data=f"delete_product_{product_id}")
                    )

                    try:
                        product_markup = InlineKeyboardMarkup([product_buttons])

                        # Приоритет отправки: локальное улучшенное > URL улучшенное > оригинальное
                        if enhanced_local_path:
                            # Отправляем улучшенное изображение из локального файла
                            logger.info(f"Sending enhanced image from local file for product {product_id}: {enhanced_local_path}")
                            with open(enhanced_local_path, 'rb') as photo_file:
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=photo_file,
                                    caption=caption + "\n\n✨ Улучшенное изображение",
                                    reply_markup=product_markup
                                )
                            logger.info(f"Enhanced image sent successfully for product {product_id}")

                        elif enhanced_image_url and not str(enhanced_image_url).startswith('local:'):
                            # Отправляем улучшенное изображение по URL
                            logger.info(f"Sending enhanced image from URL for product {product_id}: {enhanced_image_url}")
                            success = await self.send_photo_from_telegram_url(
                                chat_id=user_id,
                                photo_url=str(enhanced_image_url),
                                caption=caption + "\n\n✨ Улучшенное изображение",
                                reply_markup=product_markup
                            )
                            if not success:
                                # Fallback на оригинальное фото
                                logger.warning(f"Failed to send enhanced image, using original")
                                if photo_url:
                                    await self.send_photo_from_telegram_url(
                                        chat_id=user_id,
                                        photo_url=str(photo_url),
                                        caption=caption,
                                        reply_markup=product_markup
                                    )

                        elif photo_url:
                            # Отправляем оригинальное фото
                            photo_url_str = str(photo_url) if photo_url else ""
                            if photo_url_str.strip() and not photo_url_str.isdigit():
                                logger.info(f"Sending original photo for product {product_id}: {photo_url_str}")

                                success = await self.send_photo_from_telegram_url(
                                    chat_id=user_id,
                                    photo_url=photo_url_str,
                                    caption=caption,
                                    reply_markup=product_markup
                                )

                                if not success:
                                    # Если фото не отправилось, отправляем текст с ссылкой
                                    logger.warning(f"Failed to send photo for product {product_id}")
                                    caption += f"\n🖼️ Фото: {photo_url_str}"
                                    await context.bot.send_message(
                                        chat_id=user_id,
                                        text=caption,
                                        reply_markup=product_markup
                                    )
                            else:
                                # Если нет фото URL, отправляем только текст
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=caption,
                                    reply_markup=product_markup
                                )
                        else:
                            # Если нет фото вообще, отправляем только текст
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=caption,
                                reply_markup=product_markup
                            )

                    except Exception as send_error:
                        logger.error(f"Error sending product {i}: {send_error}")
                        # В случае ошибки отправляем простое текстовое сообщение
                        error_text = f"❌ Товар {i}: {short_desc}\nОшибка при отображении"
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=error_text
                        )

                except Exception as product_error:
                    logger.error(f"Error processing product {i}: {product_error}")
                    # Отправляем сообщение об ошибке для этого товара
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Товар {i}: Ошибка при обработке данных"
                    )

            # Отправляем финальное сообщение с общей статистикой
            summary_message = f"✅ Все товары загружены\n\n"
            summary_message += f"📊 Всего товаров: {len(products)}\n"
            summary_message += f"Используйте кнопки управления под каждым товаром"

            # Кнопка возврата в конце
            final_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад в профиль", callback_data="back_to_profile")
            ]])

            await context.bot.send_message(
                chat_id=user_id,
                text=summary_message,
                reply_markup=final_keyboard
            )

        except Exception as e:
            logger.error(f"Error in show_my_products: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"User ID: {user_id}")
            logger.error(f"Supplier ID: {supplier_id}")
            logger.error(f"Products count: {len(products) if products else 0}")

            try:
                if hasattr(update, 'callback_query') and update.callback_query:
                    await self.safe_edit_message_text(
                        update.callback_query,
                        "❌ Ошибка при загрузке товаров. Попробуйте еще раз позже."
                    )
                else:
                    await update.message.reply_text(
                        "❌ Ошибка при загрузке товаров. Попробуйте еще раз позже."
                    )
            except Exception as fallback_error:
                logger.error(f"Error in fallback message: {fallback_error}")

    async def confirm_photo_recognition(self, update: Update, context):
        """Подтвердить результаты распознавания"""
        try:
            query = update.callback_query
            await query.answer()

            recognition_results = context.user_data.get('recognition_results', [])
            if not recognition_results:
                await query.edit_message_text("❌ Нет результатов для сохранения")
                return

            context.user_data['state'] = LOCATION_SELECTION

            # Получаем локации пользователя

            user_id = query.from_user.id
            supplier = self.sheets_manager.get_supplier_by_telegram_id(user_id)
            if not supplier:
                await query.edit_message_text("❌ Поставщик не найден")
                return

            locations = self.sheets_manager.get_locations_by_supplier_id(supplier['internal_id'])

            if not locations:
                await query.edit_message_text(
                    "❌ У вас нет сохраненных локаций.\n"
                    "Сначала добавьте локацию через личный кабинет."
                )
                return

            # Формируем клавиатуру с локациями
            message = "📍 *Выберите локацию для товаров:*\n\n"
            keyboard = []

            for i, location in enumerate(locations, 1):
                message += f"{i}. {location['market_name']}, пав. {location['pavilion_number']}\n"
                keyboard.append([InlineKeyboardButton(
                    f"📍 {i}. {location['market_name']}",
                    callback_data=f"select_location_for_product_{location['location_id']}"
                )])

            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_photo_upload")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in confirm_photo_recognition: {e}")

    async def edit_photo_recognition(self, update: Update, context):
        """Редактировать результаты распознавания"""
        try:
            query = update.callback_query
            await query.answer()

            # Возвращаем к загрузке фото
            context.user_data['state'] = PHOTO_UPLOAD
            context.user_data['uploaded_photos'] = []
            context.user_data['recognition_results'] = []

            await query.edit_message_text(
                "✏️ *Редактирование фото*\n\n"
                "Отправьте новые фото товаров (максимум 10 штук).\n"
                "После загрузки всех фото напишите 'Готово' для распознавания.",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in edit_photo_recognition: {e}")

    async def back_to_photo_upload(self, update: Update, context):
        """Вернуться к загрузке фото"""
        try:
            query = update.callback_query
            await query.answer()

            context.user_data['state'] = PHOTO_UPLOAD

            # Очищаем результаты распознавания, но сохраняем загруженные фото
            uploaded_photos = context.user_data.get('uploaded_photos', [])

            if uploaded_photos:
                message = (
                    f"📸 *Загрузка фото*\n\n"
                    f"Загружено фото: {len(uploaded_photos)}/10\n\n"
                    f"Отправьте еще фото или напишите 'Готово' для распознавания:"
                )
            else:
                message = (
                    "📸 *Загрузка фото*\n\n"
                    "Пожалуйста, отправьте фотографии товаров (максимум 10 штук).\n"
                    "После загрузки всех фото напишите 'Готово' для распознавания:"
                )

            await query.edit_message_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in back_to_photo_upload: {e}")

    async def select_location_for_product(self, update: Update, context):
        """Выбрать локацию для товара"""
        try:
            query = update.callback_query
            await query.answer()

            location_id = query.data.replace('select_location_for_product_', '')
            context.user_data['selected_location_id'] = location_id
            context.user_data['state'] = QUANTITY_INPUT

            await query.edit_message_text(
                "📊 *Введите количество для каждого товара:*\n\n"
                "Напишите количество через запятую для каждого товара.\n"
                "Пример: 5, 10, 3\n\n"
                "Либо напишите 'Пропустить' чтобы использовать количество 1 для всех товаров:",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in select_location_for_product: {e}")

    async def edit_product(self, update: Update, context):
        """Редактировать товар с отображением фото"""
        try:
            query = update.callback_query
            await query.answer()

            product_id = query.data.replace('edit_product_', '')


            product = self.sheets_manager.get_product_by_id(product_id)
            if not product:
                await query.edit_message_text("❌ Товар не найден")
                return

            user_id = query.from_user.id

            # Извлекаем реальное название и краткое описание
            description = str(product.get('description', ''))
            product_name = self.extract_product_name(description)
            short_desc = self.extract_short_description(description, 120)

            # Формируем описание товара с новой структурой
            caption = f"📦 Информация о товаре\n\n"
            caption += f"🏷️ {product_name}\n"
            caption += f"📝 {escape_markdown(short_desc)}\n"
            caption += f"🆔 ID: {product_id}\n"
            caption += f"📊 Количество: {product.get('quantity', 'Не указано')}\n"

            created_at = product.get('created_at', '')
            if created_at and created_at.strip():
                caption += f"📅 Добавлен: {created_at}\n"

            caption += f"\n\n🚧 ВНИМАНИЕ: Функция редактирования товара сейчас находится в разработке.\n"
            caption += f"📝 Вы можете только просматривать информацию о товаре.\n"
            caption += f"💡 Для изменения товара удалите его и добавьте заново."

            # Кнопка возврата
            keyboard = [[InlineKeyboardButton("⬅️", callback_data="my_products")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Проверяем наличие фото
            photo_url = product.get('photo_urls', '')

            if photo_url:
                photo_url_str = str(photo_url) if photo_url else ""
                if photo_url_str.strip() and not photo_url_str.isdigit():
                    logger.info(f"Sending photo for edit product {product_id}: {photo_url_str}")

                    # Сначала редактируем текущее сообщение на "Загружаю..."
                    await query.edit_message_text(
                        "📦 Информация о товаре\n\nЗагружаю изображение...",
                        reply_markup=reply_markup
                    )

                    # Отправляем новое сообщение с фото через нашу функцию
                    success = await self.send_photo_from_telegram_url(
                        chat_id=user_id,
                        photo_url=photo_url_str,
                        caption=caption,
                        reply_markup=reply_markup
                    )

                    if success:
                        logger.info(f"Photo sent successfully for edit product {product_id}")
                    else:
                        # Если фото не отправилось, отправляем текст со ссылкой
                        logger.warning(f"Failed to send photo for edit product {product_id}")
                        caption += f"\n🖼️ Фото: {photo_url_str}"
                        await query.edit_message_text(
                            caption,
                            reply_markup=reply_markup
                        )
                else:
                    # Если нет фото URL, отправляем только текст
                    await query.edit_message_text(
                        caption,
                        reply_markup=reply_markup
                    )
            else:
                # Если нет фото, отправляем только текст
                await query.edit_message_text(
                    caption,
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"Error in edit_product: {e}")
            try:
                query = update.callback_query
                await self.safe_edit_message_text(
                    query,
                    "❌ Произошла ошибка при загрузке информации о товаре. Попробуйте позже."
                )
            except Exception as e2:
                logger.error(f"Failed to show error message: {e2}")
                try:
                    await query.message.reply_text("❌ Произошла ошибка при загрузке информации о товаре. Попробуйте позже.")
                except Exception as e3:
                    logger.error(f"Failed to send error message: {e3}")

    async def delete_product(self, update: Update, context):
        """Удалить товар"""
        try:
            query = update.callback_query
            await query.answer()

            product_id = query.data.replace('delete_product_', '')


            success = self.sheets_manager.delete_product(product_id)

            if success:
                await self.safe_edit_message_text(
                    query,
                    "✅ Товар успешно удален.\n\n"
                    "Используйте /profile для просмотра обновленного списка.",
                    parse_mode='Markdown'
                )
            else:
                await self.safe_edit_message_text(query, "❌ Не удалось удалить товар")

        except Exception as e:
            logger.error(f"Error in delete_product: {e}")
            try:
                # Если не удалось отредактировать сообщение, отправляем новое
                await query.message.reply_text(
                    "❌ Произошла ошибка при удалении товара. Попробуйте позже."
                )
            except Exception as e2:
                logger.error(f"Failed to send error message: {e2}")

    async def handle_photo_upload_text(self, update: Update, context):
        """Обработка текстовых сообщений при загрузке фото"""
        message_text = update.message.text.strip().lower()

        if message_text == 'готово':
            await self.process_photo_recognition(update, context)
        elif message_text == 'отмена':
            await self.cancel_photo_recognition(update, context)
        else:
            await update.message.reply_text(
                "Отправьте фото или напишите 'Готово' для распознавания, 'Отмена' для выхода"
            )

    async def process_photo_recognition(self, update: Update, context):
        """Обработать загруженные фото через распознавание"""
        try:
            uploaded_photos = context.user_data.get('uploaded_photos', [])

            if not uploaded_photos:
                # Определяем тип update для ответа
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text("❌ Нет загруженных фото")
                else:
                    await update.message.reply_text("❌ Нет загруженных фото")
                return

            # Определяем тип update для ответа
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text("🔄 Начинаю распознавание товаров...")
            else:
                await update.message.reply_text("🔄 Начинаю распознавание товаров...")

            # Инициализируем сервисы если необходимо
            if not self.services_initialized:
                await self.initialize_services()

            # Распознаем фото
            recognition_results = []
            photo_bytes_list = [photo['bytes'] for photo in uploaded_photos]

            if self.gemini_service:
                try:
                    recognition_results = await self.gemini_service.recognize_multiple_products(photo_bytes_list)

                    # Улучшаем контент сразу после распознавания
                    if ENABLE_CONTENT_GENERATION and self.content_generation_service:
                        # Определяем тип update для ответа
                        if hasattr(update, 'callback_query') and update.callback_query:
                            await update.callback_query.edit_message_text("🔄 Распознавание завершено. Улучшаю контент...")
                        else:
                            await update.message.reply_text("🔄 Распознавание завершено. Улучшаю контент...")

                        # Улучшаем каждый распознанный товар
                        for i, result in enumerate(recognition_results):
                            try:
                                user_id = update.effective_user.id
                                product_id = str(uuid.uuid4())  # Временный ID для товара

                                # Проверяем лимиты
                                limit_check = self.content_generation_service.usage_limits.check_daily_limit(
                                    user_id, product_id, 'content_enhancement'
                                )

                                if limit_check['allowed']:
                                    # Запускаем улучшение контента
                                    enhanced_result = await self.content_generation_service.enhance_product_content(
                                        product_info=result,
                                        product_image_bytes=photo_bytes_list[i],
                                        generate_image=True,
                                        generate_description=True,
                                        generate_marketing=True
                                    )

                                    # Обновляем результат улучшенными данными
                                    recognition_results[i] = enhanced_result

                                    # Если есть улучшенное изображение, сохраняем его временно
                                    if enhanced_result.get('enhanced_image_bytes'):
                                        recognition_results[i]['enhanced_image_bytes'] = enhanced_result['enhanced_image_bytes']
                                        recognition_results[i]['has_enhanced_image'] = True

                                    if enhanced_result.get('generated_description'):
                                        recognition_results[i]['has_enhanced_description'] = True

                                    if enhanced_result.get('marketing_text'):
                                        recognition_results[i]['has_marketing_text'] = True

                                else:
                                    logger.info(f"Content generation limit reached for photo {i+1}")

                            except Exception as e:
                                logger.error(f"Error enhancing content for photo {i+1}: {e}")
                                # Продолжаем с оригинальным результатом

                except Exception as e:
                    logger.error(f"Error in gemini service: {e}")
                    # Fallback - улучшенные заглушки с подсказками
                    product_templates = [
                        "Одежда: Футболка, джинсы, куртка и т.д.",
                        "Обувь: Кроссовки, ботинки, сандалии и т.д.",
                        "Электроника: Телефоны, наушники, аксессуары и т.д.",
                        "Продукты: Косметика, парфюмерия, уход и т.д.",
                        "Аксессуары: Сумки, кошельки, ремни и т.д.",
                        "Для дома: Посуда, декор, текстиль и т.д."
                    ]

                    for i, photo in enumerate(uploaded_photos):
                        template = product_templates[i % len(product_templates)]
                        recognition_results.append({
                            'short_description': f'Товар {i + 1}',
                            'full_description': f'Фото {i + 1}: {template}\n\n💡 *Подсказка*: Опишите товар подробно - бренд, материал, размер, цвет, состояние.'
                        })
            else:
                # Fallback - используем заглушки
                for i, photo in enumerate(uploaded_photos):
                    recognition_results.append({
                        'short_description': f'Товар {i + 1}',
                        'full_description': 'Распознавание временно недоступно. Введите описание вручную.\n\nПричина: Gemini API заблокирован в вашем регионе. Попробуйте использовать VPN или другой сервис распознавания.'
                    })

            context.user_data['recognition_results'] = recognition_results
            context.user_data['state'] = PHOTO_CONFIRMATION

            # Показываем результаты
            await self.show_photo_confirmation(update, context)

        except Exception as e:
            logger.error(f"Error in process_photo_recognition: {e}")
            await update.message.reply_text("❌ Ошибка при распознавании. Попробуйте позже.")

    async def back_to_profile(self, update: Update, context):
        """Вернуться в профиль из callback"""
        try:

            query = update.callback_query
            user = query.from_user
            telegram_user_id = user.id

            supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

            if supplier:
                # Формируем сообщение профиля
                contact_name = str(supplier.get('contact_name', 'Не указано')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                market_name = str(supplier.get('market_name', 'Не указано')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                telegram_username = str(supplier.get('telegram_username', user.username or 'Нет username')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

                # Получаем количество товаров
                supplier_id = supplier['internal_id']
                products = self.sheets_manager.get_products_by_supplier_id(supplier_id)
                product_count = len(products) if products else 0

                message = f"👤 *Личный кабинет поставщика*\n\n"
                message += f"📛 *Имя:* {contact_name}\n"
                message += f"🏪 *Рынок:* {market_name}\n"
                message += f"📱 *Telegram:* @{telegram_username}\n"
                message += f"🆔 *ID:* {telegram_user_id}\n"
                message += f"📦 *Товаров:* {product_count} шт.\n\n"

                # Получаем все локации поставщика
                locations = self.sheets_manager.get_locations_by_supplier_id(supplier_id)
                if locations:
                    message += "📍 *Ваши локации:*\n"
                    for i, loc in enumerate(locations[:3], 1):
                        market = str(loc.get('market_name', 'Неизвестный рынок')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                        pavilion = str(loc.get('pavilion_number', 'Без номера')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                        phones = str(loc.get('contact_phones', '')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                        message += f"  {i}. {market}, пав. {pavilion}"
                        if phones:
                            message += f" 📞 {phones}"
                        message += "\n"
                    if len(locations) > 3:
                        message += f"  ... и еще {len(locations) - 3} локаций\n"

                # Создаем клавиатуру с кнопками управления
                keyboard = [
                    [InlineKeyboardButton("📦", callback_data="my_products")],
                    [InlineKeyboardButton("📍", callback_data="my_locations")],
                    [InlineKeyboardButton("📸", callback_data="photo_recognition")]
                ]

                # Добавляем кнопку регистрации если товаров еще нет
                if product_count == 0:
                    keyboard.insert(1, [InlineKeyboardButton("➕", callback_data="photo_recognition")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

            else:
                await query.edit_message_text(
                    "❌ Профиль не найден. Используйте /start для регистрации."
                )

        except Exception as e:
            logger.error(f"Error in back_to_profile: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Fallback сообщение
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке профиля. Попробуйте команду /profile"
            )

    async def cancel_photo_recognition(self, update: Update, context):
        """Отменить распознавание фото"""
        try:
            context.user_data.clear()
            context.user_data['state'] = None

            await update.message.reply_text(
                "❌ Распознавание отменено.\n"
                "Используйте /profile для возврата в личный кабинет."
            )

        except Exception as e:
            logger.error(f"Error in cancel_photo_recognition: {e}")

    async def handle_quantity_input(self, update: Update, context):
        """Обработка ввода количества товаров"""
        try:
            message_text = update.message.text.strip()
            recognition_results = context.user_data.get('recognition_results', [])
            selected_location_id = context.user_data.get('selected_location_id')

            if not recognition_results or not selected_location_id:
                await update.message.reply_text("❌ Ошибка: отсутствуют данные для сохранения")
                return

            # Парсим количества
            quantities = []
            if message_text.lower() == 'пропустить':
                quantities = [1] * len(recognition_results)
            else:
                try:
                    quantities = [int(q.strip()) for q in message_text.split(',')]
                    if len(quantities) != len(recognition_results):
                        # Если количество не совпадает, добавляем или усекаем
                        while len(quantities) < len(recognition_results):
                            quantities.append(1)
                        quantities = quantities[:len(recognition_results)]
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат. Введите количества через запятую или 'Пропустить'"
                    )
                    return

            # Сохраняем товары в базу данных
            await self.save_products(update, context, quantities)

        except Exception as e:
            logger.error(f"Error in handle_quantity_input: {e}")
            await update.message.reply_text("❌ Ошибка при сохранении товаров")

    async def save_products(self, update: Update, context, quantities):
        """Сохранить товары в базу данных с новой JSON-структурой"""
        try:

            # Инициализируем сервисы если необходимо
            if not self.services_initialized:
                await self.initialize_services()

            user_id = update.effective_user.id
            supplier = self.sheets_manager.get_supplier_by_telegram_id(user_id)
            if not supplier:
                await update.message.reply_text("❌ Поставщик не найден")
                return

            recognition_results = context.user_data.get('recognition_results', [])
            selected_location_id = context.user_data.get('selected_location_id')
            uploaded_photos = context.user_data.get('uploaded_photos', [])

            saved_products = 0
            saved_product_data = []  # Сохраняем полные данные товаров для автоматической генерации

            for i, (result, quantity) in enumerate(zip(recognition_results, quantities)):
                product_id = str(uuid.uuid4())

                # Добавляем количество в данные товара
                product_data = result.copy()
                product_data['quantity'] = quantity

                # Используем прямой URL из Telegram
                image_urls = ""
                image_bytes = None
                try:
                    if i < len(uploaded_photos):
                        photo_data = uploaded_photos[i]
                        telegram_url = photo_data.get('telegram_url', '')
                        if telegram_url:
                            image_urls = telegram_url
                            logger.info(f"Using Telegram URL for product {product_id}: {telegram_url}")
                        # Сохраняем image_bytes для автоматической генерации
                        image_bytes = photo_data.get('bytes')
                except Exception as e:
                    logger.warning(f"Failed to get Telegram URL for image: {e}")

                # Если есть улучшенное изображение в recognition_results, сохраняем его
                enhanced_image_url = None
                if result.get('enhanced_image_bytes') and self.image_storage_service:
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"enhanced_{product_id}_{timestamp}.jpg"

                        # Загружаем в Google Drive
                        enhanced_image_url = await self.image_storage_service.upload_image(
                            image_bytes=result['enhanced_image_bytes'],
                            filename=filename,
                            product_id=product_id
                        )

                        if enhanced_image_url:
                            logger.info(f"✅ Enhanced image uploaded to Drive: {enhanced_image_url[:60]}...")
                        else:
                            logger.error("Failed to upload enhanced image to Drive")

                    except Exception as e:
                        logger.error(f"Error uploading enhanced image: {e}")

                # Обновляем product_data с улучшенным контентом
                if enhanced_image_url:
                    product_data['enhanced_image_url'] = enhanced_image_url
                if result.get('generated_description'):
                    product_data['enhanced_description'] = result['generated_description']
                if result.get('marketing_text'):
                    product_data['marketing_text'] = result['marketing_text']

                # Сохраняем в Google Sheets с новой структурой
                success = self.sheets_manager.add_product(
                    product_id=product_id,
                    supplier_internal_id=supplier['internal_id'],
                    location_id=selected_location_id,
                    product_data=product_data,
                    image_urls=image_urls
                )

                # Если есть улучшенный контент, обновляем запись в Sheets
                if success and (enhanced_image_url or result.get('generated_description') or result.get('marketing_text')):
                    try:
                        self.sheets_manager.update_product_enhanced_content(
                            product_id=product_id,
                            enhanced_image_url=enhanced_image_url,
                            enhanced_description=result.get('generated_description'),
                            marketing_text=result.get('marketing_text'),
                            content_generated_at=datetime.now().isoformat()
                        )
                        logger.info(f"✅ Sheets updated with enhanced content for product {product_id}")
                    except Exception as e:
                        logger.error(f"Error updating enhanced content in sheets: {e}")

                if success:
                    saved_products += 1
                    # Сохраняем полные данные товара для автоматической генерации (только если еще не было улучшения)
                    if not result.get('has_enhanced_image') and not result.get('has_enhanced_description'):
                        saved_product_data.append({
                            'product_id': product_id,
                            'product_info': product_data,
                            'photo_urls': image_urls,
                            'image_bytes': image_bytes
                        })

            # Очищаем контекст
            context.user_data.clear()
            context.user_data['state'] = None

            await update.message.reply_text(
                f"✅ Успешно сохранено {saved_products} товаров!\n\n"
                f"Используйте /profile для просмотра всех товаров."
            )

            # Запускаем автоматическую генерацию контента
            if saved_products > 0 and saved_product_data:
                await self.auto_generate_content_for_products(update, context, saved_product_data)

        except Exception as e:
            logger.error(f"Error in save_products: {e}")
            await update.message.reply_text("❌ Ошибка при сохранении товаров")

    async def auto_generate_content_for_products(self, update: Update, context, products_data: list):
        """Автоматически генерирует контент для сохраненных товаров

        Args:
            products_data: Список словарей с ключами:
                - product_id: ID товара
                - product_info: Данные товара
                - photo_urls: URL фото
                - image_bytes: Байты изображения
        """
        if not ENABLE_CONTENT_GENERATION or not AUTO_GENERATE_CONTENT:
            return

        if not self.content_generation_service:
            logger.warning("Сервис генерации контента не доступен")
            return

        try:
            user_id = update.effective_user.id
            logger.info(f"Starting automatic content generation for {len(products_data)} products")

            # Показываем сообщение о начале генерации
            status_message = await update.message.reply_text(
                "🔄 *Автоматическая генерация контента...*\n\n"
                "Для ваших товаров создаются профессиональные изображения и B2B описания.\n"
                "Это может занять некоторое время.",
                parse_mode='Markdown'
            )

            enhanced_products = []
            failed_products = []

            for i, product_data_item in enumerate(products_data):
                try:
                    product_id = product_data_item['product_id']
                    product = product_data_item['product_info']
                    image_bytes = product_data_item.get('image_bytes')

                    logger.info(f"Processing product {i+1}/{len(products_data)}: {product_id}")

                    # Если image_bytes не был передан, пытаемся скачать по URL
                    if not image_bytes:
                        photo_url = product_data_item.get('photo_urls', '')
                        if photo_url:
                            try:
                                response = requests.get(photo_url, timeout=10)
                                if response.status_code == 200:
                                    image_bytes = response.content
                                    logger.info(f"Downloaded image for product {product_id}")
                            except Exception as e:
                                logger.warning(f"Failed to download image for {product_id}: {e}")

                    # Проверяем лимиты
                    limit_check = self.content_generation_service.usage_limits.check_daily_limit(
                        user_id, product_id, 'content_enhancement'
                    )

                    if not limit_check['allowed']:
                        logger.info(f"Content generation limit reached for product {product_id}")
                        failed_products.append(product_id)
                        continue

                    # Запускаем генерацию контента (изображение + описание)
                    result = await self.content_generation_service.enhance_product_content(
                        product_info=product,
                        product_image_bytes=image_bytes,
                        generate_image=True,  # Включено улучшение фото через Gemini 2.5 Flash Image
                        generate_description=True,
                        generate_marketing=True
                    )

                    # Проверяем, был ли сгенерирован контент
                    has_generated_content = (
                        result.get('generated_description') or
                        result.get('marketing_text') or
                        result.get('enhanced_image_bytes')
                    )

                    if has_generated_content:
                        enhanced_image_url = None

                        # Сохраняем улучшенное изображение на Drive
                        if result.get('enhanced_image_bytes'):
                            try:
                                from datetime import datetime
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = f"enhanced_{product_id}_{timestamp}.jpg"

                                # Загружаем в Google Drive
                                enhanced_image_url = await self.image_storage_service.upload_image(
                                    image_bytes=result['enhanced_image_bytes'],
                                    filename=filename,
                                    product_id=product_id
                                )

                                if enhanced_image_url:
                                    logger.info(f"✅ Enhanced image uploaded to Drive: {enhanced_image_url[:60]}...")
                                else:
                                    logger.error("Failed to upload enhanced image to Drive")

                            except Exception as e:
                                logger.error(f"Error uploading enhanced image: {e}")

                        # Обновляем Google Sheets с улучшенным контентом
                        try:
                            self.sheets_manager.update_product_enhanced_content(
                                product_id=product_id,
                                enhanced_image_url=enhanced_image_url,
                                enhanced_description=result.get('generated_description'),
                                marketing_text=result.get('marketing_text'),
                                content_generated_at=datetime.now().isoformat()
                            )
                            logger.info(f"✅ Sheets updated for product {product_id}")
                        except Exception as e:
                            logger.error(f"Error updating Sheets: {e}")

                        enhanced_products.append({
                            'product_id': product_id,
                            'product_name': product.get('название', 'Товар'),
                            'enhanced_description': result.get('generated_description'),
                            'marketing_text': result.get('marketing_text'),
                            'enhanced_image_url': enhanced_image_url,
                            'has_image': bool(enhanced_image_url)
                        })
                        logger.info(f"Successfully enhanced content for product {product_id}")
                    else:
                        logger.warning(f"No content generated for product {product_id}")
                        failed_products.append(product_id)

                except Exception as e:
                    logger.error(f"Error processing product {product_id}: {e}")
                    failed_products.append(product_id)

            # Отправляем результаты
            await self.send_content_generation_results(update, enhanced_products, failed_products, status_message)

        except Exception as e:
            logger.error(f"Error in auto_generate_content_for_products: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при автоматической генерации контента. "
                "Вы можете попробовать сгенерировать контент вручную через кнопку '✨ Улучшить контент'."
            )

    async def send_content_generation_results(self, update: Update, enhanced_products: list,
                                            failed_products: list, status_message):
        """Отправляет результаты генерации контента"""
        try:
            # Обновляем статус сообщения
            if enhanced_products:
                status_text = f"✅ *Автоматическая генерация завершена!*\n\n"
                status_text += f"🎨 Улучшено товаров: {len(enhanced_products)}\n"

                if failed_products:
                    status_text += f"⚠️ Пропущено: {len(failed_products)}\n"

                status_text += f"\nВаши товары теперь имеют профессиональные изображения и B2B описания!"

                await status_message.edit_text(status_text, parse_mode='Markdown')

                # Показываем несколько примеров улучшенных товаров
                sample_products = enhanced_products[:2]  # Показываем максимум 2 примера

                for product in sample_products:
                    await self.show_enhanced_product_example(update, product)
            else:
                await status_message.edit_text(
                    "⚠️ Автоматическая генерация контента не удалась. "
                    "Вы можете попробовать сгенерировать контент вручную через кнопку '✨ Улучшить контент' в списке товаров."
                )

        except Exception as e:
            logger.error(f"Error sending content generation results: {e}")

    async def show_enhanced_product_example(self, update: Update, enhanced_product: dict):
        """Показывает пример улучшенного товара"""
        try:
            product_id = enhanced_product['product_id']
            product_name = enhanced_product['product_name']
            enhanced_image_url = enhanced_product.get('enhanced_image_url')
            enhanced_description = enhanced_product.get('enhanced_description')

            caption = f"🎨 *Пример улучшенного товара*\n\n"
            caption += f"🏷️ {escape_markdown(product_name)}\n"

            if enhanced_description:
                caption += f"📝 *Новое B2B описание:*\n{escape_markdown(enhanced_description)}\n"

            caption += f"\n💡 Чтобы управлять контентом для всех товаров, используйте /my_products"

            keyboard = [[InlineKeyboardButton("📦", callback_data="my_products")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if enhanced_image_url:
                # Пытаемся отправить улучшенное изображение
                success = await self.send_photo_from_telegram_url(
                    chat_id=update.effective_user.id,
                    photo_url=enhanced_image_url,
                    caption=caption,
                    reply_markup=reply_markup
                )

                if not success:
                    # Если не удалось, отправляем только текст
                    caption += f"\n🖼️ [Улучшенное изображение]({enhanced_image_url})"
                    await update.message.reply_text(caption, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text(caption, parse_mode='Markdown', reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error showing enhanced product example: {e}")

    async def show_my_locations(self, update: Update, context):
        """Показать мои локации"""
        try:
            query = update.callback_query
            await query.answer()


            user_id = query.from_user.id
            supplier = self.sheets_manager.get_supplier_by_telegram_id(user_id)

            if not supplier:
                await query.edit_message_text(
                    "❌ Вы не зарегистрированы. Используйте /start для регистрации."
                )
                return

            supplier_id = supplier['internal_id']

            # Получаем все локации этого поставщика
            locations = self.sheets_manager.get_locations_by_supplier_id(supplier_id)

            if not locations:
                await query.edit_message_text(
                    "📍 *Мои локации*\n\n"
                    "У вас пока нет сохраненных локаций.\n\n"
                    "Используйте кнопку ➕ ДОБАВИТЬ НОВУЮ ТОЧКУ для добавления.",
                    parse_mode='Markdown'
                )
                return

            # Формируем сообщение с локациями
            message = f"📍 *Мои локации ({len(locations)} шт.):*\n\n"

            for i, location in enumerate(locations, 1):
                market_name = str(location.get('market_name', 'Неизвестный рынок')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                pavilion_number = str(location.get('pavilion_number', 'Без номера')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                contact_phones = str(location.get('contact_phones', '')).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

                message += f"*🏪 Локация {i}*\n"
                message += f"🏬 Рынок: {market_name}\n"
                message += f"🏢 Павильон: {pavilion_number}\n"
                if contact_phones:
                    message += f"📞 Телефоны: {contact_phones}\n"
                message += "\n"

            # Создаем клавиатуру с кнопками управления
            keyboard = [
                [InlineKeyboardButton("➕ ДОБАВИТЬ НОВУЮ ТОЧКУ", callback_data="add_location")],
                [InlineKeyboardButton("⬅️ Назад в профиль", callback_data="back_to_profile")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in show_my_locations: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при загрузке локаций")

    async def enhance_product_content(self, update: Update, context):
        """Обработчик кнопки '✨ Улучшить контент'"""
        try:
            query = update.callback_query
            await query.answer()

            if not ENABLE_CONTENT_GENERATION or not self.content_generation_service:
                await self.safe_edit_message_text(
                    query,
                    "❌ Функция генерации контента временно недоступна"
                )
                return

            # Извлекаем ID товара
            product_id = query.data.replace('enhance_content_', '')
            user_id = query.from_user.id

            # Логирование для отладки
            logger.info(f"Попытка улучшить товар с ID: '{product_id}' из callback_data: '{query.data}'")

            # Проверяем лимиты
            limit_check = self.content_generation_service.usage_limits.check_daily_limit(
                user_id, product_id, 'content_enhancement'
            )

            if not limit_check['allowed']:
                await self.safe_edit_message_text(
                    query,
                    f"⏰ {limit_check['message']}\n\n"
                    "Вы сможете улучшить контент этого товара завтра.\n"
                    "Лимит обновляется в 00:00 по МСК."
                )
                return

            # Получаем информацию о товаре

            product = self.sheets_manager.get_product_by_id(product_id)

            # Логирование для отладки
            logger.info(f"Результат поиска товара с ID '{product_id}': {'найден' if product else 'не найден'}")
            if product:
                logger.info(f"Найден товар: {product.get('название', 'Без названия')}")

            if not product:
                await self.safe_edit_message_text(query, "❌ Товар не найден")
                return

            # Показываем сообщение о начале генерации
            await self.safe_edit_message_text(
                query,
                "🔄 *Улучшение контента...*\n\n"
                "Создаю профессиональное изображение и B2B описание.\n"
                "Это может занять некоторое время.",
                parse_mode='Markdown'
            )

            # Получаем оригинальное изображение
            image_bytes = None
            photo_url = product.get('photo_urls', '')
            if photo_url:
                try:
                    response = requests.get(photo_url, timeout=15)
                    if response.status_code == 200:
                        image_bytes = response.content
                        logger.info(f"Downloaded image for product {product_id}")
                except Exception as e:
                    logger.warning(f"Failed to download image for {product_id}: {e}")

            # Запускаем генерацию контента (изображение + описание)
            result = await self.content_generation_service.enhance_product_content(
                product_info=product,
                product_image_bytes=image_bytes,
                generate_image=True,  # Включено улучшение фото через Gemini 2.5 Flash Image
                generate_description=True,
                generate_marketing=True
            )

            # Если есть улучшенное изображение - загружаем в Google Drive
            enhanced_image_path = None
            enhanced_image_url_for_sheets = None
            is_enhanced_original = result.get('enhanced_original', False)
            filename_for_local = None  # Сохраняем имя файла для локального пути

            if 'enhanced_image_bytes' in result and result['enhanced_image_bytes'] and not is_enhanced_original:
                try:
                    from datetime import datetime
                    import os

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"enhanced_{product_id}_{timestamp}.jpg"
                    filename_for_local = filename  # Сохраняем для использования вне блока try

                    # 1. Загружаем в Google Drive (основное хранилище)
                    if self.image_storage_service:
                        logger.info(f"Загружаем улучшенное изображение в Google Drive...")
                        enhanced_image_url_for_sheets = await self.image_storage_service.upload_image(
                            image_bytes=result['enhanced_image_bytes'],
                            filename=filename,
                            product_id=product_id
                        )

                        if enhanced_image_url_for_sheets:
                            logger.info(f"✅ Enhanced image uploaded to Google Drive: {enhanced_image_url_for_sheets}")
                        else:
                            logger.error("Failed to upload enhanced image to Google Drive")

                    # 2. Сохраняем локально как резервную копию для быстрого доступа
                    local_dir = LOCAL_ENHANCED_IMAGES_PATH
                    os.makedirs(local_dir, exist_ok=True)

                    enhanced_image_path = os.path.join(local_dir, filename)
                    with open(enhanced_image_path, 'wb') as f:
                        f.write(result['enhanced_image_bytes'])

                    logger.info(f"✅ Enhanced image also saved locally as backup: {enhanced_image_path}")
                    result['enhanced_image_path'] = enhanced_image_path

                except Exception as e:
                    logger.error(f"Failed to save enhanced image: {e}")

            # Обработка оригинального изображения (если улучшение не удалось)
            if 'enhanced_image_bytes' in result and result['enhanced_image_bytes'] and is_enhanced_original:
                try:
                    # Сохраняем оригинальное изображение локально
                    from datetime import datetime
                    import os

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"original_{product_id}_{timestamp}.jpg"
                    filename_for_local = filename  # Сохраняем для использования вне блока try

                    local_dir = LOCAL_ENHANCED_IMAGES_PATH
                    os.makedirs(local_dir, exist_ok=True)

                    enhanced_image_path = os.path.join(local_dir, filename)
                    with open(enhanced_image_path, 'wb') as f:
                        f.write(result['enhanced_image_bytes'])

                    logger.info(f"✅ Original image saved locally: {enhanced_image_path}")
                    result['enhanced_image_path'] = enhanced_image_path
                    result['enhanced_original'] = True

                except Exception as e:
                    logger.error(f"Failed to save original image: {e}")

            # Сохраняем улучшенный контент (изображение + описание) в Google Sheets ОДИН РАЗ
            try:
                from datetime import datetime

                generated_description = result.get('generated_description')
                marketing_text = result.get('marketing_text')

                # Подготавливаем URL для сохранения
                final_image_url = enhanced_image_url_for_sheets

                # Если загрузка в Google Drive не удалась, но есть локальный файл
                if not final_image_url and enhanced_image_path and filename_for_local:
                    final_image_url = f"local:{filename_for_local}"
                # Если это оригинальное изображение (fallback)
                elif is_enhanced_original and enhanced_image_path and filename_for_local:
                    final_image_url = f"local:{filename_for_local}"

                # Обновляем только если есть что сохранять
                if final_image_url or generated_description or marketing_text:
                    logger.info(f"Сохраняем улучшенный контент для товара {product_id}")
                    logger.info(f"Final image URL: {final_image_url}")
                    self.sheets_manager.update_product_enhanced_content(
                        product_id=product_id,
                        enhanced_image_url=final_image_url,
                        enhanced_description=generated_description,
                        marketing_text=marketing_text,
                        content_generated_at=datetime.now().isoformat()
                    )
                    # Принудительно инвалидируем кеш чтобы изменения были видны сразу
                    self.sheets_manager.invalidate_cache("products")
                    logger.info(f"✅ Улучшенный контент сохранен в Google Sheets")
            except Exception as e:
                logger.error(f"Failed to save enhanced content to Google Sheets: {e}")

            # Отправляем результат
            await self.show_enhanced_content_result(update, product, result)

        except Exception as e:
            logger.error(f"Error in enhance_product_content: {e}")
            try:
                query = update.callback_query
                await self.safe_edit_message_text(
                    query,
                    "❌ Произошла ошибка при улучшении контента. Попробуйте позже."
                )
            except Exception as e2:
                logger.error(f"Failed to show error message: {e2}")
                # Если не удалось отредактировать сообщение, пытаемся отправить новое
                try:
                    await query.message.reply_text("❌ Произошла ошибка при улучшении контента. Попробуйте позже.")
                except Exception as e3:
                    logger.error(f"Failed to send error message: {e3}")

    async def enhance_content_limit_info(self, update: Update, context):
        """Показать информацию о лимитах генерации контента"""
        try:
            query = update.callback_query
            await query.answer()

            product_id = query.data.replace('enhance_content_limit_', '')
            user_id = query.from_user.id

            if not self.content_generation_service:
                await self.safe_edit_message_text(query, "❌ Сервис генерации контента недоступен")
                return

            # Получаем детальную информацию о лимитах
            limit_check = self.content_generation_service.usage_limits.check_daily_limit(
                user_id, product_id, 'content_enhancement'
            )

            message = f"📊 *Информация о лимитах*\n\n"
            message += f"🎯 Для этого товара: {limit_check['used']}/{limit_check['limit']} использований сегодня\n"
            message += f"⏰ Следующее обновление: {limit_check['next_reset'].strftime('%H:%M')}\n\n"
            message += f"Лимиты на генерацию контента установлены для обеспечения\n"
            message += f"стабильной работы сервиса для всех пользователей.\n\n"
            message += f"💡 Вы можете улучшать контент других товаров\n"
            message += f"или подождать до следующего обновления лимитов."

            keyboard = [[InlineKeyboardButton("⬅️", callback_data="my_products")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.safe_edit_message_text(
                query,
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in enhance_content_limit_info: {e}")
            try:
                await self.safe_edit_message_text(query, "❌ Ошибка при загрузке информации")
            except Exception as e2:
                logger.error(f"Failed to show error message: {e2}")
                try:
                    await query.message.reply_text("❌ Ошибка при загрузке информации")
                except Exception as e3:
                    logger.error(f"Failed to send error message: {e3}")

    async def view_enhanced_content(self, update: Update, context):
        """Просмотр улучшенного контента товара"""
        try:
            query = update.callback_query
            await query.answer()

            # Извлекаем ID товара
            product_id = query.data.replace('view_enhanced_', '')
            user_id = query.from_user.id

            logger.info(f"Просмотр улучшенного контента для товара {product_id}")

            # Получаем информацию о поставщике
            supplier = self.sheets_manager.get_supplier_by_telegram_id(user_id)
            if not supplier:
                await self.safe_edit_message_text(
                    query,
                    "❌ Доступ запрещен. Вы не зарегистрированы."
                )
                return

            supplier_id = supplier['internal_id']

            # Получаем информацию о товаре
            products = self.sheets_manager.get_products_by_supplier_id(supplier_id)
            product = None
            for p in products:
                if str(p.get('product_id')) == str(product_id):
                    product = p
                    break

            if not product:
                await self.safe_edit_message_text(
                    query,
                    "❌ Товар не найден"
                )
                return

            product_name = product.get('название', 'Товар')

            # Проверяем наличие улучшенного контента
            enhanced_description = product.get('enhanced_description', '')
            enhanced_image_url = product.get('enhanced_image_url', '')
            content_generated_at = product.get('content_generated_at', '')
            content_version = product.get('content_version', '1')

            if not enhanced_description and not enhanced_image_url:
                await self.safe_edit_message_text(
                    query,
                    f"🏷️ {escape_markdown(product_name)}\n\n"
                    "❌ Улучшенный контент не найден\n\n"
                    "Используйте кнопку '✨ Улучшить контент' для генерации",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Назад к товарам", callback_data="my_products")
                    ]])
                )
                return

            # Формируем сообщение
            message = f"🎨 *Улучшенный контент*\n\n"
            message += f"🏷️ {escape_markdown(product_name)}\n"
            message += f"🆔 ID: {product_id}\n\n"

            if enhanced_description:
                message += f"📝 *Улучшенное описание:*\n{escape_markdown(enhanced_description)}\n\n"

            if content_generated_at:
                from datetime import datetime
                try:
                    # Форматируем дату
                    dt = datetime.fromisoformat(content_generated_at.replace('Z', '+00:00'))
                    message += f"📅 Сгенерирован: {dt.strftime('%d.%m.%Y %H:%M')}\n"
                except:
                    message += f"📅 Сгенерирован: {content_generated_at}\n"

            if content_version and content_version != '1':
                message += f"🔄 Версия контента: {content_version}\n"

            keyboard = [[InlineKeyboardButton("⬅️", callback_data="my_products")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Проверяем локальное улучшенное изображение
            enhanced_local_path = None
            if enhanced_image_url and str(enhanced_image_url).startswith('local:'):
                # Извлекаем имя файла из "local:filename"
                filename = str(enhanced_image_url).replace('local:', '')
                enhanced_local_path = f"{LOCAL_ENHANCED_IMAGES_PATH}/{filename}"
                # Проверяем существование файла
                import os
                if not os.path.exists(enhanced_local_path):
                    logger.warning(f"Enhanced image file not found: {enhanced_local_path}")
                    enhanced_local_path = None

            # Отправляем сообщение
            if enhanced_local_path:
                # Сначала редактируем текущее сообщение
                await self.safe_edit_message_text(
                    query,
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

                # Затем отправляем изображение
                with open(enhanced_local_path, 'rb') as photo_file:
                    await query.message.reply_photo(
                        photo=photo_file,
                        caption=f"🎨 *Улучшенное изображение для {escape_markdown(product_name)}*\n\n"
                                f"✨ Профессиональная обработка через Gemini 2.5 Flash Image",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Назад к товарам", callback_data="my_products")
                        ]]),
                        parse_mode='Markdown'
                    )
                logger.info(f"Enhanced image sent for viewing: {enhanced_local_path}")

            elif enhanced_image_url and not str(enhanced_image_url).startswith('local:'):
                # Отправляем изображение по URL
                success = await self.send_photo_from_telegram_url(
                    chat_id=user_id,
                    photo_url=str(enhanced_image_url),
                    caption=message + f"\n\n🎨 *Улучшенное изображение*",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

                if not success:
                    # Если не удалось отправить фото, отправляем только текст
                    message += f"\n\n🖼️ [Улучшенное изображение]({enhanced_image_url})"
                    await self.safe_edit_message_text(
                        query,
                        message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            else:
                # Только текст
                await self.safe_edit_message_text(
                    query,
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in view_enhanced_content: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            try:
                query = update.callback_query
                await self.safe_edit_message_text(
                    query,
                    "❌ Произошла ошибка при загрузке контента. Попробуйте позже."
                )
            except Exception as e2:
                logger.error(f"Failed to show error message: {e2}")

    async def show_enhanced_content_result(self, update: Update, original_product: dict, result: dict):
        """Показать результат улучшения контента"""
        try:
            query = update.callback_query
            product_id = original_product.get('product_id', 'unknown')
            product_name = original_product.get('название', 'Товар')

            # Проверяем, был ли сгенерирован контент
            has_generated_content = (
                result.get('generated_description') or
                result.get('marketing_text') or
                result.get('enhanced_image_bytes') or
                result.get('enhanced_image_path')
            )

            if not has_generated_content:
                error_message = f"❌ *Не удалось улучшить контент*\n\n"
                error_message += f"🏷️ {product_name}\n"
                error_message += f"🔸 Контент не был сгенерирован\n\n"
                error_message += f"Попробуйте позже или обратитесь в поддержку."

                keyboard = [[InlineKeyboardButton("⬅️", callback_data="my_products")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await self.safe_edit_message_text(
                    query,
                    error_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return

            # Формируем сообщение об успешном улучшении
            success_message = f"✅ *Контент успешно улучшен!*\n\n"
            success_message += f"🏷️ {escape_markdown(product_name)}\n"

            # Используем правильные поля из результата
            enhanced_image_url = result.get('enhanced_image_url')
            enhanced_image_path = result.get('enhanced_image_path')  # Локальный путь к улучшенному изображению
            enhanced_image_bytes = result.get('enhanced_image_bytes')  # Байты улучшенного изображения
            generated_description = result.get('generated_description')
            marketing_text = result.get('marketing_text')
            variations = result.get('variations', [])

            if generated_description:
                success_message += f"\n📝 *Сгенерированное B2B описание:*\n{generated_description}\n"

            if marketing_text:
                success_message += f"\n📢 *Маркетинговый текст:*\n{marketing_text}\n"

            # TODO: Временно убрано, так как эти поля не генерируются
            # if background_used:
            #     bg_names = {
            #         'professional_studio': 'Профессиональная студия',
            #         'clean_white_background': 'Чистый белый фон',
            #         'marketing_showcase': 'Маркетинговая витрина',
            #         'minimalist_display': 'Минималистичное отображение'
            #     }
            #     bg_name = bg_names.get(background_used, background_used)
            #     success_message += f"\n🎨 Использован фон: {bg_name}\n"

            # if variations:
            #     success_message += f"\n💡 Дополнительные варианты описания:\n"
            #     for i, variation in enumerate(variations[:2], 1):  # Показываем первые 2 варианта
            #         success_message += f"{i}. {variation}\n"

            success_message += f"\n💎 Ваш товар теперь выглядит профессионально для B2B продаж!"

            # Автоматически сохраняем улучшенный контент в Google Sheets
            try:
                product_id = original_product.get('product_id')
                if generated_description and product_id:
                    logger.info(f"Сохраняем улучшенное описание для товара {product_id}")
                    success = self.sheets_manager.update_product(
                        product_id=product_id,
                        short_description=generated_description  # Сохраняем в колонку 'описание'
                    )
                    if success:
                        success_message += f"\n✅ *Улучшенное описание автоматически сохранено!*"
                        logger.info(f"Улучшенное описание для товара {product_id} успешно сохранено")
                        # Принудительно инвалидируем кеш чтобы изменения были видны сразу
                        self.sheets_manager.invalidate_cache("products")
                        logger.info(f"Кеш products инвалидирован после сохранения")
                    else:
                        logger.warning(f"Не удалось сохранить улучшенное описание для товара {product_id}")
                else:
                    logger.warning(f"Нет product_id или generated_description для сохранения")
            except Exception as save_error:
                logger.error(f"Ошибка при сохранении улучшенного описания: {save_error}")

            keyboard = [[InlineKeyboardButton("📦", callback_data="my_products")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Если есть улучшенное изображение, показываем его
            if enhanced_image_bytes or enhanced_image_path:
                try:
                    # Редактируем текущее сообщение с текстом
                    await self.safe_edit_message_text(
                        query,
                        success_message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )

                    # Отправляем улучшенное изображение напрямую из байтов или файла
                    if enhanced_image_bytes:
                        # Отправляем из байтов
                        from io import BytesIO
                        await query.message.reply_photo(
                            photo=BytesIO(enhanced_image_bytes),
                            caption=f"🎨 *Улучшенное изображение для {escape_markdown(product_name)}*\n\n"
                                    f"✨ Профессиональная обработка через Gemini 2.5 Flash Image\n"
                                    f"📸 Студийное освещение и композиция для B2B продаж",
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                        logger.info(f"✅ Enhanced image sent to Telegram from bytes")
                    elif enhanced_image_path:
                        # Отправляем из локального файла
                        with open(enhanced_image_path, 'rb') as photo_file:
                            await query.message.reply_photo(
                                photo=photo_file,
                                caption=f"🎨 *Улучшенное изображение для {escape_markdown(product_name)}*\n\n"
                                        f"✨ Профессиональная обработка через Gemini 2.5 Flash Image\n"
                                        f"📸 Студийное освещение и композиция для B2B продаж",
                                reply_markup=reply_markup,
                                parse_mode='Markdown'
                            )
                        logger.info(f"✅ Enhanced image sent to Telegram from file: {enhanced_image_path}")

                except Exception as e:
                    logger.error(f"Failed to send enhanced image to Telegram: {e}")
                    # Если не удалось отправить изображение, просто показываем текст
                    await self.safe_edit_message_text(
                        query,
                        success_message + "\n\n⚠️ Изображение сохранено, но не удалось его отобразить",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            else:
                # Если нет изображения, просто показываем текст
                await self.safe_edit_message_text(
                    query,
                    success_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in show_enhanced_content_result: {e}")
            try:
                query = update.callback_query
                await self.safe_edit_message_text(
                    query,
                    "❌ Ошибка при отображении результата улучшения контента"
                )
            except Exception as e2:
                logger.error(f"Failed to show error message: {e2}")
                try:
                    await query.message.reply_text("❌ Ошибка при отображении результата улучшения контента")
                except Exception as e3:
                    logger.error(f"Failed to send error message: {e3}")

    # ============= Методы для управления каналами =============

    async def channels_callback(self, update: Update, context):
        """Обработчик кнопки МОИ КАНАЛЫ"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        telegram_user_id = user.id

        supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

        if not supplier:
            await query.edit_message_text(
                "❌ Вы не зарегистрированы. Пожалуйста, используйте команду /start для регистрации.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")
                ]])
            )
            return

        # Получаем все supplier_id для пользователя
        all_suppliers = self.sheets_manager.get_all_suppliers()
        user_supplier_ids = []

        for supp_record in all_suppliers:
            if str(supp_record.get("telegram_user_id")) == str(telegram_user_id):
                user_supplier_ids.append(supp_record.get("internal_id"))

        # Получаем все каналы пользователя
        all_channels = []
        for supp_id in user_supplier_ids:
            channels = self.sheets_manager.get_channels_by_supplier_id(supp_id)
            all_channels.extend(channels)

        if not all_channels:
            text = (
                "📺 *МОИ КАНАЛЫ*\n\n"
                "У вас пока нет добавленных каналов.\n"
                "Добавьте канал, чтобы в будущем использовать его для автопостинга контента."
            )
            keyboard = [[InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")]]
        else:
            text = "📺 *МОИ КАНАЛЫ*\n\n"
            keyboard = []

            for i, channel in enumerate(all_channels, 1):
                username = channel.get('channel_username', '@unknown')
                title = channel.get('channel_title', username)
                description = channel.get('description', '')

                text += f"*{i}.* {title}\n"
                text += f"🔗 {username}\n"
                if description:
                    text += f"📝 {description}\n"
                text += "\n"

                # Кнопки управления для каждого канала
                channel_buttons = [
                    InlineKeyboardButton(f"✏️ Редактировать {i}", callback_data=f"edit_channel_{channel['channel_id']}"),
                    InlineKeyboardButton(f"🗑️ Удалить {i}", callback_data=f"delete_channel_{channel['channel_id']}")
                ]
                keyboard.append(channel_buttons)

            keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])

        keyboard.append([InlineKeyboardButton("🔙 Назад в профиль", callback_data="profile")])

        await self.safe_edit_message_text(
            query,
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def add_channel_callback(self, update: Update, context):
        """Начать процесс добавления канала"""
        query = update.callback_query
        await query.answer()

        context.user_data['state'] = 'ADD_CHANNEL_USERNAME'

        text = (
            "➕ *Добавление нового канала*\n\n"
            "Пожалуйста, введите username канала в формате @channel_name\n\n"
            "Пример: @my_channel"
        )

        await self.safe_edit_message_text(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="channels")
            ]]),
            parse_mode='Markdown'
        )

    async def get_channel_username(self, update: Update, context):
        """Обработчик ввода username канала"""
        if context.user_data.get('state') != 'ADD_CHANNEL_USERNAME':
            return

        username = update.message.text.strip()

        # Валидация формата username
        if not username.startswith('@'):
            await update.message.reply_text(
                "❌ Ошибка: username должен начинаться с @\n"
                "Попробуйте еще раз или нажмите /cancel для отмены",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отмена", callback_data="channels")
                ]])
            )
            return

        # Сохраняем username и переходим к описанию
        context.user_data['channel_username'] = username
        context.user_data['state'] = 'ADD_CHANNEL_DESCRIPTION'

        await update.message.reply_text(
            f"✅ Канал {username} добавлен\n\n"
            "Теперь введите описание канала (необязательно)\n"
            "Или отправьте /skip чтобы пропустить",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_description")
            ]])
        )

    async def get_channel_description(self, update: Update, context):
        """Обработчик ввода описания канала"""
        if context.user_data.get('state') != 'ADD_CHANNEL_DESCRIPTION':
            return

        description = update.message.text.strip()

        # Сохраняем канал
        await self.save_channel(update, context, description)

    async def save_channel(self, update, context, description="", is_callback=False):
        """Сохранение канала в Google Sheets"""
        try:
            # Определяем, откуда брать информацию о пользователе
            if is_callback and update.callback_query:
                user = update.callback_query.from_user
                message = update.callback_query.message
                reply_func = lambda text, reply_markup=None: (
                    update.callback_query.edit_message_text(text, reply_markup=reply_markup)
                )
            elif update.message:
                user = update.effective_user
                message = update.message
                reply_func = lambda text, reply_markup=None: (
                    update.message.reply_text(text, reply_markup=reply_markup)
                )
            else:
                raise ValueError("No valid update source")

            telegram_user_id = user.id

            supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

            if not supplier:
                await reply_func("❌ Ошибка: вы не зарегистрированы")
                return

            username = context.user_data.get('channel_username')
            if not username:
                await reply_func("❌ Ошибка: username не найден")
                return

            # Добавляем канал
            channel_id = self.sheets_manager.add_channel(
                supplier_internal_id=supplier['internal_id'],
                channel_username=username,
                description=description
            )

            if channel_id:
                await reply_func(
                    f"✅ Канал {username} успешно добавлен!\n\n"
                    f"Теперь вы можете использовать его для автопостинга контента"
                )

                # Показываем обновленный список каналов только если это не callback
                if not is_callback:
                    await self.show_channels_after_action(update, context)
            else:
                await reply_func("❌ Ошибка при сохранении канала")

            # Очищаем состояние
            context.user_data.clear()

        except Exception as e:
            logger.error(f"Ошибка при сохранении канала: {e}")
            try:
                if is_callback and update.callback_query:
                    await update.callback_query.edit_message_text("❌ Произошла ошибка при сохранении канала")
                elif update.message:
                    await update.message.reply_text("❌ Произошла ошибка при сохранении канала")
            except:
                pass  # Игнорируем ошибки при отправке сообщения об ошибке

    async def show_channels_after_action(self, update: Update, context):
        """Показать список каналов после действия"""
        # Получаем пользователя
        user = update.effective_user

        # Создаем новый update для channels_callback
        from types import SimpleNamespace
        mock_update = SimpleNamespace()
        mock_update.effective_user = user
        mock_update.callback_query = SimpleNamespace()
        mock_update.callback_query.answer = lambda: None
        mock_update.callback_query.from_user = user
        mock_update.callback_query.edit_message_text = lambda text, reply_markup=None, parse_mode=None: (
            update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        )
        mock_update.callback_query.message = update.message

        # Копируем контекст
        mock_context = SimpleNamespace()
        mock_context.user_data = context.user_data

        # Вызываем channels_callback с mock объектами
        await self.channels_callback(mock_update, mock_context)

    async def edit_channel_callback(self, update: Update, context):
        """Начать редактирование канала"""
        query = update.callback_query
        await query.answer()

        channel_id = query.data.replace('edit_channel_', '')

        # Получаем информацию о канале
        channel = self.sheets_manager.get_channel_by_id(channel_id)

        if not channel:
            await self.safe_edit_message_text(
                query,
                "❌ Канал не найден",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="channels")
                ]])
            )
            return

        # Сохраняем ID канала и переходим к редактированию описания
        context.user_data['editing_channel_id'] = channel_id
        context.user_data['state'] = 'EDIT_CHANNEL_DESCRIPTION'

        username = channel.get('channel_username', '')
        current_description = channel.get('description', '')
        title = channel.get('channel_title', username)

        text = (
            f"✏️ *Редактирование канала*\n\n"
            f"📺 {title}\n"
            f"🔗 {username}\n\n"
            f"Текущее описание:\n{current_description if current_description else 'Нет описания'}\n\n"
            f"Введите новое описание или отправьте /skip чтобы оставить без изменений"
        )

        await self.safe_edit_message_text(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="channels")
            ]]),
            parse_mode='Markdown'
        )

    async def update_channel_description(self, update: Update, context):
        """Обновление описания канала"""
        if context.user_data.get('state') != 'EDIT_CHANNEL_DESCRIPTION':
            return

        channel_id = context.user_data.get('editing_channel_id')
        if not channel_id:
            await update.message.reply_text("❌ Ошибка: ID канала не найден")
            return

        new_description = update.message.text.strip()

        # Обновляем канал
        success = self.sheets_manager.update_channel(
            channel_id=channel_id,
            description=new_description
        )

        if success:
            await update.message.reply_text(
                "✅ Описание канала обновлено!",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("❌ Ошибка при обновлении канала")

        # Очищаем состояние
        context.user_data.clear()

        # Показываем обновленный список каналов
        await self.show_channels_after_action(update, context)

    async def delete_channel_callback(self, update: Update, context):
        """Обработка удаления канала"""
        query = update.callback_query
        await query.answer()

        channel_id = query.data.replace('delete_channel_', '')

        # Запрашиваем подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_channel_{channel_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="channels")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.safe_edit_message_text(
            query,
            "⚠️ *Вы уверены, что хотите удалить этот канал?*\n\n"
            "Это действие нельзя отменить",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def confirm_delete_channel_callback(self, update: Update, context):
        """Подтверждение удаления канала"""
        query = update.callback_query
        await query.answer()

        channel_id = query.data.replace('confirm_delete_channel_', '')

        # Удаляем канал
        success = self.sheets_manager.delete_channel(channel_id)

        if success:
            await self.safe_edit_message_text(
                query,
                "✅ Канал успешно удален",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад к каналам", callback_data="channels")
                ]])
            )
        else:
            await self.safe_edit_message_text(
                query,
                "❌ Ошибка при удалении канала",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="channels")
                ]])
            )

    def run(self):
        """Запуск бота"""
        self.application.run_polling()

if __name__ == '__main__':
    bot = MarketBot()
    bot.run()