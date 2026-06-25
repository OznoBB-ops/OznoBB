import requests
import re
import time
import socket
import random
import ipaddress
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
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/everything.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/protocols/vless.txt",
    "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/RU.txt",
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/all.txt",
    "https://raw.githubusercontent.com/ninjastrikers/Nexus-nodes/main/configs/light.txt",
]

OUTPUT_FILE = "proxies.txt"
REPORT_FILE = "report.txt"
MAX_PROXIES = 600
TCP_TIMEOUT = 3
MAX_WORKERS = 15
LIMIT_BEFORE_CHECK = 3000

# ============================================
# СПИСОК РОССИЙСКИХ IP-ДИАПАЗОНОВ
# ============================================
RU_NETWORKS = [
    ipaddress.ip_network("5.1.0.0/19"),      # МегаФон
    ipaddress.ip_network("5.17.0.0/16"),     # МегаФон
    ipaddress.ip_network("5.44.0.0/18"),     # МТС
    ipaddress.ip_network("5.45.0.0/16"),     # МТС
    ipaddress.ip_network("5.136.0.0/13"),    # Билайн
    ipaddress.ip_network("5.164.0.0/14"),    # Билайн
    ipaddress.ip_network("5.228.0.0/16"),    # Ростелеком
    ipaddress.ip_network("31.28.0.0/16"),    # Ростелеком
    ipaddress.ip_network("31.41.0.0/16"),    # МТС
    ipaddress.ip_network("31.173.0.0/16"),   # Билайн
    ipaddress.ip_network("37.140.0.0/16"),   # МТС
    ipaddress.ip_network("37.144.0.0/14"),   # Ростелеком
    ipaddress.ip_network("37.190.0.0/16"),   # Ростелеком
    ipaddress.ip_network("46.0.0.0/15"),     # МТС
    ipaddress.ip_network("46.36.0.0/15"),    # Ростелеком
    ipaddress.ip_network("46.61.0.0/16"),    # МТС
    ipaddress.ip_network("46.138.0.0/16"),   # Ростелеком
    ipaddress.ip_network("46.158.0.0/16"),   # Ростелеком
    ipaddress.ip_network("46.188.0.0/16"),   # Билайн
    ipaddress.ip_network("62.76.0.0/14"),    # МТС
    ipaddress.ip_network("62.105.0.0/16"),   # Ростелеком
    ipaddress.ip_network("62.183.0.0/16"),   # МТС
    ipaddress.ip_network("77.34.0.0/15"),    # МТС
    ipaddress.ip_network("77.41.0.0/16"),    # Ростелеком
    ipaddress.ip_network("77.45.0.0/16"),    # Ростелеком
    ipaddress.ip_network("77.50.0.0/17"),    # Ростелеком
    ipaddress.ip_network("77.94.0.0/16"),    # Ростелеком
    ipaddress.ip_network("77.220.0.0/15"),   # Ростелеком
    ipaddress.ip_network("78.24.0.0/13"),    # МТС
    ipaddress.ip_network("78.80.0.0/14"),    # Билайн
    ipaddress.ip_network("78.106.0.0/15"),   # Ростелеком
    ipaddress.ip_network("78.108.0.0/16"),   # МТС
    ipaddress.ip_network("79.104.0.0/13"),   # Ростелеком
    ipaddress.ip_network("79.120.0.0/16"),   # МТС
    ipaddress.ip_network("79.139.0.0/16"),   # Ростелеком
    ipaddress.ip_network("79.164.0.0/14"),   # Ростелеком
    ipaddress.ip_network("80.64.0.0/14"),    # МТС
    ipaddress.ip_network("80.68.0.0/15"),    # МТС
    ipaddress.ip_network("80.73.0.0/16"),    # МТС
    ipaddress.ip_network("80.83.0.0/16"),    # МТС
    ipaddress.ip_network("80.87.0.0/16"),    # МТС
    ipaddress.ip_network("80.92.0.0/16"),    # МТС
    ipaddress.ip_network("80.93.0.0/16"),    # МТС
    ipaddress.ip_network("80.94.0.0/16"),    # МТС
    ipaddress.ip_network("80.95.0.0/16"),    # МТС
    ipaddress.ip_network("80.237.0.0/16"),   # МТС
    ipaddress.ip_network("80.240.0.0/14"),   # Ростелеком
    ipaddress.ip_network("81.1.0.0/16"),     # Ростелеком
    ipaddress.ip_network("81.2.0.0/16"),     # Ростелеком
    ipaddress.ip_network("81.88.0.0/16"),    # Ростелеком
    ipaddress.ip_network("81.89.0.0/16"),    # Ростелеком
    ipaddress.ip_network("81.90.0.0/16"),    # Ростелеком
    ipaddress.ip_network("81.91.0.0/16"),    # Ростелеком
    ipaddress.ip_network("81.161.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.162.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.163.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.164.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.165.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.166.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.167.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.168.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.169.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.170.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.171.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.172.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.173.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.174.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.175.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.176.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.177.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.178.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.179.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.180.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.181.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.182.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.183.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.184.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.185.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.186.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.187.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.188.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.189.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.190.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.191.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.192.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.193.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.194.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.195.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.196.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.197.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.198.0.0/16"),   # Ростелеком
    ipaddress.ip_network("81.199.0.0/16"),   # Ростелеком
]

