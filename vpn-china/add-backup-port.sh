#!/usr/bin/env bash
#
# add-backup-port.sh — 给已部署的 Xray Reality 增加一个「备用端口」入站
# ------------------------------------------------------------
# 为什么要备用端口:
#   回国后万一 443 端口被干扰/封锁,不用重装,直接在客户端切到备用端口即可。
#   两个入站共用同一套密钥和 UUID,所以只是端口不同,其它配置完全一样。
#
# 用法(在服务器上以 root 运行):
#   sudo bash add-backup-port.sh
#   sudo BACKUP_PORT=2053 bash add-backup-port.sh    # 自定义备用端口
#
set -euo pipefail

CFG=/usr/local/etc/xray/config.json
BACKUP_PORT="${BACKUP_PORT:-8443}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "请用 root 运行: sudo bash $0" >&2
  exit 1
fi
if [[ ! -f "${CFG}" ]]; then
  echo "找不到 ${CFG},请先运行 server-setup.sh" >&2
  exit 1
fi

echo "[1/4] 备份当前配置..."
cp "${CFG}" "${CFG}.bak.$(date +%s)"

echo "[2/4] 追加备用入站 (端口 ${BACKUP_PORT})..."
python3 - "${CFG}" "${BACKUP_PORT}" <<'PY'
import copy, json, sys

cfg_path, port = sys.argv[1], int(sys.argv[2])
with open(cfg_path) as f:
    cfg = json.load(f)

inbounds = cfg["inbounds"]
primary = next(i for i in inbounds if i.get("tag") != "backup")
# 重复执行时先移掉旧的备用入站,保证幂等
inbounds = [i for i in inbounds if i.get("tag") != "backup"]

backup = copy.deepcopy(primary)
backup["port"] = port
backup["tag"] = "backup"
inbounds.append(backup)

cfg["inbounds"] = inbounds
with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
PY

echo "[3/4] 放行防火墙并重启..."
if command -v ufw >/dev/null 2>&1; then ufw allow "${BACKUP_PORT}"/tcp >/dev/null 2>&1 || true; fi
iptables -C INPUT -p tcp --dport "${BACKUP_PORT}" -j ACCEPT 2>/dev/null \
  || iptables -I INPUT -p tcp --dport "${BACKUP_PORT}" -j ACCEPT
systemctl enable xray >/dev/null 2>&1 || true
systemctl restart xray
sleep 2

echo "[4/4] 生成链接..."
# 从现有配置里读回参数,避免手抄出错
PRIV="$(python3 -c "import json;print(json.load(open('${CFG}'))['inbounds'][0]['streamSettings']['realitySettings']['privateKey'])")"
UUID="$(python3 -c "import json;print(json.load(open('${CFG}'))['inbounds'][0]['settings']['clients'][0]['id'])")"
SID="$(python3  -c "import json;print(json.load(open('${CFG}'))['inbounds'][0]['streamSettings']['realitySettings']['shortIds'][0])")"
SNI="$(python3  -c "import json;print(json.load(open('${CFG}'))['inbounds'][0]['streamSettings']['realitySettings']['serverNames'][0])")"
MAIN_PORT="$(python3 -c "import json;print(json.load(open('${CFG}'))['inbounds'][0]['port'])")"
# 由私钥反推公钥(不同版本标签文案不同,按位置取第 2 个 43 字符密钥)
PUB="$(xray x25519 -i "${PRIV}" 2>/dev/null | grep -oE '[A-Za-z0-9_-]{43}' | sed -n 2p)"
SERVER_IP="$(curl -s --max-time 8 https://api.ipify.org || hostname -I | awk '{print $1}')"

echo ""
echo "===================== 完成 ====================="
echo " 服务状态 : $(systemctl is-active xray)"
echo " 监听端口 :"
ss -tlnp | grep xray || echo "  (未检测到监听,请看 journalctl -u xray -n 20)"
echo "------------------------------------------------"
if [[ -n "${PUB}" ]]; then
  echo " 主用链接 (端口 ${MAIN_PORT}):"
  echo " vless://${UUID}@${SERVER_IP}:${MAIN_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${SNI}&fp=chrome&pbk=${PUB}&sid=${SID}&type=tcp&headerType=none#Reality-main"
  echo ""
  echo " 备用链接 (端口 ${BACKUP_PORT}):"
  echo " vless://${UUID}@${SERVER_IP}:${BACKUP_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${SNI}&fp=chrome&pbk=${PUB}&sid=${SID}&type=tcp&headerType=none#Reality-backup"
else
  echo " 无法自动反推公钥。请用你已保存的 pbk,把主用链接里的端口"
  echo " 改成 ${BACKUP_PORT} 就是备用链接(其余参数完全相同)。"
fi
echo "================================================"
