#!/usr/bin/env python3
"""
Тестирование системы генерации контента
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.background_templates import get_background_templates
from src.usage_limits import get_usage_limits
from PIL import Image
import io

def test_background_templates():
    """Тестирование фоновых шаблонов"""
    print("🧪 Тестирование фоновых шаблонов...")

    try:
        templates = get_background_templates()
        available = templates.get_available_templates()

        print(f"✅ Доступные шаблоны: {list(available.keys())}")

        # Тестируем применение шаблона
        test_image = Image.new('RGB', (100, 100), (255, 0, 0))

        enhanced = templates.apply_background(test_image, 'professional_white')
        print(f"✅ Размер изображения после применения фона: {enhanced.size}")

        return True
    except Exception as e:
        print(f"❌ Ошибка в тестировании фоновых шаблонов: {e}")
        return False

def test_usage_limits():
    """Тестирование системы лимитов"""
    print("\n🧪 Тестирование системы лимитов...")

    try:
        usage_limits = get_usage_limits()

        # Проверка лимитов
        test_user_id = 12345
        test_product_id = "test_product_123"

        limit_check = usage_limits.check_daily_limit(
            test_user_id, test_product_id, 'content_enhancement'
        )

        print(f"✅ Проверка лимитов: {limit_check}")
        return True
    except Exception as e:
        print(f"❌ Ошибка в тестировании лимитов: {e}")
        return False

def test_import_content_generation():
    """Тестирование импорта сервиса генерации контента"""
    print("\n🧪 Тестирование импорта сервиса генерации контента...")

    try:
        from src.content_generation_service import get_content_generation_service
        print("✅ Импорт прошел успешно")

        # Проверка конфигурации
        from src.config import ENABLE_CONTENT_GENERATION, AUTO_GENERATE_CONTENT
        print(f"✅ ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")
        print(f"✅ AUTO_GENERATE_CONTENT: {AUTO_GENERATE_CONTENT}")

        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_google_sheets_integration():
    """Тестирование интеграции с Google Sheets"""
    print("\n🧪 Тестирование интеграции с Google Sheets...")

    try:
        from src.google_sheets import GoogleSheetsManager

        # Пробуем инициализировать (может вызвать ошибку без кредов)
        sheets = GoogleSheetsManager()
        print("✅ GoogleSheetsManager инициализирован")

        return True
    except Exception as e:
        print(f"⚠️ Ошибка Google Sheets (ожидаемо без кредов): {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования системы генерации контента\n")

    tests = [
        test_background_templates,
        test_usage_limits,
        test_import_content_generation,
        test_google_sheets_integration
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте: {e}")
            failed += 1

    print(f"\n📊 Результаты тестирования:")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📈 Всего: {passed + failed}")

    if failed == 0:
        print("\n🎉 Все тесты пройдены! Система готова к работе.")
    else:
        print(f"\n⚠️ Есть {failed} проблем, которые нужно решить.")

if __name__ == "__main__":
    main()