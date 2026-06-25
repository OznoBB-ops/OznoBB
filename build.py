import requests
import re
import time
import socket
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# НАСТРОЙКИ — ТОЛЬКО REALITY
# ============================================
SUBSCRIPTIONS = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "proxies.txt"
MAX_PROXIES = 300                # Для REALITY оставляем 300 лучших
TIMEOUT = 3
MAX_WORKERS = 10
PING_TARGET = "tver.ru"
MAX_PING_MS = 300

# ============================================
# ПРОВЕРКА ПРОКСИ
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

def is_reality(proxy_link):
    """Проверяет, что это VLESS с REALITY."""
    return proxy_link.startswith('vless://') and 'security=reality' in proxy_link

def check_proxy(proxy_link):
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    # Пропускаем только REALITY
    if not is_reality(proxy_link):
        return None
    
    host = extract_host(proxy_link)
    if not host:
        return None
    
    # Пинг до tver.ru
    try:
        start_ping = time.time()
        socket.gethostbyname(PING_TARGET)
        ping_to_tver = (time.time() - start_ping) * 1000
        if ping_to_tver > MAX_PING_MS:
            return None
    except:
        pass
    
    # TCP-проверка
    ports = [443, 80, 8080, 8443, 8880, 2096]
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
                    if line.startswith('vless://'):
                        all_proxies.append(line)
            
            print(f"   ✅ Найдено VLESS: {len([l for l in lines if l.startswith('vless://')])}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(set(all_proxies))

def main():
    print("=" * 50)
    print("🚀 СБОРКА REALITY-ПРОКСИ ДЛЯ RUSSIA")
    print("=" * 50)
    
    print("\n📦 Шаг 1: Загрузка подписок (только VLESS)...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    
    # Сразу фильтруем REALITY
    reality_proxies = [p for p in all_proxies if is_reality(p)]
    print(f"\n📊 Найдено VLESS: {len(all_proxies)}")
    print(f"📊 Из них REALITY: {len(reality_proxies)}")
    
    if len(reality_proxies) == 0:
        print("❌ Нет REALITY-прокси для проверки!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет REALITY-прокси\n")
        return
    
    print(f"\n⏳ Пинг до {PING_TARGET}...")
    try:
        start = time.time()
        socket.gethostbyname(PING_TARGET)
        ping = (time.time() - start) * 1000
        print(f"   ✅ Пинг до {PING_TARGET}: {ping:.0f} мс")
    except:
        print(f"   ⚠️ Не удалось пропинговать {PING_TARGET}")
        ping = 0
    
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
                    proxy, proxy_ping = result
                    working_proxies.append((proxy, proxy_ping))
                    print(f"   ✅ {proxy[:50]}... {proxy_ping:.0f} мс")
            except:
                pass
            
            if checked % 10 == 0:
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
    
    # Сохраняем отчёт
    with open("report.txt", 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до {PING_TARGET}: {ping:.0f} мс\n")
        f.write(f"Всего REALITY прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, proxy_ping in working_proxies[:10]:
            f.write(f"  {proxy_ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список REALITY-прокси сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
