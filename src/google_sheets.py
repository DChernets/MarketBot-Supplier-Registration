import gspread
import logging
import time
from google.oauth2.service_account import Credentials
from src.config import GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEETS_SPREADSHEET_ID, GOOGLE_DRIVE_SCOPES

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        self.scope = GOOGLE_DRIVE_SCOPES
        self.creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=self.scope
        )
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)

        # Получаем или создаем листы
        self.suppliers_sheet = self._get_or_create_sheet("suppliers")
        self.locations_sheet = self._get_or_create_sheet("locations")
        self.products_sheet = self._get_or_create_sheet("products")
        self.content_usage_sheet = self._get_or_create_sheet("content_usage")
        self.content_limits_sheet = self._get_or_create_sheet("content_limits")

        # Инициализируем заголовки
        self._init_sheet_headers()

        # Кеширование для ускорения запросов
        self._cache = {}
        self._cache_timeout = 60  # 60 секунд

    def _get_or_create_sheet(self, sheet_name):
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")

    def _init_sheet_headers(self):
        # Заголовки для листа suppliers
        suppliers_headers = [
            "internal_id", "telegram_user_id", "telegram_username",
            "contact_name", "created_at", "updated_at"
        ]

        # Заголовки для листа locations
        locations_headers = [
            "location_id", "supplier_internal_id", "market_name",
            "pavilion_number", "contact_phones"
        ]

        # Заголовки для листа products (новая JSON-структура с контентом)
        products_headers = [
            "product_id", "supplier_id", "location_id",
            "название", "описание", "производство", "материал", "размеры", "упаковка",
            "photo_urls", "quantity", "created_at",
            "enhanced_image_url", "enhanced_description", "content_generated_at", "content_version"
        ]

        # Заголовки для листа content_usage
        content_usage_headers = [
            "usage_id", "user_id", "product_id", "action_type",
            "created_at", "success", "error_message"
        ]

        # Заголовки для листа content_limits
        content_limits_headers = [
            "user_id", "daily_image_generations", "daily_description_generations",
            "daily_content_enhancements", "last_reset_date", "total_generations"
        ]

        # Проверяем и добавляем заголовки если нужно
        try:
            if not self.suppliers_sheet.get_all_values():
                self.suppliers_sheet.append_row(suppliers_headers)
        except:
            self.suppliers_sheet.append_row(suppliers_headers)

        try:
            if not self.locations_sheet.get_all_values():
                self.locations_sheet.append_row(locations_headers)
        except:
            self.locations_sheet.append_row(locations_headers)

        try:
            if not self.products_sheet.get_all_values():
                self.products_sheet.append_row(products_headers)
        except:
            self.products_sheet.append_row(products_headers)

        try:
            if not self.content_usage_sheet.get_all_values():
                self.content_usage_sheet.append_row(content_usage_headers)
        except:
            self.content_usage_sheet.append_row(content_usage_headers)

        try:
            if not self.content_limits_sheet.get_all_values():
                self.content_limits_sheet.append_row(content_limits_headers)
        except:
            self.content_limits_sheet.append_row(content_limits_headers)

    def _safe_int(self, value, default=1):
        """Безопасное преобразование в int"""
        try:
            if value is None or value == '':
                return default
            return int(str(value).strip() or default)
        except (ValueError, TypeError):
            return default

    def add_supplier(self, internal_id, telegram_user_id, telegram_username, contact_name):
        """Добавление нового поставщика"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            internal_id, telegram_user_id, telegram_username,
            contact_name, now, now
        ]
        self.suppliers_sheet.append_row(row)
        # Инвалидируем кеш для suppliers
        self.invalidate_cache("suppliers")
        return internal_id

    def _get_cached_records(self, sheet_name, sheet):
        """Получить записи из кеша или загрузить из API"""
        cache_key = f"{sheet_name}_records"
        current_time = time.time()

        # Проверяем кеш
        if cache_key in self._cache:
            cache_data = self._cache[cache_key]
            if current_time - cache_data['timestamp'] < self._cache_timeout:
                return cache_data['records']

        # Загружаем из API
        records = sheet.get_all_records()

        # Сохраняем в кеш
        self._cache[cache_key] = {
            'records': records,
            'timestamp': current_time
        }

        return records

    def invalidate_cache(self, sheet_name=None):
        """Очистить кеш для конкретного листа или всего кеша"""
        if sheet_name:
            cache_key = f"{sheet_name}_records"
            if cache_key in self._cache:
                del self._cache[cache_key]
        else:
            self._cache.clear()

    def get_supplier_by_telegram_id(self, telegram_user_id):
        """Получение поставщика по telegram_user_id"""
        try:
            all_records = self._get_cached_records("suppliers", self.suppliers_sheet)
            for record in all_records:
                # Сравниваем как число и как строку для надежности
                telegram_id = record.get("telegram_user_id")
                if telegram_id == telegram_user_id or str(telegram_id) == str(telegram_user_id):
                    return record
            return None
        except:
            return None

    def get_all_suppliers(self):
        """Получить всех поставщиков через кеш"""
        try:
            return self._get_cached_records("suppliers", self.suppliers_sheet)
        except:
            return []

    def add_location(self, location_id, supplier_internal_id, market_name, pavilion_number, contact_phones):
        """Добавление новой локации поставщика"""
        row = [
            location_id, supplier_internal_id, market_name,
            pavilion_number, contact_phones
        ]
        self.locations_sheet.append_row(row)
        # Инвалидируем кеш для locations
        self.invalidate_cache("locations")
        return location_id

    def get_locations_by_supplier_id(self, supplier_internal_id):
        """Получение всех локаций поставщика"""
        try:
            all_records = self._get_cached_records("locations", self.locations_sheet)
            locations = []
            for record in all_records:
                supplier_id_field = record.get("supplier_internal_id")
                # Сравниваем как число и как строку для надежности
                if supplier_id_field == supplier_internal_id or str(supplier_id_field) == str(supplier_internal_id):
                    locations.append(record)
            return locations
        except:
            return []

    def update_location(self, location_id, market_name=None, pavilion_number=None, contact_phones=None):
        """Обновление локации"""
        try:
            print(f"GoogleSheets: Updating location {location_id}")
            print(f"GoogleSheets: market_name={market_name}, pavilion_number={pavilion_number}, contact_phones={contact_phones}")

            all_records = self.locations_sheet.get_all_records()
            print(f"GoogleSheets: Found {len(all_records)} location records")

            for i, record in enumerate(all_records):
                stored_location_id = record.get("location_id")
                print(f"GoogleSheets: Comparing with record {i}: {stored_location_id}")

                if str(stored_location_id) == str(location_id):
                    row_num = i + 2  # +2 из-за заголовков и 0-based индексации
                    print(f"GoogleSheets: Found location at row {row_num}")

                    # Получаем текущие данные
                    current_row = self.locations_sheet.row_values(row_num)
                    print(f"GoogleSheets: Current row data: {current_row}")

                    # Обновляем только переданные поля
                    if market_name is not None:
                        current_row[2] = market_name  # market_name
                        print(f"GoogleSheets: Updated market_name to {market_name}")
                    if pavilion_number is not None:
                        current_row[3] = pavilion_number  # pavilion_number
                        print(f"GoogleSheets: Updated pavilion_number to {pavilion_number}")
                    if contact_phones is not None:
                        current_row[4] = contact_phones  # contact_phones
                        print(f"GoogleSheets: Updated contact_phones to {contact_phones}")

                    print(f"GoogleSheets: Final row data: {current_row}")

                    # Обновляем строку
                    self.locations_sheet.update(f"A{row_num}:E{row_num}", [current_row])
                    print(f"GoogleSheets: Successfully updated row {row_num}")
                    # Инвалидируем кеш для locations
                    self.invalidate_cache("locations")
                    return True

            print(f"GoogleSheets: Location {location_id} not found")
            return False
        except Exception as e:
            print(f"Error updating location: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_location(self, location_id):
        """Удаление локации"""
        try:
            all_records = self.locations_sheet.get_all_records()
            print(f"Attempting to delete location_id: {location_id} (type: {type(location_id)})")
            print(f"Total records in locations sheet: {len(all_records)}")

            for i, record in enumerate(all_records):
                stored_location_id = record.get("location_id")
                print(f"Comparing with record {i}: {stored_location_id} (type: {type(stored_location_id)})")

                # Сравниваем как строки для надежности
                if str(stored_location_id) == str(location_id):
                    row_num = i + 2  # +2 из-за заголовков и 0-based индексации
                    print(f"Found match at row {row_num}, deleting...")
                    self.locations_sheet.delete_rows(row_num)
                    print("Location deleted successfully")
                    # Инвалидируем кеш для locations
                    self.invalidate_cache("locations")
                    return True

            print(f"Location {location_id} not found")
            return False
        except Exception as e:
            print(f"Error deleting location: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_product(self, product_id, supplier_internal_id, location_id, product_data, image_urls):
        """Добавление нового товара с новой JSON-структурой"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Убеждаемся что quantity это число
        quantity = product_data.get('quantity', 1)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 1

        # Собираем строку в соответствии с новой структурой таблицы
        row = [
            str(product_id),                                   # product_id
            str(supplier_internal_id),                        # supplier_id
            str(location_id),                                 # location_id
            str(product_data.get('название', 'Не указано')),           # название
            str(product_data.get('описание', 'Не указано')),           # описание
            str(product_data.get('производство', 'Не указано')),       # производство
            str(product_data.get('материал', 'Не указано')),           # материал
            str(product_data.get('размеры', 'Не указано')),             # размеры
            str(product_data.get('упаковка', 'Не указано')),           # упаковка
            str(image_urls) if image_urls else "",            # photo_urls
            quantity,                                         # quantity (число)
            now,                                              # created_at
        ]


        self.products_sheet.append_row(row)
        # Инвалидируем кеш для products
        self.invalidate_cache("products")
        return product_id

    def add_product_legacy(self, product_id, supplier_internal_id, location_id, short_description,
                          full_description, quantity, image_urls):
        """Добавление нового товара (legacy-метод для обратной совместимости)"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Убеждаемся что quantity это число
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 1

        # Конвертируем старые данные в новую структуру
        product_data = {
            'название': short_description,
            'описание': full_description,
            'производство': 'Не указано',
            'материал': 'Не указано',
            'размеры': 'Не указано',
            'упаковка': 'Не указано'
        }

        return self.add_product(product_id, supplier_internal_id, location_id, product_data, image_urls)

    def get_products_by_supplier_id(self, supplier_internal_id):
        """Получение всех товаров поставщика"""
        try:
            all_records = self._get_cached_records("products", self.products_sheet)
            products = []

            for record in all_records:
                supplier_id_field = record.get("supplier_id")
                if supplier_id_field == supplier_internal_id or str(supplier_id_field) == str(supplier_internal_id):
                    products.append(record)

            return products
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []

    def get_product_by_id(self, product_id):
        """Получение товара по ID"""
        try:
            all_records = self.products_sheet.get_all_records()
            for record in all_records:
                if record.get("product_id") == product_id or str(record.get("product_id")) == str(product_id):
                    return record
            return None
        except:
            return None

    def update_product(self, product_id, short_description=None, full_description=None, quantity=None):
        """Обновление товара"""
        try:
            all_records = self._get_cached_records("products", self.products_sheet)
            for i, record in enumerate(all_records):
                if str(record.get("product_id")) == str(product_id):
                    row_num = i + 2  # +2 из-за заголовков и 0-based индексации
                    current_row = self.products_sheet.row_values(row_num)

                    # Обновляем только переданные поля в пределах колонок A-H (индексы 0-7)
                    if short_description is not None and len(current_row) > 4:
                        current_row[4] = short_description  # Колонка 'описание'
                    if full_description is not None and len(current_row) > 4:
                        current_row[4] = full_description  # Используем ту же колонку для full_description
                    if quantity is not None and len(current_row) > 5:
                        current_row[5] = quantity

                    # Обрезаем массив до 8 элементов (колонки A-H)
                    current_row = current_row[:8]
                    if len(current_row) < 8:
                        # Дополняем до 8 элементов если нужно
                        current_row.extend([''] * (8 - len(current_row)))

                    # Обновляем только существующие колонки (A-H)
                    self.products_sheet.update(f"A{row_num}:H{row_num}", [current_row])
                    # Инвалидируем кеш для products
                    self.invalidate_cache("products")
                    return True
            return False
        except Exception as e:
            print(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id):
        """Удаление товара"""
        try:
            all_records = self.products_sheet.get_all_records()
            for i, record in enumerate(all_records):
                if str(record.get("product_id")) == str(product_id):
                    row_num = i + 2  # +2 из-за заголовков и 0-based индексации
                    self.products_sheet.delete_rows(row_num)
                    # Инвалидируем кеш для products
                    self.invalidate_cache("products")
                    return True
            return False
        except Exception as e:
            print(f"Error deleting product: {e}")
            return False

    def migrate_products_structure(self):
        """Миграция существующих товаров на новую структуру"""
        try:
            print("Начинаем миграцию структуры товаров...")

            # Получаем все существующие товары
            all_records = self.products_sheet.get_all_records()

            if not all_records:
                print("Нет товаров для миграции")
                return True

            # Проверяем, есть ли старая структура (поля name, description)
            first_record = all_records[0] if all_records else {}
            has_old_structure = 'name' in first_record and 'description' in first_record

            if not has_old_structure:
                print("Структура уже новая, миграция не требуется")
                return True

            print(f"Найдено {len(all_records)} товаров для миграции")

            migrated_count = 0
            for i, record in enumerate(all_records):
                try:
                    row_num = i + 2  # +2 из-за заголовков

                    # Получаем старые данные
                    old_name = record.get('name', 'Не указано')
                    old_description = record.get('description', 'Не указано')

                    # Создаем новые поля
                    new_row = [
                        record.get('product_id', ''),
                        record.get('supplier_id', ''),
                        record.get('location_id', ''),
                        old_name,                    # название
                        old_description,            # описание
                        'Не указано',               # производство
                        'Не указано',               # материал
                        'Не указано',               # размеры
                        'Не указано',               # упаковка
                        record.get('photo_urls', ''),
                        record.get('quantity', 1),
                        record.get('created_at', '')
                    ]

                    # Обновляем строку
                    self.products_sheet.update(f"A{row_num}:L{row_num}", [new_row])
                    migrated_count += 1

                    if migrated_count % 10 == 0:
                        print(f"Смигрировано {migrated_count} товаров...")

                except Exception as e:
                    print(f"Ошибка при миграции записи {i}: {e}")
                    continue

            print(f"Миграция завершена! Обновлено {migrated_count} товаров")
            return True

        except Exception as e:
            print(f"Критическая ошибка при миграции: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_product_enhanced_content(self, product_id: str, enhanced_image_url: str = None,
                                       enhanced_description: str = None, content_generated_at: str = None, marketing_text: str = None):
        """Обновить улучшенный контент товара"""
        try:
            all_records = self.products_sheet.get_all_records()

            for i, record in enumerate(all_records):
                if record.get("product_id") == product_id or str(record.get("product_id")) == str(product_id):
                    row_num = i + 2  # +2 из-за заголовков

                    # Получаем текущие данные
                    current_data = [
                        record.get('product_id', ''),
                        record.get('supplier_id', ''),
                        record.get('location_id', ''),
                        record.get('название', ''),
                        record.get('описание', ''),
                        record.get('производство', ''),
                        record.get('материал', ''),
                        record.get('размеры', ''),
                        record.get('упаковка', ''),
                        record.get('photo_urls', ''),
                        record.get('quantity', 1),
                        record.get('created_at', ''),
                        enhanced_image_url if enhanced_image_url else record.get('enhanced_image_url', ''),
                        enhanced_description if enhanced_description else record.get('enhanced_description', ''),
                        content_generated_at if content_generated_at else record.get('content_generated_at', ''),
                        str(self._safe_int(record.get('content_version')) + 1) if enhanced_image_url or enhanced_description else str(self._safe_int(record.get('content_version')))
                    ]

                    # Добавляем маркетинговый текст в current_data
                    marketing_text_value = marketing_text if marketing_text else record.get('marketing_text', '')
                    current_data.append(marketing_text_value)

                    # Обновляем только новые поля (колонки M-Q)
                    # ВАЖНО: Google Sheets API требует двойной список [[...]]
                    self.products_sheet.update(f"M{row_num}:Q{row_num}", [[
                        current_data[12],  # enhanced_image_url
                        current_data[13],  # enhanced_description
                        current_data[14],  # content_generated_at
                        current_data[15],  # content_version
                        current_data[16]   # marketing_text
                    ]])

                    logger.info(f"Обновлен улучшенный контент для товара {product_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Ошибка при обновлении улучшенного контента: {e}")
            return False

    def add_content_usage(self, usage_record):
        """Добавить запись об использовании контента"""
        try:
            row = [
                usage_record.usage_id,
                usage_record.user_id,
                usage_record.product_id,
                usage_record.action_type,
                usage_record.created_at.isoformat(),
                str(usage_record.success),
                usage_record.error_message or ""
            ]
            self.content_usage_sheet.append_row(row)
            return True

        except Exception as e:
            logger.error(f"Ошибка при добавлении записи об использовании: {e}")
            return False

    def get_content_usage_by_user(self, user_id: int, target_date):
        """Получить записи об использовании для пользователя за указанную дату"""
        try:
            all_records = self.content_usage_sheet.get_all_records()
            usage_records = []

            target_date_str = target_date.strftime("%Y-%m-%d")

            for record in all_records:
                user_id_field = record.get("user_id")
                if (user_id_field == user_id or str(user_id_field) == str(user_id)) and \
                   record.get("created_at", "").startswith(target_date_str):
                    usage_records.append(record)

            return usage_records

        except Exception as e:
            logger.error(f"Ошибка при получении записей об использовании: {e}")
            return []

    def get_all_content_usage(self, user_id: int):
        """Получить все записи об использовании для пользователя"""
        try:
            all_records = self.content_usage_sheet.get_all_records()
            usage_records = []

            for record in all_records:
                user_id_field = record.get("user_id")
                if user_id_field == user_id or str(user_id_field) == str(user_id):
                    usage_records.append(record)

            return usage_records

        except Exception as e:
            logger.error(f"Ошибка при получении всех записей об использовании: {e}")
            return []

    def update_or_create_content_limits(self, user_id: int, action_type: str):
        """Обновить или создать лимиты для пользователя"""
        try:
            from datetime import datetime, date
            today = date.today()

            # Ищем существующие лимиты
            all_records = self.content_limits_sheet.get_all_records()

            for record in all_records:
                user_id_field = record.get("user_id")
                if user_id_field == user_id or str(user_id_field) == str(user_id):
                    # Обновляем существующую запись
                    row_num = all_records.index(record) + 2

                    # Обновляем счетчики в зависимости от типа действия
                    daily_image = int(record.get("daily_image_generations", 0))
                    daily_description = int(record.get("daily_description_generations", 0))
                    daily_enhancement = int(record.get("daily_content_enhancements", 0))

                    if action_type == "image_generation":
                        daily_image += 1
                    elif action_type == "description_generation":
                        daily_description += 1
                    elif action_type == "content_enhancement":
                        daily_enhancement += 1

                    # Проверяем, нужно ли сбросить счетчики (новый день)
                    last_reset = record.get("last_reset_date", "")
                    if last_reset != today.isoformat():
                        daily_image = 0
                        daily_description = 0
                        daily_enhancement = 0

                    updated_row = [
                        user_id,
                        daily_image,
                        daily_description,
                        daily_enhancement,
                        today.isoformat(),
                        int(record.get("total_generations", 0)) + 1
                    ]

                    self.content_limits_sheet.update(f"A{row_num}:F{row_num}", updated_row)
                    return True

            # Создаем новую запись, если не нашли существующую
            new_row = [
                user_id,
                1 if action_type == "image_generation" else 0,
                1 if action_type == "description_generation" else 0,
                1 if action_type == "content_enhancement" else 0,
                today.isoformat(),
                1
            ]

            self.content_limits_sheet.append_row(new_row)
            return True

        except Exception as e:
            logger.error(f"Ошибка при обновлении лимитов: {e}")
            return False

    def reset_daily_limits(self, reset_date):
        """Сбросить дневные лимиты для всех пользователей"""
        try:
            reset_date_str = reset_date.isoformat()

            all_records = self.content_limits_sheet.get_all_records()

            for i, record in enumerate(all_records):
                row_num = i + 2
                updated_row = [
                    record.get("user_id"),
                    0,  # daily_image_generations
                    0,  # daily_description_generations
                    0,  # daily_content_enhancements
                    reset_date_str,
                    record.get("total_generations", 0)
                ]

                self.content_limits_sheet.update(f"A{row_num}:F{row_num}", updated_row)

            logger.info(f"Дневные лимиты сброшены для {len(all_records)} пользователей")
            return True

        except Exception as e:
            logger.error(f"Ошибка при сбросе дневных лимитов: {e}")
            return False

    def cleanup_old_usage_records(self, cutoff_date):
        """Очистить старые записи об использовании"""
        try:
            cutoff_date_str = cutoff_date.isoformat()
            all_records = self.content_usage_sheet.get_all_records()

            # Фильтруем записи, которые нужно удалить
            rows_to_delete = []
            for i, record in enumerate(all_records):
                if record.get("created_at", "") < cutoff_date_str:
                    rows_to_delete.append(i + 2)  # +2 из-за заголовков

            # Удаляем старые записи (в обратном порядке, чтобы индексы не сдвигались)
            for row_num in sorted(rows_to_delete, reverse=True):
                self.content_usage_sheet.delete_rows(row_num, 1)

            if rows_to_delete:
                logger.info(f"Удалено {len(rows_to_delete)} старых записей об использовании")
                return True

            return True

        except Exception as e:
            logger.error(f"Ошибка при очистке старых записей: {e}")
            return False