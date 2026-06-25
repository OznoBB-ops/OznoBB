import requests
import re
import time
import socket
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# ============================================
# НАСТРОЙКИ (ДЛЯ ТВЕРИ)
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

# Таймауты (в секундах)
TCP_TIMEOUT = 3
PING_TIMEOUT = 5
REQUEST_TIMEOUT = 10

# Пороговые значения (в миллисекундах)
MAX_PING_MS = 300       # Максимальный пинг до tver.ru
MAX_PROXY_PING_MS = 500 # Максимальный пинг самого прокси

# Тестовые URL
PING_TARGET = "tver.ru"                      # Для измерения задержки (Тверь)
PROXY_TEST_URL = "http://cp.cloudflare.com/generate_204"  # Для проверки работы

MAX_WORKERS = 10

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def extract_host_port(proxy_link):
    """Извлекает хост и порт из любой прокси-ссылки."""
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

def measure_ping_to_tver():
    """Измеряет пинг до tver.ru через DNS-запрос."""
    try:
        start = time.time()
        socket.gethostbyname(PING_TARGET)
        return (time.time() - start) * 1000
    except:
        return None

def tcp_check(proxy_link):
    """Быстрая проверка: открыт ли порт."""
    try:
        host, port = extract_host_port(proxy_link)
        if not host or not port:
            return None
        
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            ping = (time.time() - start) * 1000
            return proxy_link, ping
    except:
        pass
    return None

def http_test_vless(proxy_link):
    """Проверяет VLESS через HTTP-запрос."""
    try:
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port or 443
        sni = parsed.hostname or host
        
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        start = time.time()
        with socket.create_connection((host, port), timeout=REQUEST_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=sni) as ssock:
                request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
                ssock.send(request.encode())
                response = ssock.recv(1024)
                if b"204" in response or b"HTTP/1.1 204" in response:
                    return (time.time() - start) * 1000
    except:
        pass
    return None

def http_test_ss(proxy_link):
    """Проверяет Shadowsocks через HTTP-запрос."""
    try:
        host, port = extract_host_port(proxy_link)
        if not host or not port:
            return None
        
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(REQUEST_TIMEOUT)
        sock.connect((host, port))
        request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
        sock.send(request.encode())
        response = sock.recv(1024)
        sock.close()
        if b"204" in response or b"HTTP/1.1 204" in response:
            return (time.time() - start) * 1000
        return (time.time() - start) * 1000
    except:
        pass
    return None

def http_test_trojan(proxy_link):
    """Проверяет Trojan через HTTP-запрос."""
    try:
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port or 443
        sni = parsed.hostname or host
        
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        start = time.time()
        with socket.create_connection((host, port), timeout=REQUEST_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=sni) as ssock:
                request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
                ssock.send(request.encode())
                response = ssock.recv(1024)
                if b"204" in response or b"HTTP/1.1 204" in response:
                    return (time.time() - start) * 1000
    except:
        pass
    return None

