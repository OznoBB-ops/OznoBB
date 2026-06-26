#!/usr/bin/env python3
"""
Check ping using check-host.net API from Russian nodes
"""

import requests
import json
import time
from typing import Dict, List
from constants import RUSSIAN_NODES, PING_TIMEOUT

class PingChecker:
    def __init__(self):
        self.api_url = 'https://check-host.net/check-ping'
        self.results_url = 'https://check-host.net/check-ping'
        
    def get_server_host(self, vless_config: str) -> str:
        """Extract hostname/IP from VLESS config"""
        # Format: vless://uuid@host:port?params
        try:
            import re
            match = re.search(r'@([^:]+):', vless_config)
            if match:
                return match.group(1)
        except:
            pass
        return None
    
    def check_ping_russia(self, host: str) -> Dict:
        """
        Check ping from Russian nodes via check-host.net
        Returns: {'status': 'ok', 'check_id': '...', 'results': {...}}
        """
        try:
            # Start check
            params = {
                'host': host,
                'node': ','.join(RUSSIAN_NODES)  # Only Russian nodes
            }
            
            response = requests.post(
                self.api_url,
                data=params,
                timeout=PING_TIMEOUT
            )
            response.raise_for_status()
            check_data = response.json()
            
            if check_data.get('ok'):
                check_id = list(check_data.get('check_id', {}).keys())[0]
                return {'status': 'started', 'check_id': check_id, 'host': host}
            
        except Exception as e:
            print(f"  ❌ Ping check failed for {host}: {e}")
        
        return {'status': 'failed', 'host': host}
    
    def get_ping_results(self, check_id: str) -> Dict:
        """Get ping results after check completes"""
        try:
            response = requests.get(
                f'{self.results_url}?check_id={check_id}&json',
                timeout=PING_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  ❌ Failed to get results for {check_id}: {e}")
            return {}
    
    def is_alive(self, results: Dict) -> bool:
        """Check if server responded to any Russian node"""
        try:
            for node, node_results in results.items():
                if node_results and isinstance(node_results, list):
                    for result in node_results:
                        if result and result.get('time'):
                            return True
        except:
            pass
        return False
    
    def get_avg_ping(self, results: Dict) -> int:
        """Calculate average ping from Russian nodes"""
        pings = []
        try:
            for node, node_results in results.items():
                if node_results and isinstance(node_results, list):
                    for result in node_results:
                        if result and result.get('time'):
                            pings.append(float(result['time']) * 1000)  # Convert to ms
        except:
            pass
        
        return int(sum(pings) / len(pings)) if pings else 999
    
    def check_vless_batch(self, vless_configs: List[str]) -> Dict[str, bool]:
        """Check all VLESS configs (simplified - async checks)"""
        print("🔗 Checking ping from Russian nodes...")
        
        alive_configs = {}
        checks = {}
        
        # Start all checks
        for i, config in enumerate(vless_configs[:50]):  # Limit to 50 per run
            host = self.get_server_host(config)
            if host:
                result = self.check_ping_russia(host)
                if result['status'] == 'started':
                    checks[result['check_id']] = config
                    print(f"  ⏳ [{i+1}] Started check for {host}")
            time.sleep(0.5)
        
        # Wait and collect results
        print("  ⏳ Waiting for results (up to 30 seconds)...")
        time.sleep(20)
        
        for check_id, config in checks.items():
            results = self.get_ping_results(check_id)
            is_alive = self.is_alive(results)
            alive_configs[config] = is_alive
            
            if is_alive:
                ping = self.get_avg_ping(results)
                print(f"    ✓ {config[:50]}... ({ping}ms)")
            else:
                print(f"    ✗ {config[:50]}... (dead)")
            
            time.sleep(0.3)
        
        return alive_configs
