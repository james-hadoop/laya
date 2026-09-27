# -*- coding: utf-8 -*-
"""laya × semantica 联动场景 3：laya 退款审批 → semantica 策略合规门禁（Govern）。

联动点：
  laya      —— 对每笔退款请求做“批准/拒绝”决策，输出结果 + 校准置信度。
  semantica —— 决策智能生命周期的「Govern」阶段：check_decision_rules 对每个 laya 决策
               执行策略门禁（置信度阈值、outcome 白名单、必填字段），低置信度/异常决策被拦截。
"""
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
sys.path.insert(0, r"D:/_AllDocMap/02_Project/github/laya")
sys.path.insert(0, r"D:/_AllDocMap/02_Project/github/semantica")

import laya
from semantica.context import ContextGraph

print("=" * 66)
print("场景 3：laya 退款审批 → semantica 策略合规门禁 (Govern)")
print("=" * 66)

graph = ContextGraph(advanced_analytics=False)
agent = laya.load("convaiinnovations/laya", device="cpu")
print("已加载 laya:", agent)

# laya 的“退款审批”决策问题：noul 布尔判断（P(approve)），校准置信度比 2-option choice 更可靠
refund_questions = {
    "approve_refund": {
        "type": "noul",
        "instructions": "Should this refund request be approved?",
        "criteria": {
            "true": "clear billing error or duplicate charge — approve refund",
            "false": "no valid refund reason — reject refund",
        },
    },
}

requests = [
    ("req_1", "We were charged twice for March, please refund the duplicate."),   # 应批准
    ("req_2", "I just changed my mind, give me my money back."),                  # 应拒绝
    ("req_3", "My account shows an unknown $500 charge I never made."),           # 应批准
]

# semantica 策略规则：门禁（默认要求 confidence>=0.7、outcome 在白名单、decision_maker 必填）
rules = {
    "min_confidence": 0.6,
    "required_outcomes": ["approved", "rejected"],
    "required_metadata": ["decision_maker"],
    "max_reasoning_length": 10000,
}

print("\n—— laya 决策 → semantica check_decision_rules 合规门禁 ——")
for req_id, text in requests:
    r = agent.predict({"message": text}, refund_questions)
    ans = r["answers"]["approve_refund"]
    p_approve = ans["noul"]           # P(approve)
    outcome = "approved" if p_approve >= 0.5 else "rejected"
    conf = ans["confidence"]          # noul 的校准置信度

    # 记录决策到 semantica
    did = graph.record_decision(
        category="refund_approval",
        scenario=text,
        reasoning="laya approve_refund P(approve)=%.3f → %s" % (p_approve, outcome),
        outcome=outcome,
        confidence=conf,
        entities=[req_id],
        decision_maker="laya-0.3.20",
    )

    # 策略门禁检查
    verdict = graph.check_decision_rules(
        decision_data={
            "outcome": outcome,
            "confidence": conf,
            "decision_maker": "laya-0.3.20",
            "reasoning": "laya approve_refund P(approve)=%.3f → %s" % (p_approve, outcome),
        },
        rules=rules,
    )
    flag = "✅ 通过" if verdict["compliant"] else "⛔ 拦截"
    print("  %-6s → %-8s conf=%.2f | %s" % (req_id, outcome, conf, flag))
    if verdict["violations"]:
        for v in verdict["violations"]:
            print("       违规: %s" % v)
    if verdict["warnings"]:
        for w in verdict["warnings"]:
            print("       警告: %s" % w)

insights = graph.get_decision_insights()
print("\n[semantica 审批结果分布]", insights.get("outcomes"))
print("[semantica 决策图] %d 节点 / %d 边" % (len(graph.nodes), len(graph.edges)))
