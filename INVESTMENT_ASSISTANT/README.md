# 📈 投资组合管理助手(澳洲定投版)

一个自动化的个人财富管理助手,为「每月固定金额定投、从零开始建仓」的投资者设计:

- 💰 **每月定投提醒**:月初自动提醒你按计划投入,并算好每只 ETF 买多少
- 🔔 **买卖信号**:建仓后自动监控止损/止盈/趋势/超买超卖,该卖提醒卖、该买提醒买
- 🧠 **AI 点评**(可选):Claude 像华尔街经理一样点评当日信号
- 📲 **自动推送**:GitHub Actions 定时运行,有信号自动创建 Issue → 手机 GitHub App 收到通知

## 💸 费用说明:核心功能完全免费

| 项目 | 费用 |
|---|---|
| 行情数据(Yahoo Finance)| 免费 |
| GitHub Actions 定时运行 + 通知推送 | 免费(公开仓库不限量,私有仓库每月 2000 分钟免费额度,绰绰有余)|
| 定投提醒、止损止盈、全部买卖信号 | 免费 |
| AI 点评(`ai_advisor.py`)| 需要 Anthropic API key,按量付费(每天约几美分)。**不配置就自动跳过,其他功能不受影响** |

> 免费替代方案:每次收到通知后,把日报内容粘贴到 claude.ai 对话里让 Claude 点评,用你现有的 Claude 订阅即可,零额外成本。

## ⚠️ 风险提示(必读)

- **没有任何工具或策略能"保证"年化 20%。** 20% 是进取型目标,长期做到这个水平是巴菲特级别;追求它意味着要接受 -20% 甚至更深的回撤。
- 本工具输出的是规则化信号和参考意见,**不是投资建议**,决策永远在你。
- 定投的优势恰恰是平滑波动:跌的时候同样的钱买到更多份额,坚持比择时重要。

## 当前方案:每月 AUD 2,000 定投(ASX 上市 ETF)

人在澳洲,直接买澳交所上市的 ETF:澳元计价免换汇、普通券商(CommSec / Stake / SelfWealth / IBKR 等)都能买,照样获得美股科技敞口:

| 标的 | 占比 | 每月 | 是什么 |
|---|---|---|---|
| NDQ.AX | 35% | $700 | BetaShares 纳指100 —— 美股科技核心 |
| IVV.AX | 25% | $500 | iShares 标普500 —— 美股大盘基石 |
| SEMI.AX | 15% | $300 | BetaShares 全球半导体 —— AI 算力进攻仓(高波动)|
| VAS.AX | 15% | $300 | Vanguard 澳洲300 —— 本土市场 + 股息抵免(franking credits)|
| GOLD.AX | 10% | $200 | 黄金 ETF —— 对冲仓 |

这是一个 75% 股票(偏科技)+ 15% 本土 + 10% 黄金的进取型配置。想更稳就提高 IVV/VAS 比例、降低 SEMI;想更激进则反之。全部在 `portfolio.json` 的 `dca_plan` 里改。

## 使用流程

1. **每月初**:收到「月度定投」通知,按金额下单买入。
2. **买入后**:把成交记录加进 `portfolio.json` 的 `holdings`,例如:
   ```json
   {"symbol": "NDQ.AX", "shares": 13, "cost_basis": 52.30, "target_weight": 0.35, "note": "纳指100"}
   ```
   (`cost_basis` 填你的平均成本;以后每次加仓后更新股数和均价)
3. **之后**:助手自动监控你的持仓,触发止损/止盈/趋势信号时推送提醒。
4. **观察列表**:`watchlist` 里的个股(NVDA、MSFT 等)出现大幅回调或超卖时也会提醒,供你判断要不要单独配置。

## 快速开始

### GitHub 自动推送(推荐)

1. workflow 每周三 13:00 左右(悉尼时间)自动运行,创建「本周仓位指令」Issue:有调整列出待执行操作,无调整也会告知"继续持有";每月第一个周三附带定投清单。
2. 手机装 GitHub App 并 watch 本仓库,即可收到 Issue 通知。
3. (可选)Settings → Secrets and variables → Actions 添加 `ANTHROPIC_API_KEY` 开启 AI 点评。
4. 随时可在 Actions 页面手动 **Run workflow** 立即检查。

### 本地运行

```bash
cd INVESTMENT_ASSISTANT
pip install -r requirements.txt
python assistant.py          # 生成 report.md + alerts.json
```

## 规则参数(portfolio.json → rules)

| 参数 | 默认 | 含义 |
|---|---|---|
| `stop_loss_pct` | 0.12 | 止损线(亏 12% 提醒卖)|
| `take_profit_pct` | 0.35 | 止盈线(赚 35% 提醒锁利)|
| `dip_buy_pct` | 0.10 | 观察标的回调多少进入买入关注 |
| `rebalance_drift_pct` | 0.05 | 权重偏离多少提醒再平衡 |
| `sma_short` / `sma_long` | 20 / 50 | 趋势均线参数 |
| `rsi_overbought` / `rsi_oversold` | 72 / 30 | 超买/超卖阈值 |
| `dca_plan.remind_window_days` | 3 | 每月前几天内提醒定投 |

> 澳股代码在 Yahoo Finance 带 `.AX` 后缀(如 VAS.AX);美股直接用代码(如 NVDA)。两边可以混用,但建议持仓以同一币种为主,市值统计才准确。
>
> 本项目仅供学习参考,不构成投资建议。投资有风险,入市需谨慎。
