import requests
import re
import time
import socket
import json
import os
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

OUTPUT_DIR = "singbox/output"
PROXIES_FILE = f"{OUTPUT_DIR}/proxies.txt"
CONFIG_FILE = f"{OUTPUT_DIR}/singbox_config.json"
REPORT_FILE = f"{OUTPUT_DIR}/report.txt"

MAX_PROXIES = 600
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
                    if re.match(r'^(ss|vless|vmess|trojan|hysteria2|socks5|http)://', line):
                        all_proxies.append(line)
            
            print(f"   ✅ Найдено {len([l for l in lines if l and not l.startswith('#')])} прокси")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return list(set(all_proxies))

# ============================================
# ГЕНЕРАЦИЯ SING-BOX КОНФИГА (ИСПРАВЛЕННАЯ)
# ============================================

def generate_singbox_config():
    config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "https://dns.google/dns-query"},
                {"tag": "dns-local", "address": "223.5.5.5", "detour": "direct"}
            ],
            "rules": [
                {"domain_suffix": [".ru", ".su", ".рф"], "server": "dns-local"}
            ]
        },
        "inbounds": [
            {
                "type": "mixed",
                "listen": "127.0.0.1",
                "listen_port": 7890,
                "set_system_proxy": False
            }
        ],
        "outbounds": [
            {"type": "selector", "tag": "PROXY", "outbounds": ["auto", "direct"]},
            {"type": "urltest", "tag": "auto", "outbounds": ["merged-sub"], "url": "http://cp.cloudflare.com/generate_204", "interval": "5m", "tolerance": 50},
            {"type": "selector", "tag": "TORRENT", "outbounds": ["auto-torrent", "direct"]},
            {"type": "urltest", "tag": "auto-torrent", "outbounds": ["merged-sub"], "url": "http://cp.cloudflare.com/generate_204", "interval": "5m", "tolerance": 100},
            {"type": "selector", "tag": "TELEGRAM", "outbounds": ["auto", "direct"]},
            {"type": "selector", "tag": "PERSONAL24", "outbounds": ["auto", "direct"]},
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"}
        ],
        "route": {
            "rules": [
                {"rule_set": ["torrent-clients", "torrent-trackers"], "outbound": "TORRENT"},
                {"rule_set": ["telegram"], "outbound": "TELEGRAM"},
                {"rule_set": ["personal24"], "outbound": "PERSONAL24"},
                {"rule_set": ["ru-bundle", "ru-custom"], "outbound": "direct"},
                {"rule_set": ["skrepysh-proxy"], "outbound": "PROXY"}
            ],
            "rule_set": [
                {
                    "tag": "ru-bundle",
                    "type": "remote",
                    "format": "yaml",
                    "url": "https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/ru-bundle/rule.yaml",
                    "update_interval": "24h",
                    "download_detour": "direct"
                },
                {
                    "tag": "ru-custom",
                    "type": "remote",
                    "format": "yaml",
                    "url": "https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/ru-custom/rule.yaml",
                    "update_interval": "24h",
                    "download_detour": "direct"
                },
                {
                    "tag": "torrent-clients",
                    "type": "remote",
                    "format": "yaml",
                    "url": "https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/refs/heads/main/other/torrent-clients.yaml",
                    "update_interval": "24h",
                    "download_detour": "direct"
                },
                {
                    "tag": "torrent-trackers",
                    "type": "remote",
                    "format": "mrs",
                    "url": "https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/torrent-trackers.mrs",
                    "update_interval": "24h",
                    "download_detour": "direct"
                },
                {
                    "tag": "telegram",
                    "type": "remote",
                    "format": "yaml",
                    "url": "https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/telegram/rule.yaml",
                    "update_interval": "24h",
                    "download_detour": "direct"
                },
                {
                    "tag": "personal24",
                    "type": "remote",
                    "format": "yaml",
                    "url": "https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/personal-24/rule.yaml",
                    "update_interval": "24h",
                    "download_detour": "direct"
                },
                {
                    "tag": "skrepysh-proxy",
                    "type": "remote",
                    "format": "yaml",
                    "url": "https://raw.githubusercontent.com/Skrepysh/mihomo-rulesets/refs/heads/main/skrepysh-rulesets/skrepysh-proxy.yaml",
                    "update_interval": "24h",
                    "download_detour": "direct"
                }
            ],
            "auto_detect_interface": True,
            "final": "PROXY"
        }
    }
    return config

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 СБОРКА SING-BOX КОНФИГА")
    print("=" * 50)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("\n📦 Шаг 1: Загрузка подписок...")
    all_proxies = fetch_subscriptions(SUBSCRIPTIONS)
    print(f"\n📊 Всего уникальных прокси: {len(all_proxies)}")
    
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
    
    print(f"\n🎯 Рабочих прокси: {len(working_proxies)}")
    
    with open(PROXIES_FILE, 'w') as f:
        if working_proxies:
            for proxy, _ in working_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих прокси\n")
    
    print(f"\n⏳ Шаг 3: Генерация Sing-box конфига...")
    singbox_config = generate_singbox_config()
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(singbox_config, f, indent=2, ensure_ascii=False)
    
    with open(REPORT_FILE, 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Пинг до {PING_TARGET}: {ping:.0f} мс\n")
        f.write(f"Всего прокси: {len(working_proxies)}\n")
        if working_proxies:
            f.write(f"Средний пинг: {sum(p for _, p in working_proxies) / len(working_proxies):.0f} мс\n")
        f.write("\nТоп-10:\n")
        for proxy, proxy_ping in working_proxies[:10]:
            f.write(f"  {proxy_ping:.0f} мс | {proxy[:80]}...\n")
    
    print(f"\n✅ Готово!")
    print(f"   📄 Список прокси: {PROXIES_FILE}")
    print(f"   📄 Sing-box конфиг: {CONFIG_FILE}")
    print(f"   📄 Отчёт: {REPORT_FILE}")

if __name__ == "__main__":
    main()
