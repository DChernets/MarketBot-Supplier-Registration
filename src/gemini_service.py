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
from src.config import GEMINI_API_KEY, GEMINI_MODEL, HTTP_PROXY, HTTPS_PROXY

# Configure proxy for all HTTP requests including google.generativeai
if HTTP_PROXY or HTTPS_PROXY:
    import os
    if HTTP_PROXY:
        os.environ['HTTP_PROXY'] = HTTP_PROXY
        os.environ['http_proxy'] = HTTP_PROXY
    if HTTPS_PROXY:
        os.environ['HTTPS_PROXY'] = HTTPS_PROXY
        os.environ['https_proxy'] = HTTPS_PROXY

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

1. Краткое описание: [Конкретное название товара 1-2 слова, например: "Бокал", "Стакан", "Тарелка"]
2. Полное описание: Подробное описание товара включая:
   - Тип товара
   - Характеристики (размер, цвет, материал)
   - Упаковка
   - Примерное назначение
   - Любые другие важные детали

ВАЖНО: В кратком описании указывай конкретное название товара, а не общее слово "Товар".
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

            short_description = "Распознанный товар"
            full_description = response_text.strip()

            # Улучшенный поиск краткого описания
            # Ищем сначала "1." или "Краткое описание"
            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Вариант 1: "1. Краткое описание: Название"
                if line_stripped.startswith("1.") and "краткое описание" in line_stripped.lower():
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        short_description = parts[1].strip()
                        break

                # Вариант 2: Просто "1. Бокал" или "Бокал для вина"
                elif line_stripped.startswith("1."):
                    parts = line.split('.', 1)
                    if len(parts) > 1:
                        short_description = parts[1].strip()
                        break

                # Вариант 3: "Краткое описание: Бокал"
                elif "краткое описание" in line_stripped.lower():
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        short_description = parts[1].strip()
                        break

            # Если краткое название не найдено, пробуем извлечь из полного описания
            if short_description in ["Распознанный товар", "Товар"]:
                # Ищем первое substantive слово/фразу в ответе
                for line in lines:
                    words = line.strip().split()
                    for word in words:
                        # Пропускаем маркеры и цифры
                        if (len(word) > 2 and
                            not word.isdigit() and
                            word.lower() not in ['1.', '2.', 'краткое', 'описание', 'полное', 'тип', 'товара']):
                            # Берем первые 1-2 слова как название
                            short_description = word
                            if len(words) > 1 and len(words[1]) > 2:
                                short_description += ' ' + words[1]
                            break
                    if short_description not in ["Распознанный товар", "Товар"]:
                        break

            # Ищем полное описание
            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Вариант 1: "2. Полное описание: ..."
                if line_stripped.startswith("2.") and "полное описание" in line_stripped.lower():
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        full_description = parts[1].strip()
                        if i + 1 < len(lines):
                            full_description += '\n' + '\n'.join(lines[i + 1:])
                        break

                # Вариант 2: "Полное описание: ..."
                elif "полное описание" in line_stripped.lower():
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        full_description = parts[1].strip()
                        if i + 1 < len(lines):
                            full_description += '\n' + '\n'.join(lines[i + 1:])
                        break

            # Если полное описание не найдено, используем весь ответ
            if full_description == response_text.strip() and len(lines) > 1:
                # Пробуем исключить первую строку если это краткое описание
                if lines[0].strip().startswith("1.") or "краткое описание" in lines[0].lower():
                    full_description = '\n'.join(lines[1:]).strip()

            # Очищаем и форматируем
            short_description = self._clean_text(short_description)
            if len(short_description) > 50:
                # Если название слишком длинное, обрезаем до первого пробела или до 30 символов
                short_description = short_description[:47] + '...'

            full_description = self._clean_text(full_description)
            if len(full_description) > 1000:
                full_description = full_description[:997] + '...'

            logger.info(f"Распознано: {short_description[:30]}...")

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