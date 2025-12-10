#!/usr/bin/env python3
"""
Сервис генерации контента для товаров
"""

import asyncio
import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image
import google.generativeai as genai

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.background_templates import get_background_templates
from src.usage_limits import get_usage_limits

logger = logging.getLogger(__name__)

class ContentGenerationService:
    """Класс для генерации контента товаров"""

    def __init__(self, sheets_manager=None):
        """Инициализация сервиса генерации контента"""
        self.sheets_manager = sheets_manager
        self.background_templates = get_background_templates()
        self.usage_limits = get_usage_limits(sheets_manager)

        # Конфигурация Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

        logger.info("Сервис генерации контента инициализирован")

    async def generate_enhanced_image(self, product_image_bytes: bytes,
                                       product_info: Dict[str, Any],
                                       background_type: str = "professional_white") -> Optional[bytes]:
        """
        Сгенерировать улучшенное изображение товара на профессиональном фоне

        Args:
            product_image_bytes: Байты изображения товара
            product_info: Информация о товаре
            background_type: Тип фона

        Returns:
            bytes: Байты улучшенного изображения или None при ошибке
        """
        try:
            logger.info(f"Начало генерации улучшенного изображения для товара")

            # Конвертируем байты в PIL Image
            product_image = Image.open(io.BytesIO(product_image_bytes))

            # Применяем фон
            enhanced_image = self.background_templates.apply_background(product_image, background_type)

            # Конвертируем обратно в байты
            enhanced_bytes = io.BytesIO()
            enhanced_image.save(enhanced_bytes, format='JPEG', quality=95, optimize=True)
            enhanced_bytes = enhanced_bytes.getvalue()

            logger.info(f"Успешно сгенерировано улучшенное изображение с фоном {background_type}")
            return enhanced_bytes

        except Exception as e:
            logger.error(f"Ошибка при генерации улучшенного изображения: {e}")
            return None

    async def generate_b2b_description(self, product_info: Dict[str, Any]) -> Optional[str]:
        """
        Сгенерировать B2B описание товара

        Args:
            product_info: Информация о товаре

        Returns:
            str: Сгенерированное описание или None при ошибке
        """
        try:
            logger.info(f"Начало генерации B2B описания для товара")

            # Создаем промпт для генерации B2B описания
            prompt = self._create_b2b_description_prompt(product_info)

            # Генерируем описание
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                        "max_output_tokens": 300,
                    }
                )
            )

            if response and response.text:
                description = response.text.strip()
                logger.info(f"Успешно сгенерировано B2B описание")
                return description
            else:
                logger.warning("Пустой ответ от Gemini API при генерации описания")
                return None

        except Exception as e:
            logger.error(f"Ошибка при генерации B2B описания: {e}")
            return None

    async def generate_content_variations(self, product_info: Dict[str, Any],
                                         count: int = 3) -> List[str]:
        """
        Сгенерировать несколько вариантов описания товара

        Args:
            product_info: Информация о товаре
            count: Количество вариантов

        Returns:
            List[str]: Список сгенерированных описаний
        """
        try:
            logger.info(f"Генерация {count} вариантов описания для товара")

            descriptions = []
            for i in range(count):
                prompt = self._create_b2b_description_prompt(product_info, variation=i+1)

                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.8 + (i * 0.1),  # Разная температура для разнообразия
                            "top_p": 0.9,
                            "top_k": 40,
                            "max_output_tokens": 250,
                        }
                    )
                )

                if response and response.text:
                    description = response.text.strip()
                    descriptions.append(description)
                    logger.info(f"Вариант {i+1} успешно сгенерирован")

            return descriptions

        except Exception as e:
            logger.error(f"Ошибка при генерации вариантов описания: {e}")
            return []

    async def enhance_product_content(self, user_id: int, product_info: Dict[str, Any],
                                        image_bytes: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Улучшить контент товара (генерация изображения и описания)

        Args:
            user_id: ID пользователя
            product_info: Информация о товаре
            image_bytes: Байты изображения (опционально)

        Returns:
            Dict: Результат улучшения контента
        """
        try:
            product_id = product_info.get('product_id')
            if not product_id:
                return {'success': False, 'error': 'ID товара не указан'}

            # Проверяем лимиты
            limit_check = self.usage_limits.check_daily_limit(user_id, product_id, 'content_enhancement')
            if not limit_check['allowed']:
                return {
                    'success': False,
                    'error': limit_check['message'],
                    'remaining': limit_check['remaining'],
                    'next_reset': limit_check['next_reset']
                }

            logger.info(f"Начало улучшения контента для товара {product_id}")

            # Записываем попытку использования
            self.usage_limits.record_usage(user_id, product_id, 'content_enhancement', success=True)

            result = {
                'success': True,
                'enhanced_image_url': None,
                'enhanced_description': None,
                'variations': [],
                'generated_at': datetime.now().isoformat(),
                'background_used': None
            }

            # Выбираем случайный профессиональный фон
            background_template = self.background_templates.get_random_template("professional")
            result['background_used'] = background_template.template_id

            # Генерируем улучшенное изображение
            if image_bytes:
                enhanced_image_bytes = await self.generate_enhanced_image(
                    image_bytes, product_info, background_template.template_id
                )

                if enhanced_image_bytes:
                    # Загружаем изображение в Google Drive
                    if self.sheets_manager:
                        try:
                            from src.image_storage import ImageStorageService
                            storage_service = ImageStorageService()

                            # Сохраняем улучшенное изображение
                            image_filename = f"enhanced_{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            image_url = storage_service.upload_image_bytes(
                                enhanced_image_bytes,
                                image_filename,
                                f"Enhanced product image for {product_info.get('название', 'Unknown')}"
                            )

                            result['enhanced_image_url'] = image_url
                            logger.info(f"Улучшенное изображение загружено: {image_url}")

                        except Exception as e:
                            logger.error(f"Ошибка при загрузке улучшенного изображения: {e}")

            # Генерируем B2B описание
            enhanced_description = await self.generate_b2b_description(product_info)
            if enhanced_description:
                result['enhanced_description'] = enhanced_description
                logger.info(f"Сгенерировано улучшенное описание для товара {product_id}")

            # Генерируем вариации описания
            variations = await self.generate_content_variations(product_info, 3)
            result['variations'] = variations

            if result['enhanced_image_url'] or result['enhanced_description']:
                # Обновляем информацию в Google Sheets
                if self.sheets_manager:
                    self.sheets_manager.update_product_enhanced_content(
                        product_id,
                        result['enhanced_image_url'],
                        result['enhanced_description'],
                        result['generated_at']
                    )

                logger.info(f"Успешно улучшен контент для товара {product_id}")
                return result
            else:
                # Откатываем запись использования если ничего не сгенерировалось
                self.usage_limits.record_usage(
                    user_id, product_id, 'content_enhancement',
                    success=False,
                    error_message="Не удалось сгенерировать ни изображение ни описание"
                )

                return {
                    'success': False,
                    'error': 'Не удалось сгенерировать контент. Попробуйте позже.'
                }

        except Exception as e:
            logger.error(f"Ошибка при улучшении контента: {e}")
            # Откатываем запись использования при ошибке
            try:
                self.usage_limits.record_usage(
                    user_id, product_info.get('product_id', ''),
                    'content_enhancement',
                    success=False,
                    error_message=str(e)
                )
            except:
                pass

            return {
                'success': False,
                'error': 'Произошла ошибка при генерации контента. Попробуйте позже.'
            }

    def _create_b2b_description_prompt(self, product_info: Dict[str, Any], variation: int = 1) -> str:
        """
        Создать промпт для генерации B2B описания

        Args:
            product_info: Информация о товаре
            variation: Номер вариации для разнообразия

        Returns:
            str: Промпт для Gemini API
        """
        product_name = product_info.get('название', 'Товар')
        description = product_info.get('описание', '')
        material = product_info.get('материал', '')
        production = product_info.get('производство', '')
        dimensions = product_info.get('размеры', '')
        packaging = product_info.get('упаковка', '')

        # Базовый промпт
        base_prompt = f"""
Создай убедительное B2B описание для оптовых продаж товара:

ТОВАР: {product_name}
Характеристики:
- Описание: {description}
- Материал: {material}
- Производство: {production}
- Размеры: {dimensions}
- Упаковка: {packaging}

ТРЕБОВАНИЯ:
1. Целевая аудитория: владельцы магазинов, оптовые покупатели, менеджеры по закупкам
2. Фокус на выгоде для бизнеса и перепродажи
3. Краткость: 2-3 предложения максимум
4. Профессиональный и убедительный тон
5. Упомяни ключевые преимущества для опта
6. Добавь легкий призыв к действию

ВАРИАНТ {variation}: Сделай описание уникальным, измени формулировки и акценты.
"""

        # Добавляем специфику для разных вариаций
        if variation == 1:
            base_prompt += """
АКЦЕНТ на качестве и надежности для долгосрочного сотрудничества."""
        elif variation == 2:
            base_prompt += """
АКЦЕНТ на сезонности и трендах, подчеркивая актуальность."""
        elif variation == 3:
            base_prompt += """
АКЦЕНТ на маржинальности и выгоде для перепродажи, используя бизнес-терминологию."""

        base_prompt += """

Отвечай только готовым описанием без дополнительных комментариев."""
        return base_prompt

    async def generate_product_showcase_description(self, product_info: Dict[str, Any]) -> Optional[str]:
        """
        Сгенерировать описание для витрины/шоукейса

        Args:
            product_info: Информация о товаре

        Returns:
            str: Описание для витрины
        """
        try:
            product_name = product_info.get('название', 'Товар')
            description = product_info.get('описание', '')
            price_info = product_info.get('цена', 'конкурентная цена')

            prompt = f"""
Создай привлекательное описание для витрины/шоукейса товара:

ТОВАР: {product_name}
Описание: {description}
Ценовая позиция: {price_info}

ТРЕБОВАНИЯ:
1. Краткое и яркое описание (1-2 предложения)
2. Фокус на визуальной привлекательности и выгоде для конечного покупателя
3. Эмоциональный язык для привлечения внимания
4. Подчеркни ключевые преимущества товара
5. Используй маркетинговые триггеры

Стиль: яркий, убедительный, привлекающий внимание.

Отвечай только готовым описанием."""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.8,
                        "max_output_tokens": 200,
                    }
                )
            )

            if response and response.text:
                return response.text.strip()
            return None

        except Exception as e:
            logger.error(f"Ошибка при генерации описания для витрины: {e}")
            return None

    def get_background_previews(self) -> Dict[str, Any]:
        """
        Получить превью всех доступных фонов

        Returns:
            Dict: Превью фонов
        """
        try:
            previews = {}
            available_templates = self.background_templates.get_available_templates()

            for template_id, template_name in available_templates.items():
                try:
                    preview_image = self.background_templates.preview_template(template_id)
                    # Конвертируем в байты для отправки
                    preview_bytes = io.BytesIO()
                    preview_image.save(preview_bytes, format='JPEG', quality=85)
                    preview_bytes = preview_bytes.getvalue()

                    previews[template_id] = {
                        'name': template_name,
                        'preview_bytes': preview_bytes,
                        'preview_url': None  # Можно добавить URL если нужно
                    }
                except Exception as e:
                    logger.error(f"Ошибка при создании превью для {template_id}: {e}")

            return previews

        except Exception as e:
            logger.error(f"Ошибка при получении превью фонов: {e}")
            return {}

    async def analyze_product_for_marketing(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проанализировать товар для маркетинговых стратегий

        Args:
            product_info: Информация о товаре

        Returns:
            Dict: Результаты анализа
        """
        try:
            prompt = f"""
Проанализируй товар для маркетинговых стратегий B2B:

ТОВАР: {product_info.get('название', 'Товар')}
Описание: {product_info.get('описание', '')}
Материал: {product_info.get('материал', '')}
Производство: {product_info.get('производство', '')}

Оцени по шкале 1-10:
1. Потенциал спроса (seasonality_score)
2. Маржинальность (margin_potential)
3. Сложность продаж (sales_complexity)
4. Целевая аудитория (target_market_broadness)
5. Уникальность (uniqueness_score)

Дай рекомендации:
1. Основные преимущества для опта
2. Ключевые маркетинговые аргументы
3. Возможные каналы продаж
4. Периодичность закупок

Формат ответа - структурированный JSON."""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 500,
                    }
                )
            )

            if response and response.text:
                # Здесь можно добавить парсинг JSON ответа
                return {'analysis': response.text.strip(), 'recommendations': True}

            return {'analysis': None, 'recommendations': False}

        except Exception as e:
            logger.error(f"Ошибка при анализе товара для маркетинга: {e}")
            return {'analysis': None, 'recommendations': False}

# Глобальный экземпляр сервиса
_content_generation_service = None

def get_content_generation_service(sheets_manager=None) -> ContentGenerationService:
    """Получить экземпляр сервиса генерации контента"""
    global _content_generation_service
    if _content_generation_service is None:
        _content_generation_service = ContentGenerationService(sheets_manager)
    return _content_generation_service