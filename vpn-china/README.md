# 中国可用的 VPN(Xray VLESS + Reality)

> 一句话:翻墙 = **墙外的服务器** + **国内设备上的客户端**,两者配合。
> 单靠一台机器是做不到的,尤其不能靠某个临时云容器。

## 为什么是这个方案

中国的防火墙(GFW)会用深度包检测(DPI)识别并封锁普通 VPN 协议
(OpenVPN / WireGuard / IPSec),还会主动探测可疑服务器。所以在国内要稳定可用,
需要**流量伪装**。

本方案用 **Xray 的 VLESS + Reality**:

- **不需要域名,也不需要自己买/申请 TLS 证书**。
- Reality 会“借用”一个真实大站(默认 `www.microsoft.com`)的 TLS 握手,
  GFW 看到的是一条指向真实知名网站的正常 HTTPS 连接,难以判定为代理。
- 能抵抗主动探测,是目前公认最难被封的方案之一。

## 你需要准备什么

1. **一台墙外的 VPS**(关键)。例如 Vultr、DigitalOcean、AWS Lightsail、
   搬瓦工(BandwagonHost)等。系统选 Ubuntu 20.04+ 或 Debian 11+。
   - 线路建议:面向国内,日本/韩国/新加坡/美西延迟较低;有条件可选 CN2 GIA 线路。
2. 你在国内的设备(Windows / Android / iOS / macOS)。

## 部署步骤

### 1. 在 VPS 上搭服务端

SSH 登录你的 VPS,然后:

```bash
curl -fsSL -o server-setup.sh https://raw.githubusercontent.com/georgehuikachun/resume/claude/vpn-china-access-xa1ann/vpn-china/server-setup.sh
sudo bash server-setup.sh
```

脚本会自动安装 Xray、生成密钥、写好配置、开放端口,最后打印一个
`vless://...` 导入链接和二维码。**把这个链接保存好。**

可选自定义(运行前设置环境变量):

```bash
sudo PORT=443 DEST=www.microsoft.com:443 SERVER_NAMES=www.microsoft.com bash server-setup.sh
```

### 2. 在国内设备上装客户端并导入

| 平台 | 推荐客户端 | 导入方式 |
|------|-----------|---------|
| Windows | [v2rayN](https://github.com/2dust/v2rayN/releases) | 复制 `vless://` 链接 → 「从剪贴板导入」 |
| Android | [v2rayNG](https://github.com/2dust/v2rayNG/releases) | 点 `+` → 「从剪贴板导入」 或扫二维码 |
| iOS | Shadowrocket / Stash(App Store) | 粘贴链接导入 |
| 跨平台 | [sing-box](https://github.com/SagerNet/sing-box) / NekoBox | 用本目录 `client-config.json`,替换占位符 |

导入后选中节点,开启代理即可。`client-config.json` 已内置**国内直连、
国外走代理**的分流规则。

### 3. 验证

连接后访问 `https://ipinfo.io`,看到的应是你 VPS 的 IP 和国家,即成功。

## 重要安全提示

- **私钥保密**:服务端 `privateKey` 不要泄露或提交到公开仓库。本仓库里只有脚本,
  密钥是在你 VPS 上运行时现场生成的。
- 本仓库的脚本/配置**不含任何真实服务器信息**,可以安全公开。
- 请遵守你所在司法管辖区的相关法律。本方案用于访问开放互联网、保护隐私等合法用途。

## 故障排查

- **连不上**:在 VPS 上 `systemctl status xray`、`journalctl -u xray -n 50` 看日志;
  确认云服务商安全组/防火墙放行了对应端口。
- **能连但很慢/掉线**:换 `PORT`、换 `DEST` 伪装站点,或更换 VPS 线路/机房。
- **被封 IP**:Reality 被封的概率较低,通常是 IP 本身被墙。换一个 VPS IP 即可,
  服务端配置不用动。
