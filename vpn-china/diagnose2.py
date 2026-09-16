#!/usr/bin/env python3
"""
diagnose2.py — 抓取 REALITY 握手失败时的「客户端」错误

前一版只测通不通,这版把客户端日志开到 debug 并打印出来,
同时对比 realitySettings 的 publicKey / password 两种字段写法
(Xray 26.x 把公钥改称 Password,客户端字段名可能随之变化)。

用法:
    sudo python3 diagnose2.py
"""
import json
import re
import subprocess
import sys
import time

CFG = "/usr/local/etc/xray/config.json"
SOCKS_PORT = 10811
PROBE = "/tmp/xray_probe2.json"
CLOG = "/tmp/xray_probe2.log"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def main():
    cfg = json.load(open(CFG))
    inb = cfg["inbounds"][0]
    rs = inb["streamSettings"]["realitySettings"]
    priv, sid, sni = rs["privateKey"], rs["shortIds"][0], rs["serverNames"][0]
    uuid = inb["settings"]["clients"][0]["id"]
    port = inb["port"]

    ver = sh("xray version").stdout.strip().splitlines()[0]
    print(f"=== Xray 版本 ===\n{ver}\n")

    raw = sh(f'xray x25519 -i "{priv}"').stdout
    toks = re.findall(r"[A-Za-z0-9_-]{43}", raw)
    pub = toks[1] if len(toks) > 1 else ""
    print(f"pub={pub}\nsid={sid}  sni={sni}  port={port}\n")

    def run(name, reality_extra, flow):
        user = {"id": uuid, "encryption": "none"}
        if flow:
            user["flow"] = flow
        reality = {"serverName": sni, "fingerprint": "chrome", "shortId": sid}
        reality.update(reality_extra)
        conf = {
            "log": {"loglevel": "debug"},
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
                    "realitySettings": reality,
                },
            }],
        }
        json.dump(conf, open(PROBE, "w"))
        with open(CLOG, "w") as lf:
            p = subprocess.Popen(["xray", "-c", PROBE], stdout=lf, stderr=lf)
        time.sleep(2)
        out = sh(f"curl -s --max-time 10 --socks5-hostname "
                 f"127.0.0.1:{SOCKS_PORT} https://ipinfo.io/json").stdout
        p.terminate()
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
        ok = '"ip"' in out
        print(f"--- {name} : {'✅ 成功' if ok else '❌ 失败'} ---")
        if ok:
            print("   ", out.replace("\n", " ")[:140])
        else:
            log = open(CLOG).read().strip().splitlines()
            keep = [l for l in log if "REALITY" in l or "failed" in l.lower()
                    or "error" in l.lower()][-8:]
            for line in (keep or log[-8:]):
                print("   ", line[:190])
        print()
        time.sleep(1)
        return ok

    print("=== 变体测试(含客户端 debug 日志)===\n")
    if run("A. publicKey + vision", {"publicKey": pub}, "xtls-rprx-vision"):
        return
    if run("B. password  + vision", {"password": pub}, "xtls-rprx-vision"):
        return
    if run("C. publicKey + 无flow", {"publicKey": pub}, ""):
        return
    if run("D. password  + 无flow", {"password": pub}, ""):
        return
    print("=== 四种写法都失败,把以上完整输出发回 ===")


if __name__ == "__main__":
    main()
