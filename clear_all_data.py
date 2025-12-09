#!/usr/bin/env python3
"""
Скрипт для полной очистки всех данных в Google Sheets
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.google_sheets import GoogleSheetsManager

def clear_all_data():
    """Полная очистка всех данных"""
    sheets = GoogleSheetsManager()

    print("🔄 Начинаем полную очистку данных...")

    # Очищаем лист suppliers
    print("\n📋 Очистка листа suppliers...")
    try:
        # Получаем все данные кроме заголовков
        suppliers_data = sheets.suppliers_sheet.get_all_values()
        if len(suppliers_data) > 1:  # Если есть данные кроме заголовков
            # Удаляем все строки кроме первой (заголовки)
            for i in range(len(suppliers_data) - 1, 0, -1):
                sheets.suppliers_sheet.delete_rows(i + 1)  # +1 потому что строки нумеруются с 1
            print(f"✅ Удалено {len(suppliers_data) - 1} записей из suppliers")
        else:
            print("✅ Лист suppliers уже пуст")
    except Exception as e:
        print(f"❌ Ошибка при очистке suppliers: {e}")

    # Очищаем лист locations
    print("\n📍 Очистка листа locations...")
    try:
        # Получаем все данные кроме заголовков
        locations_data = sheets.locations_sheet.get_all_values()
        if len(locations_data) > 1:  # Если есть данные кроме заголовков
            # Удаляем все строки кроме первой (заголовки)
            for i in range(len(locations_data) - 1, 0, -1):
                sheets.locations_sheet.delete_rows(i + 1)  # +1 потому что строки нумеруются с 1
            print(f"✅ Удалено {len(locations_data) - 1} записей из locations")
        else:
            print("✅ Лист locations уже пуст")
    except Exception as e:
        print(f"❌ Ошибка при очистке locations: {e}")

    print("\n🎉 Полная очистка завершена!")

def verify_cleanup():
    """Проверка что очистка прошла успешно"""
    sheets = GoogleSheetsManager()

    print("\n🔍 Проверка результатов очистки...")

    # Проверяем suppliers
    suppliers_data = sheets.suppliers_sheet.get_all_values()
    suppliers_count = len(suppliers_data) - 1  # Вычитаем заголовки
    print(f"📋 Suppliers: {suppliers_count} записей")

    # Проверяем locations
    locations_data = sheets.locations_sheet.get_all_values()
    locations_count = len(locations_data) - 1  # Вычитаем заголовки
    print(f"📍 Locations: {locations_count} записей")

    if suppliers_count == 0 and locations_count == 0:
        print("\n✅ Все данные успешно удалены!")
        return True
    else:
        print(f"\n⚠️ Остались данные: {suppliers_count} suppliers, {locations_count} locations")
        return False

def main():
    """Главная функция"""
    print("🗑️ ПОЛНАЯ ОЧИСТКА БАЗЫ ДАННЫХ\n")

    # Запрашиваем подтверждение
    response = input("⚠️ ВНИМАНИЕ: Это удалит ВСЕ данные из Google Sheets.\n"
                     "   Включая всех поставщиков и их локации.\n"
                     "   Это действие НЕВОЗМОЖНО отменить.\n\n"
                     "   Вы уверены, что хотите продолжить? (введите 'ДА' для подтверждения): ")

    if response.strip().upper() != 'ДА':
        print("\n❌ Операция отменена.")
        return

    print("\n🚀 Начинаем очистку...")

    try:
        # Шаг 1: Очистка
        clear_all_data()

        # Шаг 2: Проверка
        success = verify_cleanup()

        if success:
            print("\n🎯 База данных полностью очищена!")
            print("💡 Теперь вы можете заново протестировать регистрацию.")
        else:
            print("\n⚠️ Очистка завершена с предупреждениями.")

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()