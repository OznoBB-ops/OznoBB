"""Main build script for OznoBB proxy aggregator."""
import logging
import requests
import base64
import os
from typing import List, Set, Dict
from urllib.parse import urlparse, parse_qs
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Proxy sources with fallbacks
SOURCES = {
    'zieng2': [
        'https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt',
        'https://gitlab.com/zieng2/wl/raw/main/vless_universal.txt',
        'https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt',
        'https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt',
        'https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt',
    ],
    # Add other sources here
}

SECURE_TYPES = {'reality', 'tls'}
OUTPUT_DIR = 'subscription'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_configs(sources: Dict[str, List[str]]) -> tuple[List[str], List[str]]:
    """Fetch VLESS configs from sources with fallback support."""
    all_configs = []
    original_configs = []
    
    for source_name, urls in sources.items():
        logger.info(f"Processing source: {source_name}")
        
        for url in urls:
            try:
                logger.info(f"Fetching from {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                lines = response.text.strip().split('\n')
                configs = [line.strip() for line in lines if line.strip().startswith('vless://')]
                
                if configs:
                    logger.info(f"✓ Got {len(configs)} configs from {source_name}")
                    original_configs.extend(configs)
                    all_configs.extend(configs)
                    break  # Success, don't try other mirrors
                    
            except requests.RequestException as e:
                logger.warning(f"✗ Failed to fetch from {url}: {e}")
                continue
        
        if not any(url for url in urls):
            logger.error(f"All mirrors failed for {source_name}")
    
    return all_configs, original_configs


def parse_vless_config(config: str) -> Dict:
    """Parse VLESS URL and extract parameters."""
    try:
        if not config.startswith('vless://'):
            return None
        
        # Remove 'vless://' prefix
        config_data = config[8:]
        
        # Split by @ to get userinfo and server part
        if '@' not in config_data:
            return None
        
        userinfo, server_part = config_data.rsplit('@', 1)
        
        # Parse server part (host:port?params)
        if '?' in server_part:
            host_port, params_str = server_part.split('?', 1)
            params = parse_qs(params_str)
            # Flatten single-value params
            params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        else:
            host_port = server_part
            params = {}
        
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
        else:
            host = host_port
            port = '443'
        
        return {
            'url': config,
            'uuid': userinfo,
            'host': host,
            'port': port,
            'security': params.get('security', 'none'),
            'params': params,
        }
    except Exception as e:
        logger.debug(f"Failed to parse config: {e}")
        return None


def filter_configs(configs: List[str]) -> List[str]:
    """Filter configs for security (only reality/tls, no insecure)."""
    filtered = []
    
    for config in configs:
        parsed = parse_vless_config(config)
        
        if not parsed:
            continue
        
        security = parsed.get('security', 'none').lower()
        
        # Only keep reality or tls
        if security in SECURE_TYPES:
            filtered.append(config)
            logger.debug(f"✓ Kept config with security={security}")
        else:
            logger.debug(f"✗ Skipped config with security={security}")
    
    return filtered


def save_configs(verified: List[str], original: List[str]):
    """Save configs to files."""
    subscription_path = os.path.join(OUTPUT_DIR, 'subscription.txt')
    original_path = os.path.join(OUTPUT_DIR, 'original.txt')
    
    # Save verified (filtered)
    with open(subscription_path, 'w') as f:
        f.write('\n'.join(verified))
    logger.info(f"Saved {len(verified)} verified configs to {subscription_path}")
    
    # Save original (all)
    with open(original_path, 'w') as f:
        f.write('\n'.join(original))
    logger.info(f"Saved {len(original)} original configs to {original_path}")
    
    # Save metadata
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'verified_count': len(verified),
        'original_count': len(original),
        'filters_applied': list(SECURE_TYPES),
    }
    
    with open(os.path.join(OUTPUT_DIR, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Metadata: {metadata}")


def main():
    """Main execution."""
    logger.info("=" * 60)
    logger.info("Starting OznoBB proxy aggregator")
    logger.info("=" * 60)
    
    # Fetch configs from all sources
    all_configs, original_configs = fetch_configs(SOURCES)
    logger.info(f"Total fetched: {len(all_configs)} configs")
    
    # Remove duplicates while preserving order
    unique_configs = list(dict.fromkeys(all_configs))
    logger.info(f"After dedup: {len(unique_configs)} configs")
    
    # Filter for security
    verified_configs = filter_configs(unique_configs)
    logger.info(f"After security filter: {len(verified_configs)} configs")
    
    # Remove duplicates from original too
    original_unique = list(dict.fromkeys(original_configs))
    
    # Save to files
    save_configs(verified_configs, original_unique)
    
    logger.info("=" * 60)
    logger.info("Build completed successfully!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
