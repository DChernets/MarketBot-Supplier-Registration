#!/usr/bin/env python3
"""
Тест работы gspread через прокси
"""

import os
import sys
sys.path.append('/root/myAI/MarketBot')

# Устанавливаем прокси
os.environ['HTTP_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'
os.environ['HTTPS_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'

from src.config import GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEETS_SPREADSHEET_ID
from src.google_sheets import GoogleSheetsManager

def test_gspread_manager():
    """Тест GoogleSheetsManager"""
    print("🔍 Тест GoogleSheetsManager через прокси")
    print("=" * 50)

    try:
        print("📋 Инициализация GoogleSheetsManager...")
        manager = GoogleSheetsManager()
        print("✅ Менеджер успешно инициализирован")

        print("\n👥 Тест получения поставщиков...")
        suppliers = manager.suppliers_sheet.get_all_records()
        print(f"📊 Найдено поставщиков: {len(suppliers)}")

        if suppliers:
            print("📄 Первые 2 поставщика:")
            for i, supplier in enumerate(suppliers[:2]):
                print(f"  {i+1}: {supplier}")

        print("\n📍 Тест получения локаций...")
        locations = manager.locations_sheet.get_all_records()
        print(f"📊 Найдено локаций: {len(locations)}")

        if locations:
            print("📄 Первые 2 локации:")
            for i, location in enumerate(locations[:2]):
                print(f"  {i+1}: {location}")

        print("\n🛒 Тест получения товаров...")
        products = manager.products_sheet.get_all_records()
        print(f"📊 Найдено товаров: {len(products)}")

        if products:
            print("📄 Первые 2 товара:")
            for i, product in enumerate(products[:2]):
                print(f"  {i+1}: {product}")

        print("\n🎉 GoogleSheetsManager работает корректно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка GoogleSheetsManager: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_get_supplier():
    """Тест получения поставщика по telegram_id"""
    print("\n👤 Тест get_supplier_by_telegram_id...")

    try:
        manager = GoogleSheetsManager()

        # Пробуем получить с тестовым ID
        test_id = 123456789
        supplier = manager.get_supplier_by_telegram_id(test_id)

        if supplier:
            print(f"✅ Поставщик найден: {supplier}")
        else:
            print(f"ℹ️ Поставщик с ID {test_id} не найден (нормально)")

        # Проверяем реальных поставщиков
        suppliers = manager.suppliers_sheet.get_all_records()
        if suppliers:
            first_supplier = suppliers[0]
            telegram_id = first_supplier.get('telegram_user_id')
            if telegram_id:
                print(f"🔍 Поиск поставщика с telegram_id: {telegram_id}")
                found_supplier = manager.get_supplier_by_telegram_id(telegram_id)
                if found_supplier:
                    print(f"✅ Поставщик найден по telegram_id: {found_supplier.get('contact_name', 'Unknown')}")
                else:
                    print(f"❌ Поставщик с telegram_id {telegram_id} не найден")

        return True

    except Exception as e:
        print(f"❌ Ошибка при поиске поставщика: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Тестирование gspread через прокси")
    print("=" * 60)

    # Тест менеджера
    manager_works = test_gspread_manager()

    # Тест поиска поставщика
    search_works = test_get_supplier()

    print("\n" + "=" * 60)
    print("📊 ИТОГИ:")
    print(f"📋 Менеджер: {'✅ Работает' if manager_works else '❌ Не работает'}")
    print(f"👤 Поиск поставщика: {'✅ Работает' if search_works else '❌ Не работает'}")

    if manager_works and search_works:
        print("\n🎉 Все компоненты работают корректно!")
    else:
        print("\n🚨 Требуется исправление ошибок")