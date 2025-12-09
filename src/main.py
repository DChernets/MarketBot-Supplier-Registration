import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from src.config import TELEGRAM_BOT_TOKEN, DEBUG
from src.google_sheets import GoogleSheetsManager

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
NAME, MARKET, PAVILION, PHONE, ADD_MORE_PHONES, ADD_MORE_PHONES_CALLBACK, ADD_LOCATION, ADD_LOCATION_CALLBACK = range(8)

class MarketBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.sheets_manager = None
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Простые обработчики команд
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('profile', self.profile_command))
        self.application.add_handler(CommandHandler('cancel', self.cancel))

        # Глобальные обработчики для текстовых сообщений и кнопок
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback, pattern=r'.*'))

    async def start_command(self, update: Update, context):
        """Обработчик команды /start"""
        try:
            # Инициализация Google Sheets (здесь будет обработка ошибок)
            self.sheets_manager = GoogleSheetsManager()

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
        elif query.data in ['edit_supplier', 'add_location_post']:
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
        elif query.data.startswith('confirm_delete_'):
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
        elif query.data in ['edit_supplier', 'add_location_post']:
            logger.info(f"handle_callback: calling post_registration_callback")
            await self.post_registration_callback(update, context)
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
                [InlineKeyboardButton("📝 ИЗМЕНИТЬ ИНФОРМАЦИЮ ПОСТАВЩИКА", callback_data="edit_supplier")],
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

        if query.data == "edit_supplier":
            await query.edit_message_text(
                "🔧 Функция редактирования будет добавлена в следующей версии.\n"
                "Пока используйте /start для создания новой регистрации."
            )
        elif query.data == "add_location":
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
            if not self.sheets_manager:
                self.sheets_manager = GoogleSheetsManager()

            user = update.effective_user
            telegram_user_id = user.id

            supplier = self.sheets_manager.get_supplier_by_telegram_id(telegram_user_id)

            if supplier:
                # Ищем все локации для этого telegram_user_id (включая от старых регистраций)
                all_locations = []
                telegram_user_id = supplier['telegram_user_id']

                # Сначала получаем все supplier_id для этого пользователя
                all_suppliers = self.sheets_manager.suppliers_sheet.get_all_records()
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

                profile_text = (
                    f"📋 *ВАШ ПРОФИЛЬ*\n\n"
                    f"👤 Имя: {supplier['contact_name']}\n"
                    f"📱 Telegram: @{supplier['telegram_username']}\n"
                    f"🆔 ID: {supplier['internal_id']}\n\n"
                    f"🏪 *ВАШИ ТОЧКИ ПРОДАЖИ:*\n"
                )

                # Добавляем кнопки для каждой локации
                keyboard = []

                for i, location in enumerate(locations, 1):
                    profile_text += (
                        f"\n*Точка {i}:*\n"
                        f"🏬 Рынок: {location['market_name']}\n"
                        f"🏢 Павильон: {location['pavilion_number']}\n"
                        f"📞 Телефоны: {location['contact_phones']}\n"
                    )

                    # Добавляем кнопки управления для каждой локации
                    location_buttons = [
                        InlineKeyboardButton(f"✏️ Редакровать {i}", callback_data=f"edit_location_{location['location_id']}"),
                        InlineKeyboardButton(f"🗑️ Удалить {i}", callback_data=f"delete_location_{location['location_id']}")
                    ]
                    keyboard.append(location_buttons)

                # Добавляем общие кнопки управления
                keyboard.extend([
                    [InlineKeyboardButton("📝 ИЗМЕНИТЬ ИНФОРМАЦИЮ ПОСТАВЩИКА", callback_data="edit_supplier")],
                    [InlineKeyboardButton("➕ ДОБАВИТЬ НОВУЮ ТОЧКУ", callback_data="add_location")]
                ])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(profile_text, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text(
                    "Вы еще не зарегистрированы. Используйте /start для регистрации."
                )

        except Exception as e:
            logger.error(f"Error in profile_command: {e}")
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

        # Находим все локации пользователя
        all_locations = []
        all_suppliers = self.sheets_manager.suppliers_sheet.get_all_records()
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
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{location_id}")],
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

    def run(self):
        """Запуск бота"""
        self.application.run_polling()

if __name__ == '__main__':
    bot = MarketBot()
    bot.run()