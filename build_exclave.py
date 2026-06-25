import requests
import re
import time
import socket
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# НАСТРОЙКИ
# ============================================
SUBSCRIPTIONS = [
    # Твои родные
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    
    # FastNodes
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/everything.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/protocols/vless.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/RU.txt",
    
    # Nexus Nodes
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/all.txt",
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/light.txt",
]

OUTPUT_FILE = "proxies.txt"
REPORT_FILE = "report.txt"
MAX_PROXIES = 600
TIMEOUT = 3
MAX_WORKERS = 15
MAX_PING_MS = 300
LIMIT_BEFORE_CHECK = 2000

# ============================================
# ФУНКЦИИ
# ============================================

def is_reality(proxy_link):
    return proxy_link.startswith('vless://') and 'security=reality' in proxy_link

def fetch_subscriptions(urls):
    raw_proxies = []
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
                        raw_proxies.append(line)
            
            print(f"   ✅ Добавлено: {len([l for l in lines if l and not l.startswith('#')])} прокси")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    unique_proxies = list(set(raw_proxies))
    print(f"\n📊 Удалено дублей: {len(raw_proxies) - len(unique_proxies)}")
    print(f"📊 Уникальных прокси: {len(unique_proxies)}")
    
    return unique_proxies

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

def ping_target(host):
    try:
        start = time.time()
        socket.gethostbyname(host)
        return (time.time() - start) * 1000
    except:
        return None

def check_proxy(proxy_link):
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    if not is_reality(proxy_link):
        return None
    
    host = extract_host(proxy_link)
    if not host:
        return None
    
    # 1. Пинг до Google (глобальный, стабильный)
    ping_google = ping_target("google.com")
    if ping_google is None or ping_google > MAX_PING_MS:
        return None
    
    # 2. Пинг до Твери (локальный)
    ping_tver = ping_target("tver.ru")
    if ping_tver is None or ping_tver > MAX_PING_MS:
        return None
    
    # 3. TCP-проверка
    ports = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]
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
                    avg_ping = (ping_google + ping_tver) / 2
                    return proxy_link, avg_ping
        except:
            pass
    
    return None

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 СБОРКА REALITY-ПРОКСИ (Google + Тверь)")
    print("=" * 50)
    
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    
    reality_proxies = [p for p in all_proxies if is_reality(p)]
    print(f"\n📊 Найдено VLESS: {len(all_proxies)}")
    print(f"📊 Из них REALITY: {len(reality_proxies)}")
    
    if len(reality_proxies) == 0:
        print("❌ Нет REALITY-прокси!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет REALITY-прокси\n")
        return
    
    if len(reality_proxies) > LIMIT_BEFORE_CHECK:
        reality_proxies = random.sample(reality_proxies, LIMIT_BEFORE_CHECK)
        print(f"📊 Для проверки взято: {LIMIT_BEFORE_CHECK} (случайных)")
    else:
        print(f"📊 Для проверки взято: {len(reality_proxies)} (все)")
    
    print(f"\n⏳ Проверка целевых хостов...")
    ping_google = ping_target("google.com")
    ping_tver = ping_target("tver.ru")
    print(f"   📍 Google: {ping_google:.0f} мс" if ping_google else "   ❌ Google недоступен")
    print(f"   📍 Тверь: {ping_tver:.0f} мс" if ping_tver else "   ❌ Тверь недоступна")
    
    print(f"\n⏳ Шаг 2: Проверка REALITY-прокси ({MAX_WORKERS} потоков)...")
    working_proxies = []
    checked = 0
    total = len(reality_proxies)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_proxy, proxy): proxy for proxy in reality_proxies}
        
        for future in as_completed(futures):
            checked += 1
            try:
                result = future.result(timeout=10)
                if result:
                    proxy, avg_ping = result
                    working_proxies.append((proxy, avg_ping))
                    print(f"   ✅ {proxy[:50]}... {avg_ping:.0f} мс (ср.)")
            except:
                pass
            
            if checked % 25 == 0:
                print(f"   ⏳ Проверено {checked}/{total}...")
    
    working_proxies.sort(key=lambda x: x[1])
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих REALITY-прокси: {len(working_proxies)}")
    
    with open(OUTPUT_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих REALITY-прокси\n")
    
    with open(REPORT_FILE, 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до Google: {ping_google:.0f} мс\n" if ping_google else "Пинг до Google: недоступен\n")
        f.write(f"Пинг до Твери: {ping_tver:.0f} мс\n" if ping_tver else "Пинг до Твери: недоступен\n")
        f.write(f"Всего REALITY прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
            f.write(f"Минимальный: {min(p for _, p in working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, avg_ping in working_proxies[:10]:
            f.write(f"  {avg_ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список REALITY-прокси сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
