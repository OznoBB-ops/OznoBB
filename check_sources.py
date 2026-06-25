import requests
import sys
from datetime import datetime

SOURCES = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "proxies.txt"
TIMEOUT = 10

def check_sources():
    """Проверяет доступность источников"""
    print(f"[{datetime.now().isoformat()}] Checking source availability...\n")
    
    available = 0
    unavailable = 0
    
    for source in SOURCES:
        try:
            response = requests.head(source, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            print(f"✓ {source}")
            available += 1
        except requests.exceptions.Timeout:
            print(f"✗ {source} (timeout)")
            unavailable += 1
        except requests.exceptions.ConnectionError:
            print(f"✗ {source} (connection error)")
            unavailable += 1
        except Exception as e:
            print(f"✗ {source} ({e})")
            unavailable += 1
    
    print(f"\nResults: {available} available, {unavailable} unavailable\n")
    
    if unavailable > 0:
        print(f"⚠ Warning: {unavailable} sources are not accessible!\n")

def fetch_and_merge():
    """Загружает и дедуплицирует прокси из всех источников"""
    print(f"[{datetime.now().isoformat()}] Merging proxies...\n")
    
    all_proxies = set()
    total_loaded = 0
    
    for source in SOURCES:
        try:
            response = requests.get(source, timeout=TIMEOUT)
            response.raise_for_status()
            proxies = response.text.strip().split('\n')
            proxies = [p.strip() for p in proxies if p.strip()]
            all_proxies.update(proxies)
            total_loaded += len(proxies)
            print(f"✓ Loaded from {source}: {len(proxies)} proxies")
        except Exception as e:
            print(f"✗ Failed to load {source}: {e}")
    
    # Сохраняем дедуплицированные прокси
    with open(OUTPUT_FILE, 'w') as f:
        for proxy in sorted(all_proxies):
            f.write(proxy + '\n')
    
    print(f"\n✓ Total loaded: {total_loaded} proxies")
    print(f"✓ Unique proxies: {len(all_proxies)}")
    print(f"✓ Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    check_sources()
    fetch_and_merge()
