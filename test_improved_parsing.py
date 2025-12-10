#!/usr/bin/env python3
"""
Тест улучшенного парсинга URL
"""

def test_improved_parsing():
    """Тест улучшенной логики парсинга"""

    print("=== Тест улучшенного парсинга URL ===")

    # Проблемный URL с двойным дублированием
    problematic_url = "https://api.telegram.org/file/bot8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs/https://api.telegram.org/file/bot8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs/photos/file_2.jpg"

    bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"

    file_path = problematic_url

    print(f"Original file_path: {file_path}")

    # Если file_path содержит полный URL, извлекаем только путь
    if file_path.startswith('http'):
        print("URL начинается с http")

        # Извлекаем путь после /file/bot{token}/
        token_pattern = f'/file/bot{bot_token}/'
        print(f"Ищем паттерн: {token_pattern}")

        if token_pattern in file_path:
            relative_path = file_path.split(token_pattern)[-1]
            print(f"Relative path после первого разделения: {relative_path}")

            # Дополнительная проверка на случай дублирования URL
            if relative_path.startswith('http'):
                print("Обнаружено дублирование URL")
                # Если остался дублирование, берем только последнюю часть пути
                relative_path = '/'.join(relative_path.split('/')[-2:])  # photos/file_X.jpg
                print(f"Relative path после очистки: {relative_path}")

            telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{relative_path}"
            print(f"Final Telegram URL: {telegram_file_url}")
        else:
            print("Паттерн не найден")
    else:
        print("URL не начинается с http")
        telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        print(f"Сформированный URL: {telegram_file_url}")

    # Проверяем что URL не дублируется
    url_parts = telegram_file_url.split("https://api.telegram.org/file/bot")
    if len(url_parts) > 2:
        print("❌ В URL все еще есть дублирование!")
    elif len(url_parts) == 2:
        print("✅ URL правильный, без дублирования")
    else:
        print("? Неожиданный формат URL")

if __name__ == "__main__":
    test_improved_parsing()