#!/usr/bin/env python3
"""
Проверка статуса API ключа и аккаунта
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import requests
import json
from src.config import GEMINI_API_KEY

print("=== Проверка статуса API ключа и аккаунта ===")

# Тест 1: Проверка валидности API ключа
print("\n1. Проверка валидности API ключа...")
try:
    # Пробуем получить информацию о моделях
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    response = requests.get(url, timeout=10)

    print(f"Статус код: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"✅ API ключ валиден, доступно моделей: {len(models)}")

        if models:
            print("\nДоступные модели:")
            for model in models[:5]:  # Показываем первые 5
                name = model.get('name', 'Unknown')
                display_name = model.get('displayName', 'N/A')
                methods = model.get('supportedGenerationMethods', [])
                print(f"  - {name} ({display_name})")
                print(f"    Методы: {methods}")

    elif response.status_code == 403:
        print("❌ Доступ запрещен - возможно проблема с API ключом или аккаунтом")
        try:
            error_data = response.json()
            print(f"Детали ошибки: {error_data}")
        except:
            print(f"Текст ошибки: {response.text}")

    elif response.status_code == 429:
        print("❌ Превышен лимит запросов (rate limit)")

    else:
        print(f"❌ Неизвестный статус: {response.text}")

except Exception as e:
    print(f"Ошибка запроса: {e}")

# Тест 2: Проверка квот и лимитов
print("\n2. Проверка квот...")
try:
    # Пробуем сделать простой запрос для проверки квот
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": "Hi"}]
        }],
        "generationConfig": {
            "maxOutputTokens": 10
        }
    }

    response = requests.post(
        f"{url}?key={GEMINI_API_KEY}",
        headers=headers,
        json=data,
        timeout=10
    )

    print(f"Статус запроса: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result:
            text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ Запрос успешен, ответ: {text}")
        else:
            print(f"✅ Запрос успешен, но странный формат ответа: {result}")

    elif response.status_code == 400:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Unknown error')
        print(f"❌ Ошибка 400: {error_message}")

        # Анализируем тип ошибки
        if "User location is not supported" in error_message:
            print("🔍 Это ошибка геолокации - API не доступен в вашем регионе")
        elif "API key" in error_message:
            print("🔍 Это ошибка API ключа - проверьте ключ")
        elif "quota" in error_message.lower() or "limit" in error_message.lower():
            print("🔍 Это ошибка квот - возможно превысили лимиты")
        elif "permission" in error_message.lower():
            print("🔍 Это ошибка прав доступа - проверьте настройки проекта")

    elif response.status_code == 403:
        print("❌ Ошибка 403: Доступ запрещен")
        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            print(f"Детали: {error_message}")
        except:
            pass

    else:
        print(f"❌ Ошибка: {response.text}")

except Exception as e:
    print(f"Ошибка при проверке квот: {e}")

# Тест 3: Проверка информации о проекте
print("\n3. Проверка информации о проекте...")
try:
    # Пробуем получить информацию о проекте (если доступно)
    headers = {"x-goog-api-key": GEMINI_API_KEY}
    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash",
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:
        model_info = response.json()
        print(f"✅ Модель gemini-1.5-flash доступна:")
        print(f"  Название: {model_info.get('displayName', 'N/A')}")
        print(f"  Описание: {model_info.get('description', 'N/A')[:100]}...")
        print(f"  Методы: {model_info.get('supportedGenerationMethods', [])}")

except Exception as e:
    print(f"Не удалось получить информацию о модели: {e}")

print("\n=== Рекомендации ===")
print("1. Если API ключ валиден но geo-ошибка - проблема в геолокации")
print("2. Если 403 ошибка - проверьте права проекта Google Cloud")
print("3. Если ошибка квот - возможно лимиты trial периода")
print("4. Попробуйте:")
print("   - Создать новый проект в Google Cloud Console")
print("   - Сгенерировать новый API ключ")
print("   - Использовать VPN/Proxy")
print("   - Проверить настройки биллинга")