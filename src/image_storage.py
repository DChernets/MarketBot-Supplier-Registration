#!/usr/bin/env python3
"""
Сервис для управления изображениями в Google Drive
"""

import os
import asyncio
import aiofiles
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image
import io
from datetime import datetime
import uuid
from src.config import (
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    GOOGLE_SERVICE_ACCOUNT_2_FILE,
    GOOGLE_DRIVE_SCOPES,
    DRIVE_FOLDER_NAME,
    GOOGLE_DRIVE_MARKETBOT_FOLDER_ID,
    DRIVE_ENHANCED_IMAGES_SUBFOLDER,
    USE_OAUTH_FOR_DRIVE,
    GOOGLE_OAUTH_CREDENTIALS_FILE,
    GOOGLE_OAUTH_TOKENS_FILE,
    MAX_PHOTO_SIZE_MB,
    SUPPORTED_PHOTO_FORMATS,
    PHOTO_QUALITY,
    HTTP_PROXY,
    HTTPS_PROXY
)

# Configure proxy for Google APIs
if HTTP_PROXY or HTTPS_PROXY:
    import os
    if HTTP_PROXY:
        os.environ['HTTP_PROXY'] = HTTP_PROXY
    if HTTPS_PROXY:
        os.environ['HTTPS_PROXY'] = HTTPS_PROXY

logger = logging.getLogger(__name__)

