#!/usr/bin/env python3
"""
Исправление дублирующихся заголовков в листе products
"""

import os
import sys
sys.path.append('/root/myAI/MarketBot')

# Устанавливаем прокси
os.environ['HTTP_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'
os.environ['HTTPS_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'

import gspread
from google.oauth2.service_account import Credentials
from src.config import GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEETS_SPREADSHEET_ID

def fix_products_sheet():
    """Исправляем заголовки в листе products"""
    print("🔧 Исправление заголовков в листе products")
    print("=" * 50)

    try:
        # Авторизация
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)

        # Получаем лист products
        products_sheet = spreadsheet.worksheet("products")

        # Получаем все данные
        all_data = products_sheet.get_all_values()
        print(f"📊 Всего строк в листе: {len(all_data)}")

        if not all_data:
            print("❌ Лист пуст")
            return False

        # Показываем текущие заголовки
        current_headers = all_data[0] if all_data else []
        print(f"📄 Текущие заголовки: {current_headers}")

        # Проверяем дубликаты
        headers_with_counts = {}
        duplicates = []

        for i, header in enumerate(current_headers):
            if header in headers_with_counts:
                headers_with_counts[header] += 1
                duplicates.append((i, header, headers_with_counts[header]))
            else:
                headers_with_counts[header] = 1

        print(f"📊 Статистика заголовков: {headers_with_counts}")

        if duplicates:
            print(f"❌ Найдены дубликаты:")
            for pos, header, count in duplicates:
                print(f"  Позиция {pos}: '{header}' (повтор #{count})")

            # Создаем правильные заголовки
            correct_headers = [
                "product_id", "supplier_id", "location_id",
                "название", "описание", "производство", "материал", "размеры", "упаковка",
                "photo_urls", "quantity", "created_at"
            ]

            # Обновляем заголовки
            products_sheet.update("A1", [correct_headers])
            print(f"✅ Заголовки обновлены на: {correct_headers}")

        else:
            print("✅ Дубликатов заголовков не найдено")

        # Проверяем результат
        print("\n🔍 Проверка результата...")
        try:
            updated_records = products_sheet.get_all_records()
            print(f"✅ Теперь работает! Найдено записей: {len(updated_records)}")
        except Exception as e:
            print(f"❌ Все еще проблема: {e}")
            return False

        print("\n🎉 Лист products исправлен!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при исправлении листа: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🛠️ Исправление листа products")
    print("=" * 60)

    success = fix_products_sheet()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Исправление завершено успешно!")
        print("💡 Теперь команда /profile должна работать")
    else:
        print("🚨 Исправление не удалось")
        print("🔧 Проверьте логи выше")