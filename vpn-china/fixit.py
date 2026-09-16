#!/usr/bin/env python3
"""
fixit.py — 一次性修复 REALITY 握手失败

做两件事,直到成功为止:
  1. 在当前 Xray 版本上把所有 uTLS 指纹轮一遍
     (REALITY 的认证信息藏在 ClientHello 里,指纹不对会导致服务端认不出来)
  2. 全失败则自动降到已知稳定版 v25.12.31 并重测
     (26.x 早期的 REALITY 有已知认证问题;配置格式完全兼容,无需改动)

成功后直接打印可导入的 vless:// 链接。

用法:
    sudo python3 fixit.py
"""
import json
import re
import subprocess
import sys
import time

CFG = "/usr/local/etc/xray/config.json"
SOCKS_PORT = 10812
PROBE = "/tmp/xray_fix.json"
FPS = ["chrome", "firefox", "safari", "edge", "ios", "android", "randomized", "random"]
STABLE = "v25.12.31"


def sh(cmd, timeout=180):
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, timeout=timeout)


def load():
    cfg = json.load(open(CFG))
    inb = cfg["inbounds"][0]
    rs = inb["streamSettings"]["realitySettings"]
    return {
        "priv": rs["privateKey"],
        "sid": rs["shortIds"][0],
        "sni": rs["serverNames"][0],
        "uuid": inb["settings"]["clients"][0]["id"],
        "port": inb["port"],
    }


def pubkey(priv):
    toks = re.findall(r"[A-Za-z0-9_-]{43}", sh(f'xray x25519 -i "{priv}"').stdout)
    return toks[1] if len(toks) > 1 else ""


def probe(s, pub, fp):
    conf = {
        "log": {"loglevel": "error"},
        "inbounds": [{"port": SOCKS_PORT, "listen": "127.0.0.1",
                      "protocol": "socks", "settings": {"udp": True}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": "127.0.0.1", "port": s["port"],
                                    "users": [{"id": s["uuid"], "encryption": "none",
                                               "flow": "xtls-rprx-vision"}]}]},
            "streamSettings": {
                "network": "tcp", "security": "reality",
                "realitySettings": {"serverName": s["sni"], "fingerprint": fp,
                                    "publicKey": pub, "shortId": s["sid"]},
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
    return '"ip"' in out


def sweep(label):
    s = load()
    pub = pubkey(s["priv"])
    if not pub:
        print("  无法解析公钥,跳过")
        return None
    print(f"\n=== {label} — 指纹轮测 ===")
    for fp in FPS:
        ok = probe(s, pub, fp)
        print(f"  {'✅' if ok else '❌'}  fingerprint={fp}")
        if ok:
            return (s, pub, fp)
    return None


def report(s, pub, fp):
    ip = sh("curl -s --max-time 8 https://api.ipify.org").stdout.strip()
    link = (f"vless://{s['uuid']}@{ip}:{s['port']}?encryption=none"
            f"&flow=xtls-rprx-vision&security=reality&sni={s['sni']}"
            f"&fp={fp}&pbk={pub}&sid={s['sid']}&type=tcp&headerType=none#Reality-AU")
    print("\n" + "=" * 60)
    print("✅ 成功!用下面这条链接导入客户端:")
    print("=" * 60)
    print(link)
    print("=" * 60)
    print(f"\n客户端要点:Fingerprint 必须填 {fp}")
    print(f"  Address={ip}  Port={s['port']}")
    print(f"  UUID={s['uuid']}")
    print(f"  PublicKey={pub}")
    print(f"  ShortId={s['sid']}   SNI={s['sni']}")
    print("  Flow=xtls-rprx-vision   TLS=ON")


def main():
    ver = sh("xray version").stdout.strip().splitlines()[0]
    print(f"当前版本: {ver}")

    hit = sweep("第一轮:当前版本")
    if hit:
        report(*hit)
        return

    print(f"\n当前版本所有指纹均失败 → 降级到稳定版 {STABLE} 重试")
    print("(配置文件不受影响,只替换程序本体)\n")
    r = sh('bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/'
           f'install-release.sh)" @ install --version {STABLE}')
    print(r.stdout[-800:] or r.stderr[-800:])
    sh("systemctl restart xray")
    time.sleep(3)
    print(f"新版本: {sh('xray version').stdout.strip().splitlines()[0]}")
    print(f"服务状态: {sh('systemctl is-active xray').stdout.strip()}")

    hit = sweep(f"第二轮:{STABLE}")
    if hit:
        report(*hit)
        return

    print("\n❌ 两个版本都失败,请把完整输出发回。")


if __name__ == "__main__":
    main()
