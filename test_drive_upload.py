#!/usr/bin/env python3
"""
Тест загрузки файла в Google Drive через новый Service Account
"""

import sys
sys.path.append('/root/myAI/MarketBot')

from src.image_storage import ImageStorageService
import asyncio

async def test_upload():
    """Тест загрузки тестового изображения"""
    print("🧪 Тест загрузки в Google Drive...")

    try:
        # Инициализируем сервис
        storage = ImageStorageService()
        initialized = await storage.initialize()

        if not initialized:
            print("❌ Не удалось инициализировать сервис")
            return

        print("✅ Сервис инициализирован")

        # Создаем тестовое изображение
        from PIL import Image
        import io

        # Создаем простое тестовое изображение
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # Загружаем в Google Drive
        print("📤 Загружаем тестовое изображение...")
        url = await storage.upload_image(
            image_bytes=img_bytes.getvalue(),
            filename="test_image.jpg",
            product_id="test_product"
        )

        if url:
            print(f"✅ Изображение успешно загружено!")
            print(f"URL: {url}")
        else:
            print("❌ Не удалось загрузить изображение")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_upload())