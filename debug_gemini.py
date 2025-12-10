#!/usr/bin/env python3
"""
Детальная диагностика Gemini API
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import google.generativeai as genai
from src.config import GEMINI_API_KEY, GEMINI_MODEL

print("=== Детальная диагностика Gemini API ===")
print(f"API Key: {'Есть' if GEMINI_API_KEY else 'Нет'}")
if GEMINI_API_KEY:
    print(f"API Key длина: {len(GEMINI_API_KEY)}")
    print(f"API Key начинается с: {GEMINI_API_KEY[:10]}...")
    print(f"API Key заканчивается на: ...{GEMINI_API_KEY[-10:]}")

print(f"Модель: {GEMINI_MODEL}")

# Проверяем доступные модели
print("\n=== Доступные модели ===")
try:
    genai.configure(api_key=GEMINI_API_KEY)
    models = list(genai.list_models())
    gemini_models = [m for m in models if 'gemini' in m.name.lower()]

    print("Найденные Gemini модели:")
    for model in gemini_models[:10]:  # Показываем первые 10
        print(f"  - {model.name}")
        print(f"    Display name: {model.display_name}")
        print(f"    Description: {model.description[:100]}...")
        print(f"    Generation methods: {list(model.supported_generation_methods)}")
        print()

except Exception as e:
    print(f"Ошибка при получении списка моделей: {e}")
    import traceback
    traceback.print_exc()

# Тестируем конкретную модель
print(f"\n=== Тестирование модели {GEMINI_MODEL} ===")
try:
    model = genai.GenerativeModel(GEMINI_MODEL)

    # Простой тест
    print("1. Простой текстовый запрос...")
    response = model.generate_content("Привет! Ответь одним словом.")
    print(f"   Ответ: {response.text}")

    # Тест с конфигурацией
    print("2. Запрос с конфигурацией...")
    response = model.generate_content(
        "Привет! Ответь одним словом.",
        generation_config={"temperature": 0.1, "max_output_tokens": 10}
    )
    print(f"   Ответ: {response.text}")

    # Тест изображения (если есть доступное изображение)
    print("3. Тест с простым изображением...")
    try:
        from PIL import Image
        import io

        # Создаем простое тестовое изображение (1x1 пиксель)
        img = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        response = model.generate_content(
            ["Опиши что изображено на картинке одним словом.", img],
            generation_config={"temperature": 0.1, "max_output_tokens": 50}
        )
        print(f"   Ответ: {response.text}")

    except Exception as img_e:
        print(f"   Ошибка при тесте изображения: {img_e}")

except Exception as e:
    print(f"Ошибка при тестировании модели: {e}")
    print(f"Тип ошибки: {type(e).__name__}")
    import traceback
    traceback.print_exc()

# Проверяем квоты и статус проекта
print("\n=== Проверка квот и статуса ===")
try:
    # Пробуем получить информацию о проекте
    import requests

    headers = {"x-goog-api-key": GEMINI_API_KEY}

    # Проверяем доступ к API метаданным
    try:
        response = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}",
            headers=headers,
            timeout=10
        )
        print(f"Статус запроса к API: {response.status_code}")
        if response.status_code == 200:
            model_info = response.json()
            print(f"Модель найдена: {model_info.get('displayName', 'N/A')}")
        else:
            print(f"Ошибка API: {response.text}")
    except Exception as api_e:
        print(f"Ошибка при запросе к API: {api_e}")

except Exception as e:
    print(f"Ошибка при проверке квот: {e}")

print("\n=== Рекомендации ===")
if "User location is not supported" in str(e):
    print("❌ Геоблокировка - Gemini API недоступен в вашем регионе")
    print("💡 Решение: Используйте VPN или другой сервис")
elif "API key" in str(e).lower():
    print("❌ Проблема с API ключом")
    print("💡 Решение: Проверьте ключ или создайте новый")
elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
    print("❌ Проблема с правами доступа")
    print("💡 Решение: Проверьте настройки проекта Google Cloud")
elif "quota" in str(e).lower() or "limit" in str(e).lower():
    print("❌ Проблема с квотами")
    print("💡 Решение: Проверьте лимиты или пополните баланс")
else:
    print(f"❌ Неизвестная ошибка: {e}")
    print("💡 Решение: Проверьте подключение и настройки API")