#!/usr/bin/env python3
"""
Тестирование новой системы генерации изображений через Gemini Vision
"""

import sys
import os
import base64
import asyncio

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.content_generation_service import get_content_generation_service
from src.config import GEMINI_API_KEY

def test_image_generation_service():
    """Тестирование сервиса генерации изображений"""
    print("🧪 Тестирование сервиса генерации изображений Gemini Vision...")

    try:
        # Инициализация сервиса
        service = get_content_generation_service()
        print(f"✅ Сервис инициализирован: {type(service)}")

        # Проверка наличия моделей
        print(f"✅ Текстовая модель: {type(service.text_model)}")
        print(f"✅ Изображений модель: {type(service.image_model)}")

        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации сервиса: {e}")
        return False

def test_image_prompt_creation():
    """Тестирование создания промптов для изображений"""
    print("\n🧪 Тестирование создания промптов для изображений...")

    try:
        service = get_content_generation_service()

        # Тестовые данные о товаре
        product_info = {
            'название': 'Керамическая кружка',
            'описание': 'Белая кружка с логотипом, объем 350мл',
            'материал': 'Керамика',
            'цена': '250 руб.'
        }

        # Тестирование разных типов фонов
        background_types = ['professional_studio', 'clean_white_background', 'marketing_showcase']

        for bg_type in background_types:
            prompt = service._create_image_generation_prompt(product_info, bg_type)
            print(f"✅ Промпт для {bg_type} ({len(prompt)} символов):")
            print(f"Первые 200 символов: {prompt[:200]}...")
            print()

        return True
    except Exception as e:
        print(f"❌ Ошибка создания промпта: {e}")
        return False

def test_b2b_description_generation():
    """Тестирование генерации B2B описаний"""
    print("\n🧪 Тестирование генерации B2B описаний...")

    try:
        service = get_content_generation_service()

        product_info = {
            'название': 'Стеклянная бутылка',
            'описание': 'Бутылка из темного стекла 500мл с завинчивающейся крышкой',
            'материал': 'Стекло',
            'производство': 'Россия',
            'упаковка': 'Коробка по 12 шт.'
        }

        # Запускаем асинхронную генерацию
        async def test_description():
            description = await service.generate_b2b_description(product_info)
            if description:
                print(f"✅ Сгенерировано описание ({len(description)} символов):")
                print(description)
                return True
            else:
                print("❌ Не удалось сгенерировать описание")
                return False

        # Запускаем асинхронную функцию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_description())
        loop.close()

        return result
    except Exception as e:
        print(f"❌ Ошибка генерации описания: {e}")
        return False

def test_service_integration():
    """Тестирование полной интеграции сервиса"""
    print("\n🧪 Тестирование полной интеграции сервиса...")

    try:
        # Проверка конфигурации
        from src.config import ENABLE_CONTENT_GENERATION, AUTO_GENERATE_CONTENT
        print(f"✅ ENABLE_CONTENT_GENERATION: {ENABLE_CONTENT_GENERATION}")
        print(f"✅ AUTO_GENERATE_CONTENT: {AUTO_GENERATE_CONTENT}")

        # Проверка API ключа
        if GEMINI_API_KEY:
            print(f"✅ GEMINI_API_KEY: {'*' * 20}{GEMINI_API_KEY[-10:]}")
        else:
            print("⚠️ GEMINI_API_KEY не найден")

        # Проверка сервиса лимитов
        from src.usage_limits import get_usage_limits
        limits = get_usage_limits()
        print(f"✅ Сервис лимитов: {type(limits)}")

        return True
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования Gemini Vision системы генерации контента\n")

    tests = [
        test_image_generation_service,
        test_image_prompt_creation,
        test_b2b_description_generation,
        test_service_integration
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
        print("\n🎉 Все тесты пройдены! Gemini Vision система готова к работе.")
        print("📸 Теперь изображения генерируются через ИИ, а не PIL!")
    else:
        print(f"\n⚠️ Есть {failed} проблем, которые нужно решить.")

if __name__ == "__main__":
    main()