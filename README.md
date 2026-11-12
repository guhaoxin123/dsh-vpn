# dsh-vpn

自动维护的免费节点订阅，每 90 分钟更新一次。由 **DSH** 编写和维护。

抓取 19 个公开订阅源，逐个节点实测延迟，超过 2 秒的直接删除，剩下的按延迟排序编号，并按地区分组。

## 订阅地址

raw 国内被墙，地址前面统一加了加速镜像 `https://ghfast.top/`。

| 用途 | 完整版 | 极速版（延迟 < 200ms） |
| --- | --- | --- |
| Clash / Mihomo | `clash.yaml` | `fast/clash.yaml` |
| Surfboard / Surge | `surfboard.conf` | `fast/surfboard.conf` |
| v2rayNG / v2rayN / NekoBox | `v2rayng.txt` | `fast/v2rayng.txt` |

拼在 `https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/` 后面即可，例如：

```
https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/clash.yaml
https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/fast/clash.yaml
```

镜像连不上时，可以把 `https://ghfast.top/` 换成 `https://gh-proxy.com/`，
或直接用 `https://fastly.jsdelivr.net/gh/guhaoxin123/dsh-vpn@main/clash.yaml`。

## 分组

按地区自动分组（约 60 个国家/地区，名字里没写地区的按 IP 归属地判断，判断不出的归入 `OTHER`），
另有 `🚀 节点选择`、`♻️ 自动选择`（url-test）、`🔯 故障转移`（fallback）。

规则：国内域名直连 → 私有地址直连 → 中国 IP 直连 → 其余走 `🚀 节点选择`。

极速版只是把节点范围换成延迟低于 200ms 的那部分，分组和规则与完整版一致。

## 说明

- Surfboard 只支持 ss / vmess / trojan / http / socks5，vless、hysteria2、tuic 等会被跳过，所以节点比 v2rayNG 少。
- v2rayNG 支持全部协议，节点最全。
- `proxies.yaml` 是纯节点列表，可以当 proxy-provider 用。
- 节点全部来自第三方公开订阅，可用性不保证，时效性以最近一次更新为准。

## 导入

- Clash：配置 → 新建 → 从 URL 导入，自动更新间隔填 60 分钟
- Surfboard：配置 → 从 URL 导入，填对应地址
- v2rayNG：订阅设置 → 添加订阅 → 填对应地址 → 更新订阅
