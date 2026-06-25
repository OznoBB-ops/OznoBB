import asyncio
import aiohttp
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# ============================================
# ТВОИ ИСТОЧНИКИ (только твои)
# ============================================
URLS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

# ============================================
# УСЛОВИЯ
# ============================================
OUTPUT_FILE = "proxies.txt"
TCP_TIMEOUT = 3
PORTS = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]
CONCURRENCY = 50  # асинхронных проверок одновременно

# ============================================
# ФУНКЦИИ
# ============================================

def is_reality(line: str) -> bool:
    return line.startswith('vless://') and 'security=reality' in line

def extract_host_port(line: str):
    """Извлекает host и port из VLESS-ссылки."""
    try:
        parsed = urlparse(line)
        if parsed.hostname and parsed.port:
            return parsed.hostname, parsed.port
        match = re.search(r'@([^:]+):(\d+)', line)
        if match:
            return match.group(1), int(match.group(2))
    except:
        pass
    return None, None

async def tcp_probe(host: str, port: int, timeout: float) -> float | None:
    """Проверяет TCP-порт с таймаутом."""
    start = time.perf_counter()
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return (time.perf_counter() - start) * 1000
    except Exception:
        return None

async def check_proxy(line: str, sem: asyncio.Semaphore) -> tuple | None:
    """Проверяет один прокси."""
    async with sem:
        if not is_reality(line):
            return None
        
        host, port = extract_host_port(line)
        if not host or not port:
            return None
        
        # Проверяем все порты, берём лучший (минимальный) пинг
        best_ping = None
        for p in PORTS:
            ping = await tcp_probe(host, p, TCP_TIMEOUT)
            if ping is not None:
                if best_ping is None or ping < best_ping:
                    best_ping = ping
        
        if best_ping is not None and best_ping < 1000:
            return (line, best_ping)
        return None

async def fetch_text(session, url: str) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        r.raise_for_status()
        return await r.text(errors='ignore')

async def main():
    print("=" * 50)
    print("🚀 СБОРКА REALITY-ПРОКСИ (АСИНХРОННАЯ)")
    print("=" * 50)
    
    # 1. Скачиваем подписки
    print("\n📦 Шаг 1: Загрузка подписок...")
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        tasks = [fetch_text(session, url) for url in URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 2. Собираем строки
    raw = []
    for r in results:
        if isinstance(r, Exception):
            print(f"   ❌ Ошибка: {r}")
            continue
        raw.extend(r.splitlines())
    
    # 3. Оставляем только REALITY и убираем дубли
    unique = list(set(line.strip() for line in raw if line.strip() and not line.startswith('#') and is_reality(line.strip())))
    print(f"📊 Уникальных REALITY-прокси: {len(unique)}")
    
    if not unique:
        print("❌ Нет REALITY-прокси!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет REALITY-прокси\n")
        return
    
    # 4. Проверяем асинхронно
    print(f"\n⏳ Шаг 2: Проверка TCP ({CONCURRENCY} потоков)...")
    sem = asyncio.Semaphore(CONCURRENCY)
    working = []
    checked = 0
    total = len(unique)
    
    # Создаём задачи
    tasks = [check_proxy(line, sem) for line in unique]
    
    for coro in asyncio.as_completed(tasks):
        checked += 1
        try:
            result = await coro
            if result:
                line, ping = result
                working.append((line, ping))
                print(f"   ✅ {line[:50]}... {ping:.0f} мс ({len(working)} найдено)")
        except:
            pass
        
        if checked % 25 == 0:
            print(f"   ⏳ Проверено {checked}/{total}... ({len(working)} найдено)")
    
    # 5. Сортируем по пингу
    working.sort(key=lambda x: x[1])
    
    print(f"\n🎯 Рабочих REALITY-прокси: {len(working)}")
    
    # 6. Сохраняем
    with open(OUTPUT_FILE, 'w') as f:
        if working:
            for line, ping in working:
                f.write(f"{line}\n")
        else:
            f.write("# Нет рабочих REALITY-прокси\n")
    
    print(f"\n✅ Готово! Список REALITY-прокси сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
