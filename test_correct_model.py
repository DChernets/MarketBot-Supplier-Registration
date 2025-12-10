#!/usr/bin/env python3
"""
Тест с правильной моделью через прокси
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import requests
from src.config import GEMINI_API_KEY

print("=== Тест с правильной моделью ===")

proxies = {
    'http': 'http://user58477:xr58c1@46.183.28.14:6052',
    'https': 'http://user58477:xr58c1@46.183.28.14:6052'
}

# Тестируем с gemini-2.0-flash (доступна через прокси)
try:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
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

    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result:
            text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ УСПЕХ! Ответ: '{text.strip()}'")
        else:
            print(f"Странный формат ответа: {result}")
    else:
        print(f"Ошибка: {response.text}")

except Exception as e:
    print(f"Ошибка: {e}")