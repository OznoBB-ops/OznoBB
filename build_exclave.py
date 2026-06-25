import asyncio
import aiohttp
import os
import random
import re
import time
from urllib.parse import urlparse, parse_qs

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

LIMIT_MAX = 600
LIMIT_MIN = 500

# сколько кандидатов (reality) брать на проверку “с запасом”
SAMPLE_CANDIDATES = 8000

THREADS = 15
TIMEOUT = 3.0  # 3 секунды на TCP-connect
CONCURRENCY_SEM = THREADS

REALITY_RE = re.compile(r"(?i)^vless://\S+")
SECURITY_RE = re.compile(r"(?i)(?:^|\?|&)security=reality(?:&|$)")


def extract_reality_vless_lines(text: str) -> list[str]:
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
    # Пытаемся разобрать vless://... как URL.
    # Обычно host/port находятся в netloc: vless://[userinfo@]host:port?...
    u = urlparse(line)
    host = u.hostname
    port = u.port

    if host and port:
        return host, port

    # fallback: если urlparse не вытянул порт, пробуем вытащить host:port грубо
    # (берём первое появление host:port после vless://)
    m = re.search(r"(?i)^vless://[^@/]*@?([^:/\s]+):(\d+)", line)
    if m:
        return m.group(1), int(m.group(2))

    return None, None


async def tcp_probe(host: str, port: int, timeout: float) -> float | None:
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
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
        r.raise_for_status()
        return await r.text(errors="ignore")


async def main():
    # 1) скачать источники
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        pages = await asyncio.gather(
            *[fetch_text(session, u) for u in URLS],
            return_exceptions=True
        )

    all_lines = []
    for p in pages:
        if isinstance(p, Exception):
            continue
        all_lines.extend(extract_reality_vless_lines(p))

    # дедуп
    all_lines = list(dict.fromkeys(all_lines))

    # 2) кандидаты с host/port
    candidates = []
    for line in all_lines:
        host, port = parse_host_port(line)
        if host and port and 1 <= port <= 65535:
            candidates.append((host, port, line))

    if not candidates:
        out_path = os.path.join(os.path.dirname(__file__), "proxies.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("")
        return

    # 3) выборка “с запасом” перед проверкой
    if len(candidates) > SAMPLE_CANDIDATES:
        candidates = random.sample(candidates, SAMPLE_CANDIDATES)

    sem = asyncio.Semaphore(CONCURRENCY_SEM)

    async def score(item):
        host, port, line = item
        async with sem:
            dt = await tcp_probe(host, port, TIMEOUT)
            if dt is None:
                return None
            return (dt, line)

    scored = []
    tasks = [score(c) for c in candidates]
    for coro in asyncio.as_completed(tasks):
        res = await coro
        if res is not None:
            scored.append(res)

    # 4) топ-600 по времени коннекта
    scored.sort(key=lambda x: x[0])
    top = scored[:LIMIT_MAX]

    # 5) (не строгое “остановиться на 600”, но итог будет максимум 600)
    out_path = os.path.join(os.path.dirname(__file__), "proxies.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for _, line in top:
            f.write(line.strip() + "\n")

    # В лог можно посмотреть сколько живых получилось
    print(f"Reality total lines: {len(all_lines)}")
    print(f"Candidates with host:port: {len(candidates)}")
    print(f"Live after TCP: {len(scored)}")
    print(f"Wrote to proxies.txt: {len(top)}")

if __name__ == "__main__":
    asyncio.run(main())
