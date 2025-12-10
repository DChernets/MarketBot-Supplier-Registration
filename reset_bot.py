#!/usr/bin/env python3
"""
Сброс состояния бота и webhook
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import os
from telegram import Bot

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs')

async def reset_bot():
    """Сбросить webhook и состояние бота"""

    print("=== Сброс состояния бота ===")

    try:
        bot = Bot(token=BOT_TOKEN)

        # 1. Удаляем webhook
        print("Удаляем webhook...")
        webhook_info = await bot.delete_webhook(drop_pending_updates=True)
        print(f"Webhook удален: {webhook_info}")

        # 2. Получаем информацию о боте
        me = await bot.get_me()
        print(f"Bot info: {me.first_name} (@{me.username})")

        # 3. Проверяем что polling работает
        print("Проверяем обновления...")
        updates = await bot.get_updates(timeout=5, limit=1)
        print(f"Получено обновлений: {len(updates)}")

        print("✅ Бот успешно сброшен и готов к работе")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(reset_bot())