# -*- coding: utf-8 -*-
"""Laya 经典场景 1：Router 多语言自动路由。

Router 是官方推荐入口：在毫秒级内检测脚本/语言，自动把请求路由到
最优 checkpoint（英文 -> laya，非英文 -> laya-multilingual），
一次前向传播即可回答 choice / score / noul 三类 typed 问题。
"""
import os

# 国内网络直连 Hugging Face 不通，走 hf-mirror 镜像
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # 国内网络 xet CAS 服务 401，改走常规 HTTPS

from laya import Router

# 定义三类 typed 问题（choice / score / noul）
questions = {
    "department": {
        "type": "choice",
        "instructions": "Which department should handle this?",
        "criteria": {
            "billing": "invoices, payments, refunds",
            "technical": "bugs, outages, system errors",
            "sales": "pricing, new contracts",
            "other": "everything else",
        },
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent is this?",
        "criteria": ["not urgent", "soon", "blocking"],
    },
    "churn_risk": {
        "type": "noul",
        "instructions": "Does the user threaten to cancel or leave?",
    },
}

# lazy 路由：仅在某个语言首次出现时才下载对应 checkpoint
router = Router(device="cpu")

print("=" * 64)
print("场景 1：Router 多语言自动路由")
print("=" * 64)

# 1) 英文状态 -> 自动路由到英文 checkpoint (laya)
state_en = "Hi, we were billed twice for March. Please refund the duplicate today or we will cancel our plan."
res_en = router.predict(state_en, questions)
print("\n[英文] state:", state_en)
print("  路由 ->", res_en["routing"]["model"])
print("  部门  ->", res_en["answers"]["department"]["choice"],
      "(confidence=%.2f)" % res_en["answers"]["department"]["confidence"])
print("  紧急度->", res_en["answers"]["urgency"]["score"])
print("  流失风险 P(true) -> %.3f" % res_en["answers"]["churn_risk"]["noul"])

# 2) 印地语状态 -> 自动路由到多语言 checkpoint (laya-multilingual)
state_hi = "मुझसे मार्च में दो बार शुल्क लिया गया, कृपया डुप्लिकेट राशि वापस करें।"
res_hi = router.predict({"body": state_hi}, questions)
print("\n[印地语] state:", state_hi)
print("  路由 ->", res_hi["routing"]["model"])
print("  部门  ->", res_hi["answers"]["department"]["choice"],
      "(confidence=%.2f)" % res_hi["answers"]["department"]["confidence"])

# 3) 路由元数据：说明为什么这样选
print("\n[路由决策元数据]")
print("  英文  :", res_en["routing"])
print("  印地语:", res_hi["routing"])

# 4) 只做路由判断，不跑任何前向传播
rd = router.route({"body": "Der Kunde wurde zweimal belastet"}, questions)
print("\n[纯路由判断，无前向传播] 德语 ->", rd.model, "| reason:", rd.reason)
