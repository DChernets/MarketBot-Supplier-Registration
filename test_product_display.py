#!/usr/bin/env python3
"""
Тестирование функции отображения товаров с обработкой ошибок
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def test_show_my_products():
    """Тестировать логику отображения товаров"""

    print("=== Тестирование отображения товаров ===")

    try:
        sheets = GoogleSheetsManager()

        # Предположим что это ID пользователя (для теста)
        user_id = 123456789  # Замените на реальный ID если нужно

        # Получаем поставщика по user_id (для теста используем первого)
        suppliers = sheets.suppliers_sheet.get_all_records()
        if not suppliers:
            print("Нет поставщиков в таблице")
            return

        supplier = suppliers[0]  # Берем первого для теста
        print(f"Структура данных поставщика:")
        for key, value in supplier.items():
            print(f"  {key}: {value} (тип: {type(value).__name__})")

        # Получим все товары и проверим их supplier_id
        all_products = sheets.products_sheet.get_all_records()
        print(f"Всего товаров в таблице: {len(all_products)}")

        # Найдем уникальные supplier_id в товарах
        supplier_ids_in_products = set()
        for product in all_products:
            sid = product.get('supplier_id', '')
            if sid:
                supplier_ids_in_products.add(sid)

        print(f"Supplier IDs в товарах: {supplier_ids_in_products}")

        # Найдем поставщика у которого есть товары
        supplier_with_products = None
        for sid in supplier_ids_in_products:
            matching_supplier = next((s for s in suppliers if s.get('internal_id') == sid), None)
            if matching_supplier:
                supplier_with_products = matching_supplier
                break

        if not supplier_with_products:
            print("Не найдено поставщиков с товарами")
            return

        supplier_id = supplier_with_products.get('internal_id')
        company_name = supplier_with_products.get('company_name', supplier_with_products.get('name', 'Unknown'))
        telegram_user_id = supplier_with_products.get('telegram_user_id', 'Unknown')

        print(f"Тест для поставщика: {company_name} (ID: {supplier_id}, Telegram ID: {telegram_user_id})")

        # Получаем товары поставщика
        products = sheets.get_products_by_supplier_id(supplier_id)
        print(f"Найдено товаров: {len(products)}")

        if not products:
            print("Ошибка: товары должны быть но не найдены")
            return

        # Тестируем формирование сообщения для каждого товара
        print("\n=== Тестирование форматирования ===")
        for i, product in enumerate(products, 1):
            print(f"\nТовар {i}:")

            # Получаем данные с обработкой ошибок
            short_desc = product.get('name', 'Без названия')
            quantity = product.get('quantity', 'Не указано')
            created_at = product.get('created_at', '')
            photo_url = product.get('photo_urls', '')

            print(f"  name: '{short_desc}' (тип: {type(short_desc).__name__})")
            print(f"  quantity: '{quantity}' (тип: {type(quantity).__name__})")
            print(f"  created_at: '{created_at}' (тип: {type(created_at).__name__})")
            print(f"  photo_urls: '{photo_url}' (тип: {type(photo_url).__name__})")

            # Тестируем безопасное форматирование фото URL
            try:
                if photo_url:
                    # Убедимся что photo_url это строка перед вызовом .strip()
                    photo_url_str = str(photo_url) if photo_url else ""
                    print(f"  photo_url_str: '{photo_url_str}'")

                    if photo_url_str.strip():
                        print(f"  ✅ Фото URL будет добавлено в сообщение")
                    else:
                        print(f"  ⚠️ Пустой фото URL")
                else:
                    print(f"  ⚠️ Фото URL отсутствует")
            except Exception as e:
                print(f"  ❌ Ошибка при обработке фото URL: {e}")

            # Тестируем количество
            try:
                quantity_str = str(quantity) if quantity is not None else "0"
                print(f"  quantity_str: '{quantity_str}'")
                if quantity_str.isdigit():
                    print(f"  ✅ Количество корректное: {quantity_str}")
                else:
                    print(f"  ⚠️ Количество не число: {quantity_str}")
            except Exception as e:
                print(f"  ❌ Ошибка при обработке количества: {e}")

        # Формируем полное сообщение
        print("\n=== Полное сообщение ===")
        message = "📦 *Мои товары*\n\n"

        for i, product in enumerate(products, 1):
            try:
                short_desc = str(product.get('name', 'Без названия'))
                quantity = str(product.get('quantity', '0')) if product.get('quantity') is not None else "0"
                created_at = str(product.get('created_at', ''))
                photo_url = product.get('photo_urls', '')

                # Добавляем информацию о товаре
                message += f"🏷️ *Товар {i}*: {short_desc}\n"
                message += f"📊 Количество: {quantity}\n"

                # Безопасная обработка фото URL
                if photo_url:
                    photo_url_str = str(photo_url) if photo_url else ""
                    if photo_url_str.strip():
                        message += f"🖼️ Фото: {photo_url_str}\n"

                if created_at and created_at.strip():
                    message += f"📅 Добавлен: {created_at}\n"

                message += "\n"

            except Exception as e:
                print(f"Ошибка при форматировании товара {i}: {e}")
                message += f"❌ Ошибка при отображении товара {i}\n\n"

        print("Сообщение для пользователя:")
        print("-" * 50)
        print(message)
        print("-" * 50)

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_show_my_products()