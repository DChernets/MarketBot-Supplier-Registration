#!/usr/bin/env python3
"""
Тест Gemini API через шведский прокси
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import requests
import json
from src.config import GEMINI_API_KEY

print("=== Тест Gemini API через шведский прокси ===")

# Настройки прокси
proxies = {
    'http': 'http://user58477:xr58c1@46.183.28.14:6052',
    'https': 'http://user58477:xr58c1@46.183.28.14:6052'
}

print(f"Прокси: {proxies['https'][:20]}...")

# Тест 1: Проверка работы прокси
print("\n1. Проверка работы прокси...")
try:
    response = requests.get(
        "https://httpbin.org/ip",
        proxies=proxies,
        timeout=10
    )
    if response.status_code == 200:
        ip_info = response.json()
        print(f"✅ Прокси работает, IP через прокси: {ip_info}")
    else:
        print(f"❌ Прокси не работает, статус: {response.status_code}")
except Exception as e:
    print(f"❌ Ошибка прокси: {e}")

# Тест 2: Проверка геолокации через прокси
print("\n2. Проверка геолокации через прокси...")
try:
    response = requests.get(
        "http://ip-api.com/json",
        proxies=proxies,
        timeout=10
    )
    if response.status_code == 200:
        geo_info = response.json()
        print(f"✅ Геолокация через прокси:")
        print(f"   Страна: {geo_info.get('country', 'N/A')} ({geo_info.get('countryCode', 'N/A')})")
        print(f"   Город: {geo_info.get('city', 'N/A')}")
        print(f"   ISP: {geo_info.get('isp', 'N/A')}")
    else:
        print(f"❌ Не удалось получить геолокацию")
except Exception as e:
    print(f"❌ Ошибка геолокации: {e}")

# Тест 3: Тест Gemini API через прокси
print("\n3. Тест Gemini API через прокси...")
try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    response = requests.get(
        url,
        proxies=proxies,
        timeout=10
    )

    print(f"Статус запроса к Gemini: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"✅ Gemini API работает! Доступно моделей: {len(models)}")

        if models:
            print("\nДоступные модели через прокси:")
            for model in models[:5]:
                name = model.get('name', 'Unknown')
                display_name = model.get('displayName', 'N/A')
                methods = model.get('supportedGenerationMethods', [])
                print(f"  - {name} ({display_name})")
                print(f"    Методы: {methods}")

    elif response.status_code == 400:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Unknown error')
        print(f"❌ Ошибка Gemini API: {error_message}")

        if "User location is not supported" in error_message:
            print("❌ Все еще проблема с геолокацией даже через прокси")
        else:
            print("🔍 Другая ошибка - возможно в API ключе или настройках")

    else:
        print(f"❌ Неизвестный ответ: {response.text}")

except Exception as e:
    print(f"❌ Ошибка запроса к Gemini через прокси: {e}")

# Тест 4: Тест генерации контента через прокси
print("\n4. Тест генерации текста через прокси...")
try:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": "Hello! Respond with just one word."}]
        }],
        "generationConfig": {
            "maxOutputTokens": 10
        }
    }

    response = requests.post(
        f"{url}?key={GEMINI_API_KEY}",
        headers=headers,
        json=data,
        proxies=proxies,
        timeout=15
    )

    print(f"Статус генерации: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result:
            text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ Генерация работает! Ответ: '{text}'")
        else:
            print(f"✅ Запрос успешен, но странный ответ: {result}")
    else:
        print(f"❌ Ошибка генерации: {response.text}")

except Exception as e:
    print(f"❌ Ошибка генерации через прокси: {e}")

print("\n=== Результаты теста ===")
print("Если все тесты успешны - можно обновлять бота для работы через прокси")