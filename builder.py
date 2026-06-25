import asyncio
import aiohttp
import re
import time
from urllib.parse import urlparse

URLS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "proxies.txt"

TCP_TIMEOUT = 3
CONCURRENCY = 50
PORTS = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]

SCHEMES = (
    "vless", "vmess", "trojan", "ss", "ssr", "https", "http"
)

# --------- Парсинг host/port ---------

def is_probably_link(line: str) -> bool:
    s = line.strip().lower()
    if not s:
        return False
    return any(s.startswith(f"{scheme}://") for scheme in SCHEMES) or s.startswith("ss://") or s.startswith("trojan://") or s.startswith("vless://")

def extract_host_port(line: str):
    s = line.strip()

    # Попытка через urlparse (обычно работает для vless/trojan)
    parsed = urlparse(s)
    host = parsed.hostname
    port = parsed.port
    if host and port:
        return host, port

    # vless/trojan часто: scheme://...@host:port
    m = re.search(r"@(.+?):(\d+)", s)
    if m:
        return m.group(1), int(m.group(2))

    # Иногда: host:port в конце (грубая эвристика)
    m2 = re.search(r"(\b[\w\.-]+\b):(\d{2,5})", s)
    if m2:
        p = int(m2.group(2))
        if 1 <= p <= 65535:
            return m2.group(1), p

    return None, None

# --------- Проверка TCP ---------

async def tcp_probe(host: str, port: int, timeout: float) -> float | None:
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return (time.perf_counter() - start) * 1000.0
    except Exception:
        return None

async def check_proxy(line: str, sem: asyncio.Semaphore) -> tuple | None:
    async with sem:
        if not is_probably_link(line):
            return None

        host, port = extract_host_port(line)
        if not host:
            return None

        # Если порт удалось извлечь — проверяем его.
        # Иначе пробуем набор портов.
        ports_to_try = [port] if port else PORTS

        best = None
        for p in ports_to_try:
            ping = await tcp_probe(host, p, TCP_TIMEOUT)
            if ping is not None and (best is None or ping < best):
                best = ping

        if best is not None and best < 1000:
            return line, best
        return None

# --------- Загрузка ---------

async def fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        r.raise_for_status()
        return await r.text(errors="ignore")

def extract_links(text: str):
    links = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if is_probably_link(s):
            links.append(s)
    return links

# --------- main ---------

async def main():
    print("=" * 50)
    print("🚀 СБОРКА PROXIES (все типы по ссылкам) + TCP check")
    print("=" * 50)

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        tasks = [fetch_text(session, u) for u in URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    raw_links = []
    for u, r in zip(URLS, results):
        if isinstance(r, Exception):
            print("Ошибка загрузки:", u, r)
            continue
        links = extract_links(r)
        print(f"Загружено: {u} | links={len(links)}")
        raw_links.extend(links)

    # чистим/уникализируем
    cleaned = []
    for x in raw_links:
        s = x.strip()
        if s:
            cleaned.append(s)

    unique = list(dict.fromkeys(cleaned))  # порядок сохранится
    print(f"\nИтого строк ссылок: {len(unique)}")

    if not unique:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("# Нет ссылок\n")
        return

    print(f"\n⏳ Проверка TCP ({CONCURRENCY} задач одновременно) ...")
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [check_proxy(line, sem) for line in unique]

    working = []
    checked = 0
    total = len(unique)

    for coro in asyncio.as_completed(tasks):
        checked += 1
        try:
            res = await coro
            if res:
                line, ping = res
                working.append((line, ping))
                print(f"✅ {checked}/{total} найдено={len(working)} {ping:.0f}ms")
            elif checked % 50 == 0:
                print(f"Проверено {checked}/{total} найдено={len(working)}")
        except Exception:
            pass

    working.sort(key=lambda x: x[1])

    print(f"\n🎯 Рабочих: {len(working)}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        if working:
            for line, ping in working:
                f.write(line + "\n")
        else:
            f.write("# Нет рабочих прокси\n")

    if working:
        print("Пример (топ1):", working[0][0][:90], f"({working[0][1]:.0f}ms)")

if __name__ == "__main__":
    asyncio.run(main())

