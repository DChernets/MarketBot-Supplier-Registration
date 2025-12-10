#!/usr/bin/env python3
"""
Тест Gemini API с разными регионами через VPN/прокси сервисы
"""

import os
import sys
import asyncio
import requests
sys.path.append('/root/myAI/MarketBot')

from src.config import GEMINI_API_KEY, GEMINI_MODEL

async def test_gemini_region(api_url=None, headers=None, proxy=None):
    """Тест Gemini API с указанными параметрами"""
    try:
        # Конфигурация запроса
        if not api_url:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

        if not headers:
            headers = {
                "Content-Type": "application/json",
            }

        # Добавляем API ключ к URL
        api_url_with_key = f"{api_url}?key={GEMINI_API_KEY}"

        # Данные для запроса
        data = {
            "contents": [{
                "parts": [{
                    "text": "Ответь одним словом: тест"
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 10,
                "temperature": 0.1
            }
        }

        print(f"🚀 Отправка запроса на: {api_url}")
        if proxy:
            print(f"🔌 Через прокси: {proxy[:50]}...")

        # Отправка запроса
        response = requests.post(
            api_url_with_key,
            json=data,
            headers=headers,
            proxies={"https": proxy} if proxy else None,
            timeout=30
        )

        print(f"📊 Статус код: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ Успешный ответ: {text.strip()}")
                return True
            else:
                print("❌ Неожиданный формат ответа")
                print(f"📄 Ответ: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"📄 Ответ: {response.text[:500]}...")
            return False

    except Exception as e:
        print(f"❌ Исключение: {str(e)}")
        return False

async def test_with_vpn_services():
    """Тест с различными VPN сервисами"""

    print("🔍 Пробуем различные подходы к подключению...")

    # 1. Текущий прокси (Швеция)
    print("\n1️⃣ Текущий прокси (Швеция):")
    sweden_proxy = "http://user58477:xr58c1@46.183.28.14:6052"
    result1 = await test_gemini_region(proxy=sweden_proxy)

    # 2. Попробуем без прокси (если сработает)
    print("\n2️⃣ Без прокси:")
    result2 = await test_gemini_region()

    # 3. Попробуем использовать другой эндпоинт Google
    print("\n3️⃣ Альтернативный эндпоинт (vertexai):")
    try:
        # Этот может работать в других регионах
        vertex_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        result3 = await test_gemini_region(api_url=vertex_url)
    except Exception as e:
        print(f"❌ Ошибка vertex: {e}")
        result3 = False

    return result1 or result2 or result3

async def check_ip_location(proxy=None):
    """Проверить текущий IP и локацию"""
    try:
        proxies = {"https": proxy} if proxy else None
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        ip_data = response.json()
        ip = ip_data.get("origin", "unknown")

        # Получаем информацию о геолокации
        geo_response = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
        geo_data = geo_response.json()

        print(f"🌍 IP: {ip}")
        print(f"📍 Локация: {geo_data.get('country', 'Unknown')}, {geo_data.get('city', 'Unknown')}")
        print(f"🏢 ISP: {geo_data.get('isp', 'Unknown')}")

        return geo_data

    except Exception as e:
        print(f"❌ Не удалось определить локацию: {e}")
        return None

if __name__ == "__main__":
    print("🌍 Тестирование Gemini API с разных локаций")
    print("="*60)

    # Проверяем текущую локацию
    print("📍 Ваша текущая локация:")
    current_location = asyncio.run(check_ip_location())

    # Проверяем локацию через прокси
    print("\n📍 Локация через прокси:")
    sweden_proxy = "http://user58477:xr58c1@46.183.28.14:6052"
    proxy_location = asyncio.run(check_ip_location(sweden_proxy))

    # Тестируем API
    print("\n" + "="*60)
    print("🧪 Тестирование Gemini API:")
    success = asyncio.run(test_with_vpn_services())

    print("\n" + "="*60)
    print("📊 ИТОГИ:")

    if success:
        print("🎉 Найден рабочий способ подключения!")
        print("💡 Рекомендуется использовать этот метод для бота")
    else:
        print("❌ Все способы подключения не сработали")
        print("\n🔧 Возможные решения:")
        print("1. 🌐 Попробовать VPN из США/Европы (NordVPN, ExpressVPN)")
        print("2. 🔄 Использовать другой API ключ")
        print("3. 📡 Настроить туннель через поддерживаемый регион")
        print("4. 🔧 Использовать сторонний сервис для доступа к Gemini")
        print("5. 📱 Попробовать Google AI Studio через браузер")