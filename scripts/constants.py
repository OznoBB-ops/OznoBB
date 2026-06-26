"""Configuration constants for OznoBB scripts."""

# Check-host API endpoints
CHECK_HOST_API = "https://check-host.net/api/check"
CHECK_HOST_RESULTS = "https://check-host.net/check-result"

# Russian nodes for ping checks
RUSSIAN_NODES = [
    "ru1.node.check-host.net",
    "ru2.node.check-host.net",
    "ru3.node.check-host.net"
]

# Timeout settings (in seconds)
PING_TIMEOUT = 20
CHECK_TIMEOUT = 30

# Retry settings
MAX_RETRIES = 6
RETRY_DELAY = 2

# Country codes
CC_RUSSIA = "RU"
CC_UKRAINE = "UA"
CC_BELARUS = "BY"
