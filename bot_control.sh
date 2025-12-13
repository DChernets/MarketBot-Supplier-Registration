#!/bin/bash

# Скрипт для управления ботом через systemd

case "$1" in
    start)
        echo "🚀 Запуск бота..."
        systemctl start marketbot.service
        systemctl status marketbot.service --no-pager -l
        ;;
    stop)
        echo "🛑 Остановка бота..."
        systemctl stop marketbot.service
        echo "Бот остановлен"
        ;;
    restart)
        echo "🔄 Перезапуск бота..."
        systemctl restart marketbot.service
        systemctl status marketbot.service --no-pager -l
        ;;
    status)
        echo "📊 Статус бота:"
        systemctl status marketbot.service --no-pager -l
        ;;
    logs)
        echo "📝 Просмотр логов бота:"
        journalctl -u marketbot.service -f
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   - Запустить бота"
        echo "  stop    - Остановить бота"
        echo "  restart - Перезапустить бота"
        echo "  status  - Показать статус"
        echo "  logs    - Показать логи (выход - Ctrl+C)"
        exit 1
        ;;
esac