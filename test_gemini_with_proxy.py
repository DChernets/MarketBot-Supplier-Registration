#!/usr/bin/env python3
"""
Тест Gemini сервиса с прокси
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.gemini_service import initialize_gemini_service, get_gemini_service

print("=== Тест Gemini сервиса с прокси ===")

# Тест инициализации
try:
    success = initialize_gemini_service()
    print(f"Инициализация Gemini сервиса: {'✅ Успех' if success else '❌ Ошибка'}")

    if success:
        # Тест распознавания изображения
        service = get_gemini_service()

        # Создаем тестовое изображение
        from PIL import Image
        import io

        img = Image.new('RGB', (200, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        print("\nТест распознавания изображения...")
        result = service.recognize_product(img_bytes)

        print(f"Краткое описание: {result['short_description']}")
        print(f"Полное описание: {result['full_description']}")

        print("\n✅ Gemini API с прокси работает отлично!")

    else:
        print("❌ Не удалось инициализировать Gemini сервис")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()