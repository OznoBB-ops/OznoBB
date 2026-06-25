import requests
import base64
from datetime import datetime

SOURCES = [
    "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

def fetch_and_merge_configs():
    """Получает конфиги из всех источников и объединяет их"""
    all_configs = []
    
    for source in SOURCES:
        try:
            print(f"Загружаю: {source}")
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            
            # Разделяем конфиги по строкам и удаляем пустые
            configs = [line.strip() for line in response.text.split('\n') if line.strip()]
            all_configs.extend(configs)
            print(f"✓ Загружено {len(configs)} конфигов")
            
        except Exception as e:
            print(f"✗ Ошибка при загрузке {source}: {e}")
    
    # Удаляем дубликаты, сохраняя порядок
    unique_configs = []
    seen = set()
    for config in all_configs:
        if config not in seen:
            unique_configs.append(config)
            seen.add(config)
    
    print(f"\nВсего уникальных конфигов: {len(unique_configs)}")
    return '\n'.join(unique_configs)

def save_to_github(content):
    """Сохраняет контент в файл (локально)"""
    with open('proxies.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Файл proxies.txt создан")

if __name__ == "__main__":
    print("=== Объединение подписок ===\n")
    merged_content = fetch_and_merge_configs()
    save_to_github(merged_content)
    print("\nТеперь загрузи файл на GitHub вручную!")
