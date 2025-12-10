#!/usr/bin/env python3
"""
Тест Telegram File API для понимания формата URL
"""

import asyncio
from telegram import Bot
from src.config import TELEGRAM_BOT_TOKEN

async def test_telegram_file_info():
    """Тест получения информации о файле"""

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    print("=== Тест Telegram File API ===")

    # Пример file_id (нужно будет заменить на реальный)
    # Это обычный формат file_id для фото
    test_file_id = "AgACAgQAAxkDAANvZ2eE9cPn7x_8T3R3k8Xf3S7Q7Z8VAAJk7jJxW9s"

    try:
        print(f"Тестируем file_id: {test_file_id}")

        # Получаем информацию о файле
        file_info = await bot.get_file(test_file_id)

        print(f"File ID: {file_info.file_id}")
        print(f"File Path: {file_info.file_path}")
        print(f"File Size: {file_info.file_size}")

        # Формируем правильный URL
        correct_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
        print(f"Correct URL: {correct_url}")

        # Проверяем начинается ли file_path с http
        if file_info.file_path.startswith('http'):
            print("File path уже содержит полный URL")
        else:
            print("File path содержит только относительный путь")

    except Exception as e:
        print(f"Ошибка при тестировании file_id: {e}")
        print("Нужно использовать реальный file_id из загруженного фото")

if __name__ == "__main__":
    asyncio.run(test_telegram_file_info())