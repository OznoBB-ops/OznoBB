import requests
import re
import time
import socket
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# ============================================
# НАСТРОЙКИ (БЕЗ СЕРТИФИКАТОВ)
# ============================================
SUBSCRIPTIONS = [
    "https://raw.githubusercontent.com/zieng2/wl/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

OUTPUT_FILE = "exclave_list.txt"
MAX_PROXIES = 600
TCP_TIMEOUT = 3          # таймаут TCP-чека
MAX_PING_MS = 500        # максимальный пинг
MAX_WORKERS = 15         # потоков

# ============================================
# ФУНКЦИИ (ТОЛЬКО TCP + HTTP)
# ============================================

def extract_host_port(proxy_link):
    """Извлекает хост и порт из любой прокси-ссылки (без SSL)."""
    try:
        # Для SS нужна особая обработка
        if proxy_link.startswith('ss://'):
            without_proto = proxy_link.replace('ss://', '')
            if '@' in without_proto:
                _, addr = without_proto.split('@', 1)
                if ':' in addr:
                    host = addr.split(':')[0]
                    port_str = addr.split(':')[1].split('?')[0].split('#')[0]
                    return host, int(port_str)
            else:
                try:
                    decoded = base64.b64decode(without_proto + '==').decode()
                    if '@' in decoded:
                        _, addr = decoded.split('@', 1)
                        if ':' in addr:
                            host = addr.split(':')[0]
                            port_str = addr.split(':')[1].split('?')[0].split('#')[0]
                            return host, int(port_str)
                except:
                    pass
            return None, None
        
        # Для остальных протоколов
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port
        
        if not host:
            match = re.search(r'@([^:]+):(\d+)', proxy_link)
            if match:
                host = match.group(1)
                port = int(match.group(2))
        
        return host, port
    except:
        return None, None

def tcp_http_check(proxy_link):
    """Проверяет прокси через TCP + простой HTTP-запрос (без SSL)."""
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    # 1. Извлекаем хост и порт
    host, port = extract_host_port(proxy_link)
    if not host or not port:
        return None
    
    # 2. TCP-проверка
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return None  # Порт закрыт
        
        tcp_ping = (time.time() - start) * 1000
    except:
        return None
    
    # 3. Простой HTTP-запрос (только для протоколов, поддерживающих HTTP)
    # Пропускаем эту проверку для VLESS/Trojan, т.к. они требуют TLS
    if proxy_link.startswith(('vless://', 'trojan://', 'hysteria2://')):
        # Для этих протоколов достаточно TCP-чека
        if tcp_ping < MAX_PING_MS:
            return proxy_link, tcp_ping
        return None
    
    # Для SS и других пробуем HTTP
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT + 2)
        sock.connect((host, port))
        
        # Отправляем простой HTTP-запрос (без SSL)
        request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
        sock.send(request.encode())
        response = sock.recv(1024)
        sock.close()
        
        if b"204" in response or b"HTTP/1.1" in response:
            http_ping = (time.time() - start) * 1000
            if http_ping < MAX_PING_MS:
                return proxy_link, http_ping
    except:
        # Если HTTP не работает, но TCP прошел - считаем рабочим
        if tcp_ping < MAX_PING_MS:
            return proxy_link, tcp_ping
    
    return None

# ============================================
# ЗАГРУЗКА ПОДПИСОК
# ============================================

def fetch_subscriptions(urls):
    all_proxies = set()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    for url in urls:
        try:
            print(f"📥 Загрузка: {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            proxies = re.findall(
                r'^(?:ss|vless|vmess|trojan|hysteria2|socks5|http)://[^\s#]+$',
                response.text,
                re.MULTILINE
            )
            all_proxies.update(proxies)
            print(f"   ✅ Найдено {len(proxies)} прокси")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(all_proxies)

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 СБОРКА СПИСКА ДЛЯ EXCLAVE (TCP)")
    print("=" * 50)
    
    # 1. Загружаем подписки
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет доступных прокси\n")
        return
    
    # 2. Проверяем прокси
    print(f"\n⏳ Шаг 2: Проверка прокси ({MAX_WORKERS} потоков)...")
    working_proxies = []
    checked = 0
    total = len(all_proxies)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(tcp_http_check, proxy): proxy for proxy in all_proxies}
        
        for future in as_completed(futures):
            checked += 1
            try:
                result = future.result()
                if result:
                    proxy, ping = result
                    working_proxies.append((proxy, ping))
                    print(f"   ✅ {proxy[:50]}... {ping:.0f} мс")
            except:
                pass
            
            if checked % 50 == 0:
                print(f"   ⏳ Проверено {checked}/{total}...")
    
    # 3. Сортируем по пингу
    working_proxies.sort(key=lambda x: x[1])
    
    # 4. Оставляем только лучшие
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих прокси: {len(working_proxies)}")
    
    # 5. Сохраняем результат
    with open(OUTPUT_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих прокси\n")
    
    # 6. Сохраняем отчёт
    with open("report.txt", 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Всего прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
            f.write(f"Минимальный: {min(p for _, p in working_proxies):.0f} мс\n")
            f.write(f"Максимальный: {max(p for _, p in working_proxies):.0f} мс\n")
        f.write("\nТоп-15:\n")
        for proxy, ping in working_proxies[:15]:
            f.write(f"  {ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
