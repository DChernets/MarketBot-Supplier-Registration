#!/usr/bin/env python3
"""
Скрипт миграции существующих enhanced images в новую структуру Google Drive

Задачи:
1. Читает все файлы из /root/myAI/MarketBot/enhanced_images/
2. Для каждого файла ищет соответствующий product в Google Sheets (по local:filename)
3. Загружает файл в папку MarketBot/Enhanced_Images на Google Drive
4. Обновляет запись в products sheet с новым Drive URL
5. Логирует результаты

Безопасность:
- НЕ удаляет локальные файлы (оставляет как backup)
- При ошибке - пропускает файл и продолжает
- Поддерживает повторный запуск (пропускает уже мигрированные)
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импорты из проекта
from src.config import LOCAL_ENHANCED_IMAGES_PATH
from src.image_storage import get_image_storage_service
from src.google_sheets import GoogleSheetsManager


async def migrate_local_images():
    """
    Основная функция миграции:
    - Загружает локальные enhanced images в Google Drive
    - Обновляет products sheet с новыми Drive URLs
    """
    logger.info("=" * 60)
    logger.info("НАЧАЛО МИГРАЦИИ ENHANCED IMAGES В GOOGLE DRIVE")
    logger.info("=" * 60)

    # Инициализация сервисов
    logger.info("Инициализация сервисов...")
    storage_service = get_image_storage_service()
    init_success = await storage_service.initialize()

    if not init_success:
        logger.error("❌ Не удалось инициализировать Google Drive сервис")
        return

    logger.info("✅ Google Drive сервис инициализирован")

    sheets_manager = GoogleSheetsManager()
    logger.info("✅ Google Sheets менеджер инициализирован")

    # Путь к локальным файлам
    local_dir = Path(LOCAL_ENHANCED_IMAGES_PATH)

    if not local_dir.exists():
        logger.error(f"❌ Локальная директория не найдена: {local_dir}")
        return

    # Получаем список локальных файлов
    local_files = list(local_dir.glob("*.jpg")) + list(local_dir.glob("*.jpeg")) + list(local_dir.glob("*.png"))
    logger.info(f"📂 Найдено локальных файлов: {len(local_files)}")

    if not local_files:
        logger.info("✅ Нет файлов для миграции")
        return

    # Получаем все products с local: URLs
    logger.info("📊 Загрузка данных из Google Sheets...")
    all_products = sheets_manager.products_sheet.get_all_records()
    logger.info(f"📊 Всего products в Sheets: {len(all_products)}")

    # Фильтруем products с local: URLs
    products_with_local = [
        p for p in all_products
        if p.get('enhanced_image_url', '').startswith('local:')
    ]
    logger.info(f"🔍 Products с local: URLs: {len(products_with_local)}")

    # Статистика миграции
    migrated_count = 0
    skipped_count = 0
    error_count = 0

    # Миграция каждого файла
    for i, local_file in enumerate(local_files, 1):
        filename = local_file.name
        logger.info(f"\n[{i}/{len(local_files)}] Обработка: {filename}")

        # Ищем product с этим filename
        matching_product = None
        for product in products_with_local:
            enhanced_url = product.get('enhanced_image_url', '')
            if enhanced_url == f"local:{filename}":
                matching_product = product
                break

        if not matching_product:
            logger.warning(f"⚠️  Не найден product для файла: {filename}")
            skipped_count += 1
            continue

        product_id = matching_product.get('product_id')
        logger.info(f"   Product ID: {product_id}")

        try:
            # Читаем файл
            with open(local_file, 'rb') as f:
                image_bytes = f.read()

            file_size_mb = len(image_bytes) / (1024 * 1024)
            logger.info(f"   Размер файла: {file_size_mb:.2f} MB")

            # Загружаем в Google Drive
            logger.info(f"   📤 Загрузка в Google Drive...")
            drive_url = await storage_service.upload_image(
                image_bytes=image_bytes,
                filename=filename,
                product_id=product_id
            )

            if drive_url:
                logger.info(f"   ✅ Загружено в Drive: {drive_url[:60]}...")

                # Обновляем Sheets
                logger.info(f"   📝 Обновление Google Sheets...")
                sheets_manager.update_product_enhanced_content(
                    product_id=product_id,
                    enhanced_image_url=drive_url
                )

                logger.info(f"   ✅ Sheets обновлен для product_id: {product_id}")
                migrated_count += 1

                # Инвалидируем кеш для обновления данных
                sheets_manager.invalidate_cache("products")

            else:
                logger.error(f"   ❌ Не удалось загрузить в Drive: {filename}")
                error_count += 1

        except Exception as e:
            logger.error(f"   ❌ Ошибка при миграции {filename}: {e}")
            error_count += 1

        # Небольшая задержка между загрузками
        if i < len(local_files):
            await asyncio.sleep(0.5)

    # Итоговая статистика
    logger.info("\n" + "=" * 60)
    logger.info("МИГРАЦИЯ ЗАВЕРШЕНА")
    logger.info("=" * 60)
    logger.info(f"✅ Успешно мигрировано: {migrated_count}")
    logger.info(f"⚠️  Пропущено: {skipped_count}")
    logger.info(f"❌ Ошибок: {error_count}")
    logger.info(f"📊 Всего обработано: {len(local_files)}")
    logger.info("=" * 60)

    if migrated_count > 0:
        logger.info("\n💡 ВАЖНО:")
        logger.info("   - Локальные файлы НЕ удалены (оставлены как backup)")
        logger.info("   - Проверьте обновленные записи в Google Sheets")
        logger.info("   - Протестируйте отображение изображений в боте")


def main():
    """Запуск миграции"""
    try:
        asyncio.run(migrate_local_images())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Миграция прервана пользователем")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    main()
