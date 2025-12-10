#!/usr/bin/env python3
"""
Дебаг ответа от Gemini API
"""

import os
import sys
import requests
import json
sys.path.append('/root/myAI/MarketBot')

from src.config import GEMINI_API_KEY, GEMINI_MODEL

def debug_gemini_response():
    """Дебаг ответа от Gemini API"""

    # Устанавливаем прокси
    proxy = "http://user58477:xr58c1@46.183.28.14:6052"

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    data = {
        "contents": [{
            "parts": [{
                "text": "Ответь одним словом: тест"
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": 10,
            "temperature": 0.1
        }
    }

    headers = {
        "Content-Type": "application/json",
    }

    try:
        print("🔍 Отправка запроса...")
        print(f"🌐 URL: {api_url}")
        print(f"📊 Данные: {json.dumps(data, indent=2, ensure_ascii=False)}")

        response = requests.post(
            api_url,
            json=data,
            headers=headers,
            proxies={"https": proxy},
            timeout=30
        )

        print(f"\n📊 Статус код: {response.status_code}")
        print(f"📋 Заголовки: {dict(response.headers)}")

        # Проверяем контент
        print(f"\n📄 Сырой ответ:")
        print("-" * 50)
        print(response.text)
        print("-" * 50)

        # Пробуем распарсить JSON
        try:
            json_response = response.json()
            print(f"\n✅ JSON успешно распарсен:")
            print(json.dumps(json_response, indent=2, ensure_ascii=False))

            # Анализируем структуру
            if "candidates" in json_response:
                print(f"\n🎯 Найдено кандидатов: {len(json_response['candidates'])}")
                for i, candidate in enumerate(json_response["candidates"]):
                    print(f"Кандидат {i}: {json.dumps(candidate, indent=2, ensure_ascii=False)}")
            elif "error" in json_response:
                print(f"\n❌ Ошибка в ответе:")
                error = json_response["error"]
                print(f"Код: {error.get('code')}")
                print(f"Сообщение: {error.get('message')}")
                print(f"Статус: {error.get('status')}")
            else:
                print(f"\n⚠️ Неожиданная структура ответа")

        except json.JSONDecodeError as e:
            print(f"\n❌ Ошибка парсинга JSON: {e}")
            print(f"📄 Ответ (первые 1000 символов): {response.text[:1000]}")

    except Exception as e:
        print(f"❌ Исключение: {e}")

if __name__ == "__main__":
    print("🔍 Дебаг ответа от Gemini API")
    print("=" * 50)
    debug_gemini_response()