#!/usr/bin/env python3
"""
Тестирование функции с пустым списком товаров
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def test_empty_products():
    """Тестировать логику для пользователя без товаров"""

    print("=== Тестирование пользователя без товаров ===")

    try:
        sheets = GoogleSheetsManager()

        # Получаем пользователя без товаров
        user_id = 233168669
        supplier = sheets.get_supplier_by_telegram_id(user_id)

        if not supplier:
            print("Пользователь не найден")
            return

        supplier_id = supplier['internal_id']
        print(f"Пользователь: {supplier.get('contact_name')} (ID: {supplier_id})")

        # Получаем товары
        products = sheets.get_products_by_supplier_id(supplier_id)
        print(f"Найдено товаров: {len(products)}")
        print(f"Тип products: {type(products)}")

        if products:
            print("Товары найдены (неожиданно):")
            for i, p in enumerate(products[:2], 1):
                print(f"  {i}: {p}")
        else:
            print("✅ Товаров нет (ожидаемо)")

            # Тестируем что возвращает products
            if products is None:
                print("products is None")
            elif products == []:
                print("products is empty list []")
            else:
                print(f"products is: {products}")

        # Тестируем формирование сообщения как в show_my_products
        print(f"\n--- Тест формирования сообщения ---")

        if not products:
            print("✅ Условие 'if not products' сработало")

            # Формируем сообщение как в коде
            message = "📦 *Мои товары*\n\n"
            message += "У вас пока нет сохраненных товаров.\n\n"
            message += "Используйте кнопку 📸 ФОТО для добавления товаров."

            print("Сообщение:")
            print(message)
            print("✅ Сообщение сформировано успешно")
        else:
            print("❌ Условие 'if not products' НЕ сработало (проблема!)")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_empty_products()