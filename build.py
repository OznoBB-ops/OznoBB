import requests
import re
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# НАСТРОЙКИ
# ============================================
SUBSCRIPTIONS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "exclave_list.txt"
MAX_PROXIES = 600
TIMEOUT = 3
MAX_WORKERS = 10
PING_TARGET = "tver.ru"          # <-- Цель для пинга
MAX_PING_MS = 300                # <-- Максимальный пинг до tver.ru

# ============================================
# ФУНКЦИИ
# ============================================

def extract_host(proxy_link):
    try:
        match = re.search(r'@([^:]+):(\d+)', proxy_link)
        if match:
            return match.group(1)
        match = re.search(r'://([^:/]+)(?::\d+)?', proxy_link)
        if match:
            return match.group(1)
    except:
        pass
    return None

def check_proxy(proxy_link):
    """Проверяет прокси: пинг до tver.ru + TCP-коннект."""
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    host = extract_host(proxy_link)
    if not host:
        return None
    
    # 1. Пинг до tver.ru
    try:
        start_ping = time.time()
        socket.gethostbyname(PING_TARGET)
        ping_to_tver = (time.time() - start_ping) * 1000
        if ping_to_tver > MAX_PING_MS:
            return None  # Слишком высокий пинг до Твери
    except:
        pass  # Если tver.ru не отвечает, пропускаем проверку
    
    # 2. TCP-проверка прокси
    ports = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401]
    for port in ports:
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                ping = (time.time() - start) * 1000
                if ping < 1000:
                    return proxy_link, ping
        except:
            pass
    
    return None

def fetch_subscriptions(urls):
    all_proxies = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    for url in urls:
        try:
            print(f"📥 Загрузка: {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if re.match(r'^(ss|vless|vmess|trojan|hysteria2|socks5|http)://', line):
                        all_proxies.append(line)
            
            print(f"   ✅ Найдено {len([l for l in lines if l and not l.startswith('#')])} прокси")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(set(all_proxies))

def main():
    print("=" * 50)
    print("🚀 СБОРКА СПИСКА ДЛЯ EXCLAVE (ТВЕРЬ)")
    print("=" * 50)
    
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет доступных прокси\n")
        return
    
    # Проверяем пинг до tver.ru
    print(f"\n⏳ Пинг до {PING_TARGET}...")
    try:
        start = time.time()
        socket.gethostbyname(PING_TARGET)
        ping = (time.time() - start) * 1000
        print(f"   ✅ Пинг до {PING_TARGET}: {ping:.0f} мс")
    except:
        print(f"   ⚠️ Не удалось пропинговать {PING_TARGET}, продолжаем...")
    
    print(f"\n⏳ Шаг 2: Проверка прокси ({MAX_WORKERS} потоков)...")
    working_proxies = []
    checked = 0
    total = len(all_proxies)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_proxy, proxy): proxy for proxy in all_proxies}
        
        for future in as_completed(futures):
            checked += 1
            try:
                result = future.result(timeout=10)
                if result:
                    proxy, ping = result
                    working_proxies.append((proxy, ping))
                    print(f"   ✅ {proxy[:50]}... {ping:.0f} мс")
            except:
                pass
            
            if checked % 20 == 0:
                print(f"   ⏳ Проверено {checked}/{total}...")
    
    working_proxies.sort(key=lambda x: x[1])
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих прокси: {len(working_proxies)}")
    
    with open(OUTPUT_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих прокси\n")
    
    with open("report.txt", 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до {PING_TARGET}: {ping:.0f} мс\n")
        f.write(f"Всего прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, ping in working_proxies[:10]:
            f.write(f"  {ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
