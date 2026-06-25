import requests
import sys

SOURCES = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "proxies.txt"
TIMEOUT = 10

def fetch_and_merge():
    """Загружает и дедуплицирует прокси из всех источников"""
    all_proxies = set()
    
    print("=== Объединение подписок ===\n")
    
    for source in SOURCES:
        try:
            print(f"Загружаю: {source}")
            response = requests.get(source, timeout=TIMEOUT)
            response.raise_for_status()
            
            proxies = response.text.strip().split('\n')
            proxies = [p.strip() for p in proxies if p.strip()]
            all_proxies.update(proxies)
            print(f"✓ Загружено {len(proxies)} конфигов\n")
        except Exception as e:
            print(f"✗ Ошибка при загрузке {source}: {e}\n")
    
    # Сохраняем дедуплицированные прокси
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for proxy in sorted(all_proxies):
            f.write(proxy + '\n')
    
    print(f"✓ Всего уникальных конфигов: {len(all_proxies)}")
    print(f"✓ Файл {OUTPUT_FILE} создан")

if __name__ == "__main__":
    fetch_and_merge()

