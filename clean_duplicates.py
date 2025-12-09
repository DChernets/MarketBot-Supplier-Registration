#!/usr/bin/env python3
"""
Скрипт для очистки дубликатов в Google Sheets
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.google_sheets import GoogleSheetsManager

def analyze_duplicates():
    """Анализ дубликатов в таблицах"""
    sheets = GoogleSheetsManager()

    # Получаем всех поставщиков
    suppliers_records = sheets.suppliers_sheet.get_all_records()
    print(f"Всего поставщиков: {len(suppliers_records)}")

    # Группируем по telegram_user_id для поиска дубликатов
    telegram_groups = {}
    for record in suppliers_records:
        telegram_id = record.get("telegram_user_id")
        if telegram_id not in telegram_groups:
            telegram_groups[telegram_id] = []
        telegram_groups[telegram_id].append(record)

    # Показываем дубликаты поставщиков
    print("\nДубликаты поставщиков:")
    duplicates_count = 0
    for telegram_id, records in telegram_groups.items():
        if len(records) > 1:
            print(f"Telegram ID {telegram_id}: {len(records)} записей")
            duplicates_count += len(records) - 1
            for i, record in enumerate(records, 1):
                print(f"  {i}. {record.get('internal_id')} - {record.get('contact_name')}")

    print(f"\nВсего дубликатов поставщиков: {duplicates_count}")

    # Получаем все локации
    locations_records = sheets.locations_sheet.get_all_records()
    print(f"\nВсего локаций: {len(locations_records)}")

    # Анализируем дубликаты локаций по поставщикам
    print("\nЛокации по поставщикам:")
    supplier_location_counts = {}
    for record in locations_records:
        supplier_id = record.get("supplier_internal_id")
        if supplier_id not in supplier_location_counts:
            supplier_location_counts[supplier_id] = []
        supplier_location_counts[supplier_id].append(record)

    for supplier_id, locations in supplier_location_counts.items():
        # Ищем похожие локации (дубликаты)
        location_strings = []
        for loc in locations:
            loc_str = f"{loc.get('market_name','')}_{loc.get('pavilion_number','')}_{loc.get('contact_phones','')}"
            location_strings.append((loc_str, loc))

        # Считаем уникальные комбинации
        unique_locations = {}
        for loc_str, loc in location_strings:
            if loc_str not in unique_locations:
                unique_locations[loc_str] = []
            unique_locations[loc_str].append(loc)

        duplicates = [locs for locs in unique_locations.values() if len(locs) > 1]
        if duplicates:
            print(f"\nПоставщик {supplier_id}:")
            for dup_group in duplicates:
                print(f"  Дубликаты ({len(dup_group)}): {dup_group[0].get('market_name')} {dup_group[0].get('pavilion_number')}")

    return telegram_groups, supplier_location_counts

def merge_suppliers(telegram_groups):
    """Объединение дубликатов поставщиков"""
    sheets = GoogleSheetsManager()

    print("\nНачинаем объединение дубликатов поставщиков...")

    for telegram_id, records in telegram_groups.items():
        if len(records) > 1:
            print(f"\nОбрабатываем Telegram ID: {telegram_id}")

            # Оставляем первую (самую старую) запись
            main_record = records[0]
            duplicate_records = records[1:]

            print(f"Основная запись: {main_record.get('internal_id')}")
            print(f"Дубликаты для удаления: {[r.get('internal_id') for r in duplicate_records]}")

            # Перемещаем локации от дубликатов к основной записи
            for duplicate in duplicate_records:
                duplicate_id = duplicate.get('internal_id')

                # Находим все локации дубликата
                all_locations = sheets.locations_sheet.get_all_records()
                locations_to_move = []

                for i, location in enumerate(all_locations):
                    if location.get("supplier_internal_id") == duplicate_id:
                        row_num = i + 2
                        locations_to_move.append((row_num, location))

                print(f"Перемещаем {len(locations_to_move)} локаций от {duplicate_id}")

                # Сначала читаем данные локаций для перемещения
                for row_num, location in locations_to_move:
                    # Обновляем supplier_internal_id на основной
                    new_row = [
                        location.get("location_id"),
                        main_record.get("internal_id"),  # Меняем на основной supplier_id
                        location.get("market_name"),
                        location.get("pavilion_number"),
                        location.get("contact_phones")
                    ]

                    # Обновляем строку
                    sheets.locations_sheet.update(f"A{row_num}:E{row_num}", [new_row])

                # Удаляем запись дубликата поставщика
                all_suppliers = sheets.suppliers_sheet.get_all_records()
                for i, supplier in enumerate(all_suppliers):
                    if supplier.get("internal_id") == duplicate_id:
                        row_num = i + 2
                        sheets.suppliers_sheet.delete_rows(row_num)
                        print(f"Удален дубликат поставщика: {duplicate_id}")
                        break

    print("\nОбъединение завершено!")

def clean_location_duplicates():
    """Очистка дубликатов локаций"""
    sheets = GoogleSheetsManager()

    print("\nОчистка дубликатов локаций...")

    all_locations = sheets.locations_sheet.get_all_records()
    location_groups = {}

    # Группируем по supplier_internal_id
    for location in all_locations:
        supplier_id = location.get("supplier_internal_id")
        if supplier_id not in location_groups:
            location_groups[supplier_id] = []
        location_groups[supplier_id].append(location)

    deleted_count = 0

    for supplier_id, locations in location_groups.items():
        # Ищем полные дубликаты (одинаковые рынок, павильон, телефоны)
        unique_combinations = {}

        for location in locations:
            # Преобразуем все значения в строки для надежного сравнения
            market_name = str(location.get('market_name','')).lower().strip()
            pavilion_number = str(location.get('pavilion_number','')).lower().strip()
            contact_phones = str(location.get('contact_phones','')).lower().strip()
            combo_key = f"{market_name}|{pavilion_number}|{contact_phones}"

            if combo_key not in unique_combinations:
                unique_combinations[combo_key] = []
            unique_combinations[combo_key].append(location)

        # Удаляем дубликаты, оставляя только первую запись
        for combo_key, duplicates in unique_combinations.items():
            if len(duplicates) > 1:
                print(f"Найдены дубликаты для поставщика {supplier_id}: {len(duplicates)} записей")

                # Сортируем по ID чтобы удалить более новые
                duplicates.sort(key=lambda x: x.get('location_id', ''))

                # Оставляем первую, удаляем остальные
                for duplicate in duplicates[1:]:
                    location_id = duplicate.get('location_id')
                    if sheets.delete_location(location_id):
                        print(f"  Удален дубликат локации: {location_id}")
                        deleted_count += 1
                    else:
                        print(f"  Ошибка удаления дубликата: {location_id}")

    print(f"\nУдалено дубликатов локаций: {deleted_count}")

def main():
    """Главная функция"""
    print("Анализ и очистка дубликатов в Google Sheets...")

    try:
        # Шаг 1: Анализ
        telegram_groups, supplier_location_counts = analyze_duplicates()

        # Шаг 2: Объединение поставщиков
        merge_suppliers(telegram_groups)

        # Шаг 3: Очистка дубликатов локаций
        clean_location_duplicates()

        print("\n✅ Очистка завершена!")

        # Повторный анализ
        print("\nПовторный анализ после очистки:")
        analyze_duplicates()

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()