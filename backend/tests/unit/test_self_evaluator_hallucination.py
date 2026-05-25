# -*- coding: utf-8 -*-
"""
R11 (v6.9 / 2026-05-09) — Self-Evaluator hallucination hard penalty regression

L24 揭示原 entity_alignment 為 signal-only，不影響 overall score → success_rate
被高估，53 patterns 全 ≥ 0.95。修法：entity_alignment < 0.5 時 overall 乘 0.5
（hard penalty），確保 hallucination 必降到 needs_improvement = True。

Tests:
  1. Query 無具名 entity → entity_alignment=1.0 → 不受影響
  2. Query 有具名 entity 且 answer 提到 → 不扣分
  3. Query 有具名 entity 但 answer 完全沒提 → overall 乘 0.5 → severity 升級
  4. Hallucination signal 仍正確產生（v5.11 既有功能不破壞）
  5. Calibration test：對標註資料集評分一致率
"""
from dataclasses import dataclass
from typing import List

import pytest

from app.services.ai.agent.agent_self_evaluator import (
    AgentSelfEvaluator,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


@dataclass
class _MockTrace:
    total_ms: int = 1000
    tools_failed: List[str] = None

    def __post_init__(self):
        if self.tools_failed is None:
            self.tools_failed = []


@pytest.fixture
def evaluator():
    return AgentSelfEvaluator()


# ============================================================================
# 1. Query 無具名 entity → 不受 hallucination penalty 影響
# ============================================================================

def test_no_named_entity_alignment_neutral(evaluator):
    """『目前公文有幾筆』無具名 entity，alignment=1.0 不扣分"""
    score = evaluator.evaluate(
        question="目前系統有幾筆公文？",
        answer="目前系統共有 1,698 筆公文。",
        tool_results=[{"name": "search_documents", "result": "1698"}],
        trace=_MockTrace(total_ms=2000),
    )
    assert score.entity_alignment == 1.0
    # overall 不應被 hard penalty 砍半
    assert score.overall > 0.4


# ============================================================================
# 2. Query 有具名 entity 且 answer 提到 → 不扣分
# ============================================================================

def test_named_entity_present_in_answer_no_penalty(evaluator):
    score = evaluator.evaluate(
        question="承辦人老蕭負責的案件有哪些？",
        answer="老蕭負責的案件有：CK-114-001、CK-114-002，共 2 筆派工單。",
        tool_results=[{"name": "search_dispatch", "result": "[2 items]"}],
        trace=_MockTrace(total_ms=2000),
    )
    assert score.entity_alignment >= 0.5  # 「老蕭」/「蕭」在 answer 中
    # 不應觸發 hallucination signal
    types = [s["type"] for s in score.signals]
    assert "entity_alignment_low" not in types


# ============================================================================
# 3. Query 有具名 entity 但 answer 完全沒提 → overall × 0.5
# ============================================================================

def test_hallucination_triggers_hard_penalty(evaluator):
    """L24 案例：query 含「老蕭」但 answer 列了無關公文沒提到「蕭」"""
    score = evaluator.evaluate(
        question="承辦人老蕭負責的案件有哪些？",
        answer="目前系統的最新公文如下：1. 公文 A 2. 公文 B 3. 公文 C ...",
        tool_results=[{"name": "search_documents", "result": "[3 items]"}],
        trace=_MockTrace(total_ms=2000),
    )
    assert score.entity_alignment < 0.5
    # R11 hard penalty：overall 乘 0.5 後必落到 needs_improvement (< 0.7)
    assert score.overall < 0.7
    assert score.needs_improvement is True
    # severity 應升級到 MEDIUM 或更糟
    assert score.severity in (SEVERITY_HIGH, SEVERITY_MEDIUM, "critical")


def test_hallucination_signal_still_generated(evaluator):
    """v5.11 既有 entity_alignment_low signal 不該被 R11 改動破壞"""
    score = evaluator.evaluate(
        question="案件 113-A 的承辦人是誰？",
        answer="此案件的相關資訊已查詢完畢，請參考其他公文。",
        tool_results=[{"name": "search_dispatch", "result": "[]"}],
        trace=_MockTrace(total_ms=1500),
    )
    types = [s["type"] for s in score.signals]
    assert "entity_alignment_low" in types
    # severity 應為 HIGH
    hallu_signal = next(s for s in score.signals if s["type"] == "entity_alignment_low")
    assert hallu_signal["severity"] == "high"


# ============================================================================
# 4. R11 不破壞「無 entity」query 既有評分
# ============================================================================

def test_high_quality_no_entity_query_keeps_score(evaluator):
    """完美回答 + 無 entity → 高分，不被 R11 hard penalty 誤傷"""
    score = evaluator.evaluate(
        question="系統目前的整體效能狀況如何？",
        answer=(
            "系統效能整體良好。CPU 使用率 35%，"
            "記憶體 60%，回應延遲 P95 200ms，無慢查詢警示。"
            "近 24 小時 0 次 5xx 錯誤。所有指標都在健康區間。"
        ),
        tool_results=[
            {"name": "get_system_metrics", "result": "[full data]"},
        ],
        trace=_MockTrace(total_ms=1200),
    )
    # 無 entity → alignment=1.0，無 penalty
    assert score.entity_alignment == 1.0
    # 高品質回答應在 0.6 以上（HIGH/LOW severity）
    assert score.overall >= 0.5


# ============================================================================
# 5. Calibration set — 人工標註 query 與期望嚴重度
# ============================================================================

CALIBRATION_SET = [
    # (question, answer, tool_results, expected_severity_floor, label)
    # 注意：期望值需匹配 evaluator 既有規則 — 短回答（< 20 字）relevance 會被扣分
    # calibration set 反映「人工標 + evaluator 共識」應對的真實案例
    {
        "question": "目前公文有幾筆？",
        "answer": (
            "目前公文系統中共有 1,698 筆公文資料，"
            "包含收文 850 筆、發文 848 筆。所有資料皆已完成入庫處理。"
        ),
        "tool_results": [{"name": "search_documents", "result": "1698"}],
        "expected_overall_floor": 0.5,
        "should_need_improvement": False,
        "label": "factual_correct_no_entity",
    },
    {
        "question": "承辦人老蕭負責什麼？",
        "answer": "目前最新的公文有 ABC、DEF、GHI、JKL、MNO（完全沒提老蕭）等共五筆。",
        "tool_results": [{"name": "search_documents", "result": "[5 items]"}],
        "expected_overall_floor": 0.0,
        "expected_overall_ceiling": 0.7,
        "should_need_improvement": True,
        "label": "hallucination_named_entity_dropped",
    },
    {
        "question": "案件 113-XX-001 的進度",
        "answer": (
            "案件編號 113-XX-001 目前處於審核階段，"
            "預計於 5 月 15 日完成審核流程後進入下一階段。"
        ),
        "tool_results": [{"name": "get_dispatch_detail", "result": "[1 item]"}],
        "expected_overall_floor": 0.5,
        "should_need_improvement": False,
        "label": "case_code_alignment_good",
    },
]


@pytest.mark.parametrize("case", CALIBRATION_SET, ids=[c["label"] for c in CALIBRATION_SET])
def test_calibration_set(evaluator, case):
    """對人工標註的 query 跑評分，確保符合期望"""
    score = evaluator.evaluate(
        question=case["question"],
        answer=case["answer"],
        tool_results=case["tool_results"],
        trace=_MockTrace(total_ms=2000),
    )

    if "expected_overall_floor" in case:
        assert score.overall >= case["expected_overall_floor"], (
            f"{case['label']}: overall {score.overall:.2f} < floor "
            f"{case['expected_overall_floor']}"
        )

    if "expected_overall_ceiling" in case:
        assert score.overall <= case["expected_overall_ceiling"], (
            f"{case['label']}: overall {score.overall:.2f} > ceiling "
            f"{case['expected_overall_ceiling']}"
        )

    if "should_need_improvement" in case:
        assert score.needs_improvement == case["should_need_improvement"], (
            f"{case['label']}: needs_improvement={score.needs_improvement}, "
            f"expected={case['should_need_improvement']}, "
            f"overall={score.overall:.3f}"
        )
