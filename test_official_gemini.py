#!/usr/bin/env python3
"""
Тест Gemini API по официальной документации
"""

import sys
import os
sys.path.append('/root/myAI/MarketBot')

import google.generativeai as genai
from src.config import GEMINI_API_KEY

print("=== Тест по официальной документации Gemini ===")

# Инициализация по документации
genai.configure(api_key=GEMINI_API_KEY)

# Тест 1: Простая генерация текста
print("\n1. Тест генерации текста...")
try:
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("Hello")
    print(response.text)
except Exception as e:
    print(f"Ошибка: {e}")

# Тест 2: Распознавание изображения
print("\n2. Тест распознавания изображения...")
try:
    import PIL.Image
    import io

    # Создаем тестовое изображение
    img = PIL.Image.new('RGB', (100, 100), color='red')

    # Используем gemini-pro-vision как в документации
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content(["What is this image?", img])
    print(response.text)
except Exception as e:
    print(f"Ошибка: {e}")

# Тест 3: Upload файла
print("\n3. Тест с upload файла...")
try:
    import tempfile

    # Создаем временный файл
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img.save(tmp.name, 'JPEG')

        # Upload файла
        sample_file = genai.upload_file(tmp.name)
        print(f"Uploaded file: {sample_file.name}")

        # Генерация с загруженным файлом
        model = genai.GenerativeModel('gemini-pro-vision')
        response = model.generate_content([sample_file, "Describe this image"])
        print(response.text)

        # Удаление файла
        genai.delete_file(sample_file.name)
        print("File deleted")

except Exception as e:
    print(f"Ошибка: {e}")
finally:
    # Очистка временного файла
    try:
        os.unlink(tmp.name)
    except:
        pass