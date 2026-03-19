"""
Agent 後處理模組 — 從 agent_orchestrator.py 提取

負責查詢完成後的非核心處理：
1. 引用核實 (citation validation)
2. 品質自省 (self-reflection)
3. 對話記憶儲存 + 摘要壓縮
4. 使用者偏好萃取
5. 追蹤持久化 (trace → monitor + DB)
6. 模式學習 (pattern learning)
7. 查詢興趣追蹤 (query tracking)
8. 自我評估 + 自動進化 (self-evaluation + evolution)

Version: 1.0.0
Created: 2026-03-18
Extracted from: agent_orchestrator.py v2.5.0
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from app.services.ai.agent_synthesis import validate_citations
from app.services.ai.agent_pattern_learner import get_pattern_learner
from app.services.ai.agent_utils import sse
from app.services.ai.user_preference_extractor import (
    extract_preferences_from_history,
    save_preferences,
)
from app.services.ai.user_query_tracker import get_query_tracker

logger = logging.getLogger(__name__)


async def self_evaluate_and_evolve(
    question: str,
    answer: str,
    tool_results: list,
    trace: Any,
    citation_result: dict,
) -> None:
    """
    自我評估 + 自動進化觸發。

    每次回答後自動執行：
    1. 評估本次回答品質 -> 產生改進信號
    2. 檢查是否達到進化觸發條件 (每 50 次 / 每 24h)
    3. 若觸發，自動執行進化動作（升級種子/降級模式/清理）
    """
    try:
        from .agent_self_evaluator import get_self_evaluator
        from .agent_evolution_scheduler import AgentEvolutionScheduler

        evaluator = get_self_evaluator()

        # Step 1: 自我評估（零 LLM 呼叫，純規則式）
        redis = None
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
        except Exception:
            pass

        _score = await evaluator.evaluate_and_store(
            question, answer, tool_results, trace,
            citation_result, redis,
        )

        # Step 2: 檢查是否觸發自動進化
        if redis:
            scheduler = AgentEvolutionScheduler(redis)
            if await scheduler.should_evolve():
                await scheduler.evolve()

    except Exception as e:
        logger.debug("Self-evolution failed (non-critical): %s", e)


class PostProcessingContext:
    """封裝後處理所需的上下文資料"""

    __slots__ = (
        "question", "answer_text", "tool_results", "tools_used",
        "hints", "model_used", "trace", "session_id",
        "history", "t0", "actual_iterations", "config",
        "conv_memory", "summarizer", "db", "ai",
    )

    def __init__(
        self,
        question: str,
        answer_text: str,
        tool_results: List[Dict[str, Any]],
        tools_used: List[str],
        hints: Any,
        model_used: str,
        trace: Any,
        session_id: Optional[str],
        history: Optional[List[Dict[str, str]]],
        t0: float,
        actual_iterations: int,
        config: Any,
        conv_memory: Any,
        summarizer: Any,
        db: Any,
        ai: Any,
    ):
        self.question = question
        self.answer_text = answer_text
        self.tool_results = tool_results
        self.tools_used = tools_used
        self.hints = hints
        self.model_used = model_used
        self.trace = trace
        self.session_id = session_id
        self.history = history
        self.t0 = t0
        self.actual_iterations = actual_iterations
        self.config = config
        self.conv_memory = conv_memory
        self.summarizer = summarizer
        self.db = db
        self.ai = ai


async def run_post_synthesis(
    ctx: PostProcessingContext,
) -> List[str]:
    """
    執行合成後的所有後處理步驟。

    Returns:
        List of SSE event strings to yield (e.g., reflection events).
    """
    events: List[str] = []

    # ── 引用核實 ──
    citation_result = validate_citations(ctx.answer_text, ctx.tool_results)
    ctx.trace.record_synthesis_validation(
        citation_result["citation_count"],
        citation_result["citation_verified"],
    )
    if citation_result["warnings"]:
        logger.info("Citation warnings: %s", citation_result["warnings"])

    # ── 品質自省 (Phase 2C) ──
    if (
        ctx.config.self_reflect_enabled
        and ctx.tool_results
    ):
        from app.services.ai.agent_synthesis import self_reflect
        reflect_result = await self_reflect(
            ctx.ai, ctx.question, ctx.answer_text,
            ctx.tool_results, ctx.config,
        )
        reflect_score = reflect_result.get("score", 10)
        if reflect_score < ctx.config.self_reflect_threshold:
            logger.info(
                "Self-reflection score=%d < threshold=%d, issues=%s",
                reflect_score,
                ctx.config.self_reflect_threshold,
                reflect_result.get("issues", []),
            )
            events.append(sse(
                type="reflection",
                score=reflect_score,
                issues=reflect_result.get("issues", []),
            ))

    # ── 對話記憶：儲存本輪 ──
    if ctx.session_id and ctx.conv_memory:
        await ctx.conv_memory.save(
            ctx.session_id, ctx.question, ctx.answer_text, ctx.history or [],
            tool_count=len(ctx.tools_used),
        )
        full_history = (ctx.history or []) + [
            {"role": "user", "content": ctx.question},
            {"role": "assistant", "content": ctx.answer_text},
        ]
        if ctx.summarizer.should_summarize(full_history):
            asyncio.create_task(
                ctx.summarizer.summarize_and_store(
                    ctx.session_id, full_history, ctx.ai,
                )
            )

        # 非阻塞：使用者偏好萃取 (每 4 輪萃取一次)
        if len(full_history) >= 8:
            prefs = extract_preferences_from_history(full_history)
            if prefs:
                asyncio.create_task(
                    save_preferences(ctx.session_id, prefs, ctx.db)
                )

    # ── 追蹤完成 + 推送至 Monitor + DB 持久化 + Pattern 學習 ──
    ctx.trace.iterations = ctx.actual_iterations
    ctx.trace._model_used = ctx.model_used
    ctx.trace._answer_length = len(ctx.answer_text)
    ctx.trace._answer_preview = ctx.answer_text[:500] if ctx.answer_text else None
    ctx.trace.finish()
    ctx.trace.log_summary()

    # 非阻塞：工具成功率推送
    asyncio.create_task(ctx.trace.flush_to_monitor())

    # 非阻塞：持久化至 PostgreSQL
    asyncio.create_task(ctx.trace.flush_to_db(ctx.db))

    # 非阻塞：模式學習
    tool_calls_for_learn = [
        {"name": tr["tool"], "params": tr.get("params", {})}
        for tr in ctx.tool_results
    ]
    success = ctx.model_used != "fallback" and citation_result["valid"]
    asyncio.create_task(
        get_pattern_learner().learn(
            ctx.question, ctx.hints, tool_calls_for_learn,
            success=success,
            latency_ms=(time.time() - ctx.t0) * 1000,
        )
    )

    # 非阻塞：使用者查詢興趣追蹤 (Phase 9.1)
    if ctx.session_id and ctx.tool_results:
        asyncio.create_task(
            get_query_tracker().track_query(
                ctx.session_id, ctx.question, ctx.tool_results,
            )
        )

    # 非阻塞：自我評估 + 進化觸發
    asyncio.create_task(
        self_evaluate_and_evolve(
            ctx.question, ctx.answer_text, ctx.tool_results,
            ctx.trace, citation_result,
        )
    )

    return events
