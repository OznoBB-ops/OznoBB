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

TIMEOUT = 10
LOG_FILE = "sources_check.log"

def check_sources():
    timestamp = datetime.now().isoformat()
    log_lines = [f"[{timestamp}] Checking source availability...\n"]
    
    available = 0
    unavailable = 0
    
    for source in SOURCES:
        try:
            response = requests.head(source, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            status = f"✓ {source} (OK)"
            log_lines.append(status)
            print(status)
            available += 1
        except requests.exceptions.Timeout:
            status = f"✗ {source} (TIMEOUT)"
            log_lines.append(status)
            print(status)
            unavailable += 1
        except requests.exceptions.ConnectionError:
            status = f"✗ {source} (CONNECTION ERROR)"
            log_lines.append(status)
            print(status)
            unavailable += 1
        except Exception as e:
            status = f"✗ {source} ({str(e)})"
            log_lines.append(status)
            print(status)
            unavailable += 1
    
    summary = f"\nResults: {available} available, {unavailable} unavailable\n"
    log_lines.append(summary)
    print(summary)
    
    # Сохраняем в лог-файл
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write('\n'.join(log_lines) + '\n')
    
    print(f"✓ Log saved to {LOG_FILE}")
    
    return unavailable == 0

if __name__ == "__main__":
    success = check_sources()
    sys.exit(0 if success else 1)

