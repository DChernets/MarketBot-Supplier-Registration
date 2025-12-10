#!/usr/bin/env python3
"""
Тест проверки подключения к Gemini API через прокси
"""

import os
import sys
sys.path.append('/root/myAI/MarketBot')

# Устанавливаем прокси
os.environ['HTTP_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'
os.environ['HTTPS_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'

import asyncio
import google.generativeai as genai
from src.config import GEMINI_API_KEY, GEMINI_MODEL

async def test_gemini_with_proxy():
    """Тестируем подключение к Gemini через прокси"""
    print("🔍 Тест подключения к Gemini API")
    print(f"📊 Модель: {GEMINI_MODEL}")
    print(f"🔑 API Key: {GEMINI_API_KEY[:20]}...")

    # Проверяем переменные окружения прокси
    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    print(f"🌐 HTTP_PROXY: {http_proxy[:30]}..." if http_proxy else "❌ HTTP_PROXY не установлен")
    print(f"🔒 HTTPS_PROXY: {https_proxy[:30]}..." if https_proxy else "❌ HTTPS_PROXY не установлен")

    try:
        # Конфигурация API
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        print("\n🚀 Отправка тестового запроса...")

        # Простой тестовый запрос
        response = model.generate_content(
            "Ответь одним словом: подключение",
            generation_config={"max_output_tokens": 10}
        )

        if response and response.text:
            print(f"✅ Успешный ответ: {response.text.strip()}")
            return True
        else:
            print("❌ Пустой ответ от API")
            return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ Ошибка подключения: {error_str}")

        # Анализируем тип ошибки
        if "User location is not supported" in error_str:
            print("🌍 Проблема: Gemini API недоступен в вашем регионе")
            print("💡 Решение: Используйте VPN или прокси из другой страны")
        elif "timeout" in error_str.lower():
            print("⏱️ Проблема: Таймаут соединения")
            print("💡 Решение: Проверьте работу прокси или попробуйте другой")
        elif "connection" in error_str.lower() or "network" in error_str.lower():
            print("🔌 Проблема: Проблемы с соединением")
            print("💡 Решение: Проверьте настройки прокси")
        elif "quota" in error_str.lower() or "limit" in error_str.lower():
            print("📊 Проблема: Превышен лимит API")
            print("💡 Решение: Попробуйте позже или проверьте квоты")

        return False

async def test_direct_connection():
    """Тест без прокси для сравнения"""
    print("\n" + "="*50)
    print("🔍 Тест подключения БЕЗ прокси")

    # Временно удаляем прокси
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        print("🚀 Отправка тестового запроса без прокси...")

        response = model.generate_content(
            "Ответь одним словом: тест",
            generation_config={"max_output_tokens": 10}
        )

        if response and response.text:
            print(f"✅ Успешный ответ без прокси: {response.text.strip()}")
            return True
        else:
            print("❌ Пустой ответ от API без прокси")
            return False

    except Exception as e:
        print(f"❌ Ошибка подключения без прокси: {str(e)}")
        return False

if __name__ == "__main__":
    print("🤖 Запуск тестов подключения к Gemini API")
    print("="*50)

    # Тест с прокси
    result_with_proxy = asyncio.run(test_gemini_with_proxy())

    # Тест без прокси
    result_without_proxy = asyncio.run(test_direct_connection())

    print("\n" + "="*50)
    print("📊 ИТОГИ:")
    print(f"🔌 С прокси: {'✅ Успешно' if result_with_proxy else '❌ Ошибка'}")
    print(f"🔓 Без прокси: {'✅ Успешно' if result_without_proxy else '❌ Ошибка'}")

    if result_with_proxy:
        print("\n🎉 Прокси работает корректно!")
    elif result_without_proxy:
        print("\n⚠️ Прокси не работает, но подключение напрямую возможно")
        print("💡 Проклема может быть в настройках прокси")
    else:
        print("\n🚨 Ни один из способов подключения не работает")
        print("💡 Проверьте API ключ и настройки сети")