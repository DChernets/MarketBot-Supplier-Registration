#!/usr/bin/env python3
"""
Тест подключения к Google Sheets API
"""

import os
import sys
sys.path.append('/root/myAI/MarketBot')

# Устанавливаем прокси
os.environ['HTTP_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'
os.environ['HTTPS_PROXY'] = 'http://user58477:xr58c1@46.183.28.14:6052'

from src.config import GOOGLE_SHEETS_SPREADSHEET_ID, GOOGLE_SHEETS_CREDENTIALS_FILE
import gspread
from google.oauth2.service_account import Credentials
import logging

logging.basicConfig(level=logging.INFO)

def test_google_sheets_connection():
    """Тест подключения к Google Sheets API"""
    print("🔍 Тест подключения к Google Sheets API")
    print("=" * 50)

    try:
        print(f"📊 Spreadsheet ID: {GOOGLE_SHEETS_SPREADSHEET_ID}")
        print(f"📄 Credentials file: {GOOGLE_SHEETS_CREDENTIALS_FILE}")

        # Проверяем наличие файла credentials
        if not os.path.exists(GOOGLE_SHEETS_CREDENTIALS_FILE):
            print(f"❌ Файл credentials не найден: {GOOGLE_SHEETS_CREDENTIALS_FILE}")
            return False

        # Настройка авторизации
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        print("🔐 Авторизация в Google...")
        creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)

        print("✅ Авторизация прошла успешно")

        # Открываем таблицу
        print("📋 Открытие таблицы...")
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)

        print(f"✅ Таблица открыта: {spreadsheet.title}")

        # Получаем список листов
        worksheets = spreadsheet.worksheets()
        print(f"📄 Найдено листов: {len(worksheets)}")

        for i, sheet in enumerate(worksheets):
            print(f"  {i+1}. {sheet.title}")

        # Пробуем прочитать данные с первого листа
        if worksheets:
            sheet = worksheets[0]
            print(f"\n📋 Чтение данных с листа: {sheet.title}")

            try:
                # Получаем все данные
                data = sheet.get_all_records()
                print(f"📊 Прочитано записей: {len(data)}")

                if data:
                    print("📄 Первые 3 записи:")
                    for i, record in enumerate(data[:3]):
                        print(f"  {i+1}: {record}")

                print("✅ Чтение данных прошло успешно")

            except Exception as e:
                print(f"❌ Ошибка чтения данных: {e}")

                # Пробуем прочитать сырые данные
                try:
                    raw_data = sheet.get_all_values()
                    print(f"📊 Сырых данных получено: {len(raw_data)} строк")
                    if raw_data:
                        print("📄 Первая строка (заголовки):")
                        print(f"  {raw_data[0]}")
                except Exception as e2:
                    print(f"❌ Ошибка чтения сырых данных: {e2}")

        print("\n🎉 Google Sheets API работает корректно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {str(e)}")

        # Анализируем тип ошибки
        error_str = str(e).lower()
        if "spreadsheet not found" in error_str:
            print("💡 Таблица не найдена. Проверьте Spreadsheet ID")
        elif "permission" in error_str or "forbidden" in error_str:
            print("💡 Проблема с доступом. Проверьте права доступа к таблице")
        elif "credentials" in error_str or "authentication" in error_str:
            print("💡 Проблема с аутентификацией. Проверьте credentials файл")
        elif "timeout" in error_str or "connection" in error_str:
            print("💡 Проблема с соединением. Проверьте сеть и прокси")

        return False

def test_proxies():
    """Тест работы прокси для Google API"""
    print("\n🔌 Тест прокси для Google APIs...")

    try:
        import requests

        # Тестируем доступ к Google APIs через прокси
        proxies = {
            'https': 'http://user58477:xr58c1@46.183.28.14:6052',
            'http': 'http://user58477:xr58c1@46.183.28.14:6052'
        }

        response = requests.get(
            'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest',
            proxies=proxies,
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Прокси работает для Google APIs")
            return True
        else:
            print(f"❌ Прокси не работает: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Ошибка прокси: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Тестирование Google Sheets API")
    print("=" * 60)

    # Тест прокси
    proxy_works = test_proxies()

    # Тест Google Sheets
    sheets_works = test_google_sheets_connection()

    print("\n" + "=" * 60)
    print("📊 ИТОГИ:")
    print(f"🔌 Прокси: {'✅ Работает' if proxy_works else '❌ Не работает'}")
    print(f"📊 Google Sheets: {'✅ Работает' if sheets_works else '❌ Не работает'}")

    if sheets_works:
        print("\n🎉 Google Sheets API готов к работе!")
    else:
        print("\n🚨 Требуется исправление Google Sheets API")
        print("🔧 Проверьте:")
        print("  1. Правильность Spreadsheet ID")
        print("  2. Доступ к таблице для service account")
        print("  3. Файл credentials.json")
        print("  4. Настройки прокси")