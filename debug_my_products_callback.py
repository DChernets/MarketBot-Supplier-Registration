#!/usr/bin/env python3
"""
Отладка callback'а my_products из главного меню
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def debug_my_products_callback():
    """Отладка проблемы с callback'ом my_products"""

    print("=== Отладка callback'а my_products ===")

    try:
        # Тестируем получение поставщика по разным user_id
        test_user_ids = [233168669, 6477828562, 123456789]  # Разные пользователи из данных

        sheets = GoogleSheetsManager()

        for user_id in test_user_ids:
            print(f"\n--- Тест для user_id: {user_id} ---")

            try:
                # Тестируем get_supplier_by_telegram_id
                supplier = sheets.get_supplier_by_telegram_id(user_id)

                if supplier:
                    print(f"✅ Поставщик найден:")
                    for key, value in supplier.items():
                        print(f"  {key}: {value} (тип: {type(value).__name__})")

                    supplier_id = supplier.get('internal_id')
                    if supplier_id:
                        print(f"\n📦 Тестируем get_products_by_supplier_id с ID: {supplier_id}")
                        products = sheets.get_products_by_supplier_id(supplier_id)
                        print(f"Найдено товаров: {len(products)}")

                        if products:
                            print("Первые 2 товара:")
                            for i, product in enumerate(products[:2], 1):
                                print(f"  Товар {i}:")
                                for key, value in product.items():
                                    print(f"    {key}: {value}")
                        else:
                            print("⚠️ Товаров не найдено")
                    else:
                        print("❌ Нет internal_id у поставщика")
                else:
                    print("❌ Поставщик не найден")

            except Exception as e:
                print(f"❌ Ошибка для user_id {user_id}: {e}")
                import traceback
                traceback.print_exc()

        # Дополнительная проверка: посмотрим на всех поставщиков
        print(f"\n--- Все поставщики в системе ---")
        all_suppliers = sheets.suppliers_sheet.get_all_records()
        print(f"Всего поставщиков: {len(all_suppliers)}")

        for supplier in all_suppliers:
            user_id = supplier.get('telegram_user_id', 'unknown')
            internal_id = supplier.get('internal_id', 'no_id')
            contact_name = supplier.get('contact_name', 'no_name')
            print(f"  User ID: {user_id}, Internal ID: {internal_id}, Name: {contact_name}")

        # Проверим товары и их supplier_id
        print(f"\n--- Все товары в системе ---")
        all_products = sheets.products_sheet.get_all_records()
        print(f"Всего товаров: {len(all_products)}")

        supplier_ids_in_products = set()
        for product in all_products:
            sid = product.get('supplier_id', '')
            if sid:
                supplier_ids_in_products.add(sid)

        print(f"Supplier IDs в товарах: {supplier_ids_in_products}")

        # Проверим находимость supplier_id из товаров в списке поставщиков
        print(f"\n--- Проверка связей поставщик-товар ---")
        for sid in supplier_ids_in_products:
            found = False
            for supplier in all_suppliers:
                if supplier.get('internal_id') == sid:
                    print(f"✅ {sid} -> {supplier.get('contact_name', 'unknown')} (user_id: {supplier.get('telegram_user_id')})")
                    found = True
                    break
            if not found:
                print(f"❌ {sid} -> поставщик не найден!")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_my_products_callback()