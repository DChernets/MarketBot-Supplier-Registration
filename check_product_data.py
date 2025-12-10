#!/usr/bin/env python3
"""
Проверить какие данные сохранены для товара
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def check_product_data():
    """Проверить данные товара в таблице"""

    print("=== Проверка данных товара ===")

    try:
        sheets = GoogleSheetsManager()

        # Ищем товар по ID который видит пользователь
        product_id = "c0a81076-039d-4d65-84d6-f30ce5c444eb"

        product = sheets.get_product_by_id(product_id)

        if product:
            print(f"Найден товар:")
            print(f"ID: {product_id}")
            print(f"Полные данные: {product}")
            print()

            # Проверяем конкретные поля
            print("Поля товара:")
            for key, value in product.items():
                print(f"  {key}: {value}")

        else:
            print(f"Товар с ID {product_id} не найден")

            # Поищем все товары пользователя
            user_id = 233168669
            supplier = sheets.get_supplier_by_telegram_id(user_id)

            if supplier:
                supplier_id = supplier['internal_id']
                products = sheets.get_products_by_supplier_id(supplier_id)

                print(f"\nВсе товары пользователя ({len(products)} шт.):")
                for i, product in enumerate(products, 1):
                    print(f"\nТовар {i}:")
                    print(f"  product_id: {product.get('product_id')}")
                    print(f"  name: {product.get('name')}")
                    print(f"  description: {product.get('description')}")
                    print(f"  recognition_data: {product.get('recognition_data')}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_product_data()