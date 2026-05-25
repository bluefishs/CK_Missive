# -*- coding: utf-8 -*-
"""
L29 (v6.9 / 2026-05-09) — Domain score tracking regression

防範「坤哥自我成長中斷」第 N 次重演。

過去事故鏈：
  - L21 (v5.10.2): redis import path + key typo → counter 卡 0 → evolution 0 跑
    修法：app.core.redis_client + agent:evolution:query_count
  - L29 (v6.9):    self_evaluator dict key bug + TOOL_DOMAIN_MAP 涵蓋率 < 25%
    → domain_scores Redis 全空 → domain-aware trigger 5 連續低分永不觸發
    修法：tool.get("tool") + prefix fallback resolver

本檔鎖定：
  1. tool dict key 是 "tool" 不是 "name" — 不能再寫成 .get("name")
  2. resolve_tool_domain 對 19 manual + prefix-based 都能解析
  3. silent except 已改 logger.error（不是 silent pass）
  4. domain_scores 累積真活
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# 1. Tool dict key contract: "tool" 不是 "name"
# ============================================================================

def test_tool_loop_appends_with_tool_key():
    """agent_tool_loop.py 內 tool_results.append 必用 "tool" key。

    self_evaluator 對應讀 .get("tool")，若哪天 tool_loop 改成 .get("name")
    self_evaluator 必須同步——本 test 鎖定契約。
    """
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "app/services/ai/agent/agent_tool_loop.py"
    text = src.read_text(encoding="utf-8")
    # 必含 {"tool": ...} 形式（L312/L381 既有）
    assert '{"tool":' in text, "agent_tool_loop must append dict with 'tool' key"
    # 不該有 {"name": tool_name 形式（防 typo 引回）
    assert '{"name": tool_name' not in text, (
        "Don't change tool dict key from 'tool' to 'name' — "
        "self_evaluator depends on 'tool' (L29 lesson)"
    )


# ============================================================================
# 2. resolve_tool_domain — exact match + prefix fallback
# ============================================================================

def test_resolve_tool_domain_exact_match():
    from app.services.ai.agent.agent_capability_tracker import resolve_tool_domain
    # 19 manual entries 應全 match
    assert resolve_tool_domain("search_documents") == "doc"
    assert resolve_tool_domain("search_dispatch_orders") == "dispatch"
    assert resolve_tool_domain("get_financial_summary") == "erp"
    assert resolve_tool_domain("wiki_search") == "wiki"


def test_resolve_tool_domain_prefix_fallback():
    """未在 manual map 但符合 prefix 規則 → 仍能歸類"""
    from app.services.ai.agent.agent_capability_tracker import resolve_tool_domain
    # 假想新 tool（map 沒有）
    assert resolve_tool_domain("search_dispatch_anything") == "dispatch"
    assert resolve_tool_domain("get_billing_xxxxx") == "erp"
    assert resolve_tool_domain("wiki_anything") == "wiki"


def test_resolve_tool_domain_unknown_returns_none():
    from app.services.ai.agent.agent_capability_tracker import resolve_tool_domain
    assert resolve_tool_domain("totally_random_tool") is None
    assert resolve_tool_domain("") is None
    # skill_* 故意保持 None — skill 是動態的，不參與 domain trigger
    assert resolve_tool_domain("skill_python_common_pitfalls") is None


def test_tool_domain_map_has_minimum_coverage():
    """L29 lesson：原 19 entries 涵蓋率太低，擴到至少 40+"""
    from app.services.ai.agent.agent_capability_tracker import TOOL_DOMAIN_MAP
    assert len(TOOL_DOMAIN_MAP) >= 40, (
        f"TOOL_DOMAIN_MAP only has {len(TOOL_DOMAIN_MAP)} entries — "
        "should be ≥ 40 to cover business tools (L29)"
    )


# ============================================================================
# 3. self_evaluator domain tracking 真活（核心修法）
# ============================================================================

@pytest.mark.asyncio
async def test_evaluator_writes_domain_score_with_correct_tool_key():
    """tool_results 用 "tool" key（真實格式）→ domain_scores 必須被寫入"""
    from app.services.ai.agent.agent_self_evaluator import get_self_evaluator

    # 真實 tool_results 格式（agent_tool_loop.py:312/381 產出）
    tool_results = [
        {"tool": "search_documents", "params": {}, "result": "[5 items]"},
        {"tool": "get_dispatch_detail", "params": {"id": 1}, "result": "{...}"},
    ]

    redis_mock = AsyncMock()
    redis_mock.lpush = AsyncMock(return_value=1)
    redis_mock.ltrim = AsyncMock()
    redis_mock.expire = AsyncMock()
    # signals queue
    redis_mock.lpush.side_effect = None

    class _Trace:
        total_ms = 1500
        tools_failed = []

    evaluator = get_self_evaluator()
    await evaluator.evaluate_and_store(
        question="今日公文有哪些？",
        answer="今日有 5 筆公文，含派工單 3 筆。" * 5,  # ≥ 20 chars
        tool_results=tool_results,
        trace=_Trace(),
        citation_result={"valid": True, "total": 1, "verified": 1},
        redis=redis_mock,
    )

    # 必須對 doc 和 dispatch 兩個 domain 各 lpush 一次
    domain_keys_pushed = []
    for call in redis_mock.lpush.call_args_list:
        key = call.args[0] if call.args else call.kwargs.get("name", "")
        if isinstance(key, str) and key.startswith("agent:domain_scores:"):
            domain_keys_pushed.append(key)

    assert "agent:domain_scores:doc" in domain_keys_pushed, (
        f"L29 修法失效：domain_scores:doc 沒被寫入。實際 push: {domain_keys_pushed}"
    )
    assert "agent:domain_scores:dispatch" in domain_keys_pushed, (
        f"L29 修法失效：domain_scores:dispatch 沒被寫入"
    )


@pytest.mark.asyncio
async def test_evaluator_handles_dict_with_name_key_fallback():
    """tool dict 用 "name" key（其他 caller 假想格式）也要相容（fallback）"""
    from app.services.ai.agent.agent_self_evaluator import get_self_evaluator

    redis_mock = AsyncMock()

    class _Trace:
        total_ms = 1500
        tools_failed = []

    evaluator = get_self_evaluator()
    # "name" key（非 production 主格式，但 fallback 應 work）
    await evaluator.evaluate_and_store(
        question="標案資料",
        answer="找到 5 筆相符標案資訊，內容為..." * 5,
        tool_results=[
            {"name": "wiki_search", "result": "{...}"},
            {"name": "search_entities", "result": "{...}"},
        ],
        trace=_Trace(),
        citation_result={"valid": True},
        redis=redis_mock,
    )

    # wiki_search → wiki, search_entities → graph (via .get("name") fallback)
    domain_keys = [
        c.args[0] for c in redis_mock.lpush.call_args_list
        if c.args and isinstance(c.args[0], str)
        and c.args[0].startswith("agent:domain_scores:")
    ]
    assert "agent:domain_scores:wiki" in domain_keys
    assert "agent:domain_scores:graph" in domain_keys


# ============================================================================
# 4. silent except 防回退 — 失敗必須走 logger.error 不是 pass
# ============================================================================

def test_silent_except_no_longer_used_in_domain_tracking():
    """source code 不能有 'except Exception: pass' 在 domain tracking 區塊。

    取代為 logger.error(..., exc_info=True) — ADR-0028 合規。
    """
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "app/services/ai/agent/agent_self_evaluator.py"
    text = src.read_text(encoding="utf-8")

    # 找 "Domain-aware signal tracking" 區塊（取夠大 block 涵蓋多行 logger.error）
    idx = text.find("Domain-aware signal tracking")
    assert idx > 0, "domain tracking 區塊不應消失"
    # 找到下一個 method def 作為 block 結尾
    end_marker = text.find("\n    # ─── ", idx + 1)
    if end_marker < 0:
        end_marker = text.find("\n    def ", idx + 1)
    if end_marker < 0:
        end_marker = idx + 3000
    block = text[idx:end_marker]

    # 不該再有 'pass  # Non-critical' silent pattern
    assert "pass  # Non-critical" not in block, (
        "L29 修法：domain tracking 不能再走 silent pass"
    )
    # 必含 logger.error（取代 silent pass）
    assert "logger.error" in block, (
        "L29 修法：domain tracking except 必用 logger.error"
    )
    # 必有 exc_info=True（多行 logger.error 仍應在同 block 內）
    assert "exc_info=True" in block, "ADR-0028：error log 必含 exc_info"
