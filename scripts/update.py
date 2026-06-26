import requests
import socket
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SOURCES = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
]

BLACKLIST = [
    "insecure",
    "allowinsecure",
    "security=none",
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
        return x.split("@")[1].split("?")[0].split(":")[0]
    except:
        return None

def extract_uuid(x):
    try:
        return x.split("vless://")[1].split("@")[0]
    except:
        return None

def check_node(x):
    host = extract_host(x)
    if not host:
        return None

    try:
        socket.gethostbyname(host)

        start = time.time()
        socket.create_connection((host, 443), timeout=0.8).close()
        latency = time.time() - start

        return (x, latency)
    except:
        return None

def generate_clash(nodes):
    proxies = []

    for i, x in enumerate(nodes):
        proxies.append({
            "name": f"NODE-{i}",
            "type": "vless",
            "server": extract_host(x),
            "port": 443,
            "uuid": extract_uuid(x),
            "tls": True
        })

    data = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "AUTO",
                "type": "select",
                "proxies": [p["name"] for p in proxies]
            }
        ]
    }

    Path("clash.yaml").write_text(json.dumps(data, indent=2))

def generate_singbox(nodes):
    outbounds = []

    for i, x in enumerate(nodes):
        outbounds.append({
            "type": "vless",
            "tag": f"node-{i}",
            "server": extract_host(x),
            "server_port": 443,
            "uuid": extract_uuid(x),
            "tls": {
                "enabled": True
            }
        })

    data = {
        "outbounds": outbounds,
        "route": {
            "final": "node-0" if outbounds else "direct"
        }
    }

    Path("singbox.json").write_text(json.dumps(data, indent=2))

def main():
    all_data = []

    for url in SOURCES:
        all_data.extend(fetch(url))

    data = [x for x in all_data if is_vless(x)]
    data = [x for x in data if is_clean(x)]

    unique = list(dict.fromkeys(data))

    results = []

    with ThreadPoolExecutor(max_workers=60) as ex:
        futures = [ex.submit(check_node, x) for x in unique]

        for f in as_completed(futures):
            r = f.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: x[1])

    alive = [x[0] for x in results]

    reality = [x for x in alive if "reality" in x.lower()]
    tls = [x for x in alive if "reality" not in x.lower()]
    final_list = reality + tls

    Path("subscription.txt").write_text("\n".join(final_list))

    generate_clash(final_list)
    generate_singbox(final_list)

    print(f"OK: {len(final_list)} nodes | best: {results[0][1] if results else 'N/A'}")

if __name__ == "__main__":
    main()
