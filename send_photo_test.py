#!/usr/bin/env python3
"""
Отправить тестовую кнопку для проверки функции с фото
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def send_photo_test():
    """Отправить тестовое сообщение с кнопкой для проверки фото"""

    print("=== Отправка тестовой кнопки для проверки фото ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # Создаем кнопку с правильным callback_data
        keyboard = [
            [InlineKeyboardButton("📦 МОИ ТОВАРЫ С ФОТО 📸", callback_data="my_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопкой
        test_user_id = 233168669
        print(f"Отправляем сообщение пользователю {test_user_id}...")

        message = await bot.send_message(
            chat_id=test_user_id,
            text="🆕 Новая функция отображения товаров\n\n"
                 "Теперь товары будут отображаться с фотографиями!\n"
                 "Каждый товар отправляется отдельным сообщением с фото и кнопками управления.\n\n"
                 "Нажмите кнопку ниже чтобы протестировать:",
            reply_markup=reply_markup
        )
        print(f"✅ Тестовое сообщение отправлено: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_photo_test())