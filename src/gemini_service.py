#!/usr/bin/env python3
"""
Сервис для распознавания изображений с использованием Google Gemini API
"""

import google.generativeai as genai
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from PIL import Image
import io
from src.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

class GeminiService:
    """Класс для работы с Google Gemini API"""

    def __init__(self):
        """Инициализация Gemini сервиса"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY не найден в конфигурации")

        # Конфигурация API
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

        # Проверяем доступность API
        try:
            self.test_connection()
        except Exception as e:
            if "User location is not supported" in str(e):
                raise ValueError(f"Gemini API недоступен в вашем регионе. Ошибка: {str(e)}")
            else:
                raise ValueError(f"Ошибка подключения к Gemini API: {str(e)}")

        # Настройки генерации
        self.generation_config = {
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        # Системный промпт для распознавания товаров
        self.system_prompt = """Ты - эксперт по распознаванию товаров для оптовых продаж на рынках.

Твоя задача - проанализировать изображение товара и предоставить описание в следующем формате:

1. Краткое описание (1-2 слова): Название товара категории
2. Полное описание: Подробное описание товара включая:
   - Тип товара
   - Характеристики (размер, цвет,材质)
   - Упаковка
   - Примерное назначение
   - Любые другие важные детали

Отвечай на русском языке. Быть точным и конкретным."""

    def prepare_image_for_gemini(self, image_bytes: bytes) -> Image.Image:
        """Подготовка изображения для Gemini API"""
        try:
            # Конвертируем байты в PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Конвертируем в RGB если необходимо
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Оптимизируем размер если необходимо (максимум 5MB)
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            return image
        except Exception as e:
            logger.error(f"Ошибка при подготовке изображения: {e}")
            raise ValueError(f"Не удалось обработать изображение: {e}")

    async def recognize_product(self, image_bytes: bytes) -> Dict[str, str]:
        """Распознать товар на изображении"""
        try:
            logger.info("Начало распознавания товара")

            # Подготавливаем изображение
            image = self.prepare_image_for_gemini(image_bytes)

            # Создаем промпт
            prompt = f"{self.system_prompt}\n\nПроанализируй это изображение и предоставь описание товара."

            # Генерируем ответ с повторными попытками
            max_retries = 3
            base_delay = 1

            for attempt in range(max_retries):
                try:
                    logger.info(f"Попытка распознавания {attempt + 1}/{max_retries}")

                    # Генерируем контент
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.model.generate_content(
                            [prompt, image],
                            generation_config=self.generation_config
                        )
                    )

                    if response.text:
                        result = self._parse_response(response.text)
                        logger.info("Товар успешно распознан")
                        return result
                    else:
                        logger.warning(f"Пустой ответ от Gemini, попытка {attempt + 1}")

                except Exception as e:
                    logger.error(f"Ошибка при попытке {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.info(f"Повторная попытка через {delay} секунд")
                        await asyncio.sleep(delay)
                    else:
                        raise

            # Если все попытки неудачны
            raise Exception("Не удалось распознать товар после нескольких попыток")

        except Exception as e:
            logger.error(f"Ошибка распознавания товара: {e}")
            # Возвращаем результат по умолчанию
            return {
                "short_description": "Неизвестный товар",
                "full_description": f"Не удалось распознать товар: {str(e)}"
            }

    def _parse_response(self, response_text: str) -> Dict[str, str]:
        """Парсинг ответа от Gemini"""
        try:
            # Разделяем ответ на краткое и полное описание
            lines = response_text.strip().split('\n')

            short_description = "Товар"
            full_description = response_text.strip()

            # Ищем краткое описание
            for line in lines:
                if "краткое описание" in line.lower() or "1." in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        short_description = parts[1].strip()
                        break

            # Ищем полное описание
            for line in lines:
                if "полное описание" in line.lower() or "2." in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        # Собираем полное описание из всех последующих строк
                        desc_start = lines.index(line)
                        full_description = ':'.join(parts[1:]).strip()
                        if desc_start + 1 < len(lines):
                            full_description += '\n' + '\n'.join(lines[desc_start + 1:])
                        break

            # Очищаем и форматируем
            short_description = self._clean_text(short_description)[:50]  # Максимум 50 символов
            full_description = self._clean_text(full_description)[:1000]  # Максимум 1000 символов

            return {
                "short_description": short_description,
                "full_description": full_description
            }

        except Exception as e:
            logger.error(f"Ошибка парсинга ответа: {e}")
            return {
                "short_description": "Распознанный товар",
                "full_description": response_text[:500] if response_text else "Не удалось получить описание"
            }

    def _clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов"""
        if not text:
            return ""

        # Удаляем лишние пробелы и переносы строк
        text = ' '.join(text.split())

        # Удаляем специальные символы markdown
        text = text.replace('*', '').replace('#', '').replace('_', '')

        return text.strip()

    async def recognize_multiple_products(self, images_bytes: List[bytes]) -> List[Dict[str, str]]:
        """Распознать несколько товаров"""
        results = []

        for i, image_bytes in enumerate(images_bytes):
            logger.info(f"Распознавание изображения {i + 1}/{len(images_bytes)}")

            try:
                result = await self.recognize_product(image_bytes)
                results.append(result)

                # Небольшая задержка между запросами для избежания rate limiting
                if i < len(images_bytes) - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Ошибка распознавания изображения {i + 1}: {e}")
                results.append({
                    "short_description": f"Товар {i + 1}",
                    "full_description": f"Ошибка распознавания: {str(e)}"
                })

        return results

    def test_connection(self) -> bool:
        """Проверка соединения с Gemini API"""
        try:
            logger.info("Проверка соединения с Gemini API")

            # Простой тестовый запрос
            response = self.model.generate_content(
                "Ответь одним словом: тест",
                generation_config={"max_output_tokens": 10}
            )

            if response.text:
                logger.info("Соединение с Gemini API установлено")
                return True
            else:
                logger.error("Пустой ответ от Gemini API")
                return False

        except Exception as e:
            logger.error(f"Ошибка соединения с Gemini API: {e}")
            return False

# Глобальный экземпляр сервиса
_gemini_service = None

def get_gemini_service() -> GeminiService:
    """Получение экземпляра Gemini сервиса"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service

async def initialize_gemini_service() -> bool:
    """Инициализация Gemini сервиса"""
    try:
        service = get_gemini_service()
        return service.test_connection()
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini сервиса: {e}")
        return False