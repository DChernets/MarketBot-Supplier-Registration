#!/usr/bin/env python3
"""
Просмотр файлов в Google Drive старого Service Account
"""

import sys
sys.path.append('/root/myAI/MarketBot')

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Путь к старому файлу
OLD_CREDS_FILE = "/root/myAI/MarketBot/config/google_credentials.json"

def list_files():
    """Получить список файлов в старом Google Drive"""
    try:
        creds = Credentials.from_service_account_file(
            OLD_CREDS_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )

        service = build('drive', 'v3', credentials=creds)

        # Получаем все файлы
        results = service.files().list(
            pageSize=100,
            fields="files(id, name, size, createdTime)"
        ).execute()

        items = results.get('files', [])

        total_size = 0
        print(f"\n📁 Файлы в Google Drive (старый Service Account):")
        print("=" * 60)

        for item in items:
            size = int(item.get('size', 0))
            total_size += size
            size_mb = size / (1024 * 1024)

            print(f"📄 {item['name'][:50]:<50} {size_mb:>6.2f} MB")
            print(f"   ID: {item['id']}")
            print(f"   Создан: {item.get('createdTime', 'N/A')}")
            print()

        print("=" * 60)
        print(f"📊 Всего файлов: {len(items)}")
        print(f"💾 Общий размер: {total_size / (1024 * 1024):.2f} MB")

        # Квота Service Account - 15 ГБ
        quota_gb = 15
        used_gb = total_size / (1024 * 1024 * 1024)
        remaining_gb = quota_gb - used_gb

        print(f"\n💿 Квота Service Account: {quota_gb} GB")
        print(f"✅ Использовано: {used_gb:.2f} GB ({(used_gb/quota_gb*100):.1f}%)")
        print(f"🆓 Доступно: {remaining_gb:.2f} GB")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    list_files()