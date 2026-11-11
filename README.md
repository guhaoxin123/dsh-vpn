# ghx 订阅（自动更新）

- `clash.yaml`：合并 7 个公开免费订阅 + 去重 + 按顺序编号（001、002…），可直接导入 Clash Meta
- `proxies.yaml`：纯节点列表，可当 proxy-provider 用
- GitHub Actions 每小时自动更新一次

## 国内可直连的使用地址（raw.githubusercontent 被墙，要用镜像）

full 配置：
```
https://ghfast.top/https://raw.githubusercontent.com/<用户名>/<仓库名>/main/clash.yaml
```
备用镜像：`https://gh-proxy.com/...`、`https://ghproxy.net/...`、`https://fastly.jsdelivr.net/gh/<用户名>/<仓库名>@main/clash.yaml`

在 Clash Meta 里：配置 → 新建 → 从 URL 导入 → 粘贴地址 → 把该配置的「自动更新间隔」设为 60 分钟。
