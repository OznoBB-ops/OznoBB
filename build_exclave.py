import asyncio
import aiohttp
import os
import random
import re
import time
from urllib.parse import urlparse, parse_qs

# ============================================
# ИСТОЧНИКИ (10 штук)
# ============================================
URLS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/everything.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/protocols/vless.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/RU.txt",
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/all.txt",
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/light.txt",
]

# ============================================
# УСЛОВИЯ
# ============================================
LIMIT_MAX = 600
LIMIT_MIN = 500
SAMPLE_CANDIDATES = 8000
THREADS = 15
TIMEOUT = 3.0  # 3 секунды на TCP-connect
CONCURRENCY_SEM = THREADS

# ============================================
# РЕГУЛЯРКИ
# ============================================
REALITY_RE = re.compile(r"(?i)^vless://\S+")
SECURITY_RE = re.compile(r"(?i)(?:^|\?|&)security=reality(?:&|$)")

# ============================================
# ФУНКЦИИ
# ============================================

def extract_reality_vless_lines(text: str) -> list[str]:
    """Извлекает только VLESS + REALITY."""
    out = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not REALITY_RE.match(line):
            continue
        if not SECURITY_RE.search(line):
            continue
        out.append(line)
    return out

def parse_host_port(line: str):
    """Извлекает host и port из VLESS-ссылки."""
    u = urlparse(line)
    host = u.hostname
    port = u.port

    if host and port:
        return host, port

    # fallback: если urlparse не вытянул порт
    m = re.search(r"(?i)^vless://[^@/]*@?([^:/\s]+):(\d+)", line)
    if m:
        return m.group(1), int(m.group(2))

    return None, None

async def tcp_probe(host: str, port: int, timeout: float) -> float | None:
    """Проверяет TCP-порт с таймаутом 3 секунды."""
    start = time.perf_counter()
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        dt = time.perf_counter() - start
        return dt
    except Exception:
        return None

async def fetch_text(session, url: str) -> str:
    """Скачивает подписку."""
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
        r.raise_for_status()
        return await r.text(errors="ignore")

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

async def main():
    print("=" * 50)
    print("🚀 СБОРКА REALITY-ПРОКСИ (ASYNC)")
    print("=" * 50)

    # 1. Скачиваем источники
    print("\n📦 Шаг 1: Загрузка подписок...")
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        pages = await asyncio.gather(
            *[fetch_text(session, u) for u in URLS],
            return_exceptions=True
        )

    # 2. Извлекаем REALITY
    all_lines = []
    for p in pages:
        if isinstance(p, Exception):
            print(f"   ❌ Ошибка: {p}")
            continue
        all_lines.extend(extract_reality_vless_lines(p))
    
    print(f"📊 Найдено VLESS+REALITY: {len(all_lines)}")

    # 3. Дедуп
    all_lines = list(dict.fromkeys(all_lines))
    print(f"📊 Уникальных: {len(all_lines)}")

    # 4. Кандидаты с host:port
    candidates = []
    for line in all_lines:
        host, port = parse_host_port(line)
        if host and port and 1 <= port <= 65535:
            candidates.append((host, port, line))
    
    print(f"📊 Кандидатов с host:port: {len(candidates)}")

    if not candidates:
        print("❌ Нет кандидатов!")
        out_path = os.path.join(os.path.dirname(__file__), "proxies.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# Нет кандидатов\n")
        return

    # 5. Случайная выборка до проверки
    if len(candidates) > SAMPLE_CANDIDATES:
        candidates = random.sample(candidates, SAMPLE_CANDIDATES)
        print(f"📊 Взято для проверки: {SAMPLE_CANDIDATES} (случайных)")
    else:
        print(f"📊 Взято для проверки: {len(candidates)} (все)")

    # 6. Проверка через TCP
    print(f"\n⏳ Шаг 2: Проверка TCP ({THREADS} потоков)...")
    sem = asyncio.Semaphore(CONCURRENCY_SEM)
    stop = False

    async def score(item):
        nonlocal stop
        if stop:
            return None
        host, port, line = item
        async with sem:
            dt = await tcp_probe(host, port, TIMEOUT)
            if dt is None:
                return None
            return (dt, line)

    scored = []
    tasks = [score(c) for c in candidates]
    checked = 0
    total = len(candidates)

    for coro in asyncio.as_completed(tasks):
        if stop:
            break
        checked += 1
        res = await coro
        if res is not None:
            scored.append(res)
            print(f"   ✅ {res[1][:50]}... {res[0]*1000:.0f} мс ({len(scored)}/{LIMIT_MAX})")
            if len(scored) >= LIMIT_MAX:
                print(f"   🎯 Достигнут лимит {LIMIT_MAX}, останавливаем проверку...")
                stop = True
                break
        if checked % 25 == 0 and not stop:
            print(f"   ⏳ Проверено {checked}/{total}... ({len(scored)} найдено)")

    # 7. Сортируем и оставляем 600
    scored.sort(key=lambda x: x[0])
    top = scored[:LIMIT_MAX]

    print(f"\n🎯 Рабочих REALITY-прокси: {len(top)}")

    # 8. Сохраняем
    out_path = os.path.join(os.path.dirname(__file__), "proxies.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        if top:
            for _, line in top:
                f.write(line.strip() + "\n")
        else:
            f.write("# Нет рабочих REALITY-прокси\n")

    print(f"\n✅ Готово! Список REALITY-прокси сохранён в {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
