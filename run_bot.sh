#!/bin/bash

# Настройка логирования с встроенной ротацией Python
LOG_DIR="/root/myAI/MarketBot/logs"
MAIN_DIR="/root/myAI/MarketBot"

# Останавливаем предыдущий процесс
pkill -f "python.*src/main.py" 2>/dev/null

# Удаляем старые логи, если есть
rm -f "$MAIN_DIR/bot.log"

# Создаем директорию для логов
mkdir -p "$LOG_DIR"

# Переходим в директорию проекта
cd "$MAIN_DIR"

# Запускаем бота (Python сам управляет ротацией логов)
nohup python3 src/main.py > /dev/null 2>&1 &

echo "Бот запущен с автоматической ротацией логов в $LOG_DIR/bot.log (макс. 5МБ на файл)"