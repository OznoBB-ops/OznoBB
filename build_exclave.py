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

PORTS = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]

# Ваши параметры
SAMPLE_BEFORE_CHECK = 2000
LIMIT = 600
THREADS = 15
TIMEOUT_PER_PORT = 3.0

REALITY_LINE_RE = re.compile(r"^vless://\S+$", re.IGNORECASE)


def extract_reality_vless_lines(text: str) -> list[str]:
    out = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not REALITY_LINE_RE.match(line):
            continue
        # фильтруем только security=reality
        # (line может содержать параметры без порядка)
        if "security=reality" in line:
            out.append(line)
    return out


def parse_host_port_from_vless(line: str):
    # ожидаем vless://[...@]host:port?...security=reality...
    u = urlparse(line)
    host = u.hostname
    port = u.port
    if not host or not port:
        return None, None

    qs = parse_qs(u.query)
    security = qs.get("security", [None])[0]
    if security != "reality":
        return None, None

    return host, port


async def tcp_probe_first_success(host: str, sem: asyncio.Semaphore) -> float | None:
    """
    Проверяем список портов по порядку.
    Возвращаем минимальное время успешного connect среди PORTS (в секундах), либо None если все неуспешны.
    Для каждого порта используем TIMEOUT_PER_PORT.
    """
    best = None

    # sem ограничивает число одновременно выполняемых TCP connect-операций (внутри задач).
    # Мы ставим acquisition на каждый порт отдельно, чтобы параллельность реально соблюдалась.
    for p in PORTS:
        async with sem:
            start = time.perf_counter()
            try:
                conn = asyncio.open_connection(host, p)
                reader, writer = await asyncio.wait_for(conn, timeout=TIMEOUT_PER_PORT)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                dt = time.perf_counter() - start
                best = dt if best is None else min(best, dt)
                # ранняя остановка внутри прокси:
                # если нашли прям “очень быстро”, можно продолжать не всегда.
                # Но чтобы соответствовать “берём лучшие по времени” — достаточно best по минимальному dt.
                # Продолжаем перебор портов, чтобы не потерять ещё быстрее.
            except Exception:
                pass

    return best


async def fetch_all(session, url: str) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
        r.raise_for_status()
        return await r.text(errors="ignore")


async def main():
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        tasks = [fetch_all(session, u) for u in URLS]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

    all_lines = []
    for p in pages:
        if isinstance(p, Exception):
            continue
        all_lines.extend(extract_reality_vless_lines(p))

    # дедуп
    all_lines = list(dict.fromkeys(all_lines))

    # подготовим кандидатов с парсингом host/port (порт из самого vless://...:port)
    # (tcp_probe ниже игнорирует порт vless:// и проверяет фиксированный набор PORTS как в ТЗ,
    # но если в URL нет host/port — строка всё равно битая, выкидываем)
    candidates = []
    for line in all_lines:
        host, port = parse_host_port_from_vless(line)
        if host and port:
            candidates.append(line)

    if not candidates:
        # создаём пустой файл, чтобы workflow не падал
        out_path = os.path.join(os.path.dirname(__file__), "proxies.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            pass
        return

    # случайная выборка до 2000
    if len(candidates) > SAMPLE_BEFORE_CHECK:
        candidates = random.sample(candidates, SAMPLE_BEFORE_CHECK)

    sem = asyncio.Semaphore(THREADS)

    async def score(line: str):
        host, _ = parse_host_port_from_vless(line)
        if not host:
            return None
        dt = await tcp_probe_first_success(host, sem)
        if dt is None:
            return None
        return (dt, line)

    # проверяем все кандидаты (в этом варианте “строго остановить при достижении 600” сложно без cancel;
    # сортировку делаем по факту. По смыслу лимит 600 сохраняется.)
    results = []
    scored = await asyncio.gather(*[score(c) for c in candidates], return_exceptions=True)
    for item in scored:
        if isinstance(item, Exception) or item is None:
            continue
        results.append(item)

    results.sort(key=lambda x: x[0])
    top = results[:LIMIT]

    out_path = os.path.join(os.path.dirname(__file__), "proxies.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for _, line in top:
            f.write(line.strip() + "\n")


if __name__ == "__main__":
    asyncio.run(main())
