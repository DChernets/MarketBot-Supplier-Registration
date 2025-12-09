# MarketBot - Telegram бот для поставщиков

Бот для сбора брифа от поставщиков и создания визиток с информацией о точках продаж.

## Функционал

- Автоматическая регистрация поставщиков через Telegram
- Сбор информации о поставщике (имя, контакты)
- Добавление нескольких точек продаж (рынки, павильоны)
- Формирование визитки для клиентов
- Сохранение данных в Google Sheets

## Структура проекта

```
MarketBot/
├── src/
│   ├── main.py           # Основной файл бота
│   ├── config.py         # Конфигурация
│   └── google_sheets.py  # Работа с Google Sheets
├── config/
│   └── google_credentials.json  # Ключи Google API (нужно создать)
├── logs/                 # Логи
├── requirements.txt      # Зависимости
├── .env                  # Переменные окружения
└── .env.example          # Пример .env файла
```

## Настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Создайте нового бота командой `/newbot`
3. Получите токен бота и добавьте его в `.env` файл

### 3. Настройка Google Sheets API

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите Google Sheets API и Google Drive API
4. Создайте сервисный аккаунт
5. Скачайте JSON файл с ключами и переименуйте его в `google_credentials.json`
6. Положите файл в папку `config/`
7. Создайте новую Google Таблицу
8. Поделитесь таблицей с email из сервисного аккаунта
9. Добавьте ID таблицы в `.env` файл

### 4. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_бота
GOOGLE_SHEETS_SPREADSHEET_ID=ваш_id_таблицы
```

## Запуск

```bash
python src/main.py
```

## Структура данных в Google Sheets

### Лист suppliers
- internal_id - уникальный ID поставщика
- telegram_user_id - ID пользователя в Telegram
- telegram_username - ник в Telegram
- contact_name - имя представителя
- created_at - дата создания
- updated_at - дата обновления

### Лист locations
- location_id - уникальный ID точки
- supplier_internal_id - ID поставщика
- market_name - название рынка
- pavilion_number - номер павильона
- contact_phones - телефоны через запятую

## Команды бота

- `/start` - Начать регистрацию
- `/profile` - Посмотреть профиль
- `/help` - Справка