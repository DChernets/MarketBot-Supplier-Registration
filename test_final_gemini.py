#!/usr/bin/env python3
"""
Финальный тест работы Gemini API с правильной моделью
"""

import os
import sys
import asyncio
sys.path.append('/root/myAI/MarketBot')

# Устанавливаем прокси
os.environ['HTTP_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'
os.environ['HTTPS_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'

from src.gemini_service import get_gemini_service

async def test_product_recognition():
    """Тестируем распознавание товара"""
    print("🛒 Финальный тест распознавания товара")
    print("=" * 50)

    try:
        # Получаем сервис
        gemini_service = get_gemini_service()
        print(f"✅ Сервис Gemini инициализирован с моделью: {gemini_service.model.model_name}")

        # Создаем тестовое изображение (1x1 пиксель)
        from PIL import Image
        import io

        # Создаем простое тестовое изображение
        test_image = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        image_bytes = img_bytes.getvalue()

        print("🖼️ Тестовое изображение создано")

        # Распознаем товар
        print("🤖 Начинаем распознавание...")
        result = await gemini_service.recognize_product(image_bytes)

        print("📊 Результат распознавания:")
        print("-" * 30)
        for key, value in result.items():
            print(f"{key}: {value}")
        print("-" * 30)

        # Проверяем результат
        if result and result.get('название') != 'Неизвестный товар':
            print("🎉 РАСПОЗНАВАНИЕ РАБОТАЕТ!")
            return True
        else:
            print("❌ Распознавание не сработало корректно")
            return False

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Финальная проверка Gemini API")
    print("=" * 50)

    success = asyncio.run(test_product_recognition())

    print("\n" + "=" * 50)
    if success:
        print("🎉 Готово! Gemini API работает корректно")
        print("✅ Бот готов к распознаванию товаров")
    else:
        print("❌ Проблемы с Gemini API")
        print("🔧 Проверьте логи выше")