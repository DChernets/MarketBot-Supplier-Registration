#!/usr/bin/env python3
"""
Проверка текущих данных в products таблице
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

print("=== Проверка текущих данных в products таблице ===")

try:
    # Инициализация
    sheets = GoogleSheetsManager()

    # Получаем все данные из листа products
    all_values = sheets.products_sheet.get_all_values()

    print(f"Всего строк: {len(all_values)}")

    if all_values:
        headers = all_values[0]
        print(f"\nЗаголовки:")
        for i, header in enumerate(headers):
            print(f"  {i}: '{header}'")

        # Показываем последние 5 строк с данными
        print(f"\nПоследние 5 строк данных:")
        for row_num, row in enumerate(all_values[-5:], len(all_values) - 4):
            print(f"Строка {row_num}:")
            for i, cell in enumerate(row):
                print(f"  {i} ({headers[i] if i < len(headers) else f'col{i}'}): '{cell}' (тип: {type(cell).__name__})")
            print()

        # Получаем данные через get_all_records
        print("\n\nДанные через get_all_records():")
        records = sheets.products_sheet.get_all_records()
        print(f"Всего записей: {len(records)}")

        if records:
            print("\nПоследняя запись:")
            record = records[-1]
            for key, value in record.items():
                print(f"  {key}: '{value}' (тип: {type(value).__name__})")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()