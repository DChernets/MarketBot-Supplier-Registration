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
            "temperature": 0.7,  # Оптимизировано для B2B профессионального контента (баланс креативности и стабильности)
            "candidateCount": 1,
            "responseModalities": ["IMAGE"],  # Для получения изображения от Gemini 2.5 Flash Image
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
            logger.info(f"🔍 Структура ответа от Gemini: keys={list(response_json.keys())}")

            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                logger.info(f"🔍 Candidate keys: {list(candidate.keys())}")

                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    logger.info(f"🔍 Найдено {len(parts)} parts в ответе")

                    for i, part in enumerate(parts):
                        logger.info(f"🔍 Part {i} keys: {list(part.keys())}")

                        if 'inlineData' in part and part['inlineData']:
                            inline_data = part['inlineData']
                            logger.info(f"🔍 inlineData keys: {list(inline_data.keys())}")

                            # Получаем байты изображения
                            if 'data' in inline_data:
                                data_length = len(inline_data['data'])
                                logger.info(f"🔍 Найдено изображение! Размер base64 данных: {data_length} символов")
                                enhanced_bytes = base64.b64decode(inline_data['data'])
                                logger.info(f"✅ Успешно сгенерировано изображение через Gemini Vision. Размер: {len(enhanced_bytes)} байт")
                                return enhanced_bytes

                        if 'text' in part:
                            logger.info(f"🔍 Part {i} содержит текст (первые 100 символов): {part['text'][:100]}")

            logger.warning("⚠️ Gemini Vision не вернул изображение. Полный ответ для отладки сохранен в логах")
            logger.debug(f"Полный ответ от Gemini: {json.dumps(response_json, indent=2, ensure_ascii=False)[:1000]}")
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
        """
        Создать промпт для редактирования изображения товара с нарративным подходом

        Использует принцип "Describe the scene, don't just list keywords" (Google Gemini 2.5 Flash best practices 2025).
        Промпт составлен на английском языке с профессиональными фотографическими терминами
        для максимальной эффективности генерации через Gemini 2.5 Flash Image.

        Args:
            product_info: Информация о товаре (название, материал, описание)
            background_type: Тип фона (в текущей версии не используется, настройки берутся из категории)

        Returns:
            str: Детальный нарративный промпт для Gemini 2.5 Flash Image
        """
        product_name = product_info.get('название', 'товар')
        product_material = product_info.get('материал', '')
        product_description = product_info.get('описание', '')

        # Получаем категориально-специфичные настройки
        category_settings = self._get_category_photography_settings(product_info)

        # Формируем информацию о материале и описании
        material_line = f"MATERIAL: {product_material}" if product_material and product_material != "Не указано" else ""
        description_line = f"DESCRIPTION: {product_description}" if product_description and product_description != "Не указано" else ""

        prompt = f"""You are a professional product photographer specializing in B2B wholesale e-commerce imagery for Russian marketplaces.

PRODUCT INFORMATION:
- Product: {product_name}
{material_line}
{description_line}

PHOTOGRAPHY SCENE DESCRIPTION:
Imagine a professional product photoshoot in a high-end studio environment. {category_settings['scene_description']} The setting conveys premium quality and reliability that B2B wholesale buyers expect from their suppliers.

CAMERA SETUP:
The product is captured using {category_settings['lens_type']} from {category_settings['camera_angle']}, positioned to showcase the product's key features, dimensions, and material quality. The composition follows {category_settings['composition_style']}, with the product occupying 70-80% of the frame as the hero element.

LIGHTING DESIGN:
Professional three-point lighting setup creates dimensional depth:
- Main key light from large softbox positioned at 45-degree angle above-front, delivering soft directional illumination that reveals texture and form
- Fill light at quarter intensity from opposite side, preventing harsh shadows while maintaining natural depth
- Subtle rim light accentuating product edges and emphasizing {product_material if product_material and product_material != 'Не указано' else 'material'} texture
- Natural-looking shadows falling at 30-degree angle, adding dimensionality without distraction
- Gentle highlights and reflections that showcase craftsmanship and material quality

BACKGROUND & ENVIRONMENT:
{category_settings['background_description']}
The composition is clean and distraction-free, with all extraneous objects, hands, watermarks, text, and graphic elements completely removed.

VISUAL QUALITY & COLOR GRADING:
- High-resolution macro-level detail revealing texture, weave, finish quality, and craftsmanship
- Rich, vibrant {category_settings['color_style']}
- Sharp focus throughout the product with subtle depth of field effect on background
- Natural contrast that makes product stand out clearly against background
- Authentic, non-over-processed aesthetic meeting 2025 e-commerce photography standards
- Professional color accuracy for true-to-life product representation

MARKETPLACE OPTIMIZATION:
The final image must meet professional standards for major Russian B2B wholesale marketplaces (Ozon, Wildberries, AliExpress) and Telegram wholesale catalog channels. The photography should convey premium quality, inspire confidence in product reliability, and create desire for wholesale purchase.

CRITICAL CONSTRAINTS:
- Do NOT alter the product itself - ONLY enhance the presentation, lighting, and environment
- Do NOT add watermarks, logos, text overlays, or any graphic elements
- Do NOT change product colors, shape, or inherent characteristics
- Preserve authentic product appearance while optimizing visual appeal through professional photography technique
- Focus on creating trust and desire through lighting, composition, and background rather than artificial manipulation

The goal is professional catalog photography that makes wholesale buyers want to touch, examine, and order this product in bulk quantity."""

        return prompt

    def _get_category_photography_settings(self, product_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Получить категориально-специфичные фотографические настройки

        На основе названия и материала товара определяет оптимальные настройки съемки:
        - Тип объектива и угол камеры
        - Описание сцены и фона
        - Стиль композиции и цветокоррекции

        Args:
            product_info: Информация о товаре (название, материал, описание)

        Returns:
            Dict[str, str]: Словарь с фотографическими настройками для категории
        """
        product_name = product_info.get('название', '').lower()
        product_material = product_info.get('материал', '').lower()

        # Определяем категорию на основе названия и материала
        if any(word in product_name for word in ['бокал', 'стакан', 'ваза', 'посуд', 'тарелка', 'чашка', 'кружка', 'стекл']):
            return {
                'scene_description': 'The glass/dishware item is positioned on a pristine white marble surface with subtle natural veining, creating an elegant foundation.',
                'lens_type': 'macro lens (100mm equivalent)',
                'camera_angle': 'slightly elevated 20-degree angle',
                'composition_style': 'dynamic 5-degree tilt for visual energy',
                'background_description': 'Bright, clean white background with subtle gradient to light gray at edges, suggesting modern kitchen environment. Soft natural window light aesthetic creating crystal-clear transparency and elegant reflections that showcase glass quality.',
                'color_style': 'bright, high-contrast with enhanced clarity for glass transparency and reflections'
            }

        elif any(word in product_name for word in ['ткань', 'текстиль', 'полотенце', 'постельное', 'одеяло', 'подушка', 'плед']):
            return {
                'scene_description': 'The textile product is artfully arranged on natural wooden surface, showcasing fabric texture, drape, and tactile quality.',
                'lens_type': '85mm portrait lens',
                'camera_angle': 'eye-level with slight 10-degree elevation',
                'composition_style': 'gentle organic arrangement highlighting fabric flow and softness',
                'background_description': 'Warm neutral background (light beige to soft gray) with natural wood texture accent. Soft diffused lighting mimicking natural daylight from window, creating gentle shadows that emphasize textile softness and weave detail.',
                'color_style': 'warm, natural tones with emphasis on fabric texture detail and material quality'
            }

        elif any(word in product_name for word in ['электро', 'гаджет', 'провод', 'зарядка', 'устройство', 'техник']):
            return {
                'scene_description': 'The electronic item is placed on sleek modern surface in minimalist tech-forward environment.',
                'lens_type': 'standard 50mm lens with precise focus',
                'camera_angle': 'straight-on eye-level for geometric precision',
                'composition_style': 'perfectly centered alignment emphasizing clean lines and technical precision',
                'background_description': 'Minimalist gradient background transitioning from pure white at center to light cool gray at edges. Tech-aesthetic lighting with subtle blue undertones suggesting precision, innovation, and modernity.',
                'color_style': 'crisp, high-contrast with slight cool color temperature for modern tech aesthetic'
            }

        else:  # Универсальные товары
            return {
                'scene_description': 'The product is positioned on clean professional surface in neutral studio environment.',
                'lens_type': 'standard 50mm lens',
                'camera_angle': 'slightly elevated 15-degree angle for optimal perspective',
                'composition_style': 'centered with subtle asymmetric placement for visual interest',
                'background_description': 'Clean professional white to light gray background with soft gradient. Studio lighting setup creating modern, fresh aesthetic suitable for any product category.',
                'color_style': 'balanced, true-to-life colors with enhanced vibrancy'
            }

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

            # Генерация улучшенного изображения через Gemini 2.5 Flash Image
            if generate_image and product_image_bytes:
                logger.info("🖼️ Запускаем улучшение изображения через Gemini 2.5 Flash Image")
                enhanced_image = await self.generate_enhanced_image(
                    product_image_bytes,
                    product_info,
                    background_type="professional_studio"
                )
                if enhanced_image:
                    enhanced_info['enhanced_image_bytes'] = enhanced_image
                    logger.info("✅ Изображение успешно улучшено")
                else:
                    # Используем оригинальное изображение как fallback
                    enhanced_info['enhanced_image_bytes'] = product_image_bytes
                    enhanced_info['enhanced_original'] = True
                    logger.warning("⚠️ Не удалось улучшить изображение, используем оригинальное")

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