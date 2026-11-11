# dsh-vpn

由 **DSH** 编写并自动维护，每 90 分钟更新一次。

抓取 19 个公开免费订阅源，逐个节点实测延迟，超过 2 秒的直接删除，剩下的按顺序编号并按地区分组。

## 文件

- `clash.yaml` — Clash / Mihomo 配置
- `surfboard.conf` — Surfboard / Surge 配置
- `proxies.yaml` — 纯节点列表，可当 proxy-provider

## 分组

按地区自动分组（约 60 个国家/地区，名字里没写地区的按 IP 归属地识别，识别不出的进 `OTHER`），
外加 `🚀 节点选择` / `♻️ 自动选择` / `🔯 故障转移`。规则和以前一样：国内直连，其余走节点。

Surfboard 只支持 ss / vmess / trojan / http / socks5，其它协议（vless、hysteria2、tuic 等）会被跳过。

## 地址（raw 被墙，用镜像）

```
https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/clash.yaml
https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/surfboard.conf
```

备用：把 `https://ghfast.top/` 换成 `https://gh-proxy.com/` 或
`https://fastly.jsdelivr.net/gh/guhaoxin123/dsh-vpn@main/`。

## 用法

Clash：配置 → 新建 → 从 URL 导入 → 自动更新间隔 60 分钟。
Surfboard：配置 → 从 URL 导入 → 填 surfboard.conf 地址。

节点来自第三方公开订阅，可用性不保证。
