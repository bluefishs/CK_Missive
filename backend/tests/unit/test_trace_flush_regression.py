# -*- coding: utf-8 -*-
"""Trace flush regression tests — 三層 silent failure 修復驗證（2026-04-20）。

覆盤發現 agent_query_traces 在產線長期空寫入，兩批修復共揭露三層根因：
1. `_flush_trace_lightweight` fire-and-forget 背景 task 共用 orchestrator
   session，FastAPI request 結束後 session 被 dispose → save 失敗
2. `context` 欄位 varchar(20) 被寫入長字串 → StringDataRightTruncationError
3. `run_with_fresh_session` 退出時 commit，但 save_trace 內部已 commit →
   'This transaction is closed'

本檔案鎖定這三點，防止未來重構時無意重現。
"""
from __future__ import annotations


# ────────── 1. Context truncation ──────────

def test_trace_to_db_dict_truncates_long_context():
    """context varchar(20) — 長字串必須被截斷，否則 StringDataRightTruncationError。"""
    from app.services.ai.agent.agent_trace import AgentTrace

    trace = AgentTrace(
        query_id="test-ctx",
        question="測試",
        context="[自我覺察] 擅長[自我覺察] 擅長[自我覺察] 擅長[自我覺察] 系統資料暫時無法存取",
    )
    d = trace.to_db_dict()
    assert d["context"] is None or len(d["context"]) <= 20, (
        f"context must be <=20 chars, got len={len(d.get('context') or '')}"
    )


def test_trace_to_db_dict_preserves_short_context():
    """短 context 不該被切斷。"""
    from app.services.ai.agent.agent_trace import AgentTrace
    trace = AgentTrace(query_id="t", question="q", context="doc")
    assert trace.to_db_dict()["context"] == "doc"


def test_trace_to_db_dict_none_context_ok():
    """None context 保持 None。"""
    from app.services.ai.agent.agent_trace import AgentTrace
    trace = AgentTrace(query_id="t", question="q", context=None)
    assert trace.to_db_dict()["context"] is None


def test_trace_to_db_dict_truncates_long_route_type():
    """route_type 也是 varchar(20)，超長同樣被截斷。"""
    from app.services.ai.agent.agent_trace import AgentTrace
    trace = AgentTrace(query_id="t", question="q")
    trace.route_type = "x" * 50  # 故意塞 50 字
    assert len(trace.to_db_dict()["route_type"]) <= 20


def test_trace_to_db_dict_route_type_defaults_llm():
    """route_type 未設時 default 'llm'，不該被 [:20] 改變。"""
    from app.services.ai.agent.agent_trace import AgentTrace
    trace = AgentTrace(query_id="t", question="q")
    # 不設 route_type
    assert trace.to_db_dict()["route_type"] == "llm"


def test_trace_to_db_dict_truncates_long_model_used():
    """model_used varchar(50) — 長 model 名要截斷（e.g. NIM 全名 > 50 chars）。"""
    from app.services.ai.agent.agent_trace import AgentTrace
    trace = AgentTrace(query_id="t", question="q")
    trace._model_used = "nvidia/meta-llama-3.3-nemotron-super-49b-v1.5-extended"  # 53 chars
    assert len(trace.to_db_dict()["model_used"]) <= 50


# ────────── 2. run_with_fresh_session_no_commit 存在且不做外層 commit ──────────

def test_run_with_fresh_session_no_commit_exists():
    """helper 必須存在——orchestrator 和 timeout path 皆依賴。"""
    from app.db.database import run_with_fresh_session_no_commit
    assert callable(run_with_fresh_session_no_commit)


def test_run_with_fresh_session_no_commit_signature():
    """確保函式簽名維持單一 coroutine 參數（避免未來誤改介面）。"""
    import inspect
    from app.db.database import run_with_fresh_session_no_commit
    sig = inspect.signature(run_with_fresh_session_no_commit)
    params = list(sig.parameters.keys())
    assert params == ["fn"], f"Expected ['fn'], got {params}"


# ────────── 3. Orchestrator 使用 no_commit 變體 ──────────

def test_orchestrator_lightweight_flush_uses_no_commit():
    """
    `_flush_trace_lightweight` 源碼必須用 `run_with_fresh_session_no_commit`
    而非舊版本 `run_with_fresh_session`（雙重 commit bug）。
    """
    from pathlib import Path
    orchestrator = (
        Path(__file__).parents[2]
        / "app" / "services" / "ai" / "agent" / "agent_orchestrator.py"
    )
    src = orchestrator.read_text(encoding="utf-8")
    # 可能兩個 helper 都 import（歷史），但 lightweight flush 必須用 no_commit
    idx = src.index("_flush_trace_lightweight")
    # 看函式定義後 ~25 行內出現 no_commit
    window = src[idx:idx + 2500]
    assert "run_with_fresh_session_no_commit" in window, (
        "lightweight flush must use no_commit helper to avoid double commit"
    )


# ────────── 4. Timeout path 有寫 trace helper ──────────

def test_timeout_path_has_flush_helper():
    """agent_query_sync.py 必須有 _flush_timeout_trace 函式（timeout path 寫 trace）。"""
    from app.api.endpoints.ai import agent_query_sync
    assert hasattr(agent_query_sync, "_flush_timeout_trace")


def test_timeout_flush_helper_is_async():
    """必須是 async coroutine（會被 asyncio.create_task 背景化）。"""
    import asyncio
    from app.api.endpoints.ai.agent_query_sync import _flush_timeout_trace
    assert asyncio.iscoroutinefunction(_flush_timeout_trace)
