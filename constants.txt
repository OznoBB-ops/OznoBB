# Исходные ссылки
PRIMARY_SOURCES = {
    'zieng2_gitverse': 'https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt',
    'igareck_vless': 'https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt',
    'igareck_ss': 'https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt',
    'igareck_white_cidr': 'https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt',
    'igareck_white_sni': 'https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt',
}

# Зеркала zieng2
MIRRORS_ZIENG2 = [
    'https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt',
    'https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt',
    'https://gitlab.com/zieng2/wl/raw/main/vless_universal.txt',
    'https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt',
    'https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt',
]

# Зеркала igareck (7 на каждый файл)
MIRRORS_IGARECK = {
    'vless': [
        'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt',
        'https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS.txt',
        'https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_VLESS_RUS.txt',
        'https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_VLESS_RUS.txt',
        'https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/BLACK_VLESS_RUS.txt',
        'https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/BLACK_VLESS_RUS.txt',
        'https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt',
    ],
    'ss': [
        'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt',
        'https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_SS%2BAll_RUS.txt',
        'https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_SS%2BAll_RUS.txt',
        'https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_SS%2BAll_RUS.txt',
        'https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/BLACK_SS%2BAll_RUS.txt',
        'https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/BLACK_SS%2BAll_RUS.txt',
        'https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt',
    ],
    'cidr': [
        'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt',
        'https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-CIDR-RU-all.txt',
        'https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-CIDR-RU-all.txt',
        'https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-CIDR-RU-all.txt',
        'https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/WHITE-CIDR-RU-all.txt',
        'https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/WHITE-CIDR-RU-all.txt',
        'https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt',
    ],
    'sni': [
        'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt',
        'https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-SNI-RU-all.txt',
        'https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-SNI-RU-all.txt',
        'https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-SNI-RU-all.txt',
        'https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/WHITE-SNI-RU-all.txt',
        'https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/WHITE-SNI-RU-all.txt',
        'https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt',
    ],
}

# Коды стран и флаги
COUNTRY_FLAGS = {
    'RU': '🇷🇺',
    'DE': '🇩🇪',
    'FI': '🇫🇮',
    'NL': '🇳🇱',
    'GB': '🇬🇧',
    'FR': '🇫🇷',
    'US': '🇺🇸',
    'CA': '🇨🇦',
    'JP': '🇯🇵',
    'SG': '🇸🇬',
}

# Ноды check-host.net в России
RUSSIAN_NODES = [
    'ru1.node.check-host.net',
    'ru2.node.check-host.net',
    'ru3.node.check-host.net',
]

# Таймауты
FETCH_TIMEOUT = 10
PING_TIMEOUT = 30
PING_CHECK_ID = 'https://check-host.net/check-ping'
