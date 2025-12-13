"""
Утилитарные функции
"""

def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown для Telegram

    Args:
        text: Текст для экранирования

    Returns:
        str: Экранированный текст
    """
    if not text:
        return text

    # Специальные символы в Markdown
    escape_chars = '_*[]()~`>#+-=|{}.!'

    # Создаем экранированный текст
    escaped = text
    for char in escape_chars:
        escaped = escaped.replace(char, '\\' + char)

    return escaped