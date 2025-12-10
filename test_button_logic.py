#!/usr/bin/env python3
"""
Тестирование логики кнопок
"""

import sys
import os
import asyncio

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_button_logic():
    """Тестирование логики добавления кнопок"""
    print("🧪 Тестирование логики кнопок...")

    try:
        from src.main import MarketBot
        from src.config import ENABLE_CONTENT_GENERATION

        print(f"ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")

        # Создаем экземпляр бота
        bot = MarketBot()
        print(f"Бот создан: {type(bot)}")

        # Симулируем инициализацию сервисов (как в show_my_products)
        if not bot.services_initialized:
            print("Инициализация сервисов...")
            await bot.initialize_services()
            print(f"Сервисы инициализированы: {bot.services_initialized}")
            print(f"content_generation_service: {getattr(bot, 'content_generation_service', 'None')}")

        # Симулируем проверку кнопки
        product_id = "test_product_123"
        user_id = 12345

        # Проверяем условия как в show_my_products
        should_add_button = ENABLE_CONTENT_GENERATION and bot.content_generation_service

        print(f"Должна ли быть добавлена кнопка: {should_add_button}")

        if should_add_button:
            print("✅ Кнопка '✨ Улучшить контент' будет добавлена")

            # Проверяем лимиты
            limit_check = bot.content_generation_service.usage_limits.check_daily_limit(
                user_id, product_id, 'content_enhancement'
            )
            print(f"Лимиты: {limit_check}")

            if limit_check['allowed']:
                button_text = "✨ Улучшить контент"
            else:
                button_text = f"✨ Улучшить контент ({limit_check['remaining']})"

            print(f"Текст кнопки: {button_text}")
        else:
            print("❌ Кнопка '✨ Улучшить контент' НЕ будет добавлена")
            print(f"  ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")
            print(f"  content_generation_service: {getattr(bot, 'content_generation_service', 'None')}")

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование логики кнопок улучшения контента\n")

    result = asyncio.run(test_button_logic())

    if result:
        print("\n✅ Тест логики кнопок пройден успешно!")
    else:
        print("\n❌ Проблема в логике кнопок")

if __name__ == "__main__":
    main()