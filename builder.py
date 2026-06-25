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
PORTS = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]
CONCURRENCY = 50


def is_reality(line: str) -> bool:
    s = line.strip().lower()
    return s.startswith("vless://") and "security=reality" in s


def extract_host_port(line: str):
    s = line.strip()

    parsed = urlparse(s)
    if parsed.hostname and parsed.port:
        return parsed.hostname, parsed.port

    m = re.search(r"@(.+?):(\d+)", s)
    if m:
        return m.group(1), int(m.group(2))

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
        return (time.perf_counter() - start) * 1000
    except Exception:
        return None


async def check_proxy(line: str, sem: asyncio.Semaphore) -> tuple | None:
    async with sem:
        if not is_reality(line):
            return None

        host, port = extract_host_port(line)
        if not host or not port:
            return None

        best_ping = None
        for p in PORTS:
            ping = await tcp_probe(host, p, TCP_TIMEOUT)
            if ping is not None and (best_ping is None or ping < best_ping):
                best_ping = ping

        if best_ping is not None and best_ping < 1000:
            return (line, best_ping)
        return None


async def fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        r.raise_for_status()
        text = await r.text(errors="ignore")
        print(f"GET {url} len={len(text)} head={text[:120].replace(chr(10), ' ').replace(chr(13), ' ')}")
        return text


async def main():
    print("=" * 50)
    print("🚀 СБОРКА REALITY-ПРОКСИ (АСИНХРОННАЯ)")
    print("=" * 50)

    print("\n📦 Шаг 1: Загрузка подписок...")
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [fetch_text(session, url) for url in URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    raw = []
    for url, r in zip(URLS, results):
        if isinstance(r, Exception):
            print(f"   ❌ Ошибка загрузки {url}: {r}")
            continue
        raw.extend(r.splitlines())

    raw = [ln.strip() for ln in raw if ln.strip() and not ln.strip().startswith("#")]
    print(f"\n📊 raw lines (после # и пустых): {len(raw)}")

    matched = [ln for ln in raw if is_reality(ln)]
    print(f"📊 REALITY matched: {len(matched)}")

    unique = list(set(matched))
    print(f"📊 Уникальных REALITY-proxy: {len(unique)}")

    if not unique:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("# Нет REALITY-прокси\n")
        print("\n❌ Нет REALITY-прокси!")
        return

    print(f"\n⏳ Шаг 2: Проверка TCP ({CONCURRENCY} задач одновременно)...")
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [check_proxy(line, sem) for line in unique]

    working = []
    checked = 0
    total = len(unique)

    for coro in asyncio.as_completed(tasks):
        checked += 1
        try:
            result = await coro
            if result:
                line, ping = result
                working.append((line, ping))
                print(f"   ✅ {line[:60]}... {ping:.0f} мс ({len(working)} найдено)")
        except Exception:
            pass

        if checked % 25 == 0:
            print(f"   ⏳ Проверено {checked}/{total}... ({len(working)} найдено)")

    print(f"\n🎯 Рабочих REALITY-прокси: {len(working)}")

    working.sort(key=lambda x: x[1])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        if working:
            for line, ping in working:
                f.write(f"{line}\n")
        else:
            f.write("# Нет рабочих REALITY-прокси\n")

    print(f"\n✅ Готово! Список сохранён в {OUTPUT_FILE}")
    if working:
        print("sample:", working[0][0][:80], "ping=", f"{working[0][1]:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
