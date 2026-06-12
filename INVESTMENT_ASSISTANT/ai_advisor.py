#!/usr/bin/env python3
"""AI 投资顾问 — 调用 Claude 对当日组合与信号做"华尔街经理式"点评。

需要环境变量 ANTHROPIC_API_KEY。在 assistant.py 之后运行,
读取 report.md / alerts.json / portfolio.json,把 AI 分析追加到 report.md。
未设置 API key 时静默跳过(规则信号仍然有效)。
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
REPORT_PATH = BASE_DIR / "report.md"

SYSTEM_PROMPT = """你是一位经验丰富的华尔街投资组合经理,为一位目标年化收益约20%的进取型个人投资者服务。
你会收到他的持仓快照、今日规则化买卖信号和组合配置。

请用中文输出一份简短的当日点评,包含:
1. 宏观与市场环境:结合你对当前美股市场、利率环境、行业轮动的判断(说明你的知识有时效局限)。
2. 对今日各条信号的专业意见:同意/不同意,为什么,优先级如何。
3. 组合体检:集中度、行业暴露、与20%目标的匹配度,以及当前最大的风险点。
4. 一条本周最值得执行的具体行动。

风格:直接、给结论、不堆砌套话。明确提示风险,绝不承诺收益。控制在500字以内。"""


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY 未设置,跳过 AI 分析。", file=sys.stderr)
        return

    import anthropic

    portfolio = (BASE_DIR / "portfolio.json").read_text(encoding="utf-8")
    alerts = (BASE_DIR / "alerts.json").read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"## 组合配置\n```json\n{portfolio}\n```\n\n"
                f"## 今日信号\n```json\n{alerts}\n```\n\n"
                f"## 今日报告\n{report}\n\n请给出你的当日点评。"
            ),
        }],
    ) as stream:
        message = stream.get_final_message()

    analysis = next((b.text for b in message.content if b.type == "text"), "")
    if not analysis:
        print("AI 未返回文本内容,跳过追加。", file=sys.stderr)
        return

    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write("\n\n## 🧠 AI 投资经理点评(Claude)\n\n")
        f.write(analysis)
        f.write("\n")
    print("AI 分析已追加到 report.md")


if __name__ == "__main__":
    main()
