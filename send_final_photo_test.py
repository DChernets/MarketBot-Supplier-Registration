#!/usr/bin/env python3
"""
Отправить финальную тестовую кнопку с функцией скачивания фото
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def send_final_photo_test():
    """Отправить финальный тест с новой функцией фото"""

    print("=== Отправка финального теста фото ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # Создаем кнопку с правильным callback_data
        keyboard = [
            [InlineKeyboardButton("📦 ТОВАРЫ С ФОТО (НОВАЯ ВЕРСИЯ) 🖼️", callback_data="my_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопкой
        test_user_id = 233168669
        print(f"Отправляем финальное тестовое сообщение пользователю {test_user_id}...")

        message = await bot.send_message(
            chat_id=test_user_id,
            text="🔥 *УЛУЧШЕННАЯ ВЕРСИЯ ФОТО*\n\n"
                 "Проблема 'Wrong type of web page content' ИСПРАВЛЕНА!\n\n"
                 "📸 Теперь бот:\n"
                 "• СКАЧИВАЕТ фото с Telegram серверов\n"
                 "• ПЕРЕЗАГРУЖАЕТ их как новые файлы\n"
                 "• ПОКАЗЫВАЕТ изображения напрямую в чате\n\n"
                 "Как в интернет-магазинах - фото видно сразу!\n\n"
                 "Нажмите кнопку для теста:",
            reply_markup=reply_markup
        )
        print(f"✅ Финальное тестовое сообщение отправлено: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_final_photo_test())