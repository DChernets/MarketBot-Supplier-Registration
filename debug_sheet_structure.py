#!/usr/bin/env python3
"""
Проверка структуры Google Sheets таблицы
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

print("=== Проверка структуры Google Sheets таблицы ===")

try:
    # Инициализация
    sheets = GoogleSheetsManager()

    # Получаем все данные из листа products
    print("\nДанные из листа products:")
    all_values = sheets.products_sheet.get_all_values()
    print(f"Всего строк: {len(all_values)}")

    # Показываем заголовки
    if all_values:
        headers = all_values[0]
        print(f"\nЗаголовки ({len(headers)}):")
        for i, header in enumerate(headers):
            print(f"  {i}: '{header}'")

        # Показываем первые несколько строк данных
        print(f"\nПервые 3 строки данных:")
        for row_num, row in enumerate(all_values[1:4], 2):
            print(f"Строка {row_num}: {row}")

        # Получаем данные через get_all_records
        print(f"\nДанные через get_all_records():")
        records = sheets.products_sheet.get_all_records()
        print(f"Всего записей: {len(records)}")

        if records:
            print("\nПервая запись:")
            for key, value in records[0].items():
                print(f"  {key}: '{value}'")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()