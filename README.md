# dsh-vpn

> 本仓库的脚本与配置由 **DSH** 编写并自动维护。

自动合并多个公开免费订阅源，**对每一个节点做实测延迟**，超时 / 连不通的直接删除，
剩下的按顺序编号后重新生成一份干净的 Clash 配置。每小时自动跑一次。

## 产出文件

| 文件 | 说明 |
| --- | --- |
| `clash.yaml` | 完整配置，可直接导入 Clash Meta / mihomo / 各类客户端 |
| `proxies.yaml` | 纯节点列表，可当作 `proxy-provider` 使用 |
| `merge.py` | 生成脚本（DSH 编写） |

## 处理流程

1. 拉取 7 个公开订阅源（支持 Clash YAML 与 base64 v2ray 两种格式）
2. 按 `类型 + 服务器 + 端口` 去重
3. 丢弃名字里带「剩余 / 流量 / 到期 / 官网 / 订阅 / 客服」等广告信息的条目
4. **用 mihomo 内核逐个节点跑 `generate_204`，5 秒超时的直接删除**
5. 存活节点按延迟从低到高排序，命名为 `001 xxx [123ms]`、`002 xxx [456ms]` …
6. 提交回本仓库

## 使用地址

`raw.githubusercontent.com` 在国内被墙，请使用镜像地址（把 `<你的用户名>` 换成实际用户名）：

```
https://ghfast.top/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/clash.yaml
```

备用镜像：

```
https://gh-proxy.com/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/clash.yaml
https://fastly.jsdelivr.net/gh/guhaoxin123/dsh-vpn@main/clash.yaml
https://ghproxy.net/https://raw.githubusercontent.com/guhaoxin123/dsh-vpn/main/clash.yaml
```

## 客户端里怎么用

1. 配置 → 新建(+) → **从 URL 导入** → 粘贴上面的镜像地址
2. 保存后进入该配置的菜单 → **自动更新间隔** 设为 `60 分钟`
3. 启动。分组自带 `🚀 节点选择` / `♻️ 自动选择`(url-test) / `🔯 故障转移`(fallback)

## 说明

- 节点全部来自第三方公开订阅，可用性与安全性不保证，请自行判断，勿用于敏感用途。
- 每小时第 17 分自动更新；想立刻刷新可在 Actions 页手动 Run workflow。
