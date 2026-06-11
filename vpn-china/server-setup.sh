#!/usr/bin/env bash
#
# Xray VLESS + Reality 一键部署脚本(抗 GFW)
# ------------------------------------------------------------
# 在一台【墙外】的 VPS 上运行(Ubuntu 20.04+ / Debian 11+,需 root)。
# 为什么用 Reality:
#   - 不需要域名、不需要自己申请 TLS 证书
#   - 偷用一个真实大站(默认 www.microsoft.com)的 TLS 握手,
#     GFW 看到的是一条指向真实网站的正常 HTTPS 连接
#   - 能抵抗主动探测(active probing),是目前最难被封的方案之一
#
# 用法:
#   sudo bash server-setup.sh
# 运行结束后会打印客户端导入链接(vless://...)和二维码信息。
#
set -euo pipefail

# ---- 可调参数 ----
PORT="${PORT:-443}"                       # 监听端口,443 最不易被怀疑
DEST="${DEST:-www.microsoft.com:443}"     # 伪装目标(必须是支持 TLSv1.3 + H2 的大站)
SERVER_NAMES="${SERVER_NAMES:-www.microsoft.com}"  # SNI,需与 DEST 一致

if [[ "${EUID}" -ne 0 ]]; then
  echo "请用 root 运行: sudo bash $0" >&2
  exit 1
fi

echo "[1/6] 安装依赖..."
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y curl unzip qrencode ca-certificates
elif command -v yum >/dev/null 2>&1; then
  yum install -y curl unzip qrencode ca-certificates
fi

echo "[2/6] 安装 Xray-core (官方脚本)..."
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

echo "[3/6] 生成密钥与 ID..."
KEYS="$(xray x25519)"
PRIVATE_KEY="$(echo "${KEYS}" | awk '/Private/{print $3}')"
PUBLIC_KEY="$(echo "${KEYS}"  | awk '/Public/{print $3}')"
UUID="$(xray uuid)"
SHORT_ID="$(openssl rand -hex 8)"

echo "[4/6] 写入服务端配置..."
cat > /usr/local/etc/xray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": ${PORT},
      "protocol": "vless",
      "settings": {
        "clients": [
          { "id": "${UUID}", "flow": "xtls-rprx-vision" }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "${DEST}",
          "xver": 0,
          "serverNames": ["${SERVER_NAMES}"],
          "privateKey": "${PRIVATE_KEY}",
          "shortIds": ["${SHORT_ID}"]
        }
      },
      "sniffing": { "enabled": true, "destOverride": ["http", "tls", "quic"] }
    }
  ],
  "outbounds": [
    { "protocol": "freedom", "tag": "direct" },
    { "protocol": "blackhole", "tag": "block" }
  ]
}
EOF

echo "[5/6] 开放防火墙并重启服务..."
if command -v ufw >/dev/null 2>&1; then ufw allow "${PORT}"/tcp || true; fi
systemctl enable xray
systemctl restart xray
sleep 1
systemctl --no-pager --full status xray | head -n 8 || true

SERVER_IP="$(curl -s --max-time 8 https://api.ipify.org || hostname -I | awk '{print $1}')"
LINK="vless://${UUID}@${SERVER_IP}:${PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${SERVER_NAMES}&fp=chrome&pbk=${PUBLIC_KEY}&sid=${SHORT_ID}&type=tcp&headerType=none#Reality-${SERVER_IP}"

echo ""
echo "==================== 部署完成 ===================="
echo " 服务器 IP   : ${SERVER_IP}"
echo " 端口        : ${PORT}"
echo " UUID        : ${UUID}"
echo " 公钥 (pbk)  : ${PUBLIC_KEY}"
echo " ShortId     : ${SHORT_ID}"
echo " SNI / 伪装  : ${SERVER_NAMES}"
echo "--------------------------------------------------"
echo " 客户端导入链接 (复制到 v2rayN / v2rayNG / sing-box):"
echo ""
echo " ${LINK}"
echo ""
echo "[6/6] 二维码 (手机客户端扫描):"
if command -v qrencode >/dev/null 2>&1; then
  qrencode -t ANSIUTF8 "${LINK}"
fi
echo "=================================================="
echo "提示: 把上面的链接保存好。把私钥保密,不要泄露。"
