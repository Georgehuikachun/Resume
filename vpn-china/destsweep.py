#!/usr/bin/env python3
"""
destsweep.py — 轮换 REALITY 伪装目标(dest/SNI)直到握手成功

REALITY 服务端要把客户端的 TLS 握手原样转发给伪装站点、借用它的证书,
所以伪装站点必须支持 TLS 1.3 + HTTP/2 且行为稳定。站点不合格时,
**所有**客户端(包括参数完全正确的)都会握手失败 —— 现象和密钥错误一模一样。

本脚本逐个替换 dest / target / serverNames,重启服务后做回环自测,
第一个成功的就是可用配置,并直接打印可导入的 vless:// 链接。

用法:
    sudo python3 destsweep.py
"""
import json
import re
import shutil
import subprocess
import time

CFG = "/usr/local/etc/xray/config.json"
BAK = "/usr/local/etc/xray/config.json.sweepbak"
PROBE = "/tmp/xray_sweep.json"
SOCKS_PORT = 10813

CANDIDATES = [
    "www.apple.com",
    "dl.google.com",
    "www.bing.com",
    "addons.mozilla.org",
    "swdist.apple.com",
    "www.cloudflare.com",
    "www.lovelive-anime.jp",
    "www.microsoft.com",
]


def sh(cmd, timeout=60):
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, timeout=timeout)


def tls_ok(host):
    """伪装目标是否支持 TLS1.3 + h2。"""
    r = sh(f"echo | timeout 10 openssl s_client -connect {host}:443 "
           f"-servername {host} -tls1_3 -alpn h2 2>/dev/null "
           f"| grep -E 'ALPN protocol|Protocol  :'")
    out = r.stdout
    return ("h2" in out) and ("TLSv1.3" in out or "Protocol" in out), out.strip()


def set_dest(host):
    cfg = json.load(open(CFG))
    rs = cfg["inbounds"][0]["streamSettings"]["realitySettings"]
    rs["dest"] = f"{host}:443"
    rs["target"] = f"{host}:443"
    rs["serverNames"] = [host]
    json.dump(cfg, open(CFG, "w"), indent=2)
    sh("systemctl restart xray")
    time.sleep(2)
    return sh("systemctl is-active xray").stdout.strip()


def load():
    cfg = json.load(open(CFG))
    inb = cfg["inbounds"][0]
    rs = inb["streamSettings"]["realitySettings"]
    return (rs["privateKey"], rs["shortIds"][0], rs["serverNames"][0],
            inb["settings"]["clients"][0]["id"], inb["port"])


def probe(host):
    priv, sid, sni, uuid, port = load()
    toks = re.findall(r"[A-Za-z0-9_-]{43}", sh(f'xray x25519 -i "{priv}"').stdout)
    pub = toks[1] if len(toks) > 1 else ""
    conf = {
        "log": {"loglevel": "error"},
        "inbounds": [{"port": SOCKS_PORT, "listen": "127.0.0.1",
                      "protocol": "socks", "settings": {"udp": True}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": "127.0.0.1", "port": port,
                                    "users": [{"id": uuid, "encryption": "none",
                                               "flow": "xtls-rprx-vision"}]}]},
            "streamSettings": {
                "network": "tcp", "security": "reality",
                "realitySettings": {"serverName": sni, "fingerprint": "chrome",
                                    "publicKey": pub, "shortId": sid},
            },
        }],
    }
    json.dump(conf, open(PROBE, "w"))
    p = subprocess.Popen(["xray", "-c", PROBE],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    out = sh(f"curl -s --max-time 8 --socks5-hostname "
             f"127.0.0.1:{SOCKS_PORT} https://ipinfo.io/json", timeout=20).stdout
    p.terminate()
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()
    time.sleep(1)
    return ('"ip"' in out), pub, sid, uuid, port


def main():
    shutil.copy(CFG, BAK)
    print(f"原配置已备份到 {BAK}\n")
    print("=== 逐个伪装目标实测 ===")
    for host in CANDIDATES:
        ok_tls, detail = tls_ok(host)
        state = set_dest(host)
        ok, pub, sid, uuid, port = probe(host)
        print(f"{'✅' if ok else '❌'}  {host:24s} tls1.3+h2={'是' if ok_tls else '否':2s} "
              f"服务={state}")
        if ok:
            ip = sh("curl -s --max-time 8 https://api.ipify.org").stdout.strip()
            link = (f"vless://{uuid}@{ip}:{port}?encryption=none"
                    f"&flow=xtls-rprx-vision&security=reality&sni={host}"
                    f"&fp=chrome&pbk={pub}&sid={sid}&type=tcp&headerType=none#Reality-AU")
            print("\n" + "=" * 62)
            print(f"✅ 成功!可用的伪装目标是 {host}")
            print("=" * 62)
            print(link)
            print("=" * 62)
            print("\nShadowrocket 各字段:")
            print(f"  Address     = {ip}")
            print(f"  Port        = {port}")
            print(f"  UUID        = {uuid}")
            print(f"  Peer Name   = {host}      <<< 注意这里变了")
            print(f"  PublicKey   = {pub}")
            print(f"  ShortId     = {sid}")
            print("  Fingerprint = chrome")
            print("  Flow        = xtls-rprx-vision")
            print("  TLS         = ON")
            return

    print("\n❌ 所有伪装目标都失败 —— 问题不在 dest,恢复原配置。")
    shutil.copy(BAK, CFG)
    sh("systemctl restart xray")
    print("已恢复。请把完整输出发回。")
    print("\n可用的 Xray 版本(供下一步换版本参考):")
    r = sh("curl -s --max-time 20 https://api.github.com/repos/XTLS/Xray-core/"
           "releases?per_page=8 | grep '\"tag_name\"'")
    print(r.stdout.strip() or "(查询失败)")


if __name__ == "__main__":
    main()
