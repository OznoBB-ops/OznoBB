import requests
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import socket

# ============================================
# НАСТРОЙКИ
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
PING_TIMEOUT = 3  # секунды
MAX_PING_MS = 300  # отсекаем всё, что пингуется хуже 300 мс
MAX_WORKERS = 30   # количество параллельных проверок

# ============================================
# ФУНКЦИИ
# ============================================

def fetch_subscriptions(urls):
    """Скачивает все подписки и извлекает прокси-ссылки."""
    all_proxies = set()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    for url in urls:
        try:
            print(f"📥 Загрузка: {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            # Ищем строки, начинающиеся с протокола
            proxies = re.findall(
                r'^(?:ss|vless|vmess|trojan|hysteria2|socks5|http)://[^\s]+$',
                response.text,
                re.MULTILINE
            )
            
            # Убираем дубликаты
            proxies = list(set(proxies))
            all_proxies.update(proxies)
            print(f"   ✅ Найдено {len(proxies)} прокси")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(all_proxies)

def extract_host(proxy_link):
    """Извлекает хост и порт из прокси-ссылки."""
    try:
        # Парсим URL
        parsed = urlparse(proxy_link)
        host = parsed.hostname
        port = parsed.port
        
        # Если не распарсилось, ищем @host:port
        if not host:
            match = re.search(r'@([^:]+):(\d+)', proxy_link)
            if match:
                host = match.group(1)
                port = int(match.group(2))
        
        return host, port
    except:
        return None, None

def ping_host(host, port=443):
    """Проверяет доступность хоста через TCP-коннект (быстрее чем ping)."""
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(PING_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            ping_ms = (time.time() - start) * 1000
            return ping_ms
        else:
            return None
    except:
        return None

def check_proxy(proxy_link):
    """Проверяет прокси на доступность."""
    host, port = extract_host(proxy_link)
    if not host:
        return None
    
    # Если порт не указан, пробуем стандартные
    if not port:
        for test_port in [443, 80, 8080, 8443, 8880, 2096]:
            ping = ping_host(host, test_port)
            if ping:
                return proxy_link, ping
        return None
    
    ping = ping_host(host, port)
    if ping:
        return proxy_link, ping
    return None

def main():
    print("=" * 50)
    print("🚀 СБОРКА СПИСКА ДЛЯ EXCLAVE")
    print("=" * 50)
    
    # 1. Скачиваем все прокси
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        return
    
    # 2. Проверяем пинг
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
            
            # Прогресс
            if checked % 50 == 0:
                print(f"   ⏳ Проверено {checked}/{len(all_proxies)}...")
    
    # 3. Сортируем по пингу (от лучшего к худшему)
    working_proxies.sort(key=lambda x: x[1])
    
    # 4. Оставляем только лучшие (не более MAX_PROXIES)
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Финальное количество рабочих прокси: {len(working_proxies)}")
    
    # 5. Сохраняем только ссылки (без пинга)
    with open(OUTPUT_FILE, 'w') as f:
        for proxy, ping in working_proxies:
            f.write(f"{proxy}\n")
    
    # 6. Сохраняем отчёт с пингами (для отладки)
    with open("report.txt", 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Всего прокси: {len(working_proxies)}\n")
        f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, ping in working_proxies[:10]:
            f.write(f"  {ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово! Список сохранён в {OUTPUT_FILE}")
    print(f"📊 Отчёт сохранён в report.txt")

if __name__ == "__main__":
    main()
