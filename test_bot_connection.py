#!/usr/bin/env python3
"""
Проверка соединения с ботом
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def test_bot_connection():
    """Проверить соединение с ботом"""

    print("=== Проверка соединения с ботом ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"Bot info: {me}")
        print(f"Username: @{me.username}")
        print(f"Name: {me.first_name}")
        print(f"ID: {me.id}")

        # Отправляем тестовое сообщение
        test_user_id = 233168669  # Fetsteady
        print(f"\nОтправляем тестовое сообщение пользователю {test_user_id}...")

        message = await bot.send_message(
            chat_id=test_user_id,
            text="🤖 Тестовое сообщение от бота. Если вы видите это сообщение, то бот работает правильно!"
        )
        print(f"✅ Сообщение отправлено: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_bot_connection())