#!/usr/bin/env python3
import re, urllib.request, json, socket, time, concurrent.futures

MIRRORS = [
    {"name": "zieng2/vless_universal.txt", "urls": [
        "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
        "https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt",
        "https://gitlab.com/zieng2/wl/raw/main/vless_universal.txt",
        "https://hub.mos.ru/zieng2/wl/raw/main/list_universal.txt",
        "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt",
    ]},
    {"name": "igareck/BLACK_VLESS_RUS.txt", "urls": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS.txt",
        "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS.txt",
        "https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_VLESS_RUS.txt",
        "https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_VLESS_RUS.txt",
        "https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/BLACK_VLESS_RUS.txt",
        "https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/BLACK_VLESS_RUS.txt",
        "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    ]},
    {"name": "igareck/BLACK_SS+All_RUS.txt", "urls": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_SS%2BAll_RUS.txt",
        "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_SS%2BAll_RUS.txt",
        "https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_SS%2BAll_RUS.txt",
        "https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/BLACK_SS%2BAll_RUS.txt",
        "https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/BLACK_SS%2BAll_RUS.txt",
        "https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/BLACK_SS%2BAll_RUS.txt",
        "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    ]},
    {"name": "igareck/WHITE-CIDR-RU-all.txt", "urls": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-all.txt",
        "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-CIDR-RU-all.txt",
        "https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-CIDR-RU-all.txt",
        "https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-CIDR-RU-all.txt",
        "https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/WHITE-CIDR-RU-all.txt",
        "https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/WHITE-CIDR-RU-all.txt",
        "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    ]},
    {"name": "igareck/WHITE-SNI-RU-all.txt", "urls": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-SNI-RU-all.txt",
        "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-SNI-RU-all.txt",
        "https://codeberg.org/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-SNI-RU-all.txt",
        "https://gitea.com/igareck/vpn-configs-for-russia/raw/branch/main/WHITE-SNI-RU-all.txt",
        "https://git.sr.ht/~igareck/vpn-configs-for-russia/blob/main/WHITE-SNI-RU-all.txt",
        "https://bitbucket.org/igareck/vpn-configs-for-russia/raw/main/WHITE-SNI-RU-all.txt",
        "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    ]},
]

OUT_CHECKED = "subscription.txt"
OUT_ORIGINAL = "original.txt"
GEO_TIMEOUT = 4
PING_TIMEOUT = 15
RU_NODES = ["ru1.node.check-host.net", "ru2.node.check-host.net", "ru3.node.check-host.net"]
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def flag(cc):
    if not cc or len(cc) != 2:
        return "🏴‍☠️"
    return chr(ord(cc[0].upper()) + 127397) + chr(ord(cc[1].upper()) + 127397)

def fetch_with_fallback(entry):
    name = entry["name"]
    for url in entry["urls"]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    data = r.read().decode("utf-8", errors="ignore")
                    if data.strip():
                        print(f"  OK {name} from {url}")
                        return data
        except Exception as e:
            print(f"  FAIL {name} {url}: {e}")
    print(f"  ALL MIRRORS FAILED for {name}")
    return ""

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

URI_RE = re.compile(r"^[a-z]+://[^@]*@([^:/#\s]+):(\d+)", re.I)

def parse_target(line):
    m = URI_RE.match(line.strip())
    return (m.group(1), int(m.group(2))) if m else None

def is_vless(line):
    return line.strip().lower().startswith("vless://")

def is_reality(line):
    return "security=reality" in line.lower()

def is_safe(line):
    s = line.lower()
    if "security=reality" in s:
        return True
    if "security=tls" in s:
        if "insecure=1" in s or "allowinsecure=1" in s:
            return False
        return True
    if "security=none" in s:
        return False
    if "insecure=1" in s or "allowinsecure=1" in s:
        return False
    return True

def resolve(host):
    try:
        socket.inet_aton(host)
        return host
    except OSError:
        pass
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None

def geo_country(ip):
    if not ip:
        return None
    try:
        data = api_get(f"https://ipwho.is/{ip}")
        cc = data.get("country_code")
        if cc and len(cc) == 2:
            return cc.upper()
    except Exception as e:
        print(f"geo fail {ip}: {e}")
    return None

def ping_from_russia(host):
    try:
        nodes_param = "&".join(f"node[]={n}" for n in RU_NODES)
        url = f"https://api.check-host.net/check-ping?host={host}&max_nodes=3&{nodes_param}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            start = json.loads(r.read().decode("utf-8"))
        request_id = start.get("request_id")
        if not request_id:
            return None
        result_url = f"https://api.check-host.net/check-result/{request_id}"
        for _ in range(6):
            time.sleep(3)
            try:
                result = api_get(result_url)
                pings = []
                for node_data in result.values():
                    if node_data and isinstance(node_data, list):
                        for packet in node_data:
                            if isinstance(packet, list) and len(packet) >= 2 and packet[1] is not None:
                                pings.append(packet[1])
                if pings:
                    return int(sum(pings) / len(pings))
            except Exception:
                continue
        return None
    except Exception as e:
        print(f"ping fail {host}: {e}")
        return None

def rename_checked(line, cc, num):
    line = line.strip()
    if not line or line.startswith("#"):
        return line
    base = re.sub(r"#.*$", "", line)
    f = flag(cc)
    tag = f"{f}{cc or '??'}#{num}"
    return f"{base}#{tag}"

def main():
    print("=== Fetching sources with fallback ===")
    all_lines = []
    for entry in MIRRORS:
        data = fetch_with_fallback(entry)
        if data:
            all_lines.extend(data.splitlines())

    seen = set()
    unique = []
    for l in all_lines:
        s = l.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        unique.append(s)

    vless_and_rules = []
    removed_non_vless = 0
    for line in unique:
        if is_vless(line) or not parse_target(line):
            vless_and_rules.append(line)
        else:
            removed_non_vless += 1
    print(f"Filter 1: {len(vless_and_rules)} VLESS+rules kept, {removed_non_vless} non-VLESS removed")

    safe_vless_and_rules = []
    removed_unsafe = 0
    for line in vless_and_rules:
        if not parse_target(line):
            safe_vless_and_rules.append(line)
        elif is_safe(line):
            safe_vless_and_rules.append(line)
        else:
            removed_unsafe += 1
    print(f"Filter 2: {len(safe_vless_and_rules)} safe kept, {removed_unsafe} unsafe removed")

    with open(OUT_ORIGINAL, "w", encoding="utf-8") as f:
        for line in safe_vless_and_rules:
            f.write(line + "\n")
    print(f"Original: {len(safe_vless_and_rules)} lines -> {OUT_ORIGINAL}")

    servers = []
    other = []
    for line in safe_vless_and_rules:
        if parse_target(line):
            servers.append(line)
        else:
            other.append(line)
    print(f"Checking {len(servers)} VLESS servers, {len(other)} rules")

    def job(line):
        t = parse_target(line)
        host = t[0]
        ip = resolve(host)
        cc = geo_country(ip)
        ms = ping_from_russia(host)
        reality = is_reality(line)
        return line, cc, ms, reality

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(job, l): l for l in servers}
        done = 0
        total = len(futs)
        for f in concurrent.futures.as_completed(futs):
            done += 1
            r = f.result()
            results.append(r)
            if done % 20 == 0:
                print(f"progress: {done}/{total}")

    alive = [r for r in results if r[2] is not None]
    dead_count = len(results) - len(alive)
    print(f"Filter 3: {len(alive)} alive, {dead_count} dead removed")

    alive.sort(key=lambda x: (0 if x[3] else 1, x[2], x[0]))

    country_counters = {}
    numbered = []
    for line, cc, ms, reality in alive:
        cc_key = cc or "??"
        if cc_key not in country_counters:
            country_counters[cc_key] = 0
        country_counters[cc_key] += 1
        numbered.append((line, cc, country_counters[cc_key]))

    for line in other:
        numbered.append((line, None, None))

    with open(OUT_CHECKED, "w", encoding="utf-8") as f:
        for line, cc, num in numbered:
            if num is not None:
                f.write(rename_checked(line, cc, num) + "\n")
            else:
                f.write(line + "\n")
    print(f"Checked: {len(numbered)} lines -> {OUT_CHECKED}")

if __name__ == "__main__":
    main()