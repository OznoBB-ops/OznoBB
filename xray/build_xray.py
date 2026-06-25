import requests
import re
import time
import socket
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

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

OUTPUT_DIR = "xray/output"
PROXIES_FILE = f"{OUTPUT_DIR}/proxies.txt"
CONFIG_FILE = f"{OUTPUT_DIR}/config.json"
REPORT_FILE = f"{OUTPUT_DIR}/report.txt"

MAX_PROXIES = 100
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

def check_proxy(proxy_link):
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    host = extract_host(proxy_link)
    if not host:
        return None
    
    try:
        start_ping = time.time()
        socket.gethostbyname(PING_TARGET)
        ping_to_tver = (time.time() - start_ping) * 1000
        if ping_to_tver > MAX_PING_MS:
            return None
    except:
        pass
    
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
                    if re.match(r'^vless://', line):
                        all_proxies.append(line)
            
            print(f"   ✅ Найдено {len([l for l in lines if l and not l.startswith('#')])} прокси")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(set(all_proxies))

# ============================================
# ПАРСИНГ VLESS-URI В XRAY OUTBOUND
# ============================================

def parse_vless_uri(uri):
    try:
        parsed = urlparse(uri)
        uuid = parsed.username
        host = parsed.hostname
        port = parsed.port or 443
        
        params = parse_qs(parsed.query)
        flow = params.get('flow', [''])[0]
        encryption = params.get('encryption', ['none'])[0]
        sni = params.get('sni', [host])[0]
        fp = params.get('fp', ['chrome'])[0]
        pbk = params.get('pbk', [''])[0]
        sid = params.get('sid', [''])[0]
        security = params.get('security', ['reality'])[0]
        
        name = parsed.fragment or f"{host}:{port}"
        
        outbound = {
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": host,
                        "port": port,
                        "users": [
                            {
                                "id": uuid,
                                "encryption": encryption,
                                "flow": flow
                            }
                        ]
                    }
                ]
            },
            "streamSettings": {
                "network": "tcp",
                "security": security,
                "realitySettings": {
                    "serverName": sni,
                    "fingerprint": fp,
                    "publicKey": pbk,
                    "shortId": sid
                }
            },
            "tag": f"proxy-{name[:30]}"
        }
        return outbound
    except Exception as e:
        print(f"   ⚠️ Ошибка парсинга: {e}")
        return None

# ============================================
# ГЕНЕРАЦИЯ XRAY КОНФИГА
# ============================================

def generate_xray_config(proxies):
    proxies = sorted(proxies, key=lambda x: x[1])[:MAX_PROXIES]
    
    outbounds = []
    for proxy, ping in proxies:
        outbound = parse_vless_uri(proxy)
        if outbound:
            outbounds.append(outbound)
    
    outbounds.append({"protocol": "freedom", "tag": "direct"})
    outbounds.append({"protocol": "blackhole", "tag": "block"})
    
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"udp": True}},
            {"port": 1081, "listen": "127.0.0.1", "protocol": "http", "settings": {}}
        ],
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"type": "field", "domain": ["telegram.org", "tdesktop.com", "t.me", "tg.dev"], "outboundTag": "proxy"},
                {"type": "field", "domain": ["personal24.ru", "personal24.com", "p24.ru"], "outboundTag": "proxy"},
                {"type": "field", "domain": ["ya.ru", "yandex.ru", "vk.com", "mail.ru", "gosuslugi.ru"], "outboundTag": "direct"},
                {"type": "field", "domainSuffix": [".ru", ".su", ".рф", ".tver.ru"], "outboundTag": "direct"},
                {"type": "field", "outboundTag": "proxy"}
            ]
        }
    }
    return config

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 СБОРКА XRAY КОНФИГА (REALITY)")
    print("=" * 50)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("\n📦 Шаг 1: Загрузка подписок (только VLESS)...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего VLESS прокси: {len(all_proxies)}")
    
    if len(all_proxies) == 0:
        print("❌ Нет прокси для проверки!")
        with open(CONFIG_FILE, 'w') as f:
            json.dump({}, f)
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
                    proxy, proxy_ping = result
                    working_proxies.append((proxy, proxy_ping))
                    print(f"   ✅ {proxy[:50]}... {proxy_ping:.0f} мс")
            except:
                pass
            
            if checked % 20 == 0:
                print(f"   ⏳ Проверено {checked}/{total}...")
    
    working_proxies.sort(key=lambda x: x[1])
    if len(working_proxies) > MAX_PROXIES:
        working_proxies = working_proxies[:MAX_PROXIES]
    
    print(f"\n🎯 Рабочих REALITY прокси: {len(working_proxies)}")
    
    with open(PROXIES_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих прокси\n")
    
    print(f"\n⏳ Шаг 3: Генерация Xray конфига...")
    xray_config = generate_xray_config(working_proxies)
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(xray_config, f, indent=2, ensure_ascii=False)
    
    with open(REPORT_FILE, 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до {PING_TARGET}: {ping:.0f} мс\n")
        f.write(f"Всего REALITY прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, proxy_ping in working_proxies[:10]:
            f.write(f"  {proxy_ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово!")
    print(f"   📄 Список прокси: {PROXIES_FILE}")
    print(f"   📄 Xray конфиг: {CONFIG_FILE}")
    print(f"   📄 Отчёт: {REPORT_FILE}")

if __name__ == "__main__":
    main()
