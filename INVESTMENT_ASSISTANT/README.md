# 📈 投资组合管理助手

一个自动化的个人财富管理助手:监控你的持仓和观察列表,在**该卖的时候提醒你卖、该买的时候提醒你买**,并由 Claude AI 像华尔街投资经理一样给出当日点评。通过 GitHub Actions 定时运行,有信号时自动创建 Issue —— 你的手机会收到 GitHub 通知推送。

## ⚠️ 先说清楚最重要的事

- **没有任何工具、经理或策略能"保证"年化 20% 收益。** 20% 在这里是一个进取型**目标**,意味着你必须接受可能 -20% 甚至更大的回撤。
- 本工具产生的是**规则化信号 + AI 参考意见**,不是投资建议。最终决策永远是你自己的。
- 历史上长期做到年化 20% 的人(巴菲特约 20%)是世界顶级水平,请管理好预期。

## 它能做什么

| 功能 | 说明 |
|---|---|
| 🟥 止损提醒 | 持仓较成本下跌超过 12% → 紧急卖出提醒 |
| 🟧 止盈提醒 | 浮盈达到 35% → 建议部分锁定利润 |
| 🟧 趋势信号 | 20/50 日均线金叉提醒买入、死叉提醒卖出 |
| 🟧 超买超卖 | RSI > 72 提示减仓风险、RSI < 30 提示分批买入机会 |
| 🟧 再平衡 | 持仓权重偏离目标超过 5% → 提醒调仓 |
| 🟨 逢低关注 | 观察列表标的从 60 日高点回调超 10% → 提示关注 |
| 🧠 AI 点评 | Claude 结合宏观环境、行业轮动给出华尔街经理式当日分析(可选)|
| 📲 自动推送 | 工作日每天 3 次自动检查,有信号就创建 GitHub Issue 通知你 |

## 默认组合(请改成你自己的!)

`portfolio.json` 里预置了一个以 20% 年化为目标的进取型示例组合:

- **30% QQQ**(纳指100)+ **25% SPY**(标普500)— 核心仓
- **15% SMH**(半导体)+ **10% NVDA** — AI 主线进攻仓
- **10% MSFT** — 质量成长
- **10% GLD**(黄金)— 对冲仓

**这只是示例。** 打开 `portfolio.json`,把 `holdings` 改成你的真实持仓(股数 `shares`、成本价 `cost_basis`、目标权重 `target_weight`),把 `watchlist` 改成你关注的股票。规则阈值也都在 `rules` 里,可随意调整。

## 快速开始

### 方式一:GitHub 自动推送(推荐)

1. 把代码推到 GitHub(本仓库已包含 workflow)。
2. 在仓库 **Settings → Notifications** 确认你 watch 了本仓库(默认会)。手机装 GitHub App 即可收到推送。
3. (可选)在 **Settings → Secrets and variables → Actions** 添加 `ANTHROPIC_API_KEY`,开启 Claude AI 点评。
4. 完成。工作日美东盘前/午盘/收盘后各自动检查一次;也可以在 Actions 页面手动点 **Run workflow** 立即检查。

### 方式二:本地运行

```bash
cd INVESTMENT_ASSISTANT
pip install -r requirements.txt
python assistant.py          # 生成 report.md + alerts.json
export ANTHROPIC_API_KEY=sk-ant-...   # 可选
python ai_advisor.py         # 追加 AI 点评到 report.md
```

## 文件说明

```
INVESTMENT_ASSISTANT/
├── portfolio.json   # 你的持仓、观察列表、规则阈值(核心配置)
├── assistant.py     # 信号引擎:拉行情、算指标、生成买卖提醒
├── ai_advisor.py    # Claude AI 投资经理点评(可选)
├── report.md        # 每次运行生成的组合日报
├── alerts.json      # 机器可读的信号(供自动推送判断)
└── requirements.txt
.github/workflows/portfolio-check.yml  # 定时任务 + Issue 推送
```

## 想调整策略?

都在 `portfolio.json` 的 `rules` 里:

| 参数 | 默认 | 含义 |
|---|---|---|
| `stop_loss_pct` | 0.12 | 止损线(亏 12% 提醒卖)|
| `take_profit_pct` | 0.35 | 止盈线(赚 35% 提醒锁利)|
| `dip_buy_pct` | 0.10 | 观察标的回调多少进入买入关注 |
| `rebalance_drift_pct` | 0.05 | 权重偏离多少提醒再平衡 |
| `sma_short` / `sma_long` | 20 / 50 | 趋势均线参数 |
| `rsi_overbought` / `rsi_oversold` | 72 / 30 | 超买/超卖阈值 |

---

> 数据来源:Yahoo Finance(免费,约 15 分钟延迟,对日线策略足够)。
> 本项目仅供学习参考,不构成投资建议。投资有风险,入市需谨慎。
