#!/usr/bin/env python3
"""
Тестирование callback кнопок
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def test_callback():
    """Отправить тестовое сообщение с callback кнопкой"""

    print("=== Тестирование callback кнопок ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # Создаем кнопку с callback
        keyboard = [
            [InlineKeyboardButton("📦 МОИ ТОВАРЫ (ТЕСТ)", callback_data="test_my_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопкой
        test_user_id = 233168669
        print(f"Отправляем тестовое сообщение с кнопкой пользователю {test_user_id}...")

        message = await bot.send_message(
            chat_id=test_user_id,
            text="🧪 *Тестирование кнопок*\n\n"
                 "Нажмите на кнопку ниже чтобы протестировать callback:\n\n"
                 "Если вы видите ошибку 'Ошибка при загрузке товаров', "
                 "то проблема именно в обработке callback'ов.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        print(f"✅ Сообщение с кнопкой отправлено: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_callback())