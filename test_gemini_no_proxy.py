#!/usr/bin/env python3
"""
Тест Gemini API без прокси
"""

import os
import sys
sys.path.append('/root/myAI/MarketBot')

# Убираем прокси из переменных окружения
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

import asyncio
import google.generativeai as genai
from src.config import GEMINI_API_KEY, GEMINI_MODEL

async def test_gemini_without_proxy():
    """Тестируем подключение к Gemini без прокси"""
    print("🔍 Тест подключения к Gemini API БЕЗ прокси")
    print(f"📊 Модель: {GEMINI_MODEL}")
    print(f"🔑 API Key: {GEMINI_API_KEY[:20]}...")

    # Проверяем, что прокси отключен
    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    print(f"🌐 HTTP_PROXY: {'❌ Удален' if not http_proxy else f'⚠️ Все еще установлен: {http_proxy[:30]}...'}")
    print(f"🔒 HTTPS_PROXY: {'❌ Удален' if not https_proxy else f'⚠️ Все еще установлен: {https_proxy[:30]}...'}")

    try:
        # Конфигурация API
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        print("\n🚀 Отправка тестового запроса без прокси...")

        # Простой тестовый запрос
        response = model.generate_content(
            "Ответь одним словом: подключение",
            generation_config={"max_output_tokens": 10}
        )

        if response and response.text:
            print(f"✅ Успешный ответ без прокси: {response.text.strip()}")
            return True
        else:
            print("❌ Пустой ответ от API без прокси")
            return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ Ошибка подключения без прокси: {error_str}")

        # Анализируем тип ошибки
        if "User location is not supported" in error_str:
            print("🌍 Проблема: Ваш регион не поддерживается Gemini API")
            print("💡 Решение: Используйте прокси или VPN")
        elif "timeout" in error_str.lower():
            print("⏱️ Проблема: Таймаут соединения")
        elif "connection" in error_str.lower() or "network" in error_str.lower():
            print("🔌 Проблема: Проблемы с сетью")
        elif "quota" in error_str.lower() or "limit" in error_str.lower():
            print("📊 Проблема: Превышен лимит API")

        return False

async def test_product_recognition_without_proxy():
    """Тестируем распознавание товара без прокси"""
    print("\n🛒 Тест распознавания товара без прокси")
    print("=" * 50)

    try:
        from src.gemini_service import get_gemini_service
        from PIL import Image
        import io

        print("🤖 Инициализация сервиса без прокси...")
        gemini_service = get_gemini_service()
        print(f"✅ Сервис инициализирован: {gemini_service.model.model_name}")

        # Создаем тестовое изображение
        test_image = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        image_bytes = img_bytes.getvalue()

        print("🖼️ Тестовое изображение создано")
        print("🤖 Начинаем распознавание без прокси...")

        result = await gemini_service.recognize_product(image_bytes)

        print("📊 Результат распознавания без прокси:")
        print("-" * 30)
        for key, value in result.items():
            print(f"{key}: {value}")
        print("-" * 30)

        if result and result.get('название') != 'Неизвестный товар':
            print("🎉 Распознавание БЕЗ прокси работает!")
            return True
        else:
            print("❌ Распознавание без прокси не работает")
            return False

    except Exception as e:
        print(f"❌ Ошибка распознавания без прокси: {str(e)}")
        return False

async def check_real_ip():
    """Проверяем реальный IP адрес"""
    try:
        import requests
        print("🌍 Проверка реального IP адреса...")

        response = requests.get("https://httpbin.org/ip", timeout=10)
        ip_data = response.json()
        ip = ip_data.get("origin", "unknown")

        # Получаем геолокацию
        geo_response = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
        geo_data = geo_response.json()

        print(f"🌐 Ваш реальный IP: {ip}")
        print(f"📍 Ваша локация: {geo_data.get('country', 'Unknown')}, {geo_data.get('city', 'Unknown')}")

        return geo_data

    except Exception as e:
        print(f"❌ Не удалось определить IP: {e}")
        return None

if __name__ == "__main__":
    print("🚪 Тестирование Gemini API БЕЗ прокси")
    print("=" * 60)

    # Проверяем реальный IP
    real_location = asyncio.run(check_real_ip())

    # Тест API без прокси
    api_result = asyncio.run(test_gemini_without_proxy())

    # Тест распознавания без прокси
    recognition_result = asyncio.run(test_product_recognition_without_proxy())

    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТА БЕЗ ПРОКСИ:")

    if real_location:
        print(f"🌍 Ваш регион: {real_location.get('country', 'Unknown')}")

    if api_result:
        print("✅ Базовый API работает без прокси")
    else:
        print("❌ Базовый API не работает без прокси")

    if recognition_result:
        print("✅ Распознавание работает без прокси")
    else:
        print("❌ Распознавание не работает без прокси")

    if api_result and recognition_result:
        print("\n🎉 ВЫВОД: Прокси НЕ нужен! API работает в вашем регионе")
        print("💡 Можно отключить прокси для ускорения работы")
    else:
        print("\n🚨 ВЫВОД: Прокси НЕОБХОДИМ!")
        print("💡 Ваш регион не поддерживается Gemini API")