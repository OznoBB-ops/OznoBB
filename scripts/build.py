#!/usr/bin/env python3
import subprocess, re, urllib.request, time, concurrent.futures

SOURCES = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUT = "subscription.txt"
PING_TIMEOUT = 3

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"fetch fail {url}: {e}")
        return ""

URI_RE = re.compile(r"^[a-z]+://[^@]*@([^:/#\s]+):(\d+)", re.I)

def parse_target(line):
    m = URI_RE.match(line.strip())
    return (m.group(1), int(m.group(2))) if m else None

def measure_ping(host, port):
    try:
        t0 = time.time()
        cmd = f"echo | timeout {PING_TIMEOUT}s openssl s_client -connect {host}:{port} -servername {host} 2>/dev/null"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ms = int((time.time() - t0) * 1000)
        if r.returncode != 0 or ms > PING_TIMEOUT * 1000:
            return None
        return ms
    except Exception:
        return None

def rename(line, ping_ms):
    line = line.strip()
    if not line or line.startswith("#"):
        return line
    base = re.sub(r"#.*$", "", line)
    tag = "🇷🇺RU"
    if ping_ms is not None:
        tag += f"_{ping_ms}ms"
    else:
        tag += "_⚠"
    return f"{base}#{tag}"

def main():
    all_lines = []
    for url in SOURCES:
        all_lines.extend(fetch(url).splitlines())

    seen = set()
    unique = []
    for l in all_lines:
        s = l.strip()
        if not s or s in seen: continue
        seen.add(s)
        unique.append(s)

    def job(line):
        t = parse_target(line)
        if not t: return line, None
        return line, measure_ping(*t)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
        futs = {ex.submit(job, l): l for l in unique}
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())

    results.sort(key=lambda x: (1, 99999, x[0]) if x[1] is None else (0, x[1], x[0]))

    with open(OUT, "w", encoding="utf-8") as f:
        for line, ms in results:
            f.write(rename(line, ms) + "\n")
    print(f"done: {len(results)} lines -> {OUT}")

if __name__ == "__main__":
    main()
