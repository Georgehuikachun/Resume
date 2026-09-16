#!/usr/bin/env python3
"""
diagnose.py — Reality 握手失败排查

在服务器上运行,读取当前 Xray 服务端配置,然后用「服务器连自己」的方式
把所有可能的 (publicKey, flow) 组合逐一实测,找出真正能握手成功的那一组,
并直接打印可用的 vless:// 链接。

用法:
    sudo python3 diagnose.py
"""
import json
import re
import subprocess
import sys
import time

CFG = "/usr/local/etc/xray/config.json"
SOCKS_PORT = 10809
PROBE = "/tmp/xray_probe.json"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def main():
    try:
        cfg = json.load(open(CFG))
    except Exception as e:
        sys.exit(f"读不到 {CFG}: {e}")

    inb = cfg["inbounds"][0]
    rs = inb["streamSettings"]["realitySettings"]
    priv, sid, sni = rs["privateKey"], rs["shortIds"][0], rs["serverNames"][0]
    uuid = inb["settings"]["clients"][0]["id"]
    port = inb["port"]

    print("=== 服务端参数 ===")
    print(f"port={port}  uuid={uuid}")
    print(f"sid={sid}  sni={sni}")
    print(f"privateKey={priv}")
    print(f"dest={rs.get('dest')}  target={rs.get('target')}")

    raw = sh(f'xray x25519 -i "{priv}"').stdout
    print("\n=== xray x25519 -i 原始输出 ===")
    print(raw.strip())
    cands = re.findall(r"[A-Za-z0-9_-]{43}", raw)
    if not cands:
        sys.exit("无法从 x25519 输出解析出密钥")
    print(f"候选公钥数量: {len(cands)}")

    def probe(pub, flow):
        """起一个本地 socks,经由 Reality 连服务器自己,看能否取回 ipinfo。"""
        user = {"id": uuid, "encryption": "none"}
        if flow:
            user["flow"] = flow
        conf = {
            "log": {"loglevel": "error"},
            "inbounds": [{
                "port": SOCKS_PORT, "listen": "127.0.0.1",
                "protocol": "socks", "settings": {"udp": True},
            }],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": "127.0.0.1", "port": port, "users": [user],
                }]},
                "streamSettings": {
                    "network": "tcp", "security": "reality",
                    "realitySettings": {
                        "serverName": sni, "fingerprint": "chrome",
                        "publicKey": pub, "shortId": sid,
                    },
                },
            }],
        }
        json.dump(conf, open(PROBE, "w"))
        p = subprocess.Popen(["xray", "-c", PROBE],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        out = sh(f"curl -s --max-time 10 --socks5-hostname "
                 f"127.0.0.1:{SOCKS_PORT} https://ipinfo.io/json").stdout
        p.terminate()
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
        time.sleep(1)
        return out.strip()

    print("\n=== 逐组合实测 ===")
    winner = None
    for pub in cands:
        for flow in ("xtls-rprx-vision", ""):
            out = probe(pub, flow)
            ok = '"ip"' in out
            print(f"{'✅' if ok else '❌'}  pbk={pub[:14]}...  flow={flow or '(空)'}")
            if ok:
                print("    返回:", out.replace("\n", " ")[:140])
                winner = (pub, flow)
                break
        if winner:
            break

    print()
    if not winner:
        print("=== ❌ 所有组合都失败 ===")
        print("请把以上完整输出发回排查。")
        return

    pub, flow = winner
    ip = sh("curl -s --max-time 8 https://api.ipify.org").stdout.strip()
    fl = f"&flow={flow}" if flow else ""
    print("=== ✅ 找到可用组合 ===")
    print(f"pbk  = {pub}")
    print(f"flow = {flow or '(留空)'}")
    print("\n用这条链接导入客户端:")
    print(f"vless://{uuid}@{ip}:{port}?encryption=none{fl}&security=reality"
          f"&sni={sni}&fp=chrome&pbk={pub}&sid={sid}&type=tcp&headerType=none#Reality-AU")
    if not flow:
        print("\n注意: 这组不带 flow,客户端里的 Flow 字段必须清空。")


if __name__ == "__main__":
    main()
