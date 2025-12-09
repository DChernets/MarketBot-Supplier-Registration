#!/usr/bin/env python3
"""
Скрипт для создания новой Google Sheets таблицы и обновления конфигурации
"""

import requests
import json

def create_new_spreadsheet():
    """Создание новой таблицы через веб-интерфейс"""

    print("🔧 ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ GOOGLE SHEETS\n")

    print("❌ ПРОБЛЕМА: Google Sheets API не активирован в проекте")
    print("📋 ПРОЕКТ: gen-lang-client-0028763775")
    print("🆔 PROJECT ID: 807203704794")
    print()

    print("🎯 БЫСТРОЕ РЕШЕНИЕ:")
    print("1. Перейдите в Google Cloud Console:")
    print("   https://console.cloud.google.com/")
    print()
    print("2. Войдите в аккаунт Google")
    print()
    print("3. Создайте новую Google Sheets таблицу:")
    print("   - https://sheets.google.com/create")
    print("   - Дайте название: 'MarketBot База Данных'")
    print()
    print("4. Скопируйте ID новой таблицы из URL:")
    print("   URL будет вида: https://docs.google.com/spreadsheets/d/СПИСОК_ИД/edit")
    print("   Где СПИСОК_ИД - это нужный ID")
    print()
    print("5. Поделитесь доступом к новой таблице:")
    print("   - Нажмите 'Share' (в правом верхнем углу)")
    print("   - Добавьте email: marketbot@gen-lang-client-0028763775.iam.gserviceaccount.com")
    print("   - Дайте права 'Editor'")
    print()
    print("6. Обновите .env файл:")
    print("   Замените GOOGLE_SHEETS_SPREADSHEET_ID на новый ID")
    print()
    print("✅ После этого бот заработает!")

    # Временное решение - попытка активировать API через веб-интерфейс
    api_url = f"https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=gen-lang-client-0028763775"

    print(f"\n🌐 ССЫЛКА ДЛЯ АКТИВАЦИИ API:")
    print(api_url)

def main():
    create_new_spreadsheet()

if __name__ == "__main__":
    main()