#!/usr/bin/env python3
"""
Тестовый скрипт для проверки загрузки переменных окружения и Gemini API
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from dotenv import load_dotenv
from src.config import GEMINI_API_KEY, GEMINI_MODEL

print("=== Проверка загрузки .env файла ===")
print(f"Текущая рабочая директория: {os.getcwd()}")
print(f"GEMINI_API_KEY из config.py: {'Есть' if GEMINI_API_KEY else 'Нет'}")
if GEMINI_API_KEY:
    print(f"Первые 20 символов API ключа: {GEMINI_API_KEY[:20]}...")
else:
    print("API ключ пустой")

print(f"GEMINI_MODEL: {GEMINI_MODEL}")

# Пробуем инициализировать Gemini сервис
try:
    from src.gemini_service import initialize_gemini_service
    print("\n=== Тест инициализации Gemini сервиса ===")
    import asyncio

    async def test_init():
        result = await initialize_gemini_service()
        print(f"Результат инициализации: {result}")
        return result

    result = asyncio.run(test_init())

except Exception as e:
    print(f"Ошибка при инициализации Gemini: {e}")
    import traceback
    traceback.print_exc()