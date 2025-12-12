#!/usr/bin/env python3
"""
Сервис для распознавания изображений с использованием Google Gemini API через HTTP
"""

import asyncio
import base64
import logging
import json
from typing import Optional, Dict, Any, List
import io
import httpx
from PIL import Image

from src.config import GEMINI_API_KEY, GEMINI_RECOGNITION_MODEL, USE_PROXY, HTTP_PROXY, HTTPS_PROXY

# Configure proxy environment variables if enabled
if USE_PROXY and (HTTP_PROXY or HTTPS_PROXY):
    import os
    if HTTP_PROXY:
        os.environ['HTTP_PROXY'] = HTTP_PROXY
        os.environ['http_proxy'] = HTTP_PROXY
    if HTTPS_PROXY:
        os.environ['HTTPS_PROXY'] = HTTPS_PROXY
        os.environ['https_proxy'] = HTTPS_PROXY
    print(f"Gemini Service: Прокси настроен через переменные окружения")
elif not USE_PROXY:
    # Remove proxy environment variables if they were set previously
    import os
    for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy']:
        if proxy_var in os.environ:
            del os.environ[proxy_var]
    print("Gemini Service: Прокси отключен, переменные окружения очищены")

logger = logging.getLogger(__name__)

# Gemini API endpoints
def get_recognition_endpoint():
    return f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_RECOGNITION_MODEL}:generateContent"


class GeminiService:
    """Класс для работы с Google Gemini API через HTTP"""

    def __init__(self):
        """Инициализация Gemini сервиса"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY не найден в конфигурации")

        self.api_key = GEMINI_API_KEY
        self.timeout = 30.0  # 30 секунд таймаут
        self.max_retries = 3

        # Проверяем доступность API (отложенная проверка при первом использовании)
        self._connection_tested = False

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

    def build_request_contents(self, text: str, image_bytes: Optional[bytes], image_mime: Optional[str]) -> Dict[str, Any]:
        """Создает содержимое запроса к Gemini API"""
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

        return {"parts": parts}

    def prepare_image_for_gemini(self, image_bytes: bytes) -> tuple[bytes, str]:
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

            # Сохраняем в байты
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            optimized_bytes = buffer.getvalue()
            buffer.close()

            return optimized_bytes, "image/jpeg"
        except Exception as e:
            logger.error(f"Ошибка при подготовке изображения: {e}")
            raise ValueError(f"Не удалось обработать изображение: {e}")

    async def call_gemini_api(self, text: str, image_bytes: Optional[bytes] = None, image_mime: Optional[str] = None) -> Dict[str, Any]:
        """Вызов Gemini API через HTTP"""
        payload = {
            "contents": [self.build_request_contents(text, image_bytes, image_mime)],
            "generationConfig": self.generation_config,
        }

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        endpoint = get_recognition_endpoint()

        # Настраиваем прокси
        proxies = {}
        if USE_PROXY:
            if HTTP_PROXY:
                proxies["http://"] = HTTP_PROXY
            if HTTPS_PROXY:
                proxies["https://"] = HTTPS_PROXY

        # Логируем использование прокси
        if USE_PROXY and proxies:
            logger.info(f"Используем прокси: {proxies}")
        elif not USE_PROXY:
            logger.info("Прокси отключен")
        else:
            logger.info("Прокси не настроен")

        logger.info(f"Используем модель распознавания: {GEMINI_RECOGNITION_MODEL}")

        last_error = None

        async with httpx.AsyncClient(timeout=self.timeout, proxies=proxies if proxies else None) as client:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Попытка вызова Gemini API {attempt + 1}/{self.max_retries}")

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
                            logger.warning(f"Gemini API вернул {response.status_code}. Повторная попытка через {wait_time}с (попытка {attempt + 1}/{self.max_retries})")
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
                        logger.warning(f"Gemini API ошибка {e.response.status_code}: {error_text}. Повтор через {wait_time}с (попытка {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Gemini API исключение: {type(e).__name__}: {str(e)}. Повтор через {wait_time}с (попытка {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

        # Если все попытки неудачны
        if last_error:
            logger.error(f"Gemini API не ответил после {self.max_retries} попыток. Последняя ошибка: {last_error}")
            raise last_error
        raise RuntimeError("Failed to call Gemini API after retries")

    async def recognize_product(self, image_bytes: bytes) -> Dict[str, str]:
        """Распознать товар на изображении"""
        try:
            # Проверяем соединение при первом использовании
            if not self._connection_tested:
                logger.info("Проверка соединения при первом использовании")
                connection_ok = await self.test_connection()
                if not connection_ok:
                    raise ValueError("Не удалось подключиться к Gemini API")
                self._connection_tested = True

            logger.info("Начало распознавания товара")

            # Подготавливаем изображение
            optimized_image_bytes, image_mime = self.prepare_image_for_gemini(image_bytes)

            # Создаем промпт
            prompt = f"{self.system_prompt}\n\nПроанализируй это изображение и верни JSON с описанием товара."

            # Вызываем API
            response_json = await self.call_gemini_api(prompt, optimized_image_bytes, image_mime)

            # Обрабатываем ответ
            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    part = candidate['content']['parts'][0]
                    if 'text' in part:
                        result = self._parse_json_response(part['text'])
                        logger.info("Товар успешно распознан")
                        return result

            logger.warning("Пустой ответ от Gemini API")
            raise Exception("Пустой ответ от Gemini API")

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
                    "название": f"Товар {i + 1}",
                    "описание": f"Ошибка распознавания: {str(e)}",
                    "производство": "Не указано",
                    "материал": "Не указано",
                    "размеры": "Не указано",
                    "упаковка": "Не указано"
                })

        return results

    async def test_connection(self) -> bool:
        """Проверка соединения с Gemini API"""
        try:
            logger.info("Проверка соединения с Gemini API")

            # Простой тестовый запрос
            test_prompt = "Ответь одним словом: тест"
            response_json = await self.call_gemini_api(test_prompt)

            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    part = candidate['content']['parts'][0]
                    if 'text' in part and part['text'].strip():
                        logger.info("Соединение с Gemini API установлено")
                        return True
                    else:
                        logger.error("Пустой ответ от Gemini API при тесте")
                        return False
                else:
                    logger.error("Некорректная структура ответа от Gemini API")
                    return False
            else:
                logger.error("Нет candidates в ответе от Gemini API")
                return False

        except Exception as e:
            logger.error(f"Ошибка соединения с Gemini API: {e}")
            return False

    def _clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов"""
        if not text:
            return ""

        # Удаляем лишние пробелы и переносы строк
        text = ' '.join(text.split())

        # Удаляем специальные символы markdown
        text = text.replace('*', '').replace('#', '').replace('_', '')

        return text.strip()


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
        return await service.test_connection()
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini сервиса: {e}")
        return False