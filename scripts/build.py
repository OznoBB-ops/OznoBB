#!/usr/bin/env python3
import requests
import json
import re
from pathlib import Path
from datetime import datetime, timezone

# Create subscription directory
Path('subscription').mkdir(exist_ok=True)

# VLESS sources
SOURCES = [
    'https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt',
    'https://gitlab.com/zieng2/wl/raw/main/vless_universal.txt',
    'https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt',
    'https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt',
    'https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt',
]

def download_configs():
    for source in SOURCES:
        try:
            print(f'Trying {source}...')
            resp = requests.get(source, timeout=10)
            resp.raise_for_status()
            return resp.text.strip().split('\n')
        except Exception as e:
            print(f'Failed: {e}')
    return []

def is_valid_vless(url):
    if not url.startswith('vless://'):
        return False
    try:
        parsed = re.search(r'(\?|&)security=(reality|tls)', url)
        return parsed is not None
    except:
        return False

def process_urls(urls):
    filtered = []
    seen = set()
    
    for url in urls:
        url = url.strip()
        if is_valid_vless(url) and url not in seen:
            filtered.append(url)
            seen.add(url)
    
    return filtered

# Download and process
all_urls = download_configs()
filtered_urls = process_urls(all_urls)

# Save results
with open('subscription/subscription.txt', 'w') as f:
    f.write('\n'.join(filtered_urls))

with open('subscription/original.txt', 'w') as f:
    f.write('\n'.join(set(all_urls)))

metadata = {
    'filtered_count': len(filtered_urls),
    'total_unique': len(set(all_urls)),
    'timestamp': datetime.now(timezone.utc).isoformat(),
}

with open('subscription/metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f'✓ Filtered: {len(filtered_urls)}, Total: {len(set(all_urls))}')

