#!/usr/bin/env python3
"""
Скрипт для получения OAuth токена Google Drive
"""

import json
import webbrowser
from urllib.parse import urlencode
import http.server
import socketserver
import threading
import time
from pathlib import Path

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
        'redirect_uri': 'http://localhost:8080',
        'scope': 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }

    base_url = 'https://accounts.google.com/o/oauth2/auth'
    return f"{base_url}?{urlencode(params)}"

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Обработчик для получения callback от Google"""

    auth_code = None

    def do_GET(self):
        if '/oauth2callback' in self.path:
            # Извлекаем код авторизации
            query = self.path.split('?')[1] if '?' in self.path else ''
            params = dict(x.split('=') for x in query.split('&'))

            CallbackHandler.auth_code = params.get('code', '')

            # Отправляем ответ
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            if CallbackHandler.auth_code:
                self.wfile.write(b"""
                    <html>
                    <body>
                        <h1>Authorization successful!</h1>
                        <p>You can close this window.</p>
                        <p>Tokens will be saved automatically.</p>
                    </body>
                    </html>
                """)
            else:
                self.wfile.write(b"""
                    <html>
                    <body>
                        <h1>Authorization error</h1>
                        <p>Authorization code not received.</p>
                    </body>
                    </html>
                """)

    def log_message(self, format, *args):
        # Отключаем логирование HTTP запросов
        pass

def exchange_code_for_tokens(code, client_id, client_secret):
    """Обменять код на токены"""
    import httpx

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'http://localhost:8080'
    }

    response = httpx.post('https://oauth2.googleapis.com/token', data=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Ошибка при обмене кода на токены: {response.text}")
        return None

def main():
    print("🔐 Google OAuth Token Generator")
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

    # Запускаем локальный сервер для callback
    with socketserver.TCPServer(("", 8080), CallbackHandler) as httpd:
        print("\n🚀 Запускаем локальный сервер на http://localhost:8080")

        # Запускаем сервер в отдельном потоке
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Формируем URL для авторизации
        auth_url = get_auth_url(client_id)

        print("\n📋 Инструкции:")
        print("1. Откроется браузер со страницей авторизации Google")
        print("2. Войдите в свой аккаунт Google")
        print("3. Разрешите доступ к Google Drive и Google Sheets")
        print("4. После успешной авторизации вы увидите страницу с сообщением об успехе")
        print("5. Скрипт автоматически получит токены и сохранит их")
        print("\n" + "=" * 40)

        # Открываем браузер
        print(f"\n🌐 Открываю браузер для авторизации...")
        print(f"URL: {auth_url}")
        webbrowser.open(auth_url)

        # Ждем код авторизации
        print("\n⏳ Ожидаю код авторизации...")
        timeout = 120  # 2 минуты
        start_time = time.time()

        while CallbackHandler.auth_code is None and (time.time() - start_time) < timeout:
            time.sleep(1)

        if CallbackHandler.auth_code:
            print(f"\n✅ Код авторизации получен")

            # Обмениваем код на токены
            print("🔄 Обмениваю код на токены...")
            tokens = exchange_code_for_tokens(
                CallbackHandler.auth_code,
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
            print("\n⏰ Таймаут ожидания кода авторизации")
            print("Попробуйте снова")

        # Останавливаем сервер
        httpd.shutdown()

if __name__ == "__main__":
    main()