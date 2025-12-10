#!/usr/bin/env python3
"""
Тест парсинга URL с вашим примером
"""

def test_url_parsing():
    """Тест парсинга problematic URL"""

    print("=== Тест парсинга URL ===")

    # Ваш проблемный URL
    problematic_url = "https://api.telegram.org/file/bot8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs/https://api.telegram.org/file/bot8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs/photos/file_2.jpg"

    bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"

    print(f"Проблемный URL: {problematic_url}")
    print(f"Bot token: {bot_token}")

    # Тестируем нашу логику парсинга
    file_path = problematic_url

    print(f"\nOriginal file_path: {file_path}")

    # Если file_path содержит полный URL, извлекаем только путь
    if file_path.startswith('http'):
        print("URL начинается с http")

        # Извлекаем путь после /file/bot{token}/
        token_pattern = f'/file/bot{bot_token}/'
        print(f"Ищем паттерн: {token_pattern}")

        if token_pattern in file_path:
            relative_path = file_path.split(token_pattern)[-1]
            print(f"Найден относительный путь: {relative_path}")

            telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{relative_path}"
            print(f"Исправленный URL: {telegram_file_url}")

            # Проверяем есть ли еще дублирование
            if relative_path.startswith('http'):
                print("Осталось дублирование! Убираем...")
                # Если относительный путь все еще содержит URL, берем только последнюю часть
                clean_path = relative_path.split('/')[-1]
                telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{clean_path}"
                print(f"Финальный исправленный URL: {telegram_file_url}")
        else:
            print(f"Паттерн не найден в URL")
    else:
        print("URL не начинается с http, используем как есть")
        telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        print(f"Сформированный URL: {telegram_file_url}")

def test_correct_url_format():
    """Тест правильного формата URL"""

    print("\n\n=== Тест правильного формата URL ===")

    # Пример правильного относительного пути
    correct_file_path = "photos/file_2.jpg"
    bot_token = "8410046050:AAEvzOzPeQ-uj0DmWngXCQciaD3AXytFZgs"

    print(f"Правильный file_path: {correct_file_path}")

    # Формируем правильный URL
    telegram_file_url = f"https://api.telegram.org/file/bot{bot_token}/{correct_file_path}"
    print(f"Правильный URL: {telegram_file_url}")

    # Проверяем формат
    expected_pattern = "https://api.telegram.org/file/botTOKEN/photos/file_X.jpg"
    print(f"Ожидаемый формат: {expected_pattern}")

    if telegram_file_url.count("https://api.telegram.org/file/bot") == 1:
        print("✅ URL не дублируется")
    else:
        print("❌ URL дублируется")

if __name__ == "__main__":
    test_url_parsing()
    test_correct_url_format()