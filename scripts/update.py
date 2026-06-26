import requests
import re
from datetime import datetime
from pathlib import Path

SOURCES = [
    # zieng2
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt",
    "https://gitlab.com/zieng2/wl/raw/main/vless_universal.txt",
    "https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt",

    # igareck
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
]

BLACKLIST = ["insecure=1", "allowInsecure=1", "security=none"]

def fetch(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return [x.strip() for x in r.text.splitlines() if x.strip()]
    except:
        return []

def is_vless(x):
    return x.startswith("vless://")

def is_clean(x):
    return not any(b in x for b in BLACKLIST)

def main():
    all_data = []

    for url in SOURCES:
        all_data.extend(fetch(url))

    # VLESS only
    data = [x for x in all_data if is_vless(x)]
    # security filter
    data = [x for x in data if is_clean(x)]

    # deduplicate
    seen = set()
    unique = []
    for x in data:
        if x not in seen:
            seen.add(x)
            unique.append(x)

    # Reality first
    reality = [x for x in unique if "security=reality" in x]
    tls = [x for x in unique if "security=reality" not in x]

    final_list = reality + tls

    Path("subscription.txt").write_text("\n".join(final_list))

    print(f"OK: {len(final_list)} nodes saved")

if __name__ == "__main__":
    main()
