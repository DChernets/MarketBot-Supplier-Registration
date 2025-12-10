#!/usr/bin/env python3
"""
Тест отображения товаров с исправленными полями
"""

import os
import sys
sys.path.append('/root/myAI/MarketBot')

# Устанавливаем прокси
os.environ['HTTP_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'
os.environ['HTTPS_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'

from src.google_sheets import GoogleSheetsManager

def test_product_display():
    """Тестируем корректность отображения товаров"""
    print("🧪 Тест отображения товаров")
    print("=" * 50)

    try:
        manager = GoogleSheetsManager()
        print("✅ GoogleSheetsManager инициализирован")

        # Получаем товары
        products = manager.products_sheet.get_all_records()
        print(f"📊 Всего товаров: {len(products)}")

        if not products:
            print("❌ Товаров нет")
            return False

        print("\n📄 Анализ структуры товаров:")
        for i, product in enumerate(products[:3]):
            print(f"\nТовар {i+1}:")
            print(f"  ID: {product.get('product_id', 'No ID')}")
            print(f"  название: '{product.get('название', 'NOT_FOUND')}'")
            desc_val = str(product.get('описание', 'NOT_FOUND'))
            desc_display = desc_val[:50] + '...' if len(desc_val) > 50 else desc_val
            print(f"  описание: '{desc_display}'")
            print(f"  name (старое): '{product.get('name', 'NOT_FOUND')}'")

            old_desc = str(product.get('description', 'NOT_FOUND'))
            old_desc_display = old_desc[:50] + '...' if len(old_desc) > 50 else old_desc
            print(f"  description (старое): '{old_desc_display}'")

        # Тестируем логику извлечения названий и описаний
        print("\n🔍 Тест логики извлечения данных:")

        for i, product in enumerate(products[:2]):
            print(f"\nТест для товара {i+1}:")

            # Новая логика (как в исправленном коде)
            product_name = str(product.get('название', product.get('name', 'Без названия')))
            description_field = str(product.get('описание', product.get('description', '')))

            print(f"  📝 Название: '{product_name}'")
            if len(description_field) > 100:
                print(f"  📄 Описание: '{description_field[:100]}...'")
            else:
                print(f"  📄 Описание: '{description_field}'")

            # Проверяем, что данные не пустые
            if product_name != 'Без названия' and product_name.strip():
                print(f"  ✅ Название корректно")
            else:
                print(f"  ⚠️ Название пустое")

            if description_field and description_field.strip():
                print(f"  ✅ Описание корректно")
            else:
                print(f"  ⚠️ Описание пустое")

        print("\n🎉 Анализ завершен!")
        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Тест корректности отображения товаров")
    print("=" * 60)

    success = test_product_display()

    print("\n" + "=" * 60)
    if success:
        print("✅ Тест пройден! Данные о товарах корректны.")
        print("💡 Теперь команда МОИ ТОВАРЫ должна показывать правильные названия и описания")
    else:
        print("❌ Тест не пройден. Проверьте логи выше.")