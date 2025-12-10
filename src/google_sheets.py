import gspread
from google.oauth2.service_account import Credentials
from src.config import GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEETS_SPREADSHEET_ID, GOOGLE_DRIVE_SCOPES

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

        # Инициализируем заголовки
        self._init_sheet_headers()

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

        # Заголовки для листа products
        products_headers = [
            "product_id", "supplier_internal_id", "location_id",
            "short_description", "full_description", "quantity",
            "image_urls", "created_at"
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

    def add_supplier(self, internal_id, telegram_user_id, telegram_username, contact_name):
        """Добавление нового поставщика"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            internal_id, telegram_user_id, telegram_username,
            contact_name, now, now
        ]
        self.suppliers_sheet.append_row(row)
        return internal_id

    def get_supplier_by_telegram_id(self, telegram_user_id):
        """Получение поставщика по telegram_user_id"""
        try:
            all_records = self.suppliers_sheet.get_all_records()
            for record in all_records:
                # Сравниваем как число и как строку для надежности
                telegram_id = record.get("telegram_user_id")
                if telegram_id == telegram_user_id or str(telegram_id) == str(telegram_user_id):
                    return record
            return None
        except:
            return None

    def add_location(self, location_id, supplier_internal_id, market_name, pavilion_number, contact_phones):
        """Добавление новой локации поставщика"""
        row = [
            location_id, supplier_internal_id, market_name,
            pavilion_number, contact_phones
        ]
        self.locations_sheet.append_row(row)
        return location_id

    def get_locations_by_supplier_id(self, supplier_internal_id):
        """Получение всех локаций поставщика"""
        try:
            all_records = self.locations_sheet.get_all_records()
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
                    return True

            print(f"Location {location_id} not found")
            return False
        except Exception as e:
            print(f"Error deleting location: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_product(self, product_id, supplier_internal_id, location_id, short_description,
                   full_description, quantity, image_urls):
        """Добавление нового товара"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            product_id, supplier_internal_id, location_id,
            short_description, full_description, quantity,
            image_urls, now
        ]
        self.products_sheet.append_row(row)
        return product_id

    def get_products_by_supplier_id(self, supplier_internal_id):
        """Получение всех товаров поставщика"""
        try:
            all_records = self.products_sheet.get_all_records()
            products = []
            for record in all_records:
                supplier_id_field = record.get("supplier_internal_id")
                if supplier_id_field == supplier_internal_id or str(supplier_id_field) == str(supplier_internal_id):
                    products.append(record)
            return products
        except:
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
            all_records = self.products_sheet.get_all_records()
            for i, record in enumerate(all_records):
                if str(record.get("product_id")) == str(product_id):
                    row_num = i + 2  # +2 из-за заголовков и 0-based индексации
                    current_row = self.products_sheet.row_values(row_num)

                    # Обновляем только переданные поля
                    if short_description is not None:
                        current_row[3] = short_description
                    if full_description is not None:
                        current_row[4] = full_description
                    if quantity is not None:
                        current_row[5] = quantity

                    self.products_sheet.update(f"A{row_num}:H{row_num}", [current_row])
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
                    return True
            return False
        except Exception as e:
            print(f"Error deleting product: {e}")
            return False