import requests
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
    "insecure=1",
    "insecure=true",
    "allowinsecure",
    "security=none",
    "security=NONE"
]

def fetch(url):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return []
        return [i.strip() for i in r.text.splitlines() if i.strip()]
    except:
        return []

def is_valid_vless(x):
    if not x.startswith("vless://"):
        return False
    if "@" not in x:
        return False
    return True

def is_clean(x):
    x_low = x.lower()
    return not any(b in x_low for b in BLACKLIST)

def main():
    all_data = []

    for url in SOURCES:
        all_data.extend(fetch(url))

    data = [x for x in all_data if is_valid_vless(x)]
    data = [x for x in data if is_clean(x)]

    seen = set()
    unique = []
    for x in data:
        if x not in seen:
            seen.add(x)
            unique.append(x)

    reality = [x for x in unique if "security=reality" in x]
    tls = [x for x in unique if "security=reality" not in x]

    result = reality + tls

    Path("subscription.txt").write_text("\n".join(result))

    print(f"OK: {len(result)} nodes")

if __name__ == "__main__":
    main()
