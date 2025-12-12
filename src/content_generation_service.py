#!/usr/bin/env python3
"""
Сервис генерации контента для товаров
"""

import asyncio
import io
import logging
import base64
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import httpx
from PIL import Image

from src.config import GEMINI_API_KEY, GEMINI_RECOGNITION_MODEL, GEMINI_CONTENT_GENERATION_MODEL, USE_PROXY, HTTP_PROXY, HTTPS_PROXY
from src.usage_limits import get_usage_limits

logger = logging.getLogger(__name__)

# Gemini API endpoints
def get_recognition_endpoint():
    return f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_RECOGNITION_MODEL}:generateContent"

def get_content_generation_endpoint():
    return f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CONTENT_GENERATION_MODEL}:generateContent"

class ContentGenerationService:
    """Класс для генерации контента товаров"""

    def __init__(self, sheets_manager=None):
        """Инициализация сервиса генерации контента"""
        self.sheets_manager = sheets_manager
        self.usage_limits = get_usage_limits(sheets_manager)
        self.api_key = GEMINI_API_KEY
        self.timeout = 60.0  # 60 секунд таймаут для генерации изображений
        self.max_retries = 3

        # Настройки генерации текста
        self.text_generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        # Настройки генерации изображений
        self.image_generation_config = {
            "temperature": 0.8,
            "candidate_count": 1,
        }

        logger.info("Сервис генерации контента инициализирован с Gemini Vision HTTP API")

    async def call_gemini_api(self, text: str, image_bytes: Optional[bytes] = None, image_mime: Optional[str] = None, generation_config: Optional[Dict] = None, use_image_model: bool = False) -> Dict[str, Any]:
        """Вызов Gemini API через HTTP"""
        if generation_config is None:
            generation_config = self.text_generation_config

        # Создаем содержимое запроса
        parts = [{"text": text}]

        if image_bytes and image_mime:
            # Кодируем изображение в base64
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": image_mime,
                    "data": encoded_image,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": generation_config,
        }

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        # Выбираем правильный эндпоинт
        if use_image_model and image_bytes:
            endpoint = get_content_generation_endpoint()
            model_name = GEMINI_CONTENT_GENERATION_MODEL
        else:
            endpoint = get_recognition_endpoint()
            model_name = GEMINI_RECOGNITION_MODEL

        # Настраиваем прокси
        proxies = {}
        if USE_PROXY:
            if HTTP_PROXY:
                proxies["http://"] = HTTP_PROXY
            if HTTPS_PROXY:
                proxies["https://"] = HTTPS_PROXY

        # Логируем использование прокси
        if USE_PROXY and proxies:
            logger.info(f"Используем прокси для генерации контента: {proxies}")
        elif not USE_PROXY:
            logger.info("Прокси отключен для генерации контента")
        else:
            logger.info("Прокси не настроен для генерации контента")

        logger.info(f"Используем модель: {model_name}")

        last_error = None

        async with httpx.AsyncClient(timeout=self.timeout, proxies=proxies if proxies else None) as client:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Попытка вызова Gemini API для генерации контента {attempt + 1}/{self.max_retries}")

                    response = await client.post(
                        endpoint,
                        params=params,
                        headers=headers,
                        json=payload
                    )

                    # Retry на 503 (service unavailable) или 429 (rate limit)
                    if response.status_code in (503, 429):
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(f"Gemini API вернул {response.status_code} при генерации. Повторная попытка через {wait_time}с (попытка {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()

                    response.raise_for_status()
                    return response.json()

                except httpx.HTTPStatusError as e:
                    last_error = e
                    # Retry на 503 или 429 если есть попытки
                    if e.response.status_code in (503, 429) and attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        error_text = e.response.text[:200] if e.response.text else "No response text"
                        logger.warning(f"Gemini API ошибка {e.response.status_code} при генерации: {error_text}. Повтор через {wait_time}с (попытка {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Gemini API исключение при генерации: {type(e).__name__}: {str(e)}. Повтор через {wait_time}с (попытка {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

        # Если все попытки неудачны
        if last_error:
            logger.error(f"Gemini API не ответил после {self.max_retries} попыток при генерации. Последняя ошибка: {last_error}")
            raise last_error
        raise RuntimeError("Failed to call Gemini API after retries")

    async def generate_enhanced_image(self, product_image_bytes: bytes,
                                       product_info: Dict[str, Any],
                                       background_type: str = "professional_studio") -> Optional[bytes]:
        """
        Сгенерировать улучшенное изображение товара с помощью Gemini Vision

        Args:
            product_image_bytes: Байты изображения товара
            product_info: Информация о товаре
            background_type: Тип фона (professional_studio, marketing_showcase, etc.)

        Returns:
            bytes: Байты улучшенного изображения или None при ошибке
        """
        try:
            logger.info(f"Начало генерации улучшенного изображения через Gemini Vision")

            # Создаем промпт на основе типа фона и информации о товаре
            prompt = self._create_image_generation_prompt(product_info, background_type)

            # Подготавливаем изображение
            optimized_image_bytes, image_mime = self._prepare_image_for_api(product_image_bytes)

            # Вызываем API для генерации изображения
            response_json = await self.call_gemini_api(
                prompt,
                optimized_image_bytes,
                image_mime,
                self.image_generation_config,
                use_image_model=True
            )

            # Обрабатываем ответ
            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'inlineData' in part and part['inlineData']:
                            # Получаем байты изображения
                            if 'data' in part['inlineData']:
                                enhanced_bytes = base64.b64decode(part['inlineData']['data'])
                                logger.info(f"Успешно сгенерировано изображение через Gemini Vision")
                                return enhanced_bytes

            logger.warning("Gemini Vision не вернул изображение")
            return None

        except Exception as e:
            logger.error(f"Ошибка при генерации изображения через Gemini Vision: {e}")
            return None

    async def generate_product_description(self, product_info: Dict[str, Any]) -> Optional[str]:
        """
        Сгенерировать профессиональное описание товара

        Args:
            product_info: Информация о товаре

        Returns:
            str: Сгенерированное описание или None при ошибке
        """
        try:
            logger.info("Начало генерации описания товара")

            prompt = self._create_description_prompt(product_info)

            # Вызываем API для генерации текста
            response_json = await self.call_gemini_api(prompt)

            # Обрабатываем ответ
            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    part = candidate['content']['parts'][0]
                    if 'text' in part:
                        description = part['text'].strip()
                        logger.info(f"Успешно сгенерировано описание товара")
                        return description

            logger.warning("Не удалось сгенерировать описание товара")
            return None

        except Exception as e:
            logger.error(f"Ошибка при генерации описания товара: {e}")
            return None

    async def generate_marketing_text(self, product_info: Dict[str, Any]) -> Optional[str]:
        """
        Сгенерировать маркетинговый текст для товара

        Args:
            product_info: Информация о товаре

        Returns:
            str: Сгенерированный маркетинговый текст или None при ошибке
        """
        try:
            logger.info("Начало генерации маркетингового текста")

            prompt = self._create_marketing_prompt(product_info)

            # Вызываем API для генерации текста
            response_json = await self.call_gemini_api(prompt)

            # Обрабатываем ответ
            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    part = candidate['content']['parts'][0]
                    if 'text' in part:
                        marketing_text = part['text'].strip()
                        logger.info(f"Успешно сгенерирован маркетинговый текст")
                        return marketing_text

            logger.warning("Не удалось сгенерировать маркетинговый текст")
            return None

        except Exception as e:
            logger.error(f"Ошибка при генерации маркетингового текста: {e}")
            return None

    def _prepare_image_for_api(self, image_bytes: bytes) -> tuple[bytes, str]:
        """Подготовка изображения для API"""
        try:
            # Конвертируем байты в PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Конвертируем в RGB если необходимо
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Оптимизируем размер если необходимо (максимум 3MB для генерации)
            max_size = (1024, 1024)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Сохраняем в байты
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=80)
            optimized_bytes = buffer.getvalue()
            buffer.close()

            return optimized_bytes, "image/jpeg"
        except Exception as e:
            logger.error(f"Ошибка при подготовке изображения: {e}")
            raise ValueError(f"Не удалось обработать изображение: {e}")

    def _create_image_generation_prompt(self, product_info: Dict[str, Any], background_type: str) -> str:
        """Создать промпт для генерации изображения"""

        base_prompt = f"""
        Ты - профессиональный фотограф товаров и дизайнер. Создай улучшенное изображение товара для маркетинга.

        Информация о товаре:
        - Название: {product_info.get('название', 'Неизвестный товар')}
        - Описание: {product_info.get('описание', 'Нет описания')}
        - Материал: {product_info.get('материал', 'Не указано')}
        - Размеры: {product_info.get('размеры', 'Не указано')}
        - Производство: {product_info.get('производство', 'Не указано')}
        """

        background_prompts = {
            "professional_studio": """
            Тип фона: Профессиональная студия
            Создай изображение в стиле профессиональной предметной фотографии с чистым, светлым фоном.
            Хорошие освещение, минимальные тени, фокус на качестве товара.
            """,

            "marketing_showcase": """
            Тип фона: Маркетинговая витрина
            Создай привлекательное изображение товара на маркетинговом фоне.
            Используй мягкое освещение, эстетичную композицию, возможно с элементами декора.
            """,

            "lifestyle_context": """
            Тип фона: Lifestyle контекст
            Размести товар в реальном контексте использования.
            Создай атмосферу, показывающую как товар выглядит в быту или работе.
            """,

            "minimalist": """
            Тип фона: Минимализм
            Создай минималистичное изображение с фокусом на форме и текстуре товара.
            Используй нейтральный фон, чистые линии, акцент на деталях.
            """
        }

        background_prompt = background_prompts.get(background_type, background_prompts["professional_studio"])

        full_prompt = f"""
        {base_prompt}

        {background_prompt}

        Требования:
        1. Сохрани узнаваемость оригинального товара
        2. Улуччи качество изображения, освещение и композицию
        3. Создай профессиональный вид, подходящий для маркетинга
        4. В результате должно получиться улучшенное изображение товара
        """

        return full_prompt

    def _create_description_prompt(self, product_info: Dict[str, Any]) -> str:
        """Создать промпт для генерации описания товара"""

        prompt = f"""
        Ты - копирайтер для B2B маркетплейса. Напиши профессиональное описание товара для оптовых покупателей.

        Информация о товаре:
        - Название: {product_info.get('название', 'Неизвестный товар')}
        - Описание: {product_info.get('описание', 'Нет описания')}
        - Материал: {product_info.get('материал', 'Не указано')}
        - Размеры: {product_info.get('размеры', 'Не указано')}
        - Производство: {product_info.get('производство', 'Не указано')}
        - Упаковка: {product_info.get('упаковка', 'Не указано')}

        Напиши описание, которое:
        1. Содержит 3-4 предложения
        2. Подчеркивает ключевые преимущества для оптовых покупателей
        3. Включает технические характеристики (материал, размеры)
        4. Упоминает упаковку и логистические преимущества
        5. Написано профессиональным, но понятным языком
        6. Длиной 100-200 символов

        Верни только текст описания без дополнительных комментариев.
        """

        return prompt

    def _create_marketing_prompt(self, product_info: Dict[str, Any]) -> str:
        """Создать промпт для генерации маркетингового текста"""

        prompt = f"""
        Ты - маркетолог. Создай короткий маркетинговый текст для товара в B2B маркетплейсе.

        Информация о товаре:
        - Название: {product_info.get('название', 'Неизвестный товар')}
        - Описание: {product_info.get('описание', 'Нет описания')}
        - Материал: {product_info.get('материал', 'Не указано')}
        - Размеры: {product_info.get('размеры', 'Не указано')}

        Создай маркетинговый текст который:
        1. Привлекает внимание оптовых покупателей
        2. Подчеркивает выгоду оптовой закупки
        3. Содержит 1-2 предложения
        4. Использует убедительные формулировки
        5. Длиной 50-100 символов

        Верни только маркетинговый текст без дополнительных комментариев.
        """

        return prompt

    async def enhance_product_content(self, product_info: Dict[str, Any],
                                    product_image_bytes: Optional[bytes] = None,
                                    generate_image: bool = False,
                                    generate_description: bool = False,
                                    generate_marketing: bool = False) -> Dict[str, Any]:
        """
        Комплексное улучшение контента товара

        Args:
            product_info: Информация о товаре
            product_image_bytes: Байты изображения товара
            generate_image: Генерировать улучшенное изображение
            generate_description: Генерировать описание
            generate_marketing: Генерировать маркетинговый текст

        Returns:
            Dict[str, Any]: Обновленная информация о товаре
        """
        try:
            logger.info("Начало комплексного улучшения контента товара")

            enhanced_info = product_info.copy()

            # TODO: Gemini не может генерировать изображения с нуля
            # Временно отключаем генерацию изображений
            if generate_image and product_image_bytes:
                logger.info("⚠️ Генерация изображений временно отключена - Gemini не создает изображения с нуля")
                # enhanced_image = await self.generate_enhanced_image(
                #     product_image_bytes,
                #     product_info,
                #     background_type="professional_studio"
                # )
                # if enhanced_image:
                #     enhanced_info['enhanced_image_bytes'] = enhanced_image

            # Генерация описания
            if generate_description:
                description = await self.generate_product_description(product_info)
                if description:
                    enhanced_info['generated_description'] = description

            # Генерация маркетингового текста
            if generate_marketing:
                marketing_text = await self.generate_marketing_text(product_info)
                if marketing_text:
                    enhanced_info['marketing_text'] = marketing_text

            logger.info("Завершено комплексное улучшение контента товара")
            return enhanced_info

        except Exception as e:
            # Дополнительная диагностика для отладки
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Ошибка при комплексном улучшении контента: {e}")
            logger.error(f"Full traceback: {error_details}")
            return product_info

    async def batch_enhance_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Массовое улучшение контента для списка товаров

        Args:
            products: Список товаров

        Returns:
            List[Dict[str, Any]]: Список улучшенных товаров
        """
        enhanced_products = []

        for i, product in enumerate(products):
            logger.info(f"Улучшение контента для товара {i + 1}/{len(products)}")

            try:
                # Комплексное улучшение с ограничениями (без генерации изображений)
                enhanced_product = await self.enhance_product_content(
                    product,
                    product_image_bytes=product.get('image_bytes'),
                    generate_image=False,  # Временно отключено
                    generate_description=True,
                    generate_marketing=True
                )

                enhanced_products.append(enhanced_product)

                # Небольшая задержка между запросами
                if i < len(products) - 1:
                    await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Ошибка при улучшении товара {i + 1}: {e}")
                enhanced_products.append(product)

        return enhanced_products

    def get_enhancement_statistics(self) -> Dict[str, Any]:
        """Получить статистику использования сервиса генерации контента"""
        return self.usage_limits.get_daily_usage()

# Глобальный экземпляр сервиса
_content_generation_service = None

def get_content_generation_service(sheets_manager=None) -> ContentGenerationService:
    """Получение экземпляра сервиса генерации контента"""
    global _content_generation_service
    if _content_generation_service is None:
        _content_generation_service = ContentGenerationService(sheets_manager)
    return _content_generation_service

async def initialize_content_generation_service(sheets_manager=None) -> bool:
    """Инициализация сервиса генерации контента"""
    try:
        service = get_content_generation_service(sheets_manager)
        # Пробуем сгенерировать тестовый текст для проверки соединения
        test_response = await service.call_gemini_api("Ответь одним словом: тест")
        if test_response:
            logger.info("Сервис генерации контента успешно инициализирован")
            return True
        else:
            logger.error("Не удалось проверить работу сервиса генерации контента")
            return False
    except Exception as e:
        logger.error(f"Ошибка инициализации сервиса генерации контента: {e}")
        return False