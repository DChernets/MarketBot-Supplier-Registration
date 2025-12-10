#!/usr/bin/env python3
"""
Тест сохранения Telegram URL для фото
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager
import uuid

print("=== Тест сохранения Telegram URL для фото ===")

try:
    # Инициализация
    sheets = GoogleSheetsManager()

    # Тестовые данные с Telegram URL
    supplier_id = "test_telegram_001"
    location_id = "test_location_001"
    product_id = str(uuid.uuid4())

    # Пример Telegram URL (формат)
    telegram_url = "https://api.telegram.org/file/botTOKEN/photos/file_1.jpg"

    print(f"Сохраняем товар с Telegram URL...")
    print(f"Product ID: {product_id}")
    print(f"Telegram URL: {telegram_url}")

    # Сохраняем товар
    result = sheets.add_product(
        product_id=product_id,
        supplier_internal_id=supplier_id,
        location_id=location_id,
        short_description="Товар с фото из Telegram",
        full_description="Тестирование сохранения прямого URL на фото из Telegram",
        quantity=50,
        image_urls=telegram_url
    )

    print(f"Результат сохранения: {result}")

    # Получаем товары для проверки
    print(f"\nПроверяем сохранение...")
    products = sheets.get_products_by_supplier_id(supplier_id)

    print(f"Найдено товаров: {len(products)}")

    for i, product in enumerate(products, 1):
        print(f"\nТовар {i}:")
        print(f"  ID: {product.get('product_id', 'N/A')}")
        print(f"  Название: {product.get('name', 'N/A')}")
        print(f"  Количество: {product.get('quantity', 'N/A')}")
        print(f"  Фото URL: {product.get('photo_urls', 'N/A')}")
        print(f"  Фото URL тип: {type(product.get('photo_urls', 'N/A'))}")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()