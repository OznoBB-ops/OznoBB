import requests
import re
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# ТВОИ ИСТОЧНИКИ (только твои)
# ============================================
SUBSCRIPTIONS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

# ============================================
# УСЛОВИЯ
# ============================================
OUTPUT_FILE = "proxies.txt"
TCP_TIMEOUT = 3
MAX_WORKERS = 15
PORTS = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]

# ============================================
# ФУНКЦИИ
# ============================================

def is_reality(proxy_link):
    """Только VLESS + REALITY."""
    return proxy_link.startswith('vless://') and 'security=reality' in proxy_link

def fetch_subscriptions(urls):
    """Скачивает все подписки, возвращает список уникальных прокси."""
    raw = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    for url in urls:
        try:
            print(f"📥 Загрузка: {url}")
            r = session.get(url, timeout=30)
            r.raise_for_status()
            for line in r.text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if re.match(r'^(ss|vless|vmess|trojan|hysteria2|socks5|http)://', line):
                        raw.append(line)
            print(f"   ✅ Добавлено")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    # Убираем дубли
    unique = list(set(raw))
    print(f"\n📊 Уникальных прокси: {len(unique)} (дублей удалено: {len(raw) - len(unique)})")
    return unique

def extract_host_port(proxy_link):
    """Извлекает host и port из VLESS-ссылки."""
    try:
        match = re.search(r'@([^:]+):(\d+)', proxy_link)
        if match:
            return match.group(1), int(match.group(2))
        match = re.search(r'://([^:/]+):(\d+)', proxy_link)
        if match:
            return match.group(1), int(match.group(2))
    except:
        pass
    return None, None

def check_proxy(proxy_link):
    """Проверяет прокси через TCP-коннект."""
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    if not is_reality(proxy_link):
        return None
    
    host, port = extract_host_port(proxy_link)
    if not host or not port:
        return None
    
    best_ping = None
    for p in PORTS:
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT)
            result = sock.connect_ex((host, p))
            sock.close()
            
            if result == 0:
                ping = (time.time() - start) * 1000
                if ping < 1000:
                    if best_ping is None or ping < best_ping:
                        best_ping = ping
        except:
            pass
    
    if best_ping is not None:
        return proxy_link, best_ping
    return None

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 СБОРКА REALITY-ПРОКСИ (БЕЗ ЛИМИТА)")
    print("=" * 50)
    
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    
    reality = [p for p in all_proxies if is_reality(p)]
    print(f"📊 Из них REALITY: {len(reality)}")
    
    if not reality:
        print("❌ Нет REALITY-прокси!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет REALITY-прокси\n")
        return
    
    print(f"\n⏳ Шаг 2: Проверка REALITY-прокси ({MAX_WORKERS} потоков)...")
    working = []
    checked = 0
    total = len(reality)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_proxy, p): p for p in reality}
        
        for future in as_completed(futures):
            checked += 1
            try:
                result = future.result(timeout=10)
                if result:
                    proxy, ping = result
                    working.append((proxy, ping))
                    print(f"   ✅ {proxy[:50]}... {ping:.0f} мс ({len(working)} найдено)")
            except:
                pass
            
            if checked % 25 == 0:
                print(f"   ⏳ Проверено {checked}/{total}... ({len(working)} найдено)")
    
    # Сортируем по пингу (от лучшего к худшему)
    working.sort(key=lambda x: x[1])
    
    print(f"\n🎯 Рабочих REALITY-прокси: {len(working)}")
    
    with open(OUTPUT_FILE, 'w') as f:
        if working:
            for proxy, ping in working:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих REALITY-прокси\n")
    
    print(f"\n✅ Готово! Список REALITY-прокси сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
