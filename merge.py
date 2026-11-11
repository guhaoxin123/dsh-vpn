#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dsh-vpn 订阅生成器 —— 由 DSH 编写
流程：拉取多个公开订阅源 -> 解析(clash yaml / base64 v2ray) -> 去重
      -> 用 mihomo 对每个节点实测延迟 -> 超时/失败的直接剔除
      -> 按顺序编号命名 -> 输出 clash.yaml / proxies.yaml
"""
import base64, json, os, re, socket, subprocess, sys, time
import urllib.parse, urllib.request
import yaml
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    ("sunmiao", "https://sunmiao4458.github.io/free-proxy-airport/clash.yaml"),
    ("Au1rxx",  "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/clash.yaml"),
    ("Pawdroid","https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub"),
    ("dalazhi", "https://raw.githubusercontent.com/dalazhi/v2ray/main/dalazhi.yaml"),
    ("getNode", "https://raw.githubusercontent.com/a2470982985/getNode/main/clash.yaml"),
    ("free18",  "https://cdn.jsdelivr.net/gh/free18/v2ray@main/c.yaml"),
    ("anaer",   "https://raw.githubusercontent.com/anaer/Sub/main/clash.yaml"),
]
JUNK = re.compile(r"剩余|流量|到期|过期|官网|订阅|客服|更新|重置|网址|traffic|expire|official|"
                  r"官网地址|TG|telegram", re.I)
TCP_TYPES = {"ss", "vmess", "vless", "trojan", "http", "socks5", "anytls", "snell"}
UDP_TYPES = {"hysteria", "hysteria2", "tuic", "wireguard", "ssh"}
TEST_URL = "https://www.gstatic.com/generate_204"
TIMEOUT_MS = 5000
CTRL_PORT = 19090


# ---------------------------------------------------------------- 抓取解析
def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dsh-vpn/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"  ! {url} try{i+1}: {e}", file=sys.stderr)
            time.sleep(2)
    return ""


def from_clash(text):
    try:
        data = yaml.safe_load(text)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    out = list(data.get("proxies") or [])
    for p in (data.get("proxy-providers") or {}).values():
        if isinstance(p, dict) and isinstance(p.get("proxies"), list):
            out.extend(p["proxies"])
    return [p for p in out if isinstance(p, dict) and p.get("name") and p.get("server")]


def b64d(s):
    s = s.strip().replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s).decode("utf-8", "ignore")


def conv_link(link):
    try:
        if link.startswith("ss://"):
            body = link[5:].split("#")[0]
            name = urllib.parse.unquote(link.split("#", 1)[1]) if "#" in link else ""
            if "@" in body:
                userinfo, host = body.split("@", 1)
                if ":" in userinfo:
                    method, _, pwd = userinfo.partition(":")
                else:
                    method, _, pwd = b64d(userinfo).partition(":")
                host = host.split("/")[0].split("?")[0]
                host, _, port = host.rpartition(":")
                return {"name": name or host, "type": "ss", "server": host, "port": int(port),
                        "cipher": method, "password": pwd, "udp": True}
        elif link.startswith("vmess://"):
            j = json.loads(b64d(link[8:]))
            return {"name": j.get("ps") or j["add"], "type": "vmess", "server": j["add"],
                    "port": int(j["port"]), "uuid": j["id"], "alterId": int(j.get("aid", 0) or 0),
                    "cipher": "auto", "udp": True, "tls": (j.get("tls") == "tls"),
                    "servername": j.get("host") or "", "network": j.get("net", "tcp")}
        elif link.startswith("trojan://"):
            u = urllib.parse.urlparse(link)
            q = urllib.parse.parse_qs(u.query)
            return {"name": urllib.parse.unquote(u.fragment) or u.hostname, "type": "trojan",
                    "server": u.hostname, "port": u.port or 443, "password": u.username,
                    "sni": (q.get("sni") or [u.hostname])[0], "udp": True}
        elif link.startswith("vless://"):
            u = urllib.parse.urlparse(link)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            p = {"name": urllib.parse.unquote(u.fragment) or u.hostname, "type": "vless",
                 "server": u.hostname, "port": u.port or 443, "uuid": u.username,
                 "udp": True, "network": q.get("type", "tcp")}
            if q.get("security") in ("tls", "reality"):
                p["tls"] = True
                p["servername"] = q.get("sni") or u.hostname
                if q.get("fp"):
                    p["client-fingerprint"] = q["fp"]
                if q.get("security") == "reality":
                    p["reality-opts"] = {"public-key": q.get("pbk", ""), "short-id": q.get("sid", "")}
            if q.get("flow"):
                p["flow"] = q["flow"]
            if q.get("type") == "ws":
                p["ws-opts"] = {"path": q.get("path", "/"),
                                "headers": {"Host": q.get("host", "")}}
            if q.get("type") == "grpc":
                p["grpc-opts"] = {"grpc-service-name": q.get("serviceName", "")}
            return p
    except Exception:
        return None
    return None


def from_v2ray(text):
    raw = text.strip()
    if "://" not in raw[:200]:
        try:
            raw = b64d(raw)
        except Exception:
            return []
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if "://" in line:
            p = conv_link(line)
            if p:
                out.append(p)
    return out


# ---------------------------------------------------------------- 测速剔除
def tcp_ok(p, to=4):
    try:
        socket.create_connection((str(p["server"]), int(p["port"])), timeout=to).close()
        return True
    except Exception:
        return False


def start_mihomo(proxies):
    cfg = {"mixed-port": 7891, "mode": "rule", "log-level": "warn",
           "external-controller": f"127.0.0.1:{CTRL_PORT}",
           "proxies": proxies, "rules": ["MATCH,DIRECT"]}
    os.makedirs("runtime", exist_ok=True)
    with open("runtime/test-config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=4096)
    try:
        proc = subprocess.Popen(["./mihomo", "-d", "runtime", "-f", "runtime/test-config.yaml"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  ! mihomo 启动失败: {e}", file=sys.stderr)
        return None
    for _ in range(30):
        time.sleep(1)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{CTRL_PORT}/version", timeout=3).read()
            print("  mihomo API 就绪")
            return proc
        except Exception:
            if proc.poll() is not None:
                print("  ! mihomo 进程已退出", file=sys.stderr)
                return None
    proc.kill()
    return None


def delay_of(name):
    q = urllib.parse.quote(name, safe="")
    url = (f"http://127.0.0.1:{CTRL_PORT}/proxies/{q}/delay"
           f"?timeout={TIMEOUT_MS}&url={urllib.parse.quote(TEST_URL, safe='')}")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_MS / 1000 + 8) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
            return int(d.get("delay", 0)) or None
    except Exception:
        return None


def prune(proxies):
    total = len(proxies)
    proc = start_mihomo(proxies)
    alive = []
    if proc is not None:
        args = [p["name"] for p in proxies]
        with ThreadPoolExecutor(max_workers=64) as ex:
            results = list(ex.map(delay_of, args))
        for p, d in zip(proxies, results):
            if d:
                p["_delay"] = d
                alive.append(p)
        proc.kill()
        print(f"  实测延迟：{len(alive)}/{total} 可用")
        if not alive:
            print("  ! 全部超时，放弃剔除（避免生成空配置）", file=sys.stderr)
            return proxies, total
        return alive, total
    print("  ! 无 mihomo，退化为 TCP 连通性检测", file=sys.stderr)
    def check(p):
        if str(p.get("type")) in UDP_TYPES:
            return p
        return p if tcp_ok(p) else None
    with ThreadPoolExecutor(max_workers=64) as ex:
        for r in ex.map(check, proxies):
            if r:
                alive.append(r)
    print(f"  TCP 检测：{len(alive)}/{total} 可用")
    return (alive or proxies), total



# ---------------------------------------------------------------- 地区分组
REGION_DEFS = [
    ("HK", ["\U0001F1ED\U0001F1F0", "香港", "Hong Kong", "HKG", "HK"]),
    ("SG", ["\U0001F1F8\U0001F1EC", "新加坡", "狮城", "Singapore", "SGP", "SG"]),
    ("JP", ["\U0001F1EF\U0001F1F5", "日本", "东京", "大阪", "Japan", "Tokyo", "Osaka", "JPN", "JP"]),
    ("US", ["\U0001F1FA\U0001F1F8", "美国", "洛杉矶", "圣何塞", "西雅图", "芝加哥", "达拉斯", "纽约",
            "United States", "USA", "US"]),
    ("TW", ["\U0001F1F9\U0001F1FC", "台湾", "台北", "Taiwan", "TPE", "TW"]),
    ("KR", ["\U0001F1F0\U0001F1F7", "韩国", "首尔", "Korea", "Seoul", "ICN", "KR"]),
    ("UK", ["\U0001F1EC\U0001F1E7", "英国", "伦敦", "Britain", "London", "GB", "UK"]),
    ("DE", ["\U0001F1E9\U0001F1EA", "德国", "法兰克福", "Germany", "Frankfurt", "DE"]),
    ("FR", ["\U0001F1EB\U0001F1F7", "法国", "巴黎", "France", "Paris", "FR"]),
    ("CA", ["\U0001F1E8\U0001F1E6", "加拿大", "多伦多", "Canada", "Toronto", "CA"]),
    ("AU", ["\U0001F1E6\U0001F1FA", "澳大利亚", "澳洲", "悉尼", "Australia", "Sydney", "AU"]),
    ("NL", ["\U0001F1F3\U0001F1F1", "荷兰", "阿姆斯特丹", "Netherlands", "NL"]),
    ("RU", ["\U0001F1F7\U0001F1FA", "俄罗斯", "莫斯科", "Russia", "RU"]),
    ("IN", ["\U0001F1EE\U0001F1F3", "印度", "India", "IN"]),
    ("TR", ["\U0001F1F9\U0001F1F7", "土耳其", "Turkey", "TR"]),
]


def _build_pattern(words):
    parts = []
    for w in words:
        if w.isascii():
            parts.append(r"\b" + re.escape(w) + r"\b")
        else:
            parts.append(re.escape(w))
    return re.compile("|".join(parts), re.I)


REGION_PATTERNS = [(name, _build_pattern(words)) for name, words in REGION_DEFS]


def detect_region(name):
    for gname, pat in REGION_PATTERNS:
        if pat.search(name):
            return gname
    return "OTHER"


# ---------------------------------------------------------------- 主流程
def main():
    all_px, seen = [], set()
    for tag, url in SOURCES:
        text = fetch(url)
        if not text.strip():
            print(f"[skip] {tag}: 空内容")
            continue
        px = from_clash(text) or from_v2ray(text)
        kept = 0
        for p in px:
            key = (str(p.get("type")), str(p.get("server")), str(p.get("port")))
            if key in seen or JUNK.search(str(p.get("name", ""))):
                continue
            seen.add(key)
            all_px.append(p)
            kept += 1
        print(f"[ok] {tag}: 解析 {len(px)}，去重保留 {kept}")

    print(f"合并后 {len(all_px)} 个节点，开始逐个测速…")
    alive, total = prune(all_px)

    alive.sort(key=lambda p: p.get("_delay") or 9999)
    for i, p in enumerate(alive, 1):
        old = str(p.get("name", "")).strip()[:40]
        p.pop("_delay", None)
        p["name"] = f"{i:03d} {old}" if old else f"{i:03d}"

    buckets = {}
    for p in alive:
        buckets.setdefault(detect_region(p["name"]), []).append(p["name"])

    region_groups = []
    for code, _ in REGION_DEFS:
        if buckets.get(code):
            region_groups.append({"name": code, "type": "select", "proxies": buckets[code]})
    if buckets.get("OTHER"):
        region_groups.append({"name": "OTHER", "type": "select", "proxies": buckets["OTHER"]})
    for g in region_groups:
        print(f"  分组 {g['name']}: {len(g['proxies'])} 个节点")

    all_names = [p["name"] for p in alive]
    cfg = {
        "mixed-port": 7890, "allow-lan": False, "mode": "rule", "log-level": "info",
        "ipv6": False, "external-controller": "127.0.0.1:9090",
        "profile": {"store-selected": True, "store-fake-ip": True},
        "dns": {"enable": True, "ipv6": False, "enhanced-mode": "fake-ip",
                "fake-ip-range": "198.18.0.1/16",
                "default-nameserver": ["223.5.5.5", "119.29.29.29"],
                "nameserver": ["223.5.5.5", "119.29.29.29", "https://doh.pub/dns-query"],
                "fallback": ["tls://8.8.4.4:853", "tls://1.1.1.1:853"],
                "fallback-filter": {"geoip": True, "geoip-code": "CN"}},
        "proxies": alive,
        "proxy-groups": [
            {"name": "🚀 节点选择", "type": "select",
             "proxies": [g["name"] for g in region_groups] + ["♻️ 自动选择", "🔯 故障转移", "DIRECT"]},
        ] + region_groups + [
            {"name": "♻️ 自动选择", "type": "url-test", "proxies": all_names,
             "url": TEST_URL, "interval": 300, "tolerance": 50},
            {"name": "🔯 故障转移", "type": "fallback", "proxies": all_names,
             "url": TEST_URL, "interval": 300},
        ],
        "rules": ["DOMAIN-SUFFIX,cn,DIRECT", "DOMAIN-KEYWORD,-cn,DIRECT",
                  "GEOIP,private,DIRECT,no-resolve", "GEOIP,CN,DIRECT", "MATCH,🚀 节点选择"],
    }
    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=4096)
    with open("proxies.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"proxies": alive}, f, allow_unicode=True, sort_keys=False, width=4096)
    print(f"完成：原始 {total} -> 存活 {len(alive)}，已写出 clash.yaml / proxies.yaml")


# ---- 补充国家：追加进上面的列表，然后重建匹配表 ----
REGION_DEFS.extend([
    ("IT", ["🇮🇹", "意大利", "Italy", "ITA"]),
    ("ES", ["🇪🇸", "西班牙", "Spain", "ESP"]),
    ("CH", ["🇨🇭", "瑞士", "Switzerland", "CHE"]),
    ("SE", ["🇸🇪", "瑞典", "Sweden", "SWE"]),
    ("NO", ["🇳🇴", "挪威", "Norway", "NOR"]),
    ("DK", ["🇩🇰", "丹麦", "Denmark", "DNK"]),
    ("FI", ["🇫🇮", "芬兰", "Finland", "FIN"]),
    ("IE", ["🇮🇪", "爱尔兰", "Ireland", "IRL"]),
    ("PT", ["🇵🇹", "葡萄牙", "Portugal", "PRT"]),
    ("PL", ["🇵🇱", "波兰", "Poland", "POL"]),
    ("CZ", ["🇨🇿", "捷克", "Czech", "CZE"]),
    ("AT", ["🇦🇹", "奥地利", "Austria", "AUT"]),
    ("BE", ["🇧🇪", "比利时", "Belgium", "BEL"]),
    ("GR", ["🇬🇷", "希腊", "Greece", "GRC"]),
    ("HU", ["🇭🇺", "匈牙利", "Hungary", "HUN"]),
    ("RO", ["🇷🇴", "罗马尼亚", "Romania", "ROU"]),
    ("BG", ["🇧🇬", "保加利亚", "Bulgaria", "BGR"]),
    ("UA", ["🇺🇦", "乌克兰", "Ukraine", "UKR"]),
    ("RS", ["🇷🇸", "塞尔维亚", "Serbia", "SRB"]),
    ("HR", ["🇭🇷", "克罗地亚", "Croatia", "HRV"]),
    ("SK", ["🇸🇰", "斯洛伐克", "Slovakia", "SVK"]),
    ("LT", ["🇱🇹", "立陶宛", "Lithuania", "LTU"]),
    ("LV", ["🇱🇻", "拉脱维亚", "Latvia", "LVA"]),
    ("EE", ["🇪🇪", "爱沙尼亚", "Estonia", "EST"]),
    ("MD", ["🇲🇩", "摩尔多瓦", "Moldova", "MDA"]),
    ("BR", ["🇧🇷", "巴西", "Brazil", "BRA"]),
    ("AR", ["🇦🇷", "阿根廷", "Argentina", "ARG"]),
    ("CL", ["🇨🇱", "智利", "Chile", "CHL"]),
    ("MX", ["🇲🇽", "墨西哥", "Mexico", "MEX"]),
    ("CO", ["🇨🇴", "哥伦比亚", "Colombia", "COL"]),
    ("VN", ["🇻🇳", "越南", "Vietnam", "VNM"]),
    ("MY", ["🇲🇾", "马来西亚", "Malaysia", "MYS"]),
    ("TH", ["🇹🇭", "泰国", "Thailand", "THA"]),
    ("PH", ["🇵🇭", "菲律宾", "Philippines", "PHL"]),
    ("ID", ["🇮🇩", "印尼", "印度尼西亚", "Indonesia", "IDN"]),
    ("KH", ["🇰🇭", "柬埔寨", "Cambodia", "KHM"]),
    ("NP", ["🇳🇵", "尼泊尔", "Nepal", "NPL"]),
    ("AE", ["🇦🇪", "阿联酋", "迪拜", "UAE", "Dubai"]),
    ("SA", ["🇸🇦", "沙特", "Saudi"]),
    ("IL", ["🇮🇱", "以色列", "Israel", "ISR"]),
    ("IR", ["🇮🇷", "伊朗", "Iran", "IRN"]),
    ("PK", ["🇵🇰", "巴基斯坦", "Pakistan", "PAK"]),
    ("BD", ["🇧🇩", "孟加拉", "Bangladesh", "BGD"]),
    ("LK", ["🇱🇰", "斯里兰卡", "Sri Lanka", "LKA"]),
    ("KZ", ["🇰🇿", "哈萨克", "Kazakh", "KAZ"]),
    ("ZA", ["🇿🇦", "南非", "South Africa", "ZAF"]),
    ("NG", ["🇳🇬", "尼日利亚", "Nigeria", "NGA"]),
    ("EG", ["🇪🇬", "埃及", "Egypt", "EGY"]),
    ("MA", ["🇲🇦", "摩洛哥", "Morocco", "MAR"]),
    ("NZ", ["🇳🇿", "新西兰", "New Zealand", "NZL"]),
])

REGION_PATTERNS = [(name, _build_pattern(words)) for name, words in REGION_DEFS]


if __name__ == "__main__":
    main()
