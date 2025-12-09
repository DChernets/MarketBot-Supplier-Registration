#!/usr/bin/env python3
"""
Скрипт для проверки состояния базы данных
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.google_sheets import GoogleSheetsManager

def check_database_status():
    """Проверка состояния базы данных"""
    sheets = GoogleSheetsManager()

    print("📊 СОСТОЯНИЕ БАЗЫ ДАННЫХ\n")

    # Проверяем suppliers
    suppliers_data = sheets.suppliers_sheet.get_all_records()
    suppliers_count = len(suppliers_data)
    print(f"👤 Поставщики: {suppliers_count} записей")

    if suppliers_count > 0:
        print("   Список поставщиков:")
        for i, supplier in enumerate(suppliers_data, 1):
            print(f"   {i}. {supplier.get('contact_name', 'N/A')} (ID: {supplier.get('telegram_user_id', 'N/A')})")

    # Проверяем locations
    locations_data = sheets.locations_sheet.get_all_records()
    locations_count = len(locations_data)
    print(f"\n🏪 Локации: {locations_count} записей")

    if locations_count > 0:
        print("   Список локаций:")
        for i, location in enumerate(locations_data, 1):
            market = location.get('market_name', 'N/A')
            pavilion = location.get('pavilion_number', 'N/A')
            phones = location.get('contact_phones', 'N/A')
            supplier_id = location.get('supplier_internal_id', 'N/A')
            print(f"   {i}. {market} - {pavilion} ({phones}) [Supplier: {supplier_id[:8]}...]")

    # Статистика
    print(f"\n📈 СТАТИСТИКА:")
    print(f"   Всего поставщиков: {suppliers_count}")
    print(f"   Всего локаций: {locations_count}")

    if suppliers_count > 0:
        avg_locations = locations_count / suppliers_count
        print(f"   Среднее локаций на поставщика: {avg_locations:.1f}")

    print(f"\n🔧 Google Sheets подключение: ✅ Активно")

def main():
    """Главная функция"""
    check_database_status()

if __name__ == "__main__":
    main()