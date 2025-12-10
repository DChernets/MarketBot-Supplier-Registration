#!/usr/bin/env python3
"""
Исправление испорченных данных в products таблице
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def fix_corrupted_products():
    """Исправить продукты с перепутанными колонками"""

    print("=== Исправление испорченных данных в products ===")

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
                        photo_urls_value.startswith('http') and
                        str(quantity_value).isdigit()):

                        # Если photo_urls начинается с http и quantity это число - значит перепутаны
                        print(f"Исправляем строку {row_num}:")

                        # Получаем правильный URL из дублированного
                        bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"
                        if f'https://api.telegram.org/file/bot{bot_token}/https://api.telegram.org/file/bot{bot_token}/' in photo_urls_value:
                            # Убираем дублирование
                            clean_url = photo_urls_value.split(f'https://api.telegram.org/file/bot{bot_token}/https://api.telegram.org/file/bot{bot_token}/')[-1]
                            row[photo_urls_idx] = clean_url
                            row[quantity_idx] = quantity_value

                            # Обновляем строку в таблице
                            sheets.products_sheet.update(f"A{row_num}:I{row_num}", [row])
                            fixed_count += 1
                            print(f"  Исправлено: photo_urls={clean_url[:50]}..., quantity={quantity_value}")
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