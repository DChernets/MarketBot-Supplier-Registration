#!/usr/bin/env python3
"""
Тест разных моделей Gemini API
"""

import os
import sys
import requests
import json
sys.path.append('/root/myAI/MarketBot')

from src.config import GEMINI_API_KEY

def test_model(model_name):
    """Тест конкретной модели"""

    proxy = "http://user58477:xr58c1@46.183.28.14:6052"

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    data = {
        "contents": [{
            "parts": [{
                "text": "Ответь одним словом: тест"
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": 50,
            "temperature": 0.1
        }
    }

    headers = {
        "Content-Type": "application/json",
    }

    try:
        print(f"🤖 Тест модели: {model_name}")

        response = requests.post(
            api_url,
            json=data,
            headers=headers,
            proxies={"https": proxy},
            timeout=30
        )

        print(f"📊 Статус: {response.status_code}")

        if response.status_code == 200:
            json_response = response.json()

            if "candidates" in json_response and json_response["candidates"]:
                candidate = json_response["candidates"][0]

                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0]["text"]
                    print(f"✅ Ответ: {text.strip()}")
                    return True
                else:
                    print(f"❌ Нет поля parts в ответе")
                    print(f"📄 Структура: {json.dumps(candidate, indent=2, ensure_ascii=False)}")
                    return False
            else:
                print(f"❌ Нет кандидатов в ответе")
                return False
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            try:
                error_data = response.json()
                if "error" in error_data:
                    print(f"📄 Ошибка: {error_data['error'].get('message', 'Unknown error')}")
            except:
                print(f"📄 Ответ: {response.text[:200]}...")
            return False

    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def main():
    print("🧪 Тестирование разных моделей Gemini API")
    print("=" * 50)

    # Список моделей для теста
    models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-thinking-exp",
        "gemini-2.0-flash-exp-1212",
        "gemini-2.5-flash"  # текущая
    ]

    working_models = []

    for model in models:
        print(f"\n{'='*20}")
        if test_model(model):
            working_models.append(model)
            print(f"🎉 Модель {model} РАБОТАЕТ!")

    print(f"\n{'='*50}")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")

    if working_models:
        print(f"✅ Рабочие модели ({len(working_models)}):")
        for model in working_models:
            print(f"  🤖 {model}")

        print(f"\n💡 РЕКОМЕНДАЦИЯ:")
        print(f"Используйте одну из рабочих моделей вместо gemini-2.5-flash")
        print(f"Лучший выбор: gemini-1.5-flash (быстрая и стабильная)")
    else:
        print("❌ Ни одна модель не работает!")
        print("🔧 Возможные решения:")
        print("1. Проверить API ключ")
        print("2. Попробовать другой регион/VPN")
        print("3. Обратиться в поддержку Google")

if __name__ == "__main__":
    main()