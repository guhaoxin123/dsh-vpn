#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取多个订阅源 -> 合并去重 -> 按顺序编号重命名 -> 输出 clash.yaml / proxies.yaml"""
import base64, json, re, sys, time, urllib.parse, urllib.request
import yaml

SOURCES = [
    ("sunmiao", "https://sunmiao4458.github.io/free-proxy-airport/clash.yaml"),
    ("Au1rxx",  "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/clash.yaml"),
    ("Pawdroid","https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub"),
    ("dalazhi", "https://raw.githubusercontent.com/dalazhi/v2ray/main/dalazhi.yaml"),
    ("getNode", "https://raw.githubusercontent.com/a2470982985/getNode/main/clash.yaml"),
    ("free18",  "https://cdn.jsdelivr.net/gh/free18/v2ray@main/c.yaml"),
    ("anaer",   "https://raw.githubusercontent.com/anaer/Sub/main/clash.yaml"),
]
JUNK = re.compile(r"剩余|流量|到期|过期|官网|订阅|客服|更新|重置|网址|traffic|expire|official", re.I)

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "clash-merge/1.0"})
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
    # 有些源自身也是 provider 结构，尝试展开
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
                method, _, pwd = b64d(userinfo).partition(":") if ":" not in userinfo else userinfo.partition(":")
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
                p["ws-opts"] = {"path": q.get("path", "/"), "headers": {"Host": q.get("host", "")}}
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

def main():
    all_px, seen = [], set()
    for tag, url in SOURCES:
        text = fetch(url)
        if not text.strip():
            print(f"[skip] {tag}: 空内容")
            continue
        px = from_clash(text)
        if not px:
            px = from_v2ray(text)
        n0 = len(px)
        kept = 0
        for p in px:
            key = (str(p.get("type")), str(p.get("server")), str(p.get("port")))
            if key in seen or JUNK.search(str(p.get("name", ""))):
                continue
            seen.add(key)
            all_px.append(p)
            kept += 1
        print(f"[ok] {tag}: 解析 {n0}，去重保留 {kept}")

    for i, p in enumerate(all_px, 1):
        old = str(p.get("name", "")).strip()[:40]
        p["name"] = f"{i:03d} {old}" if old else f"{i:03d}"
    print(f"总计 {len(all_px)} 个节点")

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
        "proxies": all_px,
        "proxy-groups": [
            {"name": "🚀 节点选择", "type": "select", "proxies": ["♻️ 自动选择", "🔯 故障转移", "DIRECT"]},
            {"name": "♻️ 自动选择", "type": "url-test", "proxies": [p["name"] for p in all_px],
             "url": "https://www.gstatic.com/generate_204", "interval": 300, "tolerance": 50},
            {"name": "🔯 故障转移", "type": "fallback", "proxies": [p["name"] for p in all_px],
             "url": "https://www.gstatic.com/generate_204", "interval": 300},
        ],
        "rules": ["DOMAIN-SUFFIX,cn,DIRECT", "DOMAIN-KEYWORD,-cn,DIRECT",
                  "GEOIP,private,DIRECT,no-resolve", "GEOIP,CN,DIRECT", "MATCH,🚀 节点选择"],
    }
    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=4096)
    with open("proxies.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"proxies": all_px}, f, allow_unicode=True, sort_keys=False, width=4096)
    print("已生成 clash.yaml / proxies.yaml")

if __name__ == "__main__":
    main()