def http_test_hysteria2(proxy_link):
    """Проверяет Hysteria2 (упрощённо)."""
    try:
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port or 443
        
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(REQUEST_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return (time.time() - start) * 1000
    except:
        pass
    return None

def full_check(proxy_link):
    """Полная проверка: TCP + HTTP + пинг до tver.ru."""
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    # 1. Измеряем пинг до tver.ru (только один раз для всех)
    ping_to_tver = measure_ping_to_tver()
    if ping_to_tver and ping_to_tver > MAX_PING_MS:
        # Если пинг до Твери слишком высокий, пропускаем все проверки
        # (это актуально для GitHub Actions, где сервер может быть далеко)
        pass
    
    # 2. TCP-проверка
    host, port = extract_host_port(proxy_link)
    if not host or not port:
        return None
    
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return None
    except:
        return None
    
    # 3. HTTP-проверка (в зависимости от протокола)
    try:
        if proxy_link.startswith('vless://'):
            ping = http_test_vless(proxy_link)
        elif proxy_link.startswith('ss://'):
            ping = http_test_ss(proxy_link)
        elif proxy_link.startswith('trojan://'):
            ping = http_test_trojan(proxy_link)
        elif proxy_link.startswith('hysteria2://'):
            ping = http_test_hysteria2(proxy_link)
        else:
            # Для неизвестных протоколов - только TCP
            ping = (time.time() - start) * 1000
        
        if ping and ping < MAX_PROXY_PING_MS:
            return proxy_link, ping
    except:
        pass
    
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
    print("=" * 60)
    print("🚀 СБОРКА СПИСКА ДЛЯ EXCLAVE (ТВЕРЬ)")
    print("=" * 60)
    
    # 1. Загружаем подписки
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Нет доступных прокси\n")
        return
    
    # 2. Проверяем пинг до tver.ru
    print(f"\n⏳ Шаг 2: Пинг до {PING_TARGET}...")
    ping_to_tver = measure_ping_to_tver()
    if ping_to_tver:
        print(f"   ✅ Пинг до {PING_TARGET}: {ping_to_tver:.0f} мс")
    else:
        print(f"   ⚠️ Не удалось пропинговать {PING_TARGET}")
    
    # 3. Проверяем прокси
    print(f"\n⏳ Шаг 3: Проверка прокси ({MAX_WORKERS} потоков)...")
    working_proxies = []
    checked = 0
    total = len(all_proxies)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(full_check, proxy): proxy for proxy in all_proxies}
        
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
    
    # 4. Сортируем по пингу
    working_proxies.sort(key=lambda x: x[1])
    
    # 5. Оставляем только лучшие
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих прокси: {len(working_proxies)}")
    
    # 6. Сохраняем результат
    with open(OUTPUT_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих прокси\n")
    
    # 7. Сохраняем отчёт
    with open("report.txt", 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до {PING_TARGET}: {ping_to_tver:.0f} мс\n" if ping_to_tver else f"Пинг до {PING_TARGET}: недоступен\n")
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
    main()        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        start = time.time()
        with socket.create_connection((host, port), timeout=URL_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=sni) as ssock:
                # Отправляем простой HTTP-запрос
                request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
                ssock.send(request.encode())
                response = ssock.recv(1024)
                if b"204" in response or b"HTTP/1.1 204" in response:
                    return (time.time() - start) * 1000
    except:
        pass
    return None

def http_test_ss(proxy_link):
    """Проверяет Shadowsocks через HTTP-запрос."""
    try:
        # Извлекаем хост и порт
        host, port = extract_host_port(proxy_link)
        if not host or not port:
            return None
        
        # Для SS используем HTTP-прокси (если поддерживается)
        # Или просто проверяем через socket
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(URL_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # Попытка HTTP-запроса через обычный сокет
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(URL_TIMEOUT)
                sock.connect((host, port))
                request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
                sock.send(request.encode())
                response = sock.recv(1024)
                sock.close()
                if b"204" in response or b"HTTP/1.1 204" in response:
                    return (time.time() - start) * 1000
                # Если не получили 204, но порт открыт - считаем рабочим
                return (time.time() - start) * 1000
            except:
                return (time.time() - start) * 1000
    except:
        pass
    return None

def http_test_trojan(proxy_link):
    """Проверяет Trojan через HTTP-запрос."""
    try:
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port or 443
        sni = parsed.hostname or host
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        start = time.time()
        with socket.create_connection((host, port), timeout=URL_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=sni) as ssock:
                request = f"GET /generate_204 HTTP/1.1\r\nHost: cp.cloudflare.com\r\nConnection: close\r\n\r\n"
                ssock.send(request.encode())
                response = ssock.recv(1024)
                if b"204" in response or b"HTTP/1.1 204" in response:
                    return (time.time() - start) * 1000
    except:
        pass
    return None

def http_test_hysteria2(proxy_link):
    """Проверяет Hysteria2 через HTTP-запрос (упрощённо)."""
    try:
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port or 443
        
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(URL_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # Hysteria2 использует QUIC, но TCP-порт тоже должен быть открыт
            return (time.time() - start) * 1000
    except:
        pass
    return None

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ ПРОВЕРКИ
# ============================================

def check_proxy(proxy_link):
    """Полная проверка прокси: TCP + HTTP."""
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    # 1. Быстрая TCP-проверка
    host, port = extract_host_port(proxy_link)
    if host and port:
        tcp_ping = tcp_check(host, port)
        if not tcp_ping:
            return None  # Порт закрыт - даже не пытаемся
    else:
        return None
    
    # 2. HTTP-проверка (в зависимости от протокола)
    if proxy_link.startswith('vless://'):
        ping = http_test_vless(proxy_link)
    elif proxy_link.startswith('ss://'):
        ping = http_test_ss(proxy_link)
    elif proxy_link.startswith('trojan://'):
        ping = http_test_trojan(proxy_link)
    elif proxy_link.startswith('hysteria2://'):
        ping = http_test_hysteria2(proxy_link)
    else:
        # Для неизвестных протоколов - только TCP
        ping = tcp_ping
    
    if ping and ping < MAX_PING_MS:
        return proxy_link, ping
    return None

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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
                r'^(?:ss|vless|vmess|trojan|hysteria2|socks5|http)://[^\s]+$',
                response.text,
                re.MULTILINE
            )
            all_proxies.update(proxies)
            print(f"   ✅ Найдено {len(proxies)} прокси")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(all_proxies)

def main():
    print("=" * 60)
    print("🚀 ДВУХУРОВНЕВАЯ ПРОВЕРКА ПРОКСИ (TCP + HTTP)")
    print("=" * 60)
    
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        return
    
    print(f"\n⏳ Шаг 2: Проверка (TCP → HTTP)...")
    working_proxies = []
    checked = 0
    total = len(all_proxies)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_proxy, proxy): proxy for proxy in all_proxies}
        
        for future in as_completed(futures):
            checked += 1
            result = future.result()
            if result:
                proxy, ping = result
                working_proxies.append((proxy, ping))
                print(f"   ✅ {proxy[:50]}... {ping:.0f} мс")
            
            if checked % 20 == 0:
                print(f"   ⏳ Проверено {checked}/{total}...")
    
    # Сортируем по пингу
    working_proxies.sort(key=lambda x: x[1])
    
    # Оставляем только лучшие
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих прокси: {len(working_proxies)}")
    
    # Сохраняем
    with open(OUTPUT_FILE, 'w') as f:
        for proxy, _ in working_proxies:
            f.write(f"{proxy}\n")
    
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
    main()    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        return
    
    print(f"\n⏳ Шаг 2: Проверка пинга ({MAX_WORKERS} потоков)...")
    working_proxies = []
    checked = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_proxy, proxy): proxy for proxy in all_proxies}
        
        for future in as_completed(futures):
            checked += 1
            result = future.result()
            if result:
                proxy, ping = result
                if ping <= MAX_PING_MS:
                    working_proxies.append((proxy, ping))
                    print(f"   ✅ {proxy[:60]}... пинг {ping:.0f} мс")
            
            if checked % 50 == 0:
                print(f"   ⏳ Проверено {checked}/{len(all_proxies)}...")
    
    working_proxies.sort(key=lambda x: x[1])
    
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Финальное количество рабочих прокси: {len(working_proxies)}")
    
    with open(OUTPUT_FILE, 'w') as f:
        for proxy, ping in working_proxies:
            f.write(f"{proxy}\n")
    
    with open("report.txt", 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Всего прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, ping in working_proxies[:10]:
            f.write(f"  {ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
