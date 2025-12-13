#!/usr/bin/env python3
"""
Скрипт для тестирования улучшения контента
"""
import asyncio
import sys
import logging

# Устанавливаем PYTHONPATH
sys.path.insert(0, '/root/myAI/MarketBot')

from src.content_generation_service import ContentGenerationService
from src.gemini_service import GeminiService
from src.google_sheets import GoogleSheetsManager
from src.config import GEMINI_API_KEY, GOOGLE_SHEETS_SPREADSHEET_ID

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhancement():
    """Тестирование улучшения контента"""
    try:
        # Инициализация сервисов
        sheets_manager = GoogleSheetsManager(GOOGLE_SHEETS_SPREADSHEET_ID)
        content_service = ContentGenerationService(sheets_manager)

        # Тестовый товар
        test_product = {
            'название': 'Стеклянный бокал для вина',
            'описание': 'Бокал из прозрачного стекла, объем 250 мл, классический дизайн',
            'материал': 'Стекло',
            'размеры': 'Высота 15 см, диаметр 8 см',
            'производство': 'Турция',
            'упаковка': 'Коробка, 12 штук'
        }

        # Тестовое изображение (создадим простое для теста)
        from PIL import Image
        import io

        # Создаем тестовое изображение
        img = Image.new('RGB', (400, 300), color='lightblue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # Запускаем улучшение
        logger.info("Начинаем тестирование улучшения контента...")

        result = await content_service.enhance_product_content(
            product_info=test_product,
            product_image_bytes=img_bytes.getvalue(),
            generate_image=True,
            generate_description=True,
            generate_marketing=True
        )

        # Проверяем результаты
        logger.info("Результаты улучшения:")
        if result.get('enhanced_image_bytes'):
            logger.info("✅ Улучшенное изображение сгенерировано")
        else:
            logger.info("❌ Улучшенное изображение не сгенерировано")

        if result.get('generated_description'):
            logger.info(f"✅ Улучшенное описание: {result['generated_description']}")
        else:
            logger.info("❌ Улучшенное описание не сгенерировано")

        if result.get('marketing_text'):
            logger.info(f"✅ Маркетинговый текст: {result['marketing_text']}")
        else:
            logger.info("❌ Маркетинговый текст не сгенерирован")

        return result

    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_enhancement())
    if result:
        print("\n✅ Тест завершен успешно!")
    else:
        print("\n❌ Тест завершился с ошибкой!")