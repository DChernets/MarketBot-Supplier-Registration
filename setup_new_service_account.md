# Инструкции по созданию нового Service Account

## 1. Создание Service Account

1. Перейдите в Google Cloud Console: https://console.cloud.google.com/
2. Выберите ваш проект
3. Перейдите: IAM & Admin → Service Accounts
4. Нажмите "+ CREATE SERVICE ACCOUNT"
5. Заполните:
   - Service account name: `marketbot-storage-2`
   - Service account ID: `marketbot-storage-2@PROJECT_ID.iam.gserviceaccount.com`
   - Description: `MarketBot storage account with fresh quota`

## 2. Создание ключей

1. После создания аккаунта, нажмите на него
2. Перейдите на вкладку "KEYS"
3. Нажмите "ADD KEY" → "Create new key"
4. Выберите JSON
5. Скачайте файл
6. Переименуйте в `google_service_account_2.json`
7. Положите в `/root/myAI/MarketBot/config/`

## 3. Настройка доступа Google Drive

1. Откройте downloaded JSON файл
2. Найдите `client_email` (например: `marketbot-storage-2@PROJECT_ID.iam.gserviceaccount.com`)
3. Создайте новую папку в Google Drive с названием "MarketBot Storage"
4. Поделитесь этой папкой с email Service Account
   - Права: Editor
5. ID папки будет использоваться в коде

## 4. Включение API

Убедитесь, что включены:
- Google Drive API
- Google Sheets API

## 5. Обновление кода

Нужно будет обновить пути к ключам в:
- src/config.py - GOOGLE_SHEETS_CREDENTIALS_FILE
- src/image_storage.py