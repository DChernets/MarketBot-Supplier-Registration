#!/usr/bin/env python3
"""
Проверка доступных моделей Gemini
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import google.generativeai as genai
from src.config import GEMINI_API_KEY

print("=== Проверка доступных моделей ===")

try:
    genai.configure(api_key=GEMINI_API_KEY)

    # Получаем список всех моделей
    models = list(genai.list_models())

    print(f"Всего моделей найдено: {len(models)}")

    # Показываем только Gemini модели
    gemini_models = [m for m in models if 'gemini' in m.name.lower()]
    print(f"Gemini моделей: {len(gemini_models)}")

    for model in gemini_models:
        print(f"\nНазвание: {model.name}")
        print(f"Display Name: {model.display_name}")
        print(f"Методы: {model.supported_generation_methods}")
        print(f"Описание: {model.description[:100]}...")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()