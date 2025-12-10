#!/usr/bin/env python3
"""
Отправить новую тестовую кнопку с исправленным callback
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def send_fixed_callback():
    """Отправить тестовое сообщение с исправленной кнопкой"""

    print("=== Отправка исправленной тестовой кнопки ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # Создаем кнопку с правильным callback_data
        keyboard = [
            [InlineKeyboardButton("📦 МОИ ТОВАРЫ (ИСПРАВЛЕНО)", callback_data="my_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопкой
        test_user_id = 233168669
        print(f"Отправляем исправленное сообщение пользователю {test_user_id}...")

        message = await bot.send_message(
            chat_id=test_user_id,
            text="✅ Исправленная версия\n\n"
                 "Callback кнопка теперь использует правильный data='my_products'\n"
                 "Нажмите на кнопку ниже для тестирования:\n\n"
                 "Если всё работает, вы увидите свои товары или сообщение об их отсутствии.",
            reply_markup=reply_markup
        )
        print(f"✅ Исправленное сообщение отправлено: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_fixed_callback())