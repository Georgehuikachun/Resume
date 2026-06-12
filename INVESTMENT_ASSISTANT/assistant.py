#!/usr/bin/env python3
"""投资组合管理助手 — 规则化买卖信号引擎。

读取 portfolio.json,拉取市场行情,生成:
  - report.md   人类可读的组合报告 + 买卖提醒
  - alerts.json 机器可读的信号列表(供 GitHub Actions 决定是否推送通知)

信号规则:
  卖出/减仓: 触发止损、达到止盈目标、死叉(短均线下穿长均线)、RSI 超买
  买入/加仓: 金叉(短均线上穿长均线)、RSI 超卖、自近期高点回调超过阈值
  再平衡:   实际权重偏离目标权重超过阈值
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "portfolio.json"
REPORT_PATH = BASE_DIR / "report.md"
ALERTS_PATH = BASE_DIR / "alerts.json"

SEVERITY_ORDER = {"urgent": 0, "action": 1, "info": 2}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def fetch_history(symbols, period="1y"):
    """逐个拉取日线历史,返回 {symbol: DataFrame}。失败的标的跳过并记录。"""
    data, failed = {}, []
    for sym in symbols:
        try:
            df = yf.Ticker(sym).history(period=period, interval="1d", auto_adjust=True)
            if df.empty or len(df) < 60:
                failed.append(sym)
                continue
            data[sym] = df
        except Exception as e:
            print(f"warning: fetch {sym} failed: {e}", file=sys.stderr)
            failed.append(sym)
    return data, failed


def compute_indicators(df, rules):
    close = df["Close"]
    out = {}
    out["price"] = float(close.iloc[-1])
    out["prev_price"] = float(close.iloc[-2])
    out["sma_short"] = close.rolling(rules["sma_short"]).mean()
    out["sma_long"] = close.rolling(rules["sma_long"]).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / rules["rsi_period"], adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / rules["rsi_period"], adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    out["rsi"] = float((100 - 100 / (1 + rs)).iloc[-1])

    out["high_60d"] = float(close.tail(60).max())
    out["chg_1d_pct"] = (out["price"] / out["prev_price"] - 1) * 100
    return out


def cross_signal(short_ma, long_ma):
    """返回 'golden' / 'death' / None,只在最近一根K线发生交叉时触发。"""
    if pd.isna(short_ma.iloc[-2]) or pd.isna(long_ma.iloc[-2]):
        return None
    prev_above = short_ma.iloc[-2] > long_ma.iloc[-2]
    now_above = short_ma.iloc[-1] > long_ma.iloc[-1]
    if not prev_above and now_above:
        return "golden"
    if prev_above and not now_above:
        return "death"
    return None


def analyze(config):
    rules = config["rules"]
    holdings = {h["symbol"]: h for h in config["holdings"]}
    all_symbols = list(holdings) + [s for s in config["watchlist"] if s not in holdings]

    history, failed = fetch_history(all_symbols)
    alerts, snapshot = [], []

    # 持仓市值与权重
    values = {}
    for sym, h in holdings.items():
        if sym in history:
            ind = compute_indicators(history[sym], rules)
            values[sym] = ind["price"] * h["shares"]
    total_value = sum(values.values())

    for sym in all_symbols:
        if sym not in history:
            continue
        ind = compute_indicators(history[sym], rules)
        held = sym in holdings
        h = holdings.get(sym)

        row = {
            "symbol": sym,
            "held": held,
            "price": round(ind["price"], 2),
            "chg_1d_pct": round(ind["chg_1d_pct"], 2),
            "rsi": round(ind["rsi"], 1),
        }

        if held:
            cost = h["cost_basis"]
            pnl_pct = (ind["price"] / cost - 1) * 100
            weight = values[sym] / total_value if total_value else 0
            row.update({
                "shares": h["shares"],
                "cost_basis": cost,
                "pnl_pct": round(pnl_pct, 2),
                "weight": round(weight, 4),
                "target_weight": h["target_weight"],
                "value": round(values[sym], 2),
            })

            # 卖出信号
            if ind["price"] <= cost * (1 - rules["stop_loss_pct"]):
                alerts.append(dict(symbol=sym, side="SELL", severity="urgent",
                    reason=f"触发止损:现价 {ind['price']:.2f},较成本 {cost:.2f} 下跌 {-pnl_pct:.1f}%(止损线 {rules['stop_loss_pct']*100:.0f}%)。建议立即评估卖出。"))
            if ind["price"] >= cost * (1 + rules["take_profit_pct"]):
                alerts.append(dict(symbol=sym, side="SELL", severity="action",
                    reason=f"达到止盈目标:浮盈 {pnl_pct:.1f}%(目标 {rules['take_profit_pct']*100:.0f}%)。建议部分止盈锁定利润。"))
            if ind["rsi"] >= rules["rsi_overbought"]:
                alerts.append(dict(symbol=sym, side="SELL", severity="info",
                    reason=f"RSI {ind['rsi']:.0f} 超买(阈值 {rules['rsi_overbought']}),短期回调风险升高,可考虑减仓。"))

            # 再平衡
            drift = weight - h["target_weight"]
            if abs(drift) >= rules["rebalance_drift_pct"]:
                side = "SELL" if drift > 0 else "BUY"
                alerts.append(dict(symbol=sym, side=side, severity="action",
                    reason=f"权重偏离:当前 {weight*100:.1f}% vs 目标 {h['target_weight']*100:.0f}%,建议再平衡({'减持' if drift > 0 else '增持'})。"))

        # 买入信号(持仓和观察列表都检查)
        cross = cross_signal(ind["sma_short"], ind["sma_long"])
        if cross == "golden":
            alerts.append(dict(symbol=sym, side="BUY", severity="action",
                reason=f"金叉:{rules['sma_short']}日均线上穿{rules['sma_long']}日均线,趋势转多,可考虑{'加仓' if held else '建仓'}。"))
        elif cross == "death" and held:
            alerts.append(dict(symbol=sym, side="SELL", severity="action",
                reason=f"死叉:{rules['sma_short']}日均线下穿{rules['sma_long']}日均线,趋势转弱,建议减仓或离场。"))

        if ind["rsi"] <= rules["rsi_oversold"]:
            alerts.append(dict(symbol=sym, side="BUY", severity="action",
                reason=f"RSI {ind['rsi']:.0f} 超卖(阈值 {rules['rsi_oversold']}),可考虑分批{'加仓' if held else '建仓'}。"))

        dip = 1 - ind["price"] / ind["high_60d"]
        if dip >= rules["dip_buy_pct"] and not held:
            alerts.append(dict(symbol=sym, side="BUY", severity="info",
                reason=f"较60日高点 {ind['high_60d']:.2f} 回调 {dip*100:.1f}%,观察列表标的进入逢低关注区。"))

        snapshot.append(row)

    alerts.sort(key=lambda a: SEVERITY_ORDER[a["severity"]])
    return snapshot, alerts, total_value, failed


def write_report(config, snapshot, alerts, total_value, failed):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# 投资组合日报 — {now}",
        "",
        f"**组合总市值:${total_value:,.2f}** | 目标年化:{config['target_annual_return_pct']}%(目标值,非保证)",
        "",
    ]

    if alerts:
        lines += ["## 🔔 操作提醒", ""]
        icon = {"urgent": "🟥", "action": "🟧", "info": "🟨"}
        for a in alerts:
            lines.append(f"- {icon[a['severity']]} **[{a['side']}] {a['symbol']}** — {a['reason']}")
        lines.append("")
    else:
        lines += ["## ✅ 今日无操作信号,继续持有。", ""]

    lines += ["## 持仓概览", "",
              "| 标的 | 现价 | 日涨跌 | 成本 | 盈亏 | 权重/目标 | RSI |",
              "|---|---|---|---|---|---|---|"]
    for r in snapshot:
        if r["held"]:
            lines.append(
                f"| {r['symbol']} | {r['price']} | {r['chg_1d_pct']:+.2f}% | {r['cost_basis']} "
                f"| {r['pnl_pct']:+.2f}% | {r['weight']*100:.1f}%/{r['target_weight']*100:.0f}% | {r['rsi']} |")

    lines += ["", "## 观察列表", "",
              "| 标的 | 现价 | 日涨跌 | RSI |", "|---|---|---|---|"]
    for r in snapshot:
        if not r["held"]:
            lines.append(f"| {r['symbol']} | {r['price']} | {r['chg_1d_pct']:+.2f}% | {r['rsi']} |")

    if failed:
        lines += ["", f"> ⚠️ 以下标的行情获取失败,本次未分析:{', '.join(failed)}"]

    lines += ["", "---",
              "> 免责声明:本报告由规则化程序自动生成,仅供参考,不构成投资建议。",
              "> 市场有风险,任何策略都无法保证收益,目标年化 20% 意味着需要承担显著回撤风险。"]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    config = load_config()
    snapshot, alerts, total_value, failed = analyze(config)
    write_report(config, snapshot, alerts, total_value, failed)

    ALERTS_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_value": round(total_value, 2),
        "alert_count": len(alerts),
        "has_urgent": any(a["severity"] == "urgent" for a in alerts),
        "alerts": alerts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"报告已生成:{REPORT_PATH}")
    print(f"信号数量:{len(alerts)}")
    for a in alerts:
        print(f"  [{a['severity'].upper()}] {a['side']} {a['symbol']}: {a['reason']}")


if __name__ == "__main__":
    main()
