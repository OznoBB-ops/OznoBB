import requests
import socket
from pathlib import Path

SOURCES = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt",
    "https://gitlab.com/zieng2/wl/raw/main/vless_universal.txt",
    "https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
]

BLACKLIST = [
    "insecure",
    "allowinsecure",
    "security=none",
    "security=NONE",
    "insecure=true",
    "tls=false"
]

def fetch(url):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return []
        return [x.strip() for x in r.text.splitlines() if x.strip()]
    except:
        return []

def is_vless(x):
    return x.startswith("vless://") and "@" in x

def is_clean(x):
    x_low = x.lower()
    return not any(b in x_low for b in BLACKLIST)

def extract_host(x):
    try:
        h = x.split("@")[1].split("?")[0]
        return h.split(":")[0]
    except:
        return None

def tcp_check(host):
    try:
        socket.create_connection((host, 443), timeout=0.6).close()
        return True
    except:
        return False

def main():
    all_data = []

    for url in SOURCES:
        all_data.extend(fetch(url))

    data = [x for x in all_data if is_vless(x)]
    data = [x for x in data if is_clean(x)]

    unique = list(dict.fromkeys(data))

    alive = []
    for x in unique:
        host = extract_host(x)
        if host and tcp_check(host):
            alive.append(x)

    reality = [x for x in alive if "security=reality" in x]
    tls = [x for x in alive if "security=reality" not in x]

    result = reality + tls

    Path("subscription.txt").write_text("\n".join(result))

    print(f"OK: {len(result)} live nodes")

if __name__ == "__main__":
    main()
