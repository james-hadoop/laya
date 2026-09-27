# -*- coding: utf-8 -*-
"""laya × semantica 联动场景 1：laya 快速决策 → semantica 决策记录与图溯源（Record）。

联动点：
  laya      —— 非自回归 System 1 决策引擎：33ms 一次前向传播返回分类/打分/布尔 + 校准置信度。
  semantica —— 决策智能生命周期的「Record」阶段：把每个 laya 决策（连同置信度、实体、元数据、
               决策者、时间）写入决策图，形成可审计的决策溯源。
"""
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # 国内网络 xet CAS 401，走常规 HTTPS
sys.path.insert(0, r"D:/_AllDocMap/02_Project/github/laya")
sys.path.insert(0, r"D:/_AllDocMap/02_Project/github/semantica")

import laya
from semantica.context import ContextGraph

print("=" * 66)
print("场景 1：laya 决策 → semantica 决策记录与图溯源 (Record)")
print("=" * 66)

# semantica 决策图（关闭重型图分析，聚焦决策记录与溯源）
graph = ContextGraph(advanced_analytics=False)

# laya 英文决策引擎（模型已缓存，秒级加载）
agent = laya.load("convaiinnovations/laya", device="cpu")
print("已加载 laya:", agent)

tickets = [
    ("billing",      "We were billed twice for March, please refund the duplicate today."),
    ("technical",    "My app crashes every time I open settings."),
    ("sales",        "Can I get a discount on the annual plan?"),
    ("cancellation", "I want to downgrade to the free plan immediately."),
]

# —— laya 决策 → semantica 记录 ——
print("\n—— laya 决策 → semantica record_decision ——")
for topic, text in tickets:
    r = agent.predict({"message": text}, laya.triage_questions())
    ans = r["answers"]
    intent = ans["intent"]["choice"]
    conf = ans["intent"]["confidence"]
    urgent = ans["is_urgent"]["noul"]
    churn = ans["churn_risk"]["noul"]

    did = graph.record_decision(
        category="ticket_triage",
        scenario=text,
        reasoning="laya 一次前向传播：intent=%s urgent=%.2f churn_risk=%.2f" % (intent, urgent, churn),
        outcome=intent,
        confidence=conf,
        entities=[topic],
        decision_maker="laya-0.3.20",
        metadata={"is_urgent": round(urgent, 3), "churn_risk": round(churn, 3)},
    )
    print("  laya→%-14s conf=%.2f | semantica 记录 %s" % (intent, conf, did[:8]))

# —— semantica 决策图溯源 ——
insights = graph.get_decision_insights()
print("\n[semantica 决策图溯源]")
print("  决策总数   :", insights.get("total_decisions"))
print("  类别分布   :", insights.get("categories"))
print("  结果分布   :", insights.get("outcomes"))
print("  置信度统计 : mean=%.2f min=%.2f max=%.2f" % (
    insights["confidence_stats"]["mean"],
    insights["confidence_stats"]["min"],
    insights["confidence_stats"]["max"],
))
print("  图规模     : %d 节点 / %d 边" % (len(graph.nodes), len(graph.edges)))