class ImageStorageService:
    """Класс для управления изображениями в Google Drive"""

    def __init__(self):
        """Инициализация сервиса"""
        self.scopes = GOOGLE_DRIVE_SCOPES
        self.use_oauth = USE_OAUTH_FOR_DRIVE

        # Выбираем метод авторизации
        if self.use_oauth:
            # OAuth авторизация (от имени пользователя)
            self.creds = self._load_oauth_credentials()
            logger.info("Используется OAuth авторизация для Google Drive")
        else:
            # Service Account авторизация
            self.creds = Credentials.from_service_account_file(
                GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=self.scopes
            )
            logger.info("Используется Service Account для Google Drive")

        self.drive_service: Optional[Resource] = None
        self.marketbot_folder_id: Optional[str] = GOOGLE_DRIVE_MARKETBOT_FOLDER_ID  # Корневая папка MarketBot
        self.folder_id: Optional[str] = None  # ID подпапки Enhanced_Images

    def _load_oauth_credentials(self) -> Optional[OAuthCredentials]:
        """Загрузка OAuth credentials из токенов"""
        try:
            tokens_file = Path(GOOGLE_OAUTH_TOKENS_FILE)

            if not tokens_file.exists():
                logger.error(f"Файл OAuth токенов не найден: {tokens_file}")
                logger.error("Запустите: python3 get_oauth_token_manual.py")
                return None

            with open(tokens_file, 'r') as f:
                token_data = json.load(f)

            # Создаем credentials из токенов
            creds = OAuthCredentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', self.scopes)
            )

            # Проверяем и обновляем токен если нужно
            if creds and creds.expired and creds.refresh_token:
                logger.info("OAuth токен истек, обновляю...")
                creds.refresh(Request())

                # Сохраняем обновленные токены
                self._save_oauth_tokens(creds, tokens_file)
                logger.info("OAuth токен обновлен")

            return creds

        except Exception as e:
            logger.error(f"Ошибка загрузки OAuth credentials: {e}")
            return None

    def _save_oauth_tokens(self, creds: OAuthCredentials, tokens_file: Path):
        """Сохранение обновленных OAuth токенов"""
        try:
            token_data = {
                'access_token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': list(creds.scopes) if creds.scopes else [],
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }

            with open(tokens_file, 'w') as f:
                json.dump(token_data, f, indent=2)

        except Exception as e:
            logger.error(f"Ошибка сохранения OAuth токенов: {e}")

    async def initialize(self) -> bool:
        """Инициализация сервиса и создание папки"""
        try:
            logger.info("Инициализация Google Drive сервиса")

            # Создаем сервис
            self.drive_service = build('drive', 'v3', credentials=self.creds)

            # Новая логика: если задан GOOGLE_DRIVE_MARKETBOT_FOLDER_ID, создаем подпапку
            if self.marketbot_folder_id:
                logger.info(f"Используется корневая папка MarketBot: {self.marketbot_folder_id}")
                # Создаем подпапку Enhanced_Images внутри MarketBot
                self.folder_id = await self._create_subfolder_in_parent(
                    parent_id=self.marketbot_folder_id,
                    subfolder_name=DRIVE_ENHANCED_IMAGES_SUBFOLDER
                )
            else:
                # Старая логика: создаем папку "MarketBot Images" в корне
                logger.info("GOOGLE_DRIVE_MARKETBOT_FOLDER_ID не задан, используется старая логика")
                self.folder_id = await self._get_or_create_folder()

            if self.folder_id:
                logger.info(f"Google Drive сервис инициализирован. Folder ID: {self.folder_id}")
                return True
            else:
                logger.error("Не удалось создать папку в Google Drive")
                return False

        except Exception as e:
            logger.error(f"Ошибка инициализации Google Drive сервиса: {e}")
            return False

    async def _get_or_create_folder(self) -> Optional[str]:
        """Получить или создать папку для изображений"""
        try:
            # Ищем папку с нужным именем
            query = f"name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
            )

            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Найдена существующая папка: {folder_id}")
                return folder_id

            # Если папки нет, создаем новую
            logger.info("Создание новой папки для изображений")
            folder_metadata = {
                'name': DRIVE_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
            )

            folder_id = folder.get('id')
            logger.info(f"Создана новая папка: {folder_id}")

            # Делаем папку доступной для всех
            await self._make_folder_public(folder_id)

            return folder_id

        except Exception as e:
            logger.error(f"Ошибка при работе с папкой: {e}")
            return None

    async def _create_subfolder_in_parent(self, parent_id: str, subfolder_name: str) -> Optional[str]:
        """Создать или получить подпапку внутри родительской папки"""
        try:
            # Ищем подпапку с нужным именем внутри parent_id
            query = f"name='{subfolder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
            )

            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Найдена существующая подпапка '{subfolder_name}': {folder_id}")
                return folder_id

            # Если подпапки нет, создаем новую
            logger.info(f"Создание подпапки '{subfolder_name}' внутри {parent_id}")
            folder_metadata = {
                'name': subfolder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }

            folder = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
            )

            folder_id = folder.get('id')
            logger.info(f"Создана подпапка '{subfolder_name}': {folder_id}")

            return folder_id

        except Exception as e:
            logger.error(f"Ошибка при создании подпапки '{subfolder_name}': {e}")
            return None

    async def _make_folder_public(self, folder_id: str):
        """Сделать папку общедоступной"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.permissions().create(
                    fileId=folder_id,
                    body=permission,
                    fields='id'
                ).execute()
            )

            logger.info(f"Папка {folder_id} сделана общедоступной")

        except Exception as e:
            logger.warning(f"Не удалось сделать папку общедоступной: {e}")

    def _validate_image(self, image_bytes: bytes, filename: str) -> bool:
        """Валидация изображения"""
        try:
            # Проверяем размер файла
            size_mb = len(image_bytes) / (1024 * 1024)
            if size_mb > MAX_PHOTO_SIZE_MB:
                logger.error(f"Размер файла {size_mb:.2f}MB превышает лимит {MAX_PHOTO_SIZE_MB}MB")
                return False

            # Проверяем формат
            file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
            if file_ext not in SUPPORTED_PHOTO_FORMATS:
                logger.error(f"Неподдерживаемый формат файла: {file_ext}")
                return False

            # Проверяем, что это действительно изображение
            try:
                Image.open(io.BytesIO(image_bytes))
                return True
            except:
                logger.error("Файл не является валидным изображением")
                return False

        except Exception as e:
            logger.error(f"Ошибка валидации изображения: {e}")
            return False

    def _optimize_image(self, image_bytes: bytes) -> bytes:
        """Оптимизация изображения"""
        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Конвертируем в RGB если необходимо
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Оптимизируем размер
            max_width = 1920
            max_height = 1080

            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Сохраняем с оптимизацией
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=PHOTO_QUALITY, optimize=True)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Ошибка оптимизации изображения: {e}")
            return image_bytes

    async def upload_image(self, image_bytes: bytes, filename: str, product_id: Optional[str] = None) -> Optional[str]:
        """Загрузить изображение в Google Drive"""
        try:
            if not self.drive_service or not self.folder_id:
                logger.error("Сервис не инициализирован")
                return None

            # Валидация
            if not self._validate_image(image_bytes, filename):
                return None

            # Оптимизация
            optimized_bytes = self._optimize_image(image_bytes)

            # Генерируем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_ext = os.path.splitext(filename)[1].lower() or '.jpg'

            if product_id:
                upload_filename = f"product_{product_id}_{timestamp}_{unique_id}{file_ext}"
            else:
                upload_filename = f"upload_{timestamp}_{unique_id}{file_ext}"

            # Метаданные файла
            file_metadata = {
                'name': upload_filename,
                'parents': [self.folder_id]
            }

            # Загрузка файла
            media = MediaIoBaseUpload(
                io.BytesIO(optimized_bytes),
                mimetype='image/jpeg',
                resumable=True
            )

            logger.info(f"Загрузка файла: {upload_filename}")

            file = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink,size'
                ).execute()
            )

            file_id = file.get('id')

            # Делаем файл общедоступным
            await self._make_file_public(file_id)

            # Возвращаем прямую ссылку для скачивания (не webViewLink)
            # Формат: https://drive.google.com/uc?export=view&id=FILE_ID
            direct_link = f"https://drive.google.com/uc?export=view&id={file_id}"

            logger.info(f"Файл успешно загружен: {file_id}")
            logger.info(f"Прямая ссылка: {direct_link}")
            return direct_link

        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            return None

    async def _make_file_public(self, file_id: str):
        """Сделать файл общедоступным"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    fields='id'
                ).execute()
            )

        except Exception as e:
            logger.warning(f"Не удалось сделать файл общедоступным: {e}")

    async def upload_multiple_images(self, images_data: List[tuple], product_id: Optional[str] = None) -> List[str]:
        """Загрузить несколько изображений"""
        urls = []

        for i, (image_bytes, filename) in enumerate(images_data):
            logger.info(f"Загрузка изображения {i + 1}/{len(images_data)}")

            try:
                url = await self.upload_image(image_bytes, filename, product_id)
                if url:
                    urls.append(url)
                else:
                    logger.error(f"Не удалось загрузить изображение {i + 1}")

                # Небольшая задержка между запросами
                if i < len(images_data) - 1:
                    await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"Ошибка загрузки изображения {i + 1}: {e}")

        return urls

    async def delete_image(self, file_url: str) -> bool:
        """Удалить изображение из Google Drive"""
        try:
            if not self.drive_service:
                logger.error("Сервис не инициализирован")
                return False

            # Извлекаем ID файла из URL
            file_id = self._extract_file_id_from_url(file_url)
            if not file_id:
                logger.error("Не удалось извлечь ID файла из URL")
                return False

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().delete(fileId=file_id).execute()
            )

            logger.info(f"Файл {file_id} успешно удален")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Файл не найден: {file_url}")
                return True  # Считаем успешным, если файла уже нет
            else:
                logger.error(f"Ошибка удаления файла: {e}")
                return False
        except Exception as e:
            logger.error(f"Ошибка удаления изображения: {e}")
            return False

    def _extract_file_id_from_url(self, file_url: str) -> Optional[str]:
        """Извлечь ID файла из URL Google Drive"""
        try:
            # URL формата: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
            if '/file/d/' in file_url:
                start = file_url.find('/file/d/') + len('/file/d/')
                end = file_url.find('/view', start)
                return file_url[start:end] if end != -1 else file_url[start:]
            return None
        except:
            return None

    async def get_storage_info(self) -> Dict[str, Any]:
        """Получить информацию о хранилище"""
        try:
            if not self.drive_service or not self.folder_id:
                return {"error": "Сервис не инициализирован"}

            # Получаем информацию о папке
            folder = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().get(
                    fileId=self.folder_id,
                    fields='name,size,createdTime'
                ).execute()
            )

            # Получаем количество файлов
            query = f"'{self.folder_id}' in parents"
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id,name,size,createdTime)'
                ).execute()
            )

            files = results.get('files', [])
            total_size = sum(int(f.get('size', 0)) for f in files)

            return {
                "folder_name": folder.get('name'),
                "folder_id": self.folder_id,
                "folder_created": folder.get('createdTime'),
                "files_count": len(files),
                "total_size_mb": total_size / (1024 * 1024),
                "files": files[:10]  # Первые 10 файлов
            }

        except Exception as e:
            logger.error(f"Ошибка получения информации о хранилище: {e}")
            return {"error": str(e)}

# Глобальный экземпляр сервиса
_image_storage_service = None

def get_image_storage_service() -> ImageStorageService:
    """Получение экземпляра сервиса хранения изображений"""
    global _image_storage_service
    if _image_storage_service is None:
        _image_storage_service = ImageStorageService()
    return _image_storage_service

async def initialize_image_storage() -> bool:
    """Инициализация сервиса хранения изображений"""
    try:
        service = get_image_storage_service()
        return await service.initialize()
    except Exception as e:
        logger.error(f"Ошибка инициализации сервиса хранения изображений: {e}")
        return False