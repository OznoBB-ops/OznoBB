import requests
import os

# ============================================
# ТВОИ ИСТОЧНИКИ
# ============================================
URLS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "proxies.txt"

# ============================================
# ФУНКЦИИ
# ============================================

def fetch_all(urls):
    """Скачивает все подписки и объединяет в один список."""
    all_lines = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    for url in urls:
        try:
            print(f"📥 Загрузка: {url}")
            r = session.get(url, timeout=30)
            r.raise_for_status()
            
            lines = r.text.splitlines()
            added = 0
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    all_lines.append(line)
                    added += 1
            print(f"   ✅ Добавлено: {added}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print(f"\n📊 Всего строк: {len(all_lines)}")
    return all_lines

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 ОБЪЕДИНЕНИЕ ВСЕХ ПОДПИСОК")
    print("=" * 50)
    
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_lines = fetch_all(URLS)
    
    if not all_lines:
        print("❌ Нет данных!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет данных\n")
        return
    
    # 2. Сохраняем всё без изменений
    print(f"\n💾 Сохраняем {len(all_lines)} строк в {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w') as f:
        for line in all_lines:
            f.write(line + "\n")
    
    print(f"\n✅ Готово! Все подписки объединены в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
