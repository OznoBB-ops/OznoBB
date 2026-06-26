"""CheckHost API client for ping verification."""

import requests
import time
import logging
from typing import Optional, Dict, Any, List
from constants import (
    CHECK_HOST_API,
    CHECK_HOST_RESULTS,
    RUSSIAN_NODES,
    PING_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY
)

logger = logging.getLogger(__name__)


class CheckHost:
    """Client for check-host.net API."""
    
    def __init__(self, timeout: int = PING_TIMEOUT):
        """
        Initialize CheckHost client.
        
        Args:
            timeout: Timeout for requests in seconds
        """
        self.api_url = CHECK_HOST_API
        self.results_url = CHECK_HOST_RESULTS
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OznoBB/1.0'
        })
    
    def ping(self, host: str) -> Optional[Dict[str, Any]]:
        """
        Perform a ping check from Russian nodes.
        
        Args:
            host: Hostname or IP address to ping
            
        Returns:
            Dictionary with check results or None if failed
        """
        check_id = self._start_check(host)
        
        if not check_id:
            logger.warning(f"Failed to start ping check for {host}")
            return None
        
        # Wait for results
        results = self._wait_for_results(check_id)
        return results
    
    def _start_check(self, host: str) -> Optional[str]:
        """
        Start a ping check on check-host.net.
        
        Args:
            host: Hostname or IP to check
            
        Returns:
            Check ID or None if request failed
        """
        params = {
            'host': host,
            'node[]': RUSSIAN_NODES  # Array-style parameter
        }
        
        try:
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            check_id = data.get('check_id')
            
            if check_id:
                logger.info(f"Started check {check_id} for {host}")
            else:
                logger.warning(f"No check_id in response: {data}")
            
            return check_id
            
        except requests.RequestException as e:
            logger.error(f"Failed to start check for {host}: {e}")
            return None
    
    def _wait_for_results(self, check_id: str, retries: int = MAX_RETRIES) -> Optional[Dict[str, Any]]:
        """
        Wait for ping check results.
        
        Args:
            check_id: Check ID from initial request
            retries: Number of retry attempts
            
        Returns:
            Results dictionary or None if check didn't complete
        """
        for attempt in range(retries):
            time.sleep(RETRY_DELAY)
            
            try:
                # Correct parameter name: id, not check_id
                response = self.session.get(
                    self.results_url,
                    params={'id': check_id, 'json': ''},
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Check if results are ready
                if data and any(data.values()):
                    logger.info(f"Results received for check {check_id}")
                    return self._parse_results(data)
                
                logger.debug(f"Check {check_id} not ready yet (attempt {attempt + 1}/{retries})")
                
            except requests.RequestException as e:
                logger.warning(f"Error fetching results for check {check_id}: {e}")
                continue
        
        logger.warning(f"Failed to get results for check {check_id} after {retries} attempts")
        return None
    
    def _parse_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse check results.
        
        Args:
            data: Raw results from API
            
        Returns:
            Parsed results dictionary
        """
        parsed = {
            'nodes_checked': len(data),
            'nodes_accessible': 0,
            'latencies': [],
            'nodes': {}
        }
        
        for node, result in data.items():
            if result and isinstance(result, list) and len(result) > 0:
                # Result is in milliseconds, keep as is
                latency = result[0][0] if result[0] else None
                
                if latency:
                    parsed['nodes_accessible'] += 1
                    parsed['latencies'].append(latency)
                    parsed['nodes'][node] = {'latency_ms': latency, 'accessible': True}
                else:
                    parsed['nodes'][node] = {'latency_ms': None, 'accessible': False}
            else:
                parsed['nodes'][node] = {'latency_ms': None, 'accessible': False}
        
        if parsed['latencies']:
            parsed['avg_latency_ms'] = sum(parsed['latencies']) / len(parsed['latencies'])
        
        return parsed
    
    def __del__(self):
        """Cleanup session on object destruction."""
        try:
            self.session.close()
        except Exception:
            pass
