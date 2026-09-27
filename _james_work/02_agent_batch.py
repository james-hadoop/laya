# -*- coding: utf-8 -*-
"""Laya 经典场景 2：单模型 SDK + 批量打分 (predict_batch)。

直接加载单个 checkpoint，`predict` 逐条打分；当有一批工单/表格/日志
要按同一组问题打分时，`predict_batch` 把它们打包进共享的前向传播，
充分用满 batch 维度（GPU 上吞吐可提升 ~9-10x）。
"""
import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # 国内网络 xet CAS 服务 401，改走常规 HTTPS

import laya

questions = {
    "intent": {
        "type": "choice",
        "instructions": "What is the customer's intent?",
        "criteria": {
            "refund": "wants money back",
            "technical_help": "bug or outage",
            "billing_question": "invoice or plan question",
            "cancellation": "wants to cancel",
        },
    },
    "is_urgent": {
        "type": "noul",
        "instructions": "Is there time pressure or a deadline?",
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated is the customer?",
        "criteria": ["calm", "concerned", "annoyed", "very angry"],
    },
}

print("=" * 64)
print("场景 2：单模型 SDK + 批量打分")
print("=" * 64)

# 直接加载英文 checkpoint（repo 根目录）
agent = laya.load("convaiinnovations/laya", device="cpu")
print("已加载:", agent)

# 1) 单条预测
state = "We were billed twice for March, please refund the duplicate today."
res = agent.predict(state, questions)
print("\n[单条 predict]")
print("  intent     ->", res["answers"]["intent"]["choice"])
print("  is_urgent  -> %.3f" % res["answers"]["is_urgent"]["noul"])
print("  frustration->", res["answers"]["frustration"]["score"])
print("  usage      ->", res["usage"])

# 2) 批量预测：一条前向传播打一整批工单
ticket_texts = [
    "My app crashes every time I open settings.",
    "Can you explain the charge on my last invoice?",
    "I want to downgrade to the free plan immediately.",
    "The checkout page is down and we are losing sales right now.",
    "Please refund the duplicate charge on my card.",
]
states = [{"body": t} for t in ticket_texts]

results = agent.predict_batch(states, questions)

print("\n[批量 predict_batch，%d 条共享前向传播]" % len(results))
for i, (t, r) in enumerate(zip(ticket_texts, results), 1):
    ans = r["answers"]
    print("  %d) %-52s | intent=%s | urgent=%.2f | frust=%s" % (
        i, t[:52], ans["intent"]["choice"], ans["is_urgent"]["noul"], ans["frustration"]["score"],
    ))
