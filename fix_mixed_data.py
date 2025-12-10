#!/usr/bin/env python3
"""
Исправление перепутанных данных в photo_urls и quantity колонках
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def fix_mixed_data():
    """Исправить перепутанные данные в photo_urls и quantity"""

    print("=== Исправление перепутанных данных ===")

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
                    photo_urls_value = row[photo_urls_idx] if photo_urls_idx < len(row) else ''
                    quantity_value = row[quantity_idx] if quantity_idx < len(row) else ''

                    # Проверяем, перепутаны ли данные
                    # photo_urls должен содержать URL или путь к файлу, а quantity - число
                    photo_is_number = str(photo_urls_value).isdigit() and str(photo_urls_value) != ''
                    quantity_is_url = str(quantity_value).startswith('http') or 'example.com' in str(quantity_value)

                    if photo_is_number and quantity_is_url:
                        print(f"Исправляем строку {row_num}:")
                        print(f"  Было: photo_urls={photo_urls_value} (число!)")
                        print(f"  Было: quantity={quantity_value} (URL!)")

                        # Меняем значения местами
                        row[photo_urls_idx], row[quantity_idx] = quantity_value, photo_urls_value

                        # Обновляем строку в таблице
                        sheets.products_sheet.update(f"A{row_num}:I{row_num}", [row[:9]])  # Обновляем первые 9 колонок
                        fixed_count += 1
                        print(f"  Стало: photo_urls={row[photo_urls_idx]}")
                        print(f"  Стало: quantity={row[quantity_idx]}")

                    # Также проверим случай когда photo_urls содержит относительный путь без полного URL
                    elif (photo_urls_value and isinstance(photo_urls_value, str) and
                          not photo_urls_value.startswith('http') and
                          '/' in photo_urls_value and
                          not photo_urls_value.startswith('photos/')):

                        print(f"Исправляем строку {row_num} (относительный путь):")
                        print(f"  Было: photo_urls={photo_urls_value}")

                        # Формируем полный URL
                        bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"
                        if photo_urls_value.startswith('/'):
                            full_url = f"https://api.telegram.org/file/bot{bot_token}{photo_urls_value}"
                        else:
                            full_url = f"https://api.telegram.org/file/bot{bot_token}/{photo_urls_value}"

                        row[photo_urls_idx] = full_url

                        # Обновляем только фото URL
                        sheets.products_sheet.update(f"F{row_num}", [[full_url]])
                        fixed_count += 1
                        print(f"  Стало: photo_urls={full_url}")

                    else:
                        # Проверим что quantity это действительно число
                        try:
                            int_quantity = int(quantity_value) if quantity_value else 0
                            # Если quantity не число, попробуем исправить
                            if not str(quantity_value).isdigit() and quantity_value:
                                print(f"Проблема в строке {row_num}: quantity не число - {quantity_value}")
                        except (ValueError, TypeError):
                            print(f"Проблема в строке {row_num}: quantity не конвертируется в число - {quantity_value}")

                except Exception as e:
                    print(f"  Ошибка в строке {row_num}: {e}")

        print(f"\nИсправлено записей: {fixed_count}")

    except Exception as e:
        print(f"Ошибка при исправлении данных: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_mixed_data()