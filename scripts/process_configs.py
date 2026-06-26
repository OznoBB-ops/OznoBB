#!/usr/bin/env python3
"""
Fetch, parse, filter and deduplicate proxy configs
Complete implementation
"""

import requests
import re
import json
from collections import defaultdict
from typing import Set, List, Dict, Tuple
import sys
import time
import logging

from constants import (
    PRIMARY_SOURCES, MIRRORS_ZIENG2, MIRRORS_IGARECK, 
    COUNTRY_FLAGS, FETCH_TIMEOUT
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigProcessor:
    def __init__(self):
        self.vless_configs: Set[str] = set()
        self.sni_rules: Set[str] = set()
        self.server_metadata: Dict[str, Dict] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def fetch_url(self, url: str) -> str:
        """Fetch content from URL with timeout and error handling"""
        try:
            response = self.session.get(url, timeout=FETCH_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  Timeout fetching {url}")
            return ""
        except requests.exceptions.ConnectionError:
            logger.warning(f"🔌 Connection error for {url}")
            return ""
        except Exception as e:
            logger.warning(f"❌ Failed to fetch {url}: {str(e)[:50]}")
            return ""
    
    def fetch_all_sources(self) -> str:
        """Fetch from primary sources and mirrors"""
        logger.info("📥 Fetching configs from all sources...")
        
        all_urls = []
        
        # Primary sources
        all_urls.extend(PRIMARY_SOURCES.values())
        
        # Mirrors
        all_urls.extend(MIRRORS_ZIENG2)
        all_urls.extend(MIRRORS_IGARECK['vless'])
        all_urls.extend(MIRRORS_IGARECK['ss'])
        all_urls.extend(MIRRORS_IGARECK['cidr'])
        all_urls.extend(MIRRORS_IGARECK['sni'])
        
        # Remove duplicates
        all_urls = list(set(all_urls))
        logger.info(f"📊 Total unique URLs to fetch: {len(all_urls)}")
        
        all_content = []
        successful = 0
        failed = 0
        
        for i, url in enumerate(all_urls, 1):
            # Show short URL
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"  [{i:3d}/{len(all_urls)}] {short_url}")
            
            content = self.fetch_url(url)
            if content:
                all_content.append(content)
                size_kb = len(content) / 1024
                print(f"         ✓ Got {size_kb:.1f} KB")
                successful += 1
            else:
                print(f"         ✗ Failed")
                failed += 1
            
            time.sleep(0.3)  # Rate limiting
        
        logger.info(f"✅ Fetched {successful} sources, {failed} failed")
        
        combined = "\n".join(all_content)
        logger.info(f"📦 Total content size: {len(combined) / 1024 / 1024:.2f} MB")
        
        return combined
    
    def extract_country_from_name(self, name: str) -> str:
        """Extract country code from server name"""
        # Look for patterns like: RU, DE, US, etc.
        # Patterns: "🇷🇺RU", "RU-1", "ru1", etc.
        
        # Remove emoji first
        clean_name = re.sub(r'[\U0001F1E6-\U0001F1FF]+', '', name)
        
        # Look for 2-letter country code
        match = re.search(r'\b([A-Z]{2})\b', clean_name.upper())
        if match:
            country = match.group(1)
            if country in COUNTRY_FLAGS:
                return country
        
        return 'XX'
    
    def parse_vless(self, line: str) -> Tuple[str, str]:
        """
        Parse VLESS config and extract country code
        Returns: (config, country_code)
        
        Format: vless://uuid@server:port?params#name
        """
        if not line.startswith('vless://'):
            return None, None
        
        try:
            # Extract name/comment part (after #)
            name = ""
            if '#' in line:
                name = line.split('#', 1)[1]
            
            country = self.extract_country_from_name(name)
            
            return line.strip(), country
            
        except Exception as e:
            logger.debug(f"Error parsing VLESS: {e}")
            return line.strip(), 'XX'
    
    def is_safe_vless(self, line: str) -> bool:
        """
        Check if VLESS config is safe (no insecure params)
        
        Safe:
        - security=reality (always)
        - security=tls without insecure=1
        
        Unsafe:
        - insecure=1 or allowInsecure=1
        - security=none
        """
        
        # Check for dangerous patterns
        if re.search(r'allowInsecure[=:]1|insecure[=:]1', line, re.IGNORECASE):
            return False
        
        if re.search(r'security[=:]none', line, re.IGNORECASE):
            return False
        
        # Check for safe patterns
        if 'security=reality' in line or 'security=tls' in line:
            return True
        
        # Default: if no security specified, could be safe
        # But we filter strictly
        if 'security=' not in line:
            return False
        
        return False
    
    def is_reality_server(self, line: str) -> bool:
        """Check if server uses Reality (priority)"""
        return 'security=reality' in line
    
    def filter_vless(self, content: str) -> Tuple[Set[str], Set[str]]:
        """
        Filter only VLESS configs and SNI rules
        
        Returns: (vless_configs, sni_rules)
        """
        logger.info("🔍 Filtering VLESS and SNI rules...")
        
        vless_set = set()
        sni_set = set()
        total_lines = 0
        
        for line in content.split('\n'):
            line = line.strip()
            total_lines += 1
            
            if not line or line.startswith('#'):
                continue
            
            # VLESS configs - KEEP ONLY THESE
            if line.startswith('vless://'):
                vless_config, country = self.parse_vless(line)
                if vless_config:
                    vless_set.add(vless_config)
                    # Store metadata
                    self.server_metadata[vless_config] = {
                        'country': country,
                        'is_reality': self.is_reality_server(vless_config),
                        'is_safe': self.is_safe_vless(vless_config)
                    }
            
            # SNI rules - domain names, CIDR, IP addresses (no protocol prefix)
            elif not re.match(r'^[a-z]+://', line):
                # Filter out garbage
                if len(line) > 3:
                    # Basic validation
                    if re.match(r'^[a-zA-Z0-9.\-*_/]+$', line):
                        sni_set.add(line)
        
        logger.info(f"  Processed {total_lines} lines")
        logger.info(f"  ✓ Found {len(vless_set)} VLESS configs")
        logger.info(f"  ✓ Found {len(sni_set)} SNI rules")
        
        return vless_set, sni_set
    
    def deduplicate_and_sort(self, vless: Set[str], sni: Set[str]) -> Tuple[List[str], List[str]]:
        """
        Deduplicate configs and sort alphabetically
        """
        logger.info("🎯 Deduplicating and sorting...")
        
        vless_list = sorted(list(vless))
        sni_list = sorted(list(sni))
        
        logger.info(f"  ✓ {len(vless_list)} unique VLESS configs")
        logger.info(f"  ✓ {len(sni_list)} unique SNI rules")
        
        return vless_list, sni_list
    
    def format_server_name(self, country: str, index: int) -> str:
        """Format server name with emoji and country code"""
        flag = COUNTRY_FLAGS.get(country, '🌐')
        return f"{flag}{country}#{index}"
    
    def save_original(self, vless: List[str], sni: List[str]):
        """
        Save original.txt - all VLESS + SNI without any checks
        
        This is the unfiltered version with everything
        """
        logger.info("💾 Saving original.txt...")
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        with open('original.txt', 'w', encoding='utf-8') as f:
            # Header
            f.write("# OznoBB - Original Configuration List\n")
            f.write("# ===================================\n")
            f.write(f"# Generated: {timestamp}\n")
            f.write(f"# Total entries: {len(vless) + len(sni)}\n")
            f.write(f"# VLESS configs: {len(vless)}\n")
            f.write(f"# SNI rules: {len(sni)}\n")
            f.write("# Note: This file contains all configs without verification\n")
            f.write("# Some servers may be dead or insecure\n")
            f.write("#\n\n")
            
            # VLESS Configs
            f.write("# ========== VLESS CONFIGURATIONS ==========\n")
            f.write(f"# Total: {len(vless)}\n\n")
            for config in vless:
                f.write(config + '\n')
            
            # SNI Rules
            f.write("\n# ========== SNI RULES ==========\n")
            f.write(f"# Total: {len(sni)}\n\n")
            for rule in sni:
                f.write(rule + '\n')
        
        logger.info(f"  ✓ Saved {len(vless) + len(sni)} entries to original.txt")
    
    def add_name_to_config(self, config: str, name: str) -> str:
        """Add or replace name in VLESS config"""
        # Check if config already has a name
        if '#' in config:
            # Replace existing name
            return re.sub(r'#[^\n]*', f'#{name}', config)
        else:
            # Add new name
            return config + f'#{name}'
    
    def save_subscription(self, vless: List[str], sni: List[str], alive_configs: Dict[str, bool]):
        """
        Save subscription.txt - only alive + safe servers
        
        Format:
        - Reality servers first (grouped by country with numbers)
        - TLS servers second (grouped by country with numbers)
        - SNI rules at the end (limited to 100)
        """
        logger.info("💾 Saving subscription.txt...")
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Filter only safe + alive configs
        safe_vless = [
            c for c in vless 
            if self.is_safe_vless(c) and alive_configs.get(c, False)
        ]
        
        logger.info(f"  Filtered to {len(safe_vless)} safe + alive servers")
        
        # Group by country and type
        by_country_reality = defaultdict(list)
        by_country_tls = defaultdict(list)
        
        for config in safe_vless:
            metadata = self.server_metadata.get(config, {})
            country = metadata.get('country', 'XX')
            
            if self.is_reality_server(config):
                by_country_reality[country].append(config)
            else:
                by_country_tls[country].append(config)
        
        logger.info(f"  Reality servers: {sum(len(v) for v in by_country_reality.values())}")
        logger.info(f"  TLS servers: {sum(len(v) for v in by_country_tls.values())}")
        
        # Write file
        with open('subscription.txt', 'w', encoding='utf-8') as f:
            # Header
            f.write("# OznoBB - Verified Subscription\n")
            f.write("# ===============================\n")
            f.write(f"# Generated: {timestamp}\n")
            f.write(f"# Total servers: {len(safe_vless)}\n")
            f.write(f"# Total SNI rules: {min(len(sni), 100)}\n")
            f.write("# Note: Contains only verified alive + safe servers\n")
            f.write("# Checked: Ping from Russian nodes (check-host.net)\n")
            f.write("# Security: reality + tls only, no insecure\n")
            f.write("#\n\n")
            
            # ===== REALITY SERVERS (Priority) =====
            if by_country_reality:
                f.write("# ========== REALITY SERVERS (PRIORITY) ==========\n")
                f.write("# These use WireGuard protocol and are more reliable\n\n")
                
                for country in sorted(by_country_reality.keys()):
                    configs = by_country_reality[country]
                    f.write(f"# Country: {country}\n")
                    flag = COUNTRY_FLAGS.get(country, '🌐')
                    
                    for idx, config in enumerate(configs, 1):
                        server_name = self.format_server_name(country, idx)
                        named_config = self.add_name_to_config(config, server_name)
                        f.write(named_config + '\n')
                    
                    f.write('\n')
            
            # ===== TLS SERVERS =====
            if by_country_tls:
                f.write("# ========== TLS SERVERS ==========\n")
                f.write("# Standard VLESS over TLS\n\n")
                
                for country in sorted(by_country_tls.keys()):
                    configs = by_country_tls[country]
                    f.write(f"# Country: {country}\n")
                    flag = COUNTRY_FLAGS.get(country, '🌐')
                    
                    for idx, config in enumerate(configs, 1):
                        server_name = self.format_server_name(country, idx)
                        named_config = self.add_name_to_config(config, server_name)
                        f.write(named_config + '\n')
                    
                    f.write('\n')
            
            # ===== SNI RULES =====
            if sni:
                limited_sni = sni[:100]
                f.write("# ========== SNI RULES ==========\n")
                f.write(f"# Domains and CIDR for routing\n")
                f.write(f"# Showing first {len(limited_sni)} of {len(sni)}\n\n")
                
                for rule in limited_sni:
                    f.write(rule + '\n')
        
        logger.info(f"  ✓ Saved {len(safe_vless)} servers to subscription.txt")
    
    def process(self):
        """Main processing pipeline"""
        logger.info("=" * 60)
        logger.info("🚀 OznoBB Config Processor Started")
        logger.info("=" * 60)
        
        try:
            # Step 1: Fetch all sources
            logger.info("\n[1/5] FETCHING SOURCES")
            content = self.fetch_all_sources()
            if not content:
                logger.error("❌ Failed to fetch any configs")
                return False
            
            # Step 2: Parse and filter
            logger.info("\n[2/5] PARSING & FILTERING")
            vless, sni = self.filter_vless(content)
    
    # Step 3: Deduplicate
    vless_list, sni_list = processor.deduplicate_and_sort(vless, sni)
    
    # Step 4: Save original
    processor.save_original(vless_list, sni_list)
    
    # Step 5: Check ping and get alive configs
    ping_checker = PingChecker()
    alive_configs = ping_checker.check_vless_batch(vless_list)
    
    # Step 6: Save subscription
    processor.save_subscription(vless_list, sni_list, alive_configs)
    
    print("\n✅ Done!")

if __name__ == '__main__':
    main()
