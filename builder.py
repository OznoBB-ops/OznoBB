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

TCP_TIMEOUT = 2.5
CONCURRENCY = 60

# Если в ссылке порт не удалось вытащить — пробуем эти
FALLBACK_PORTS = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]

SCHEMES = ("vless://", "vmess://", "trojan://", "ss://", "ssr://", "http://", "https://")

def looks_like_link(s: str) -> bool:
    t = s.strip()
    return any(t.lower().startswith(x) for x in SCHEMES)

def extract_host_port(line: str):
    s = line.strip()

    # vless/trojan обычно: ...@host:port (часто)
    m = re.search(r'@(.+?):(\d+)', s)
    if m:
        return m.group(1), int(m.group(2))

    # попробовать urlparse
    try:
        p = urlparse(s)
        if p.hostname and p.port:
            return p.hostname, p.port
    except Exception:
        pass

    # host:port на конце (грубая эвристика)
    m2 = re.search(r'(^|[^\w-])([A-Za-z0-9][A-Za-z0-9\.\-]*):(\d{2,5})(?!\d)', s)
    if m2:
        port = int(m2.group(3))
        if 1 <= port <= 65535:
            return m2.group(2), port

    return None, None

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

async def check_line(line: str, sem: asyncio.Semaphore):
    async with sem:
        if not looks_like_link(line):
            return None

        host, port = extract_host_port(line)
        if not host:
            return None

        ports = [port] if port else FALLBACK_PORTS

        best = None
        for p in ports:
            t = await tcp_probe(host, p, TCP_TIMEOUT)
            if t is not None and (best is None or t < best):
                best = t

        # порог “живой”
        if best is not None and best < 1000:
            return (line, best)
        return None

async def fetch_text(session, url: str) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        r.raise_for_status()
        return await r.text(errors="ignore")

def extract_candidates(text: str):
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if looks_like_link(s):
            out.append(s)
    return out

async def main():
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        res = await asyncio.gather(*[fetch_text(session, u) for u in URLS], return_exceptions=True)

    candidates = []
    for u, r in zip(URLS, res):
        if isinstance(r, Exception):
            print(f"Ошибка загрузки: {u}: {r}")
            continue
        links = extract_candidates(r)
        print(f"Загружено {len(links)} ссылок из {u}")
        candidates.extend(links)

    # уникализация (с сохранением порядка)
    seen = set()
    unique = []
    for x in candidates:
        if x not in seen:
            seen.add(x)
            unique.append(x)

    print(f"\nВсего кандидатов: {len(unique)}")

    if not unique:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("# Нет данных\n")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [check_line(x, sem) for x in unique]

    working = []
    checked = 0
    total = len(unique)

    for coro in asyncio.as_completed(tasks):
        checked += 1
        res = await coro
        if res:
            working.append(res)
        if checked % 50 == 0:
            print(f"Проверено {checked}/{total} | живых найдено {len(working)}")

    working.sort(key=lambda t: t[1])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        if working:
            for line, ms in working:
                f.write(line + "\n")
        else:
            f.write("# Нет рабочих прокси\n")

    print(f"\nЖивых прокси: {len(working)} -> {OUTPUT_FILE}")
    if working:
        print("Топ-1:", working[0][0][:90], f"({working[0][1]:.0f}ms)")

if __name__ == "__main__":
    asyncio.run(main())

