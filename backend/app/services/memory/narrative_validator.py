# -*- coding: utf-8 -*-
"""Narrative Validator — 週自傳品質閘

2026-04-19 Memory Wiki Phase 4。

檢查：
- 長度 100~600 字
- 不含簡體字（常見字符檢測）
- 不含 API key / token / URL 模式
- 至少含 1 個具體數字（query 數/成功率/案號）
- 不超過 3 個模糊詞（「可能」「大概」「或許」）
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


# 常見簡體字（非窮舉，只擋高頻）
SIMPLIFIED_BLOCKLIST = set(
    "实体关系统计数据节点查询文档系统这个这样这里那个为这时间说话发送录这种这次这么对话系统"
    "这儿这样这些这样这种这点这里进展进行获取连接认为见证简单广告发现发生灵感觉得觉得个别"
)
# 真正需要擋的簡體字（正體對應註記 — 只列繁中不使用的獨有簡體字形）
# 注意：「那/查/獲/個/關/數/查/詢/系/統」等繁簡同形或繁體仍正確使用，已移除
CORE_SIMPLIFIED = set("这为时说发种对样们么觉广")


SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),                 # OpenAI style（含 sk-proj-... 變體）
    re.compile(r"gsk_[a-zA-Z0-9_\-]{30,}"),                # Groq
    re.compile(r"eyJ[A-Za-z0-9_\-=]+\.[A-Za-z0-9_\-=]+\.[A-Za-z0-9_.\-=]+"),  # JWT
    re.compile(r"MCP_SERVICE_TOKEN[\"':\s=]+[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?:password|secret|api_key)[\"':\s=]+[^\s\"']{8,}", re.IGNORECASE),
]

VAGUE_WORDS = ["可能", "大概", "或許", "也許", "似乎", "應該", "差不多"]


@dataclass
class ValidationResult:
    ok: bool
    reasons: List[str]
    stats: dict


def validate_narrative(text: str) -> ValidationResult:
    """驗證週自傳品質。"""
    reasons: List[str] = []

    if not text or not text.strip():
        return ValidationResult(ok=False, reasons=["empty"], stats={})

    t = text.strip()
    length = len(t)

    stats = {
        "length": length,
        "simplified_chars": 0,
        "secrets": 0,
        "numbers": 0,
        "vague_count": 0,
    }

    # Length
    if length < 100:
        reasons.append(f"too_short ({length} < 100)")
    if length > 600:
        reasons.append(f"too_long ({length} > 600)")

    # Simplified Chinese
    sim_chars = [ch for ch in t if ch in CORE_SIMPLIFIED]
    stats["simplified_chars"] = len(sim_chars)
    if sim_chars:
        reasons.append(f"simplified_chinese: {''.join(set(sim_chars))[:10]}")

    # Secrets
    secret_hits = []
    for pat in SECRET_PATTERNS:
        hits = pat.findall(t)
        if hits:
            secret_hits.extend(hits)
    stats["secrets"] = len(secret_hits)
    if secret_hits:
        reasons.append(f"secret_leak ({len(secret_hits)} match)")

    # Numbers（至少 1 個）
    num_matches = re.findall(r"\d+(?:[,.]\d+)*", t)
    stats["numbers"] = len(num_matches)
    if len(num_matches) < 1:
        reasons.append("no_concrete_numbers")

    # Vague words
    vague_count = sum(t.count(w) for w in VAGUE_WORDS)
    stats["vague_count"] = vague_count
    if vague_count > 3:
        reasons.append(f"too_vague ({vague_count} vague words)")

    return ValidationResult(ok=(len(reasons) == 0), reasons=reasons, stats=stats)
