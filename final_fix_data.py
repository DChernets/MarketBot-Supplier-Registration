#!/usr/bin/env python3
"""
Финальное исправление всех проблем с данными
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

from src.google_sheets import GoogleSheetsManager

def final_fix():
    """Финальное исправление данных"""

    print("=== Финальное исправление данных ===")

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

        fixed_count = 0
        for row_num, row in enumerate(all_values[1:], 2):
            # Проверяем есть ли у нас данные в строке
            if len(row) > max(photo_urls_idx, quantity_idx):
                try:
                    photo_urls_value = row[photo_urls_idx] if photo_urls_idx < len(row) else ''
                    quantity_value = row[quantity_idx] if quantity_idx < len(row) else ''

                    print(f"\nСтрока {row_num}:")
                    print(f"  photo_urls: '{photo_urls_value}' (тип: {type(photo_urls_value).__name__})")
                    print(f"  quantity: '{quantity_value}' (тип: {type(quantity_value).__name__})")

                    # Случай 1: photo_urls это число, а quantity пустой или URL
                    if (str(photo_urls_value).isdigit() and
                        (str(quantity_value) == '' or str(quantity_value).startswith('http') or 'example.com' in str(quantity_value))):

                        print(f"  🔄 Исправляем: photo_urls это число ({photo_urls_value})")

                        # Если quantity содержит URL, меняем местами
                        if str(quantity_value).startswith('http') or 'example.com' in str(quantity_value):
                            print(f"  🔄 Меняем местами: photo_urls={quantity_value}, quantity={photo_urls_value}")
                            row[photo_urls_idx], row[quantity_idx] = quantity_value, photo_urls_value
                            fixed_count += 1
                        else:
                            # Иначе просто ставим пустое значение в photo_urls
                            print(f"  🔄 Устанавливаем photo_urls='', quantity={photo_urls_value}")
                            row[photo_urls_idx] = ''
                            row[quantity_idx] = photo_urls_value
                            fixed_count += 1

                    # Случай 2: photo_urls содержит относительный путь без полного URL
                    elif (photo_urls_value and
                          isinstance(photo_urls_value, str) and
                          not photo_urls_value.startswith('http') and
                          not photo_urls_value.startswith('photos/') and
                          '/' in photo_urls_value):

                        print(f"  🔄 Исправляем относительный путь: {photo_urls_value}")
                        bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"
                        if photo_urls_value.startswith('/'):
                            full_url = f"https://api.telegram.org/file/bot{bot_token}{photo_urls_value}"
                        else:
                            full_url = f"https://api.telegram.org/file/bot{bot_token}/{photo_urls_value}"

                        row[photo_urls_idx] = full_url
                        print(f"  🔄 Установлен полный URL: {full_url}")
                        fixed_count += 1

                    # Случай 3: quantity пустое, а есть photo_urls
                    elif (str(quantity_value) == '' and photo_urls_value):
                        # Проверяем что quantity действительно должно быть числом
                        if str(photo_urls_value).isdigit():
                            print(f"  🔄 quantity пустое, photo_urls это число: {photo_urls_value}")
                            row[quantity_idx] = photo_urls_value
                            row[photo_urls_idx] = ''
                            print(f"  🔄 Переносим: quantity={photo_urls_value}, photo_urls=''")
                            fixed_count += 1

                    # Проверяем что quantity это число
                    if quantity_value:
                        try:
                            int_quantity = int(quantity_value)
                            if int_quantity < 0:
                                print(f"  ⚠️ Отрицательное количество: {int_quantity}")
                        except (ValueError, TypeError):
                            print(f"  ⚠️ quantity не число: {quantity_value}")
                            # Если quantity содержит что-то похожее на число в строке
                            import re
                            numbers = re.findall(r'\d+', str(quantity_value))
                            if numbers:
                                row[quantity_idx] = numbers[0]
                                print(f"  🔄 Извлечено число: {numbers[0]}")
                                fixed_count += 1

                    # Обновляем строку если были изменения
                    if fixed_count > 0:
                        print(f"  💾 Обновляем строку {row_num}")
                        # Обновляем только нужные колонки для эффективности
                        sheets.products_sheet.update(f"F{row_num}:G{row_num}", [[row[photo_urls_idx], row[quantity_idx]]])

                except Exception as e:
                    print(f"  ❌ Ошибка в строке {row_num}: {e}")

        print(f"\n✅ Исправлено записей: {fixed_count}")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_fix()