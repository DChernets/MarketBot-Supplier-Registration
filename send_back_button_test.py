#!/usr/bin/env python3
"""
Отправить тестовое сообщение для проверки кнопки "Назад в профиль"
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def send_back_button_test():
    """Отправить тест для кнопки назад"""

    print("=== Отправка теста для кнопки 'Назад в профиль' ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # Создаем кнопку для теста
        keyboard = [
            [InlineKeyboardButton("📦 ТОВАРЫ ДЛЯ ТЕСТА КНОПКИ", callback_data="my_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение
        test_user_id = 233168669
        print(f"Отправляем тестовое сообщение пользователю {test_user_id}...")

        message = await bot.send_message(
            chat_id=test_user_id,
            text="🔧 *ТЕСТ КНОПКИ 'НАЗАД В ПРОФИЛЬ'*\n\n"
                 "Проблема была исправлена!\n\n"
                 "❌ *Было:* Кнопка 'Назад в профиль' не работала\n"
                 "✅ *Стало:* Создана специальная функция для возврата в профиль\n\n"
                 "Инструкция:\n"
                 "1. Нажми кнопку ниже 👇\n"
                 "2. В списке товаров нажми '⬅️ Назад в профиль'\n"
                 "3. Теперь должен открыться личный кабинет!\n\n"
                 "Проверяем:",
            reply_markup=reply_markup
        )
        print(f"✅ Тестовое сообщение отправлено: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_back_button_test())