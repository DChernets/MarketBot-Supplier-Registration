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

Проанализируй изображение товара и верни JSON-объект со следующими полями:
- название: Конкретное название товара (1-3 слова)
- описание: Краткое описание товара (1 предложение)
- производство: Страна производитель
- материал: Основной материал товара
- размеры: Габариты, объем или размеры
- упаковка: Информация об упаковке товара

ВАЖНО:
1. Верни ТОЛЬКО JSON без дополнительного текста
2. Все поля обязательны, используй "Не указано" если информация не определена
3. Название должно быть конкретным, а не общим словом "Товар"
4. Отвечай на русском языке

Пример формата:
{
  "название": "Бокал для вина",
  "описание": "Стеклянный бокал на высокой ножке для красного вина",
  "производство": "Китай",
  "материал": "Стекло",
  "размеры": "высота 18см, объем 250мл",
  "упаковка": "коробка по 12 штук"
}"""

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
            prompt = f"{self.system_prompt}\n\nПроанализируй это изображение и верни JSON с описанием товара."

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
                        result = self._parse_json_response(response.text)
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
                'название': 'Неизвестный товар',
                'описание': f'Не удалось распознать товар: {str(e)}',
                'производство': 'Не указано',
                'материал': 'Не указано',
                'размеры': 'Не указано',
                'упаковка': 'Не указано'
            }

    def _parse_json_response(self, response_text: str) -> Dict[str, str]:
        """Парсинг JSON-ответа от Gemini"""
        import json

        try:
            logger.info(f"Получен ответ: {response_text[:200]}...")

            # Очищаем текст от возможных проблемных символов и лишнего текста
            cleaned_text = response_text.strip()

            # Ищем JSON в тексте (если Gemini вернул с дополнительным текстом)
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = cleaned_text[start_idx:end_idx + 1]
                logger.info(f"Извлеченный JSON: {json_str[:100]}...")
            else:
                # Если не нашли JSON, пробуем обработать весь текст
                json_str = cleaned_text
                logger.warning(f"Не найдено JSON-разделение, обрабатываем весь текст")

            # Парсим JSON
            data = json.loads(json_str)

            # Валидация обязательных полей
            required_fields = ['название', 'описание', 'производство', 'материал', 'размеры', 'упаковка']
            result = {}

            for field in required_fields:
                value = data.get(field, 'Не указано')
                if value is None or value == '':
                    value = 'Не указано'
                result[field] = str(value).strip()

            # Логирование распознанного товара
            logger.info(f"Распознано: {result['название']} ({result['производство']}, {result['материал']})")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            logger.error(f"Текст ответа: {response_text[:500]}...")

            # Fallback: пробуем извлечь базовую информацию
            return self._fallback_parse(response_text)

        except Exception as e:
            logger.error(f"Ошибка парсинга JSON-ответа: {e}")
            logger.error(f"Текст ответа: {response_text[:500]}...")

            # Fallback: пробуем извлечь базовую информацию
            return self._fallback_parse(response_text)

    def _fallback_parse(self, response_text: str) -> Dict[str, str]:
        """Fallback-парсер на случай, если JSON не удалось распознать"""
        try:
            # Ищем название товара (первое substantive слово)
            words = response_text.replace('\n', ' ').split()
            title = "Товар"

            for word in words:
                word = word.strip('.,!?:;()[]{}"\'')
                if (len(word) > 2 and
                    word.lower() not in ['для', 'из', 'с', 'на', 'и', 'или', 'не', 'по', 'под', 'при', 'над', 'без']):
                    title = word
                    break

            return {
                'название': title,
                'описание': response_text[:200] + '...' if len(response_text) > 200 else response_text,
                'производство': 'Не указано',
                'материал': 'Не указано',
                'размеры': 'Не указано',
                'упаковка': 'Не указано'
            }

        except Exception as e:
            logger.error(f"Ошибка в fallback-парсере: {e}")
            return {
                'название': 'Распознанный товар',
                'описание': 'Не удалось распознать описание',
                'производство': 'Не указано',
                'материал': 'Не указано',
                'размеры': 'Не указано',
                'упаковка': 'Не указано'
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