#!/bin/bash

# Ротация логов при достижении лимита 5MB
LOG_FILE="/root/myAI/MarketBot/logs/bot.log"
MAX_SIZE=$((5 * 1024 * 1024))  # 5MB

# Проверяем размер файла
if [ -f "$LOG_FILE" ]; then
    CURRENT_SIZE=$(stat -f% "$LOG_FILE")

    if [ "$CURRENT_SIZE" -gt "$MAX_SIZE" ]; then
        echo "$(date): Log file reached ${MAX_SIZE} bytes, rotating..."

        # Создаем бэкап текущего лога
        mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d_%H%M%S).bak"

        # Создаем новый пустой файл
        touch "$LOG_FILE"

        echo "$(date): Log rotation completed. New log file created."
    fi
fi