PL_NETWORKS = [
    ipaddress.ip_network("2.56.0.0/14"),
    ipaddress.ip_network("5.252.0.0/16"),
    ipaddress.ip_network("31.60.0.0/16"),
    ipaddress.ip_network("37.248.0.0/14"),
    ipaddress.ip_network("46.112.0.0/14"),
    ipaddress.ip_network("46.152.0.0/15"),
    ipaddress.ip_network("46.175.0.0/16"),
    ipaddress.ip_network("62.21.0.0/16"),
    ipaddress.ip_network("62.93.0.0/16"),
    ipaddress.ip_network("62.122.0.0/16"),
    ipaddress.ip_network("77.65.0.0/16"),
    ipaddress.ip_network("77.79.0.0/16"),
    ipaddress.ip_network("77.113.0.0/16"),
    ipaddress.ip_network("77.252.0.0/15"),
    ipaddress.ip_network("78.8.0.0/15"),
    ipaddress.ip_network("78.31.0.0/16"),
    ipaddress.ip_network("79.184.0.0/15"),
    ipaddress.ip_network("79.185.0.0/16"),
    ipaddress.ip_network("80.50.0.0/15"),
    ipaddress.ip_network("80.53.0.0/16"),
    ipaddress.ip_network("81.18.0.0/16"),
    ipaddress.ip_network("81.190.0.0/16"),
    ipaddress.ip_network("81.210.0.0/16"),
    ipaddress.ip_network("82.160.0.0/14"),
    ipaddress.ip_network("83.0.0.0/15"),
    ipaddress.ip_network("83.21.0.0/16"),
    ipaddress.ip_network("83.24.0.0/15"),
    ipaddress.ip_network("83.26.0.0/16"),
    ipaddress.ip_network("83.238.0.0/16"),
    ipaddress.ip_network("83.239.0.0/16"),
    ipaddress.ip_network("84.10.0.0/16"),
    ipaddress.ip_network("84.38.0.0/16"),
    ipaddress.ip_network("84.40.0.0/14"),
    ipaddress.ip_network("85.221.0.0/16"),
    ipaddress.ip_network("87.204.0.0/15"),
    ipaddress.ip_network("88.156.0.0/15"),
    ipaddress.ip_network("88.199.0.0/16"),
    ipaddress.ip_network("89.64.0.0/14"),
    ipaddress.ip_network("89.151.0.0/16"),
    ipaddress.ip_network("89.174.0.0/15"),
    ipaddress.ip_network("89.228.0.0/15"),
    ipaddress.ip_network("91.90.0.0/16"),
    ipaddress.ip_network("91.124.0.0/16"),
    ipaddress.ip_network("91.145.0.0/16"),
    ipaddress.ip_network("91.198.0.0/16"),
    ipaddress.ip_network("91.215.0.0/16"),
    ipaddress.ip_network("91.231.0.0/16"),
    ipaddress.ip_network("91.237.0.0/16"),
    ipaddress.ip_network("91.244.0.0/16"),
    ipaddress.ip_network("92.42.0.0/16"),
    ipaddress.ip_network("93.94.0.0/15"),
    ipaddress.ip_network("93.105.0.0/16"),
    ipaddress.ip_network("93.175.0.0/16"),
    ipaddress.ip_network("94.254.0.0/15"),
    ipaddress.ip_network("95.40.0.0/14"),
    ipaddress.ip_network("95.49.0.0/16"),
    ipaddress.ip_network("95.160.0.0/15"),
    ipaddress.ip_network("109.196.0.0/16"),
    ipaddress.ip_network("109.243.0.0/16"),
    ipaddress.ip_network("176.103.0.0/16"),
    ipaddress.ip_network("176.221.0.0/16"),
    ipaddress.ip_network("178.32.0.0/16"),
    ipaddress.ip_network("178.37.0.0/16"),
    ipaddress.ip_network("185.2.0.0/16"),
    ipaddress.ip_network("185.63.0.0/16"),
    ipaddress.ip_network("185.153.0.0/16"),
    ipaddress.ip_network("188.124.0.0/16"),
    ipaddress.ip_network("188.128.0.0/16"),
    ipaddress.ip_network("188.146.0.0/16"),
    ipaddress.ip_network("193.27.0.0/16"),
    ipaddress.ip_network("193.34.0.0/16"),
    ipaddress.ip_network("193.105.0.0/16"),
    ipaddress.ip_network("193.151.0.0/16"),
    ipaddress.ip_network("193.178.0.0/16"),
    ipaddress.ip_network("193.239.0.0/16"),
    ipaddress.ip_network("194.9.0.0/16"),
    ipaddress.ip_network("194.15.0.0/16"),
    ipaddress.ip_network("194.33.0.0/16"),
    ipaddress.ip_network("194.36.0.0/16"),
    ipaddress.ip_network("194.114.0.0/16"),
    ipaddress.ip_network("194.145.0.0/16"),
    ipaddress.ip_network("194.181.0.0/16"),
    ipaddress.ip_network("195.34.0.0/16"),
    ipaddress.ip_network("195.42.0.0/16"),
    ipaddress.ip_network("195.54.0.0/16"),
    ipaddress.ip_network("195.66.0.0/16"),
    ipaddress.ip_network("195.80.0.0/16"),
    ipaddress.ip_network("195.114.0.0/16"),
    ipaddress.ip_network("195.117.0.0/16"),
    ipaddress.ip_network("195.136.0.0/16"),
    ipaddress.ip_network("195.150.0.0/16"),
    ipaddress.ip_network("195.182.0.0/16"),
    ipaddress.ip_network("195.187.0.0/16"),
    ipaddress.ip_network("195.189.0.0/16"),
    ipaddress.ip_network("195.205.0.0/16"),
    ipaddress.ip_network("195.213.0.0/16"),
    ipaddress.ip_network("195.242.0.0/16"),
    ipaddress.ip_network("195.244.0.0/16"),
    ipaddress.ip_network("195.248.0.0/16"),
    ipaddress.ip_network("195.254.0.0/16"),
    ipaddress.ip_network("195.255.0.0/16"),
    ipaddress.ip_network("212.2.0.0/16"),
    ipaddress.ip_network("212.7.0.0/16"),
    ipaddress.ip_network("212.14.0.0/16"),
    ipaddress.ip_network("212.21.0.0/16"),
    ipaddress.ip_network("212.25.0.0/16"),
    ipaddress.ip_network("212.33.0.0/16"),
    ipaddress.ip_network("212.35.0.0/16"),
    ipaddress.ip_network("212.37.0.0/16"),
    ipaddress.ip_network("212.43.0.0/16"),
    ipaddress.ip_network("212.51.0.0/16"),
    ipaddress.ip_network("212.59.0.0/16"),
    ipaddress.ip_network("212.62.0.0/16"),
    ipaddress.ip_network("212.67.0.0/16"),
    ipaddress.ip_network("212.74.0.0/16"),
    ipaddress.ip_network("212.76.0.0/16"),
    ipaddress.ip_network("212.77.0.0/16"),
    ipaddress.ip_network("212.78.0.0/16"),
    ipaddress.ip_network("212.79.0.0/16"),
    ipaddress.ip_network("212.80.0.0/16"),
    ipaddress.ip_network("212.82.0.0/16"),
    ipaddress.ip_network("212.85.0.0/16"),
    ipaddress.ip_network("212.86.0.0/16"),
    ipaddress.ip_network("212.87.0.0/16"),
    ipaddress.ip_network("212.90.0.0/16"),
    ipaddress.ip_network("212.91.0.0/16"),
    ipaddress.ip_network("212.93.0.0/16"),
    ipaddress.ip_network("212.96.0.0/16"),
    ipaddress.ip_network("212.97.0.0/16"),
    ipaddress.ip_network("212.98.0.0/16"),
    ipaddress.ip_network("212.99.0.0/16"),
    ipaddress.ip_network("212.100.0.0/16"),
    ipaddress.ip_network("212.101.0.0/16"),
    ipaddress.ip_network("212.102.0.0/16"),
    ipaddress.ip_network("212.104.0.0/16"),
    ipaddress.ip_network("212.105.0.0/16"),
    ipaddress.ip_network("212.106.0.0/16"),
    ipaddress.ip_network("212.109.0.0/16"),
    ipaddress.ip_network("212.110.0.0/16"),
    ipaddress.ip_network("212.111.0.0/16"),
    ipaddress.ip_network("213.25.0.0/16"),
    ipaddress.ip_network("213.29.0.0/16"),
    ipaddress.ip_network("213.35.0.0/16"),
    ipaddress.ip_network("213.45.0.0/16"),
    ipaddress.ip_network("213.51.0.0/16"),
    ipaddress.ip_network("213.55.0.0/16"),
    ipaddress.ip_network("213.59.0.0/16"),
    ipaddress.ip_network("213.77.0.0/16"),
    ipaddress.ip_network("213.108.0.0/16"),
    ipaddress.ip_network("213.134.0.0/16"),
    ipaddress.ip_network("213.135.0.0/16"),
    ipaddress.ip_network("213.136.0.0/16"),
    ipaddress.ip_network("213.140.0.0/16"),
    ipaddress.ip_network("213.158.0.0/16"),
    ipaddress.ip_network("213.164.0.0/16"),
    ipaddress.ip_network("213.172.0.0/16"),
    ipaddress.ip_network("213.174.0.0/16"),
    ipaddress.ip_network("213.184.0.0/16"),
    ipaddress.ip_network("213.189.0.0/16"),
    ipaddress.ip_network("213.191.0.0/16"),
    ipaddress.ip_network("213.222.0.0/16"),
    ipaddress.ip_network("213.227.0.0/16"),
    ipaddress.ip_network("213.232.0.0/16"),
    ipaddress.ip_network("213.233.0.0/16"),
    ipaddress.ip_network("213.234.0.0/16"),
    ipaddress.ip_network("213.235.0.0/16"),
    ipaddress.ip_network("213.238.0.0/16"),
    ipaddress.ip_network("213.240.0.0/16"),
    ipaddress.ip_network("213.241.0.0/16"),
    ipaddress.ip_network("213.243.0.0/16"),
    ipaddress.ip_network("213.244.0.0/16"),
    ipaddress.ip_network("213.245.0.0/16"),
    ipaddress.ip_network("213.246.0.0/16"),
    ipaddress.ip_network("213.247.0.0/16"),
    ipaddress.ip_network("213.248.0.0/16"),
    ipaddress.ip_network("213.249.0.0/16"),
    ipaddress.ip_network("213.250.0.0/16"),
    ipaddress.ip_network("213.251.0.0/16"),
    ipaddress.ip_network("213.252.0.0/16"),
    ipaddress.ip_network("213.253.0.0/16"),
    ipaddress.ip_network("213.254.0.0/16"),
    ipaddress.ip_network("213.255.0.0/16"),
    ipaddress.ip_network("217.17.0.0/16"),
    ipaddress.ip_network("217.19.0.0/16"),
    ipaddress.ip_network("217.30.0.0/16"),
    ipaddress.ip_network("217.73.0.0/16"),
    ipaddress.ip_network("217.74.0.0/16"),
    ipaddress.ip_network("217.96.0.0/15"),
    ipaddress.ip_network("217.118.0.0/16"),
    ipaddress.ip_network("217.149.0.0/16"),
    ipaddress.ip_network("217.153.0.0/16"),
    ipaddress.ip_network("217.168.0.0/16"),
    ipaddress.ip_network("217.173.0.0/16"),
    ipaddress.ip_network("217.197.0.0/16"),
    ipaddress.ip_network("217.199.0.0/16"),
    ipaddress.ip_network("217.254.0.0/16"),
]

