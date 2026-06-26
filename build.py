"""Build script for OznoBB with ping verification."""

import socket
import json
import ipaddress
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote
from scripts.check_ping import CheckHost
from scripts.constants import CC_RUSSIA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def flag(cc: str) -> str:
    """
    Convert country code to flag emoji.
    
    Args:
        cc: Two-letter country code (e.g., 'RU', 'UA')
        
    Returns:
        Flag emoji or default flag if invalid
    """
    if not cc or len(cc) != 2:
        return "🏴"
    
    try:
        # Convert country code to regional indicator symbols
        return chr(0x1F1E6 + ord(cc[0].upper()) - ord('A')) + \
               chr(0x1F1E6 + ord(cc[1].upper()) - ord('A'))
    except (ValueError, OverflowError):
        return "🏴"


def resolve(hostname: str) -> Optional[str]:
    """
    Resolve hostname to IP address.
    
    Args:
        hostname: Domain name to resolve
        
    Returns:
        IP address as string or None if resolution fails
    """
    try:
        # Use socket.getaddrinfo instead of deprecated inet_aton
        ip = socket.getaddrinfo(hostname, None)[0][4][0]
        # Validate it's a proper IP address
        ipaddress.ip_address(ip)
        return ip
    except (socket.gaierror, ValueError, ipaddress.AddressValueError) as e:
        logger.warning(f"Failed to resolve {hostname}: {e}")
        return None


def encode_url(url: str) -> str:
    """
    Properly encode URL for API requests.
    
    Args:
        url: URL to encode
        
    Returns:
        URL-encoded string
    """
    return quote(url, safe='/:?&=')


def ping_from_russia(host: str, check_host: CheckHost) -> Optional[Dict[str, Any]]:
    """
    Check if host is accessible from Russian nodes.
    
    Args:
        host: Hostname or IP to ping
        check_host: CheckHost API client
        
    Returns:
        Dictionary with ping results or None if all attempts failed
    """
    try:
        # Resolve hostname to IP if needed
        ip = resolve(host)
        if not ip:
            logger.warning(f"Could not resolve host: {host}")
            return None
        
        # Perform ping check
        result = check_host.ping(ip)
        
        if result:
            logger.info(f"Ping check successful for {host}: {result}")
            return result
        else:
            logger.warning(f"Ping check returned no results for {host}")
            return None
            
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return None


def build_status_message(host: str, is_accessible: bool) -> str:
    """
    Build a status message with flag and accessibility info.
    
    Args:
        host: Hostname being checked
        is_accessible: Whether host is accessible from Russia
        
    Returns:
        Formatted status message
    """
    flag_emoji = flag(CC_RUSSIA)
    status = "✅ Accessible" if is_accessible else "❌ Not accessible"
    return f"{flag_emoji} {host}: {status}"


def main():
    """Main build function."""
    hosts_to_check = [
        "example.com",
        "test.org",
    ]
    
    check_host = CheckHost()
    results = {}
    
    for host in hosts_to_check:
        result = ping_from_russia(host, check_host)
        is_accessible = result is not None
        results[host] = {
            "accessible": is_accessible,
            "result": result
        }
        logger.info(build_status_message(host, is_accessible))
    
    # Save results to JSON
    with open("build_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Build complete. Results saved to build_results.json")


if __name__ == "__main__":
    main()
