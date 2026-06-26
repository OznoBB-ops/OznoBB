#!/usr/bin/env python3
import requests
import json
from datetime import datetime
from pathlib import Path
import re

# 6 ИСТОЧНИКОВ (2 zieng2 + 4 igareck)
SOURCES = [
    # zieng2
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt",
    
    # igareck (WHITE-SNI и CIDR — безопасные списки)
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
]

def fetch_configs(source):
    """Загружает конфиги из источника"""
    try:
        response = requests.get(source, timeout=10)
        response.raise_for_status()
        configs = [line.strip() for line in response.text.split('\n') if line.strip()]
        print(f"✅ {source.split('/')[-1]}: {len(configs)} конфигов")
        return configs
    except Exception as e:
        print(f"❌ {source.split('/')[-1]}: {e}")
        return []

def is_vless_reality_sni(config):
    """Проверяет: VLESS + Reality + SNI"""
    if not config.startswith('vless://'):
        return False
    
    # Проверяем наличие reality
    if 'security=reality' not in config:
        return False
    
    # Проверяем наличие sni (serverName)
    if 'sni=' not in config:
        return False
    
    # Проверяем базовую структуру
    if '@' not in config or '#' not in config:
        return False
    
    return True

def is_safe_config(config):
    """Проверяет безопасность конфига"""
    # Черные слова (опасные серверы)
    blacklist = ['proxy', 'test', 'temp', 'invalid', 'error', 'fail']
    
    name = config.split('#')[-1].lower() if '#' in config else ''
    
    for word in blacklist:
        if word in name:
            return False
    
    # Проверяем валидность UUID и IP
    try:
        # Извлекаем UUID
        uuid_pattern = r'vless://([a-f0-9\-]{36})'
        if not re.search(uuid_pattern, config):
            return False
        
        # Проверяем IP в URL
        ip_pattern = r'@([\d\.:a-f]+)'
        ip_match = re.search(ip_pattern, config)
        if not ip_match:
            return False
        
        ip = ip_match.group(1)
        # Исключаем localhost и invalid IPs
        if ip.startswith('127.') or ip.startswith('0.0.0.'):
            return False
        
        return True
    except:
        return False

def main():
    all_configs = []
    
    print("🔄 Загружаю VLESS + Reality + SNI конфиги...\n")
    
    for source in SOURCES:
        configs = fetch_configs(source)
        all_configs.extend(configs)
    
    print(f"\n📊 Всего загружено: {len(all_configs)} конфигов")
    
    # Фильтруем: VLESS + Reality + SNI
    filtered = [c for c in all_configs if is_vless_reality_sni(c)]
    print(f"🔐 VLESS + Reality + SNI: {len(filtered)}")
    
    # Фильтруем: безопасные
    safe = [c for c in filtered if is_safe_config(c)]
    print(f"✅ Безопасные: {len(safe)}")
    
    # Удаляем дубли (сохраняем первый)
    seen = set()
    unique_configs = []
    for config in safe:
        if config not in seen:
            seen.add(config)
            unique_configs.append(config)
    
    print(f"🔄 После удаления дублей: {len(unique_configs)}")
    
    # Сохраняем файлы
    subscription_dir = Path("subscription")
    subscription_dir.mkdir(exist_ok=True)
    
    # subscription.txt (финальный файл)
    with open(subscription_dir / "subscription.txt", "w") as f:
        f.write('\n'.join(unique_configs))
    
    # metadata.json
    metadata = {
        "total_configs": len(unique_configs),
        "type": "VLESS+Reality+SNI",
        "safe": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sources": len(SOURCES),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    
    with open(subscription_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ Сохранено в subscription.txt: {len(unique_configs)} конфигов")
    print(f"📝 metadata.json обновлён")

if __name__ == "__main__":
    main()