# ============================================
# ФУНКЦИИ
# ============================================

def is_reality(proxy_link):
    return proxy_link.startswith('vless://') and 'security=reality' in proxy_link

def is_sni_reality(proxy_link):
    """Проверяет, что это VLESS с REALITY и SNI."""
    return (proxy_link.startswith('vless://') and 
            'security=reality' in proxy_link and 
            'sni=' in proxy_link)

def get_ip_from_host(host):
    try:
        return socket.gethostbyname(host)
    except:
        return None

def is_ip_in_networks(ip_str, networks):
    try:
        ip = ipaddress.ip_address(ip_str)
        for net in networks:
            if ip in net:
                return True
        return False
    except:
        return False

def get_country_code(ip_str):
    if is_ip_in_networks(ip_str, RU_NETWORKS):
        return "RU"
    elif is_ip_in_networks(ip_str, PL_NETWORKS):
        return "PL"
    else:
        return "OTHER"

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

def check_proxy(proxy_link):
    proxy_link = proxy_link.strip()
    if not proxy_link or proxy_link.startswith('#'):
        return None
    
    if not is_reality(proxy_link):
        return None
    
    host = extract_host(proxy_link)
    if not host:
        return None
    
    ports = [443, 80, 8080, 8443, 8880, 2096, 2377, 1935, 41930, 35401, 666, 1080]
    for port in ports:
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT)
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
    print("🚀 СБОРКА REALITY-ПРОКСИ (50% RU + 25% RU SNI + 25% PL)")
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
    
    print(f"\n⏳ Гео-фильтрация (RU + PL)...")
    ru_proxies = []
    ru_sni_proxies = []
    pl_proxies = []
    checked = 0
    
    for proxy in reality_proxies:
        host = extract_host(proxy)
        if host:
            ip = get_ip_from_host(host)
            if ip:
                country = get_country_code(ip)
                if country == "RU":
                    if is_sni_reality(proxy):
                        ru_sni_proxies.append(proxy)
                    else:
                        ru_proxies.append(proxy)
                elif country == "PL":
                    pl_proxies.append(proxy)
            checked += 1
            if checked % 100 == 0:
                print(f"   ⏳ Обработано {checked}/{len(reality_proxies)}...")
    
    print(f"\n📊 Найдено российских REALITY: {len(ru_proxies)}")
    print(f"📊 Найдено российских SNI REALITY: {len(ru_sni_proxies)}")
    print(f"📊 Найдено польских REALITY: {len(pl_proxies)}")
    
    target_ru = int(MAX_PROXIES * 0.5)      # 300
    target_ru_sni = int(MAX_PROXIES * 0.25) # 150
    target_pl = int(MAX_PROXIES * 0.25)     # 150
    
    final_proxies = []
    
    # Российские (50%)
    if len(ru_proxies) > 0:
        ru_sample = random.sample(ru_proxies, min(target_ru, len(ru_proxies)))
        final_proxies.extend(ru_sample)
        print(f"✅ Взято российских: {len(ru_sample)}")
    else:
        print("⚠️ Нет российских прокси!")
    
    # Российские SNI (25%)
    if len(ru_sni_proxies) > 0:
        ru_sni_sample = random.sample(ru_sni_proxies, min(target_ru_sni, len(ru_sni_proxies)))
        final_proxies.extend(ru_sni_sample)
        print(f"✅ Взято российских SNI: {len(ru_sni_sample)}")
    else:
        print("⚠️ Нет российских SNI прокси!")
    
    # Польские (25%)
    if len(pl_proxies) > 0:
        pl_sample = random.sample(pl_proxies, min(target_pl, len(pl_proxies)))
        final_proxies.extend(pl_sample)
        print(f"✅ Взято польских: {len(pl_sample)}")
    else:
        print("⚠️ Нет польских прокси!")
    
    # Если не хватает, добираем остальными
    if len(final_proxies) < MAX_PROXIES:
        others = [p for p in reality_proxies if p not in final_proxies]
        if others:
            need = MAX_PROXIES - len(final_proxies)
            extra = random.sample(others, min(need, len(others)))
            final_proxies.extend(extra)
            print(f"✅ Добрано другими: {len(extra)}")
    
    random.shuffle(final_proxies)
    
    print(f"\n🎯 Итоговое количество прокси: {len(final_proxies)}")
    
    with open(OUTPUT_FILE, 'w') as f:
        if final_proxies:
            for proxy in final_proxies:
                f.write(f"{proxy}\n")
        else:
            f.write("# Нет рабочих REALITY-прокси\n")
    
    with open(REPORT_FILE, 'w') as f:
        f.write(f"Собрано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Всего прокси: {len(final_proxies)}\n")
        f.write(f"Российских: {len(ru_sample) if 'ru_sample' in locals() else 0}\n")
        f.write(f"Российских SNI: {len(ru_sni_sample) if 'ru_sni_sample' in locals() else 0}\n")
        f.write(f"Польских: {len(pl_sample) if 'pl_sample' in locals() else 0}\n")
    
    print(f"\n✅ Готово! Список REALITY-прокси сохранён в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
