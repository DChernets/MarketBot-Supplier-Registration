#!/usr/bin/env python3
"""
Ручное получение OAuth токена Google Drive
"""

import json
from pathlib import Path
from urllib.parse import urlencode

# Путь к файлам
CREDENTIALS_FILE = Path(__file__).parent / "config" / "google_oauth_credentials.json"
TOKENS_FILE = Path(__file__).parent / "config" / "oauth_tokens.json"

def load_credentials():
    """Загрузить OAuth credentials"""
    with open(CREDENTIALS_FILE, 'r') as f:
        return json.load(f)

def save_tokens(token_data):
    """Сохранить токены"""
    with open(TOKENS_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)
    print(f"\n✅ Токены сохранены в {TOKENS_FILE}")

def get_auth_url(client_id):
    """Получить URL для авторизации"""
    params = {
        'client_id': client_id,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'scope': 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }

    base_url = 'https://accounts.google.com/o/oauth2/auth'
    return f"{base_url}?{urlencode(params)}"

def exchange_code_for_tokens(code, client_id, client_secret):
    """Обменять код на токены"""
    import httpx

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
    }

    response = httpx.post('https://oauth2.googleapis.com/token', data=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Ошибка при обмене кода на токены: {response.text}")
        return None

def main():
    print("🔐 Google OAuth Token Generator (Manual)")
    print("=" * 40)

    # Загружаем credentials
    try:
        credentials = load_credentials()
        client_id = credentials['installed']['client_id']
        client_secret = credentials['installed']['client_secret']
        print("✅ OAuth credentials загружены")
    except Exception as e:
        print(f"❌ Ошибка загрузки credentials: {e}")
        return

    # Формируем URL для авторизации
    auth_url = get_auth_url(client_id)

    print("\n📋 Инструкции:")
    print("1. Скопируйте URL ниже и вставьте в браузер:")
    print(f"\n{auth_url}\n")
    print("2. Войдите в свой аккаунт Google")
    print("3. Разрешите доступ к Google Drive и Google Sheets")
    print("4. После авторизации вы будете перенаправлены на страницу с ошибкой")
    print("5. Скопируйте 'code' параметр из URL")
    print("\n" + "=" * 40)

    # Получаем код от пользователя
    auth_code = input("\n🔑 Введите код авторизации (code parameter): ").strip()

    if auth_code:
        print(f"\n✅ Код авторизации получен")

        # Обмениваем код на токены
        print("🔄 Обмениваю код на токены...")
        tokens = exchange_code_for_tokens(
            auth_code,
            client_id,
            client_secret
        )

        if tokens:
            # Добавляем client_id и client_secret для будущих запросов
            tokens['client_id'] = client_id
            tokens['client_secret'] = client_secret

            # Сохраняем токены
            save_tokens(tokens)

            print("\n✅ Токены успешно получены и сохранены!")
            print(f"Access Token expires in: {tokens.get('expires_in', 3600)} seconds")
            if 'refresh_token' in tokens:
                print("✅ Refresh token получен (для автоматического обновления)")

            print("\n🎉 Теперь бот может использовать ваш Google Drive!")

        else:
            print("❌ Не удалось получить токены")
    else:
        print("\n❌ Код авторизации не введен")

if __name__ == "__main__":
    main()