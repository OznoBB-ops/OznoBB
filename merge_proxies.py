import requests
import asyncio
import aiohttp
from datetime import datetime

SOURCES = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "proxies.txt"
TIMEOUT = 5
MAX_CONCURRENT = 20

async def check_proxy_alive(proxy_string: str, session: aiohttp.ClientSession) -> bool:
    """Проверяет, живой ли прокси через подключение к тестовому URL"""
    try:
        # Парсим тип прокси
        if not any(proxy_string.startswith(p) for p in ["vless://", "ss://", "trojan://", "hysteria://", "tuic://"]):
            return False
        
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        # Используем прокси для подключения
        async with session.get(
            "https://www.google.com",
            timeout=timeout,
            ssl=False,
            proxy=proxy_string if proxy_string.startswith(("http://", "https://")) else None
        ) as resp:
            return resp.status == 200
    except:
        return False

async def fetch_proxies(url: str, session: aiohttp.ClientSession) -> list:
    """Загружает прокси из источника"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                text = await resp.text()
                proxies = [line.strip() for line in text.split('\n') if line.strip()]
                print(f"✓ Загружено {len(proxies)} из {url}")
                return proxies
    except Exception as e:
        print(f"✗ Ошибка загрузки {url}: {e}")
    return []

async def check_all_proxies(proxies: list) -> list:
    """Проверяет все прокси асинхронно"""
    print(f"\n🔍 Проверяю {len(proxies)} прокси на живость...")
    
    alive_proxies = []
    checked = 0
    
    async with aiohttp.ClientSession() as session:
        # Обрабатываем прокси пакетами
        for i in range(0, len(proxies), MAX_CONCURRENT):
            batch = proxies[i:i + MAX_CONCURRENT]
            tasks = [check_proxy_alive(p, session) for p in batch]
            results = await asyncio.gather(*tasks)
            
            for proxy, is_alive in zip(batch, results):
                checked += 1
                if is_alive:
                    alive_proxies.append(proxy)
                    print(f"✓ [{checked}/{len(proxies)}] Живой: {proxy[:50]}...")
                else:
                    print(f"✗ [{checked}/{len(proxies)}] Мертвый: {proxy[:50]}...")
    
    return alive_proxies

async def main():
    """Главная функция"""
    print("=== Объединение и проверка прокси ===\n")
    
    # Загружаем все прокси
    all_proxies = set()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_proxies(url, session) for url in SOURCES]
        results = await asyncio.gather(*tasks)
        
        for proxies in results:
            all_proxies.update(proxies)
    
    print(f"\n✓ Всего загружено: {len(all_proxies)} прокси")
    
    # Дедуплицируем
    unique_proxies = list(all_proxies)
    
    # Проверяем живые
    alive = await check_all_proxies(unique_proxies)
    
    # Сохраняем
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for proxy in alive:
            f.write(proxy + '\n')
    
    print(f"\n✓ Живых прокси: {len(alive)} из {len(unique_proxies)}")
    print(f"✓ Файл {OUTPUT_FILE} создан")

if __name__ == "__main__":
    asyncio.run(main())
