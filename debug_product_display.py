#!/usr/bin/env python3
"""
Диагностика проблемы с отображением товаров
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

print("=== Диагностика проблемы с отображением товаров ===")

try:
    # Инициализация
    sheets = GoogleSheetsManager()

    # Получаем все данные из листа products
    all_values = sheets.products_sheet.get_all_values()
    records = sheets.products_sheet.get_all_records()

    print(f"Всего строк в таблице: {len(all_values)}")
    print(f"Всего записей через get_all_records: {len(records)}")

    if all_values:
        headers = all_values[0]
        print(f"\nЗаголовки:")
        for i, header in enumerate(headers):
            print(f"  {i}: '{header}'")

        # Проверяем последние 3 записи подробнее
        print(f"\nПоследние 3 записи:")
        for i, record in enumerate(records[-3:], len(records)-2):
            print(f"\nЗапись {i}:")
            for key, value in record.items():
                print(f"  {key}: '{value}' (тип: {type(value).__name__})")
                if key == 'photo_urls' and value:
                    print(f"    -> Длина строки: {len(str(value))}")
                    print(f"    -> Начало: {str(value)[:100]}...")

        # Проверяем конкретные проблемы
        print(f"\n=== Проверка проблем ===")
        for i, record in enumerate(records, 1):
            issues = []

            # Проверяем photo_urls
            photo_urls = record.get('photo_urls', '')
            if photo_urls:
                photo_str = str(photo_urls)
                if 'api.telegram.org/file/bot' in photo_str and photo_str.count('api.telegram.org/file/bot') > 1:
                    issues.append("Дублирование URL в photo_urls")
                if len(photo_str) > 500:
                    issues.append("Слишком длинный URL")

            # Проверяем quantity
            quantity = record.get('quantity', '')
            if quantity and not str(quantity).isdigit():
                issues.append("Quantity не число")

            if issues:
                print(f"Запись {i}: {', '.join(issues)}")
                print(f"  photo_urls: {photo_urls}")
                print(f"  quantity: {quantity}")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()