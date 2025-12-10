#!/usr/bin/env python3
"""
Тест сохранения и получения товаров
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager
import uuid

print("=== Тест сохранения и получения товаров ===")

try:
    # Инициализация
    sheets = GoogleSheetsManager()

    # Тестовые данные
    supplier_id = "test_supplier_001"
    location_id = "test_location_001"
    product_id = str(uuid.uuid4())

    print(f"Сохраняем тестовый товар...")
    print(f"Product ID: {product_id}")
    print(f"Supplier ID: {supplier_id}")
    print(f"Location ID: {location_id}")

    # Сохраняем товар
    result = sheets.add_product(
        product_id=product_id,
        supplier_internal_id=supplier_id,
        location_id=location_id,
        short_description="Тестовый товар",
        full_description="Это тестовое описание товара для проверки сохранения",
        quantity=100,
        image_urls="https://example.com/test.jpg"
    )

    print(f"Результат сохранения: {result}")

    # Получаем товары поставщика
    print(f"\nПолучаем товары для поставщика {supplier_id}...")
    products = sheets.get_products_by_supplier_id(supplier_id)

    print(f"Найдено товаров: {len(products)}")

    for i, product in enumerate(products, 1):
        print(f"\nТовар {i}:")
        print(f"  ID: {product.get('product_id', 'N/A')}")
        print(f"  Название: {product.get('name', 'N/A')}")
        print(f"  Количество: {product.get('quantity', 'N/A')}")
        print(f"  Фото: {product.get('photo_urls', 'N/A')}")
        print(f"  Создан: {product.get('created_at', 'N/A')}")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()