#!/usr/bin/env python3
"""Проверка файлов на Google Drive"""
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Загружаем OAuth токены
tokens_file = Path("config/oauth_tokens.json")
with open(tokens_file, 'r') as f:
    token_data = json.load(f)

creds = Credentials(
    token=token_data.get('access_token'),
    refresh_token=token_data.get('refresh_token'),
    token_uri=token_data.get('token_uri'),
    client_id=token_data.get('client_id'),
    client_secret=token_data.get('client_secret'),
    scopes=token_data.get('scopes')
)

# Создаем сервис
service = build('drive', 'v3', credentials=creds)

# ID папки MarketBot
marketbot_folder_id = "1ZG51f0NTqlOg_h_timWStjWhz7vNPULc"

print(f"🔍 Проверка папки MarketBot (ID: {marketbot_folder_id})\n")

# Проверяем папку MarketBot
try:
    folder = service.files().get(fileId=marketbot_folder_id, fields='id,name,webViewLink,owners').execute()
    print(f"✅ Папка найдена: {folder.get('name')}")
    print(f"🔗 Ссылка: {folder.get('webViewLink')}")
    print(f"👤 Владелец: {folder.get('owners', [{}])[0].get('emailAddress', 'Unknown')}\n")
except Exception as e:
    print(f"❌ Ошибка доступа к папке: {e}\n")

# Список содержимого папки MarketBot
print("📂 Содержимое папки MarketBot:")
try:
    results = service.files().list(
        q=f"'{marketbot_folder_id}' in parents",
        fields='files(id, name, mimeType, webViewLink, createdTime)',
        orderBy='createdTime desc'
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print("   (пусто)")
    else:
        for item in items:
            icon = "📁" if item['mimeType'] == 'application/vnd.google-apps.folder' else "🖼️"
            print(f"{icon} {item['name']}")
            print(f"   ID: {item['id']}")
            print(f"   🔗 {item.get('webViewLink', 'N/A')}")
            print(f"   📅 {item.get('createdTime', 'N/A')}\n")
            
            # Если это папка Enhanced_Images, показываем её содержимое
            if item['mimeType'] == 'application/vnd.google-apps.folder' and 'Enhanced' in item['name']:
                print(f"   📂 Содержимое {item['name']}:")
                sub_results = service.files().list(
                    q=f"'{item['id']}' in parents",
                    fields='files(id, name, webViewLink, size)',
                    orderBy='createdTime desc'
                ).execute()
                
                sub_items = sub_results.get('files', [])
                if not sub_items:
                    print("      (пусто)")
                else:
                    for sub_item in sub_items:
                        size_mb = int(sub_item.get('size', 0)) / (1024 * 1024)
                        print(f"      🖼️ {sub_item['name']} ({size_mb:.2f} MB)")
                        print(f"         🔗 {sub_item.get('webViewLink', 'N/A')}")
                print()
                
except Exception as e:
    print(f"❌ Ошибка: {e}")
