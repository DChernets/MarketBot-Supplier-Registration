"""
Сервис хранения изображений в Google Drive с использованием нового Service Account
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

from src.config import GOOGLE_SERVICE_ACCOUNT_2_FILE

logger = logging.getLogger(__name__)

class GoogleDriveStorageOAuth:
    """Класс для работы с Google Drive через OAuth Service Account"""

    def __init__(self):
        """Инициализация сервиса Google Drive"""
        self.scopes = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]
        self.service = None
        self.folder_id = None
        self._initialize_service()
        self._create_or_get_folder()

    def _initialize_service(self):
        """Инициализация Google Drive service"""
        try:
            # Загружаем учетные данные нового Service Account
            credentials_path = Path(GOOGLE_SERVICE_ACCOUNT_2_FILE)
            if not credentials_path.exists():
                raise FileNotFoundError(f"Файл учетных данных не найден: {credentials_path}")

            credentials = Credentials.from_service_account_file(
                credentials_path,
                scopes=self.scopes
            )

            # Создаем сервис
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive сервис успешно инициализирован с новым Service Account")

        except Exception as e:
            logger.error(f"Ошибка инициализации Google Drive сервиса: {e}")
            raise

    def _create_or_get_folder(self):
        """Создать или получить папку для изображений"""
        try:
            folder_name = "MarketBot Storage"

            # Ищем папку
            response = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            folders = response.get('files', [])

            if folders:
                # Папка найдена
                self.folder_id = folders[0]['id']
                logger.info(f"Найдена существующая папка: {folder_name} (ID: {self.folder_id})")
            else:
                # Создаем новую папку
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }

                folder = self.service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()

                self.folder_id = folder.get('id')
                logger.info(f"Создана новая папка: {folder_name} (ID: {self.folder_id})")

        except Exception as e:
            logger.error(f"Ошибка при работе с папкой: {e}")
            raise

    async def upload_image(self, image_bytes: bytes, filename: str, product_id: str = None) -> str:
        """
        Загрузить изображение в Google Drive

        Args:
            image_bytes: Байты изображения
            filename: Имя файла
            product_id: ID товара (опционально)

        Returns:
            str: URL загруженного изображения
        """
        try:
            # Генерируем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if product_id:
                unique_filename = f"{product_id}_{timestamp}_{filename}"
            else:
                unique_filename = f"image_{timestamp}_{filename}"

            # Подготавливаем метаданные файла
            file_metadata = {
                'name': unique_filename,
                'parents': [self.folder_id]
            }

            # Создаем медиа объект
            media = MediaIoBaseUpload(
                io.BytesIO(image_bytes),
                mimetype='image/jpeg',
                resumable=True
            )

            # Загружаем файл
            logger.info(f"Загрузка файла: {unique_filename}")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,webViewLink'
            ).execute()

            file_id = file.get('id')
            file_name = file.get('name')
            file_size = file.get('size')
            view_link = file.get('webViewLink')

            logger.info(f"Файл успешно загружен: {file_name} ({file_size} bytes)")
            logger.info(f"ID файла: {file_id}")
            logger.info(f"Ссылка: {view_link}")

            # Делаем файл доступным для публичного просмотра
            self.service.permissions().create(
                fileId=file_id,
                body={
                    'role': 'reader',
                    'type': 'anyone'
                }
            ).execute()

            # Возвращаем прямую ссылку на файл
            # Формат: https://drive.google.com/uc?id=FILE_ID
            download_url = f"https://drive.google.com/uc?id={file_id}"

            return download_url

        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            return None

    def get_folder_info(self):
        """Получить информацию о папке"""
        try:
            if not self.folder_id:
                return None

            folder = self.service.files().get(
                fileId=self.folder_id,
                fields='id,name,size,webViewLink'
            ).execute()

            return {
                'id': folder.get('id'),
                'name': folder.get('name'),
                'size': folder.get('size', '0'),
                'web_view_link': folder.get('webViewLink')
            }

        except Exception as e:
            logger.error(f"Ошибка получения информации о папке: {e}")
            return None

    def list_files(self, limit: int = 10):
        """Получить список файлов в папке"""
        try:
            if not self.folder_id:
                return []

            response = self.service.files().list(
                q=f"'{self.folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id,name,size,createdTime)',
                orderBy='createdTime desc',
                pageSize=limit
            ).execute()

            return response.get('files', [])

        except Exception as e:
            logger.error(f"Ошибка получения списка файлов: {e}")
            return []

    def delete_file(self, file_id: str) -> bool:
        """Удалить файл"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Файл {file_id} успешно удален")
            return True

        except Exception as e:
            logger.error(f"Ошибка удаления файла {file_id}: {e}")
            return False

# Синглтон
_drive_storage_oauth = None

def get_drive_storage_oauth():
    """Получить экземпляр Google Drive Storage"""
    global _drive_storage_oauth
    if _drive_storage_oauth is None:
        _drive_storage_oauth = GoogleDriveStorageOAuth()
    return _drive_storage_oauth