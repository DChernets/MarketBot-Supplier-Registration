#!/usr/bin/env python3
"""
Исправление испорченных данных в products таблице - исправленная версия
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def fix_corrupted_products():
    """Исправить продукты с перепутанными колонками"""

    print("=== Исправление испорченных данных в products (v2) ===")

    try:
        sheets = GoogleSheetsManager()

        # Получаем все данные
        all_values = sheets.products_sheet.get_all_values()

        if len(all_values) <= 1:
            print("Нет данных для исправления")
            return

        headers = all_values[0]
        print(f"Заголовки: {headers}")

        # Находим индексы колонок
        photo_urls_idx = headers.index('photo_urls')
        quantity_idx = headers.index('quantity')

        print(f"photo_urls индекс: {photo_urls_idx}")
        print(f"quantity индекс: {quantity_idx}")

        # Исправляем данные начиная со второй строки
        fixed_count = 0
        for row_num, row in enumerate(all_values[1:], 2):
            # Проверяем есть ли у нас данные в строке
            if len(row) > max(photo_urls_idx, quantity_idx):
                try:
                    photo_urls_value = row[photo_urls_idx]
                    quantity_value = row[quantity_idx]

                    # Проверяем, перепутаны ли данные
                    if (photo_urls_value and isinstance(photo_urls_value, str) and
                        'https://api.telegram.org/file/bot8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs/https://api.telegram.org/file/bot8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs/photos/file_' in photo_urls_value):

                        print(f"Исправляем строку {row_num}:")
                        print(f"  Было: photo_urls={photo_urls_value[:50]}...")
                        print(f"  Было: quantity={quantity_value}")

                        # Получаем правильный URL из дублированного
                        bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"
                        pattern = f'https://api.telegram.org/file/bot{bot_token}/https://api.telegram.org/file/bot{bot_token}/'

                        if pattern in photo_urls_value:
                            # Убираем дублирование
                            clean_url = photo_urls_value.split(pattern)[-1]
                            row[photo_urls_idx] = clean_url
                            # quantity уже правильное число

                            # Обновляем только нужные ячейки
                            sheets.products_sheet.update(f"F{row_num}:F{row_num}", [[row[photo_urls_idx]]])
                            sheets.products_sheet.update(f"G{row_num}:G{row_num}", [[row[quantity_idx]]])

                            fixed_count += 1
                            print(f"  Стало: photo_urls={clean_url}")
                            print(f"  Стало: quantity={quantity_value}")
                        else:
                            print(f"  Пропускаем строку {row_num} - не распознан паттерн")
                    else:
                        print(f"  Пропускаем строку {row_num} - данные в порядке")

                except Exception as e:
                    print(f"  Ошибка в строке {row_num}: {e}")

        print(f"\nИсправлено записей: {fixed_count}")

    except Exception as e:
        print(f"Ошибка при исправлении данных: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_corrupted_products()