# -*- coding: utf-8 -*-
"""laya × semantica 联动场景 2：laya 流失预警 → semantica 因果链 + 先例检索（Link / Query）。

联动点：
  laya      —— 判断每个客户的流失风险（churn_risk）与意图，输出 P(true) 概率。
  semantica —— 决策智能生命周期的「Link」+「Query」阶段：
              · add_causal_relationship  把“高风险”决策与“升级人工”决策连成因果链；
              · find_precedents_by_scenario  检索相似历史决策（先例）；
              · trace_decision_causality     追踪某个决策的完整因果链。
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
print("场景 2：laya 流失预警 → semantica 因果链 + 先例检索 (Link/Query)")
print("=" * 66)

graph = ContextGraph(advanced_analytics=False)
agent = laya.load("convaiinnovations/laya", device="cpu")
print("已加载 laya:", agent)

customers = [
    ("acme",   "Your support ignored my ticket for a week. We will move to a competitor."),
    ("globex", "Can you tell me how to enable two-factor authentication?"),
    ("initech", "The price went up again and this outage is unacceptable. We're leaving."),
]

# 1) laya 判断流失风险；semantica 记录“风险”决策
risk_ids = {}
for name, text in customers:
    r = agent.predict({"message": text}, laya.triage_questions())
    ans = r["answers"]
    churn = ans["churn_risk"]["noul"]
    risk_outcome = "high_risk" if churn >= 0.5 else "low_risk"
    did = graph.record_decision(
        category="churn_risk",
        scenario=text,
        reasoning="laya churn_risk P(true)=%.3f" % churn,
        outcome=risk_outcome,
        confidence=ans["churn_risk"]["confidence"],
        entities=[name],
        decision_maker="laya-0.3.20",
        metadata={"p_true": round(churn, 3)},
    )
    risk_ids[name] = (did, risk_outcome)
    print("  %-8s churn P(true)=%.2f → %s  [%s]" % (name, churn, risk_outcome, did[:8]))

# 2) 对高风险客户：记录“升级人工”决策，并建立因果链
print("\n—— semantica add_causal_relationship（高风险 CAUSED 升级人工）——")
escalation_ids = []
for name, text in customers:
    risk_did, risk_outcome = risk_ids[name]
    if risk_outcome == "high_risk":
        esc_did = graph.record_decision(
            category="escalation",
            scenario=text,
            reasoning="churn_risk=high，需人工介入挽留",
            outcome="escalate_to_human",
            confidence=0.9,
            entities=[name],
            decision_maker="policy-rule",
        )
        ok = graph.add_causal_relationship(risk_did, esc_did, "CAUSED")
        escalation_ids.append(esc_did)
        print("  高风险 %-8s → 升级决策 %s  (因果边插入=%s)" % (name, esc_did[:8], ok))

# 3) 先例检索：找一个高风险场景，检索相似历史决策
print("\n—— semantica find_precedents_by_scenario（相似先例检索）——")
query = "The customer is furious about repeated outages and threatens to cancel."
precedents = graph.find_precedents_by_scenario(
    query, category="churn_risk", limit=3, similarity_threshold=0.0,
)
print("  查询场景: %s" % query)
if precedents:
    for p in precedents:
        d = p["decision"]
        print("   相似度=%.3f | %s | outcome=%s | conf=%.2f" % (
            p["similarity"], d["scenario"][:40], d["outcome"], d["confidence"],
        ))
else:
    print("  （未检索到超过阈值的先例）")

# 4) 因果链追踪：从“升级人工”决策回溯其成因
print("\n—— semantica trace_decision_causality（因果链追踪）——")
for esc_did in escalation_ids:
    chains = graph.trace_decision_causality(esc_did)
    print("  升级决策 %s 的因果链:" % esc_did[:8])
    if chains:
        for chain in chains:
            # 每条链是一条有序路径，展示其中的决策 outcome
            path = chain if isinstance(chain, list) else chain.get("chain", chain)
            print("    ", path)
    else:
        print("    （无显式因果链）")

print("\n[semantica 决策图] %d 节点 / %d 边" % (len(graph.nodes), len(graph.edges)))
