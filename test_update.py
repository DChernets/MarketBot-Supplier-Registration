#!/usr/bin/env python3
"""
Скрипт для тестирования функции обновления локации
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.google_sheets import GoogleSheetsManager

def test_location_update():
    """Тестирование обновления локации"""
    sheets = GoogleSheetsManager()

    print("🧪 ТЕСТИРОВАНИЕ ОБНОВЛЕНИЯ ЛОКАЦИИ\n")

    # Получаем все локации
    all_locations = sheets.locations_sheet.get_all_records()
    print(f"Всего локаций: {len(all_locations)}")

    if not all_locations:
        print("❌ Нет локаций для тестирования")
        return

    # Показываем все локации
    print("\n📍 Список локаций:")
    for i, location in enumerate(all_locations, 1):
        location_id = location.get('location_id')
        market = location.get('market_name')
        pavilion = location.get('pavilion_number')
        phones = location.get('contact_phones')
        print(f"{i}. ID: {location_id[:8]}... | {market} - {pavilion} | {phones}")

    # Выбираем первую локацию для теста
    test_location = all_locations[0]
    location_id = test_location.get('location_id')
    current_pavilion = test_location.get('pavilion_number')

    print(f"\n🎯 Тестируем локацию: {location_id}")
    print(f"Текущий павильон: {current_pavilion}")

    # Тест 1: Обновление павильона
    new_pavilion = "TEST123"
    print(f"\n📝 Тестируем обновление павильона на: {new_pavilion}")

    success = sheets.update_location(
        location_id=location_id,
        pavilion_number=new_pavilion
    )

    if success:
        print("✅ Обновление успешно!")
    else:
        print("❌ Обновление не удалось!")
        return

    # Проверяем результат
    print("\n🔍 Проверяем результат...")
    updated_locations = sheets.locations_sheet.get_all_records()

    updated_location = None
    for location in updated_locations:
        if location.get('location_id') == location_id:
            updated_location = location
            break

    if updated_location:
        updated_pavilion = updated_location.get('pavilion_number')
        print(f"Обновленный павильон: {updated_pavilion}")

        if updated_pavilion == new_pavilion:
            print("✅ Обновление подтверждено!")
        else:
            print("❌ Обновление не сохранилось!")
    else:
        print("❌ Локация не найдена после обновления!")

    # Тест 2: Возврат к исходному значению
    print(f"\n🔄 Возвращаем исходное значение: {current_pavilion}")
    success = sheets.update_location(
        location_id=location_id,
        pavilion_number=current_pavilion
    )

    if success:
        print("✅ Возврат успешно выполнен!")
    else:
        print("❌ Ошибка возврата!")

def main():
    """Главная функция"""
    test_location_update()

if __name__ == "__main__":
    main()