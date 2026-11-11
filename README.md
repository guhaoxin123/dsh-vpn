# dsh-vpn

由 **DSH** 编写并自动维护，每小时更新一次。

合并多个公开免费订阅源，逐个节点实测延迟，超时的删除，剩下的按顺序编号并按地区分组。

## 文件

- `clash.yaml` — 完整配置，直接导入即可
- `proxies.yaml` — 纯节点列表，可当 proxy-provider

## 分组

按地区自动生成：`HK` `SG` `JP` `US` `TW` `KR` `UK` `DE` `FR` `CA` `AU` `NL` `RU` `IN` `TR` `OTHER`
外加 `🚀 节点选择` / `♻️ 自动选择` / `🔯 故障转移`。

## 地址（raw 被墙，用镜像）

```
https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/clash.yaml
```

备用：`https://gh-proxy.com/` 或 `https://fastly.jsdelivr.net/gh/guhaoxin123/dsh-vpn@main/clash.yaml` 前缀替换。

## 用法

配置 → 新建 → 从 URL 导入 → 粘贴地址 → 自动更新间隔设 60 分钟。

节点来自第三方公开订阅，可用性不保证。
