import requests
import re
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# НАСТРОЙКИ — ВСЕ ИСТОЧНИКИ
# ============================================
SUBSCRIPTIONS = [
    # ===== ТВОИ РОДНЫЕ ПОДПИСКИ =====
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    
    # ===== НОВЫЕ ИСТОЧНИКИ =====
    # FastNodes — лучший агрегатор
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/everything.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/protocols/vless.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/RU.txt",
    
    # Nexus Nodes — тестирует задержку
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/all.txt",
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/light.txt",
    
    # Hidashimora — проверенные короткие списки
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/1.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/2.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/3.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/4.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/5.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/6.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/7.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/8.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/9.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/10.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/11.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/12.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/13.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/14.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/15.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/16.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/17.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/18.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/19.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/20.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/21.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/22.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/23.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/24.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/25.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/26.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/27.1.txt",
    "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/28.1.txt",
]

OUTPUT_FILE = "proxies.txt"
REPORT_FILE = "report.txt"
MAX_PROXIES = 600
TIMEOUT = 3
MAX_WORKERS = 15
PING_TARGET = "tver.ru"
MAX_PING_MS = 400

# ============================================
# ЗАГРУЗКА ПОДПИСОК И УДАЛЕНИЕ ДУБЛЕЙ
# ============================================

def fetch_subscriptions(urls):
    """Скачивает все подписки и возвращает список УНИКАЛЬНЫХ прокси."""
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
    
    # УДАЛЯЕМ ДУБЛИКИ
    unique_proxies = list(set(raw_proxies))
    print(f"\n📊 Удалено дублей: {len(raw_proxies) - len(unique_proxies)}")
    print(f"📊 Уникальных прокси: {len(unique_proxies)}")
    
    return unique_proxies

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

def check_proxy(proxy_link):
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    host = extract_host(proxy_link)
    if not host:
        return None
    
    # Пинг до Tver.ru
    try:
        start_ping = time.time()
        socket.gethostbyname(PING_TARGET)
        ping_to_tver = (time.time() - start_ping) * 1000
        if ping_to_tver > MAX_PING_MS:
            return None
    except:
        pass
    
    # TCP-проверка
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
                    return proxy_link, ping
        except:
            pass
    
    return None

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 СБОРКА СПИСКА ПРОКСИ")
    print("=" * 50)
    
    print("\n📦 Шаг 1: Загрузка подписок и удаление дублей...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет прокси\n")
        return
    
    # Пинг до Tver.ru (для отчёта)
    print(f"\n⏳ Пинг до {PING_TARGET}...")
    try:
        start = time.time()
        socket.gethostbyname(PING_TARGET)
        ping = (time.time() - start) * 1000
        print(f"   ✅ Пинг до {PING_TARGET}: {ping:.0f} мс")
    except:
        print(f"   ⚠️ Не удалось пропинговать {PING_TARGET}")
        ping = 0
    
    # Проверка прокси
    print(f"\n⏳ Шаг 2: Проверка ({MAX_WORKERS} потоков)...")
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
                    proxy, proxy_ping = result
                    working_proxies.append((proxy, proxy_ping))
                    print(f"   ✅ {proxy[:50]}... {proxy_ping:.0f} мс")
            except:
                pass
            
            if checked % 25 == 0:
                print(f"   ⏳ Проверено {checked}/{total}...")
    
    # Сортируем по пингу и оставляем лучшие
    working_proxies.sort(key=lambda x: x[1])
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих прокси: {len(working_proxies)}")
    
    # Сохраняем результат
    with open(OUTPUT_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих прокси\n")
    
    # Отчёт
    with open(REPORT_FILE, 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до {PING_TARGET}: {ping:.0f} мс\n")
        f.write(f"Всего прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
            f.write(f"Минимальный: {min(p for _, p in working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, proxy_ping in working_proxies[:10]:
            f.write(f"  {proxy_ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
