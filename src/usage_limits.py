#!/usr/bin/env python3
"""
Сервис управления лимитами использования функций генерации контента
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class UsageRecord:
    """Запись об использовании функции"""
    usage_id: str
    user_id: int
    product_id: str
    action_type: str  # 'image_generation', 'description_generation', 'content_enhancement'
    created_at: datetime
    success: bool
    error_message: Optional[str] = None

@dataclass
class DailyLimit:
    """Дневные лимиты пользователя"""
    user_id: int
    daily_image_generations: int
    daily_description_generations: int
    daily_content_enhancements: int
    last_reset_date: date
    total_generations: int

class UsageLimits:
    """Класс для управления лимитами использования"""

    # Константы лимитов
    DAILY_IMAGE_GENERATION_LIMIT = 1
    DAILY_DESCRIPTION_GENERATION_LIMIT = 1
    DAILY_CONTENT_ENHANCEMENT_LIMIT = 1

    def __init__(self, sheets_manager=None):
        """Инициализация сервиса лимитов"""
        self.sheets_manager = sheets_manager
        logger.info("Сервис управления лимитами инициализирован")

    def check_daily_limit(self, user_id: int, product_id: str, action_type: str) -> Dict[str, Any]:
        """
        Проверить дневной лимит для пользователя

        Args:
            user_id: ID пользователя Telegram
            product_id: ID товара
            action_type: Тип действия ('image_generation', 'description_generation', 'content_enhancement')

        Returns:
            Dict: {
                'allowed': bool,
                'remaining': int,
                'next_reset': datetime,
                'message': str
            }
        """
        try:
            # Получаем текущую дату
            today = datetime.now().date()
            next_reset = datetime.combine(today, datetime.max.time())

            # Проверяем лимит для конкретного действия
            if action_type == 'image_generation':
                limit = self.DAILY_IMAGE_GENERATION_LIMIT
                count = self._get_today_usage_count(user_id, 'image_generation', product_id)
                action_name = "генерации изображений"

            elif action_type == 'description_generation':
                limit = self.DAILY_DESCRIPTION_GENERATION_LIMIT
                count = self._get_today_usage_count(user_id, 'description_generation', product_id)
                action_name = "генерации описаний"

            elif action_type == 'content_enhancement':
                limit = self.DAILY_CONTENT_ENHANCEMENT_LIMIT
                count = self._get_today_usage_count(user_id, 'content_enhancement', product_id)
                action_name = "улучшения контента"

            else:
                logger.error(f"Неизвестный тип действия: {action_type}")
                return {
                    'allowed': False,
                    'remaining': 0,
                    'next_reset': next_reset,
                    'message': "Неизвестный тип действия"
                }

            remaining = max(0, limit - count)

            result = {
                'allowed': count < limit,
                'remaining': remaining,
                'next_reset': next_reset,
                'limit': limit,
                'used': count,
                'action_name': action_name
            }

            if not result['allowed']:
                # Формируем сообщение об исчерпании лимита
                hours_until_reset = 24 - datetime.now().hour
                result['message'] = (
                    f"❌ Лимит на {action_name} исчерпан ({limit} раз в день).\n"
                    f"Следующее обновление через {hours_until_reset} часов."
                )
            else:
                result['message'] = (
                    f"✅ Доступно: {remaining}/{limit} {action_name} сегодня."
                )

            return result

        except Exception as e:
            logger.error(f"Ошибка при проверке лимитов: {e}")
            return {
                'allowed': False,
                'remaining': 0,
                'next_reset': datetime.combine(datetime.now().date(), datetime.max.time()),
                'message': "Ошибка при проверке лимитов. Попробуйте позже."
            }

    def record_usage(self, user_id: int, product_id: str, action_type: str,
                     success: bool = True, error_message: str = None) -> bool:
        """
        Записать использование функции

        Args:
            user_id: ID пользователя Telegram
            product_id: ID товара
            action_type: Тип действия
            success: Успешность выполнения
            error_message: Сообщение об ошибке (если есть)

        Returns:
            bool: Успешность записи
        """
        try:
            import uuid

            # Создаем запись
            usage_record = UsageRecord(
                usage_id=str(uuid.uuid4()),
                user_id=user_id,
                product_id=product_id,
                action_type=action_type,
                created_at=datetime.now(),
                success=success,
                error_message=error_message
            )

            if self.sheets_manager:
                # Записываем в Google Sheets
                self.sheets_manager.add_content_usage(usage_record)
                logger.info(f"Записано использование: {action_type} для пользователя {user_id}")
                return True
            else:
                logger.warning("Sheets manager не доступен, запись не сохранена")
                return False

        except Exception as e:
            logger.error(f"Ошибка при записи использования: {e}")
            return False

    def _get_today_usage_count(self, user_id: int, action_type: str, product_id: str) -> int:
        """
        Получить количество использований за сегодня

        Args:
            user_id: ID пользователя
            action_type: Тип действия
            product_id: ID товара (опционально, для проверки лимитов на конкретный товар)

        Returns:
            int: Количество использований
        """
        try:
            if not self.sheets_manager:
                return 0

            today = datetime.now().date()
            usage_records = self.sheets_manager.get_content_usage_by_user(user_id, today)

            # Фильтруем по типу действия и продукту
            count = 0
            for record in usage_records:
                if (record['action_type'] == action_type and
                    record['success'] == 'True' and
                    record['product_id'] == product_id):
                    count += 1

            return count

        except Exception as e:
            logger.error(f"Ошибка при получении счетчика использования: {e}")
            return 0

    def get_usage_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику использования для пользователя

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Dict: Статистика использования
        """
        try:
            if not self.sheets_manager:
                return {}

            today = datetime.now().date()
            usage_records = self.sheets_manager.get_content_usage_by_user(user_id, today)

            stats = {
                'today': {
                    'image_generations': 0,
                    'description_generations': 0,
                    'content_enhancements': 0,
                    'successful': 0,
                    'failed': 0
                },
                'total': {
                    'generations': 0,
                    'last_usage': None
                }
            }

            # Считаем статистику за сегодня
            for record in usage_records:
                action_type = record['action_type']
                success = record['success'] == 'True'

                if success:
                    stats['today']['successful'] += 1
                    if action_type == 'image_generation':
                        stats['today']['image_generations'] += 1
                    elif action_type == 'description_generation':
                        stats['today']['description_generations'] += 1
                    elif action_type == 'content_enhancement':
                        stats['today']['content_enhancements'] += 1
                else:
                    stats['today']['failed'] += 1

            # Получаем общую статистику
            all_usage = self.sheets_manager.get_all_content_usage(user_id)
            stats['total']['generations'] = len(all_usage)

            if all_usage:
                last_usage = max(all_usage, key=lambda x: datetime.fromisoformat(x['created_at']))
                stats['total']['last_usage'] = last_usage['created_at']

            return stats

        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}

    def reset_daily_limits(self) -> bool:
        """
        Сбросить дневные лимиты (вызывать в 00:00 UTC)

        Returns:
            bool: Успешность сброса
        """
        try:
            if self.sheets_manager:
                # Сбрасываем лимиты в Google Sheets
                self.sheets_manager.reset_daily_limits(datetime.now().date())
                logger.info("Дневные лимиты успешно сброшены")
                return True
            else:
                logger.warning("Sheets manager не доступен, сброс лимитов не выполнен")
                return False

        except Exception as e:
            logger.error(f"Ошибка при сбросе лимитов: {e}")
            return False

    def get_user_products_with_available_generation(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить список товаров пользователя, для которых доступна генерация контента

        Args:
            user_id: ID пользователя

        Returns:
            List[Dict]: Список товаров с информацией о доступности
        """
        try:
            if not self.sheets_manager:
                return []

            # Получаем товары пользователя
            supplier = self.sheets_manager.get_supplier_by_telegram_id(user_id)
            if not supplier:
                return []

            products = self.sheets_manager.get_products_by_supplier_id(supplier['internal_id'])
            products_with_status = []

            today = datetime.now().date()

            for product in products:
                product_id = product.get('product_id')

                # Проверяем лимиты для каждого типа действий
                image_limit = self.check_daily_limit(user_id, product_id, 'image_generation')
                description_limit = self.check_daily_limit(user_id, product_id, 'description_generation')
                enhancement_limit = self.check_daily_limit(user_id, product_id, 'content_enhancement')

                products_with_status.append({
                    'product': product,
                    'can_generate_image': image_limit['allowed'],
                    'can_generate_description': description_limit['allowed'],
                    'can_enhance_content': enhancement_limit['allowed'],
                    'remaining_image': image_limit['remaining'],
                    'remaining_description': description_limit['remaining'],
                    'remaining_enhancement': enhancement_limit['remaining']
                })

            return products_with_status

        except Exception as e:
            logger.error(f"Ошибка при получении товаров с доступной генерацией: {e}")
            return []

    def is_enhancement_available(self, user_id: int, product_id: str) -> bool:
        """
        Проверить, доступно ли улучшение контента для товара

        Args:
            user_id: ID пользователя
            product_id: ID товара

        Returns:
            bool: Доступность улучшения
        """
        try:
            limit_check = self.check_daily_limit(user_id, product_id, 'content_enhancement')
            return limit_check['allowed']

        except Exception as e:
            logger.error(f"Ошибка при проверке доступности улучшения: {e}")
            return False

    def cleanup_old_usage_records(self, days_to_keep: int = 30) -> bool:
        """
        Очистить старые записи об использовании

        Args:
            days_to_keep: Количество дней для хранения записей

        Returns:
            bool: Успешность очистки
        """
        try:
            if self.sheets_manager:
                cutoff_date = datetime.now().date() - datetime.timedelta(days=days_to_keep)
                self.sheets_manager.cleanup_old_usage_records(cutoff_date)
                logger.info(f"Старые записи об использовании удалены (старше {days_to_keep} дней)")
                return True
            else:
                logger.warning("Sheets manager не доступен, очистка не выполнена")
                return False

        except Exception as e:
            logger.error(f"Ошибка при очистке старых записей: {e}")
            return False

# Глобальный экземпляр сервиса
_usage_limits = None

def get_usage_limits(sheets_manager=None) -> UsageLimits:
    """Получить экземпляр сервиса управления лимитами"""
    global _usage_limits
    if _usage_limits is None:
        _usage_limits = UsageLimits(sheets_manager)
    return _usage_limits