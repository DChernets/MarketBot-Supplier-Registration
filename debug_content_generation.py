#!/usr/bin/env python3
"""
Диагностика проблем с генерацией контента
"""

import sys
import os
import asyncio

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """Проверка конфигурации"""
    print("🔍 Проверка конфигурации...")

    from src.config import ENABLE_CONTENT_GENERATION, AUTO_GENERATE_CONTENT, GEMINI_API_KEY

    print(f"ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")
    print(f"AUTO_GENERATE_CONTENT: {AUTO_GENERATE_CONTENT}")
    print(f"GEMINI_API_KEY установлен: {'Да' if GEMINI_API_KEY else 'Нет'}")

    return ENABLE_CONTENT_GENERATION and bool(GEMINI_API_KEY)

def test_service_initialization():
    """Проверка инициализации сервиса"""
    print("\n🔍 Проверка инициализации сервиса...")

    try:
        from src.google_sheets import GoogleSheetsManager

        # Пробуем инициализировать sheets manager
        print("Инициализация GoogleSheetsManager...")
        sheets_manager = GoogleSheetsManager()
        print(f"✅ GoogleSheetsManager: {type(sheets_manager)}")

        # Пробуем инициализировать сервис генерации контента
        from src.content_generation_service import get_content_generation_service

        print("Инициализация ContentGenerationService...")
        content_service = get_content_generation_service(sheets_manager)
        print(f"✅ ContentGenerationService: {type(content_service)}")

        # Проверяем атрибуты
        print(f"  - text_model: {hasattr(content_service, 'text_model')}")
        print(f"  - image_model: {hasattr(content_service, 'image_model')}")
        print(f"  - usage_limits: {hasattr(content_service, 'usage_limits')}")

        return True, content_service

    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_bot_initialization():
    """Проверка инициализации бота"""
    print("\n🔍 Проверка инициализации бота...")

    try:
        from src.main import MarketBot

        print("Создание экземпляра бота...")
        bot = MarketBot()

        print(f"✅ Бот создан: {type(bot)}")
        print(f"  - content_generation_service: {getattr(bot, 'content_generation_service', 'None')}")
        print(f"  - services_initialized: {getattr(bot, 'services_initialized', False)}")

        return True, bot

    except Exception as e:
        print(f"❌ Ошибка создания бота: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def test_service_methods(service):
    """Проверка методов сервиса"""
    print("\n🔍 Проверка методов сервиса...")

    try:
        # Тестовые данные
        product_info = {
            'название': 'Тестовый товар',
            'описание': 'Тестовое описание',
            'материал': 'Пластик'
        }

        # Проверка лимитов
        print("Проверка лимитов...")
        limit_check = service.usage_limits.check_daily_limit(12345, "test_product", "content_enhancement")
        print(f"✅ Проверка лимитов: {limit_check}")

        return True

    except Exception as e:
        print(f"❌ Ошибка методов сервиса: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция диагностики"""
    print("🚀 Запуск диагностики системы генерации контента\n")

    # 1. Проверка конфигурации
    config_ok = test_config()

    # 2. Проверка инициализации сервиса
    service_ok, service = test_service_initialization()

    # 3. Проверка инициализации бота
    bot_ok, bot = test_bot_initialization()

    # 4. Проверка методов сервиса
    methods_ok = False
    if service:
        methods_ok = asyncio.run(test_service_methods(service))

    # Итоги
    print(f"\n📊 Результаты диагностики:")
    print(f"✅ Конфигурация: {'OK' if config_ok else 'ПРОБЛЕМА'}")
    print(f"✅ Сервис генерации: {'OK' if service_ok else 'ПРОБЛЕМА'}")
    print(f"✅ Инициализация бота: {'OK' if bot_ok else 'ПРОБЛЕМА'}")
    print(f"✅ Методы сервиса: {'OK' if methods_ok else 'ПРОБЛЕМА'}")

    # Рекомендации
    print(f"\n💡 Рекомендации:")

    if not config_ok:
        print("  - Проверьте переменные окружения в .env файле")
        print("  - Убедитесь что ENABLE_CONTENT_GENERATION=True")
        print("  - Проверьте что GEMINI_API_KEY установлен")

    if not service_ok:
        print("  - Проблема с инициализацией сервиса генерации контента")
        print("  - Проверьте импорты и зависимости")

    if not bot_ok:
        print("  - Проблема с инициализацией бота")
        print("  - content_generation_service может быть None")

    if not methods_ok:
        print("  - Проблема с методами сервиса")
        print("  - Проверьте работу usage_limits")

    if all([config_ok, service_ok, bot_ok, methods_ok]):
        print("  🎉 Все компоненты работают корректно!")
    else:
        print("  ⚠️ Найдены проблемы, которые нужно решить")

if __name__ == "__main__":
    main()