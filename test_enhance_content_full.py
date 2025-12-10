#!/usr/bin/env python3
"""
🚀 Полный тест функционала улучшения контента
"""

import sys
import os
sys.path.append('.')

from src.main import MarketBot
from src.config import ENABLE_CONTENT_GENERATION
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
import asyncio

async def test_enhance_content_functionality():
    """Тестируем полный функционал улучшения контента"""

    print("🚀 Полный тест функционала улучшения контента")
    print("=" * 50)

    # Создаем экземпляр бота
    bot = MarketBot()

    print("🔍 Проверка инициализации...")
    print(f"  services_initialized: {bot.services_initialized}")
    print(f"  content_generation_service: {bot.content_generation_service is not None}")

    # Инициализируем сервисы
    if not bot.services_initialized:
        print("\n🔄 Инициализация сервисов...")
        await bot.initialize_services()
        print(f"  После инициализации: {bot.services_initialized}")
        print(f"  content_generation_service: {bot.content_generation_service is not None}")

    # Проверяем настройку обработчиков
    print(f"\n🎯 Проверка обработчиков...")
    print(f"  Количество обработчиков в приложении: {len(bot.application.handlers)}")

    # Проверяем наличие обработчиков для разных типов сообщений
    all_handlers = []
    for group_handlers in bot.application.handlers.values():
        all_handlers.extend(group_handlers)

    callback_handlers = [h for h in all_handlers if isinstance(h, CallbackQueryHandler)]
    command_handlers = [h for h in all_handlers if isinstance(h, CommandHandler)]
    message_handlers = [h for h in all_handlers if isinstance(h, MessageHandler)]

    print(f"  Callback handlers: {len(callback_handlers)}")
    print(f"  Command handlers: {len(command_handlers)}")
    print(f"  Message handlers: {len(message_handlers)}")
    print(f"  Всего обработчиков: {len(all_handlers)}")

    if callback_handlers:
        print(f"  ✅ CallbackQueryHandler найден: {callback_handlers[0]}")

    # Проверяем конфигурацию
    print(f"\n⚙️ Проверка конфигурации...")
    print(f"  ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")
    print(f"  bot.content_generation_service: {bot.content_generation_service is not None}")

    # Проверяем логику кнопок
    should_add_button = ENABLE_CONTENT_GENERATION and bot.content_generation_service
    print(f"  Кнопка должна быть добавлена: {should_add_button}")

    if should_add_button:
        print(f"\n🎉 Тест создания кнопки...")
        from telegram import InlineKeyboardButton

        test_product_id = "test_product_123"
        callback_data = f"enhance_content_{test_product_id}"
        button = InlineKeyboardButton("✨ Улучшить контент", callback_data=callback_data)

        print(f"  ✅ Кнопка создана: {button.text}")
        print(f"  ✅ Callback data: {button.callback_data}")

        # Проверяем обработчик callback
        print(f"\n🔄 Проверка обработки callback...")

        # Имитируем callback query
        class MockQuery:
            def __init__(self):
                self.data = callback_data
                self.from_user = MockUser()

            async def answer(self):
                pass

        class MockUser:
            def __init__(self):
                self.id = 12345

        # Проверяем, что обработчик распознает callback
        if callback_handlers:
            for handler in callback_handlers:
                pattern = getattr(handler, 'pattern', None)
                if pattern:
                    import re
                    if re.match(pattern, callback_data):
                        print(f"  ✅ Handler matched pattern: {pattern}")
                        break
            else:
                print(f"  ⚠️ No handler matched for callback_data: {callback_data}")
        else:
            print(f"  ❌ No callback handlers found")

    print(f"\n📊 Результат теста:")
    if should_add_button and callback_handlers:
        print("  ✅ Все компоненты для кнопки 'Улучшить контент' на месте!")
        print("  ✅ Кнопка должна отображаться и обрабатываться корректно")
    else:
        print("  ❌ Проблема с компонентами:")
        if not should_add_button:
            print("    - Кнопка не будет добавлена (проверьте ENABLE_CONTENT_GENERATION или сервис)")
        if not callback_handlers:
            print("    - Нет обработчиков для callback")

    return should_add_button and bool(callback_handlers)

if __name__ == "__main__":
    try:
        result = asyncio.run(test_enhance_content_functionality())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)