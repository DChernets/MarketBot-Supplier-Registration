#!/bin/bash

LOG_DIR="/root/myAI/MarketBot/logs"

if [ ! -f "$LOG_DIR/bot.log" ]; then
    echo "Лог файл не найден: $LOG_DIR/bot.log"
    exit 1
fi

echo "Просмотр логов бота (Ctrl+C для выхода):"
echo "========================================"
tail -f "$LOG_DIR/bot.log"