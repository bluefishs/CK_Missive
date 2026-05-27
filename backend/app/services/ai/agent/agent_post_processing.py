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

from app.services.ai.agent.agent_synthesis import validate_citations
from app.services.ai.agent.agent_pattern_learner import get_pattern_learner
from app.services.ai.core.agent_utils import sse
from app.services.ai.misc.user_preference_extractor import (
    extract_preferences_from_history,
    save_preferences,
)
from app.services.ai.misc.user_query_tracker import get_query_tracker

logger = logging.getLogger(__name__)

# ── 簡體→繁體（臺灣用語）轉換器 ──
_opencc_converter = None

def _sc2tc(text: str) -> str:
    """簡體→繁體臺灣用語轉換（OpenCC s2twp，懶初始化）"""
    global _opencc_converter
    if _opencc_converter is None:
        try:
            from opencc import OpenCC
            _opencc_converter = OpenCC("s2twp")
        except ImportError:
            logger.warning("opencc-python-reimplemented not installed, skipping SC→TC")
            return text
    return _opencc_converter.convert(text)


async def self_talk(
    question: str,
    answer: str,
    tools_used: list,
    tool_results: list,
    ai_connector: Any,
    db: Any,
) -> None:
    """Agent 自省對話：Agent 與自己對話，產生改進教訓"""
    try:
        tools_summary = ", ".join(tools_used) if tools_used else "無"
        result_count = sum(r.get("count", 0) for r in tool_results)

        messages = [
            {"role": "system", "content": (
                "用一句繁體中文（臺灣正體）總結這次回答可以改進的具體做法。"
                "必須指出具體問題和具體改善方式，禁止泛泛而談如「可以提供更多資訊」。"
                "嚴禁使用簡體字（如关、应、为、进、据、询、问、统、节等）。"
                "只輸出一句話，不超過60字。"
            )},
            {"role": "user", "content": (
                f"問題：{question[:150]}\n"
                f"工具：{tools_summary}\n"
                f"結果：{result_count}筆\n"
                f"回答前50字：{answer[:50]}"
            )},
        ]

        reflection = await ai_connector.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=100,
            # 走 vLLM P0 優先鏈，不用 prefer_local (那走 Ollama thinking mode)
        )

        lesson = reflection.strip()
        # 品質過濾：丟棄空洞或過度簡體的反思
        _VAGUE_PATTERNS = ("可以提供更多", "可以增加", "可以更", "应明确", "应该更")
        if any(p in lesson for p in _VAGUE_PATTERNS):
            logger.debug("Self-talk discarded (vague): %s", lesson[:60])
            return
        # 簡體→繁體 後處理（OpenCC 詞彙級轉換）
        lesson = _sc2tc(lesson)
        if lesson and len(lesson) > 5 and len(lesson) < 200:
            import hashlib
            from app.extended.models import AgentLearning
            from app.db.database import AsyncSessionLocal

            content_hash = hashlib.md5(
                f"self_talk:{question[:80]}:{lesson[:30]}".encode()
            ).hexdigest()

            async with AsyncSessionLocal() as db_session:
                async with db_session.begin():
                    learning = AgentLearning(
                        session_id="self-talk",
                        learning_type="self_reflection",
                        content=lesson,
                        content_hash=content_hash,
                        source_question=question[:200],
                        confidence=0.7,
                    )
                    db_session.add(learning)
            logger.info("Self-talk saved: %s", lesson[:80])
    except Exception as e:
        logger.debug("Self-talk failed (non-critical): %s", e)


async def self_evaluate_and_evolve(
    question: str,
    answer: str,
    tool_results: list,
    trace: Any,
    citation_result: dict,
    context: Optional[str] = None,
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
        # 2026-04-29 修：原 import 路徑 `app.core.redis` 不存在 → ImportError 被
        # silent except 吞掉（違反 ADR-0028）→ redis=None → should_evolve() 永
        # 不呼叫 incr → counter 14 天卡 0 → evolution 從未跑。
        # 正確 module 是 `app.core.redis_client`（agent_evolution.py 用法相同）。
        redis = None
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
        except Exception as redis_err:
            logger.error(
                "Failed to acquire redis for self-evaluation (evolution will skip): %s",
                redis_err,
                exc_info=True,
            )

        # 正規化 context → DOMAIN_WEIGHTS key
        _ctx_map = {"knowledge-graph": "graph", "finance": "erp", "agent": None}
        eval_context = _ctx_map.get(context, context) if context else None

        _score = await evaluator.evaluate_and_store(
            question, answer, tool_results, trace,
            citation_result, redis, context=eval_context,
        )

        # Step 2: 檢查是否觸發自動進化
        if redis:
            scheduler = AgentEvolutionScheduler(redis)
            if await scheduler.should_evolve():
                await scheduler.evolve()

        # v6.0 Gap 7 POC: critic agent 審品質（multi-agent 雛形）
        # v6.2 Phase B3 (ADR-0028 合規)：silent fail debug → error + exc_info
        try:
            from app.services.ai.agent.agent_critic import get_agent_critic
            critic = get_agent_critic()
            tools_used_names = [
                tr.get("tool", "") for tr in (tool_results or [])
                if isinstance(tr, dict)
            ]
            await critic.review(
                question=question,
                answer=answer,
                tools_used=tools_used_names,
                eval_score={
                    "entity_alignment": getattr(_score, "entity_alignment", 1.0),
                    "completeness": getattr(_score, "completeness", 1.0),
                    "tool_efficiency": getattr(_score, "tool_efficiency", 1.0),
                    "overall": getattr(_score, "overall", 1.0),
                },
            )
        except Exception as critic_err:
            logger.error(
                "Critic review failed (multi-agent loop 部分受影響): %s",
                critic_err,
                exc_info=True,
            )

    except Exception as e:
        logger.debug("Self-evolution failed (non-critical): %s", e)


async def _learn_tool_combo(ctx, success: bool) -> None:
    """
    學習工具組合模式 — 追蹤哪些工具組合在特定場景下成功/失敗。

    以 AgentLearning(learning_type='tool_combo') 持久化，
    讓 inject_cross_session_learnings 在未來查詢中提供工具組合建議。

    2026-04-20 修：不可用 ctx.db（request session），此函式透過
    asyncio.create_task 背景執行；FastAPI request 結束時 get_async_db
    會 commit session，若此 task 還在用 → asyncpg 'another operation
    is in progress' race。改用 run_with_fresh_session_no_commit 拿獨立
    session（ADR-0021 pattern）。
    """
    try:
        tool_names = [tr["tool"] for tr in ctx.tool_results]
        combo_key = " → ".join(tool_names)  # 保留順序
        content = f"工具組合: {combo_key} ({'成功' if success else '失敗'})"

        from app.repositories.agent_learning_repository import AgentLearningRepository
        from app.db.database import run_with_fresh_session_no_commit

        async def _do_upsert(db):
            repo = AgentLearningRepository(db)
            return await repo.upsert_learning(
                session_id=ctx.session_id or "unknown",
                learning_type="tool_combo",
                content=content[:500],
                source_question=ctx.question[:200],
                confidence=0.8 if success else 0.4,
            )

        await run_with_fresh_session_no_commit(_do_upsert)
    except Exception as e:
        logger.debug("Tool combo learning failed: %s", e)


class PostProcessingContext:
    """封裝後處理所需的上下文資料"""

    __slots__ = (
        "question", "answer_text", "tool_results", "tools_used",
        "hints", "model_used", "trace", "session_id",
        "history", "t0", "actual_iterations", "config",
        "conv_memory", "summarizer", "db", "ai", "context",
        "channel",  # 2026-04-25: 修復 Hermes 對話無法進 diary 斷鏈
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
        context: Optional[str] = None,
        channel: Optional[str] = None,
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
        self.context = context
        self.channel = channel


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
        from app.services.ai.tools.tool_result_formatter import self_reflect
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
        # 2026-04-20 修：同上，save_preferences 若用 ctx.db 會與 FastAPI 結束
        # 時的 session.commit() 搶 asyncpg connection。改用獨立 session。
        if len(full_history) >= 8:
            prefs = extract_preferences_from_history(full_history)
            if prefs:
                from app.db.database import run_with_fresh_session_no_commit
                asyncio.create_task(
                    run_with_fresh_session_no_commit(
                        lambda db: save_preferences(ctx.session_id, prefs, db)
                    )
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
    # 2026-04-20 修：不可用 ctx.db（request session）做背景 task，會與
    # FastAPI 結束時的 session.commit() 搶 asyncpg connection → race。
    # 用 run_with_fresh_session_no_commit 拿獨立 session（save_trace 內部已 commit）。
    from app.db.database import run_with_fresh_session_no_commit
    asyncio.create_task(
        run_with_fresh_session_no_commit(lambda db: ctx.trace.flush_to_db(db))
    )

    # 非阻塞：模式學習
    tool_calls_for_learn = [
        {"name": tr["tool"], "params": tr.get("params", {})}
        for tr in ctx.tool_results
    ]
    # v5.12 Phase B.1：排除 hallucination 案例汙染 pattern_learner
    # 若 query 含具名 entity 但 answer 沒提到 → 不算成功（避免 53/53 全 success≥0.95 病）
    try:
        from app.services.ai.agent.agent_self_evaluator import get_self_evaluator
        _eval = get_self_evaluator()
        _entity_alignment = _eval._eval_query_entity_alignment(
            ctx.question, ctx.answer_text,
        )
    except Exception:
        _entity_alignment = 1.0  # 偵測失敗時不擋 learn

    success = (
        ctx.model_used != "fallback"
        and citation_result["valid"]
        and _entity_alignment >= 0.5
    )
    if _entity_alignment < 0.5:
        logger.info(
            "Pattern learn skipped (entity_alignment=%.2f, hallucination 警示): %s",
            _entity_alignment, ctx.question[:80],
        )
    asyncio.create_task(
        get_pattern_learner().learn(
            ctx.question, ctx.hints, tool_calls_for_learn,
            success=success,
            latency_ms=(time.time() - ctx.t0) * 1000,
        )
    )

    # 非阻塞：工具組合模式學習 (tool_combo)
    if len(ctx.tool_results) >= 2:
        asyncio.create_task(
            _learn_tool_combo(ctx, success)
        )

    # 非阻塞：使用者查詢興趣追蹤 (Phase 9.1)
    if ctx.session_id and ctx.tool_results:
        asyncio.create_task(
            get_query_tracker().track_query(
                ctx.session_id, ctx.question, ctx.tool_results,
            )
        )

    # 2026-04-19 Memory Wiki Phase 1: 非阻塞 Diary append（自我觀層 L3 入口）
    # 每次成功 query 結束 → 寫一筆到 wiki/memory/diary/{today}.md
    # v6.10 P1: 走 MemoryFacade 而非直 import memory.diary_service (step 32)
    try:
        from app.services.contracts.facades.memory import MemoryFacade
        latency_ms_int = int((time.time() - ctx.t0) * 1000)
        asyncio.create_task(
            MemoryFacade().append_diary_entry(
                question=ctx.question,
                answer=ctx.answer_text,
                tools_used=list(set(ctx.tools_used)) if ctx.tools_used else [],
                success=(ctx.model_used != "fallback" and ctx.model_used != "error"),
                latency_ms=latency_ms_int,
                session_id=ctx.session_id,
                channel=getattr(ctx, "channel", None),
                route_type=getattr(ctx.trace, "route_type", "llm"),
            )
        )
    except Exception as _e:
        # L29 治理：原 debug 級在生產 INFO+ 設定下 invisible，升 warning
        logger.warning(
            "Diary append asyncio scheduling failed (non-blocking): %s",
            _e, exc_info=True,
        )

    # 非阻塞：自我評估 + 進化觸發
    asyncio.create_task(
        self_evaluate_and_evolve(
            ctx.question, ctx.answer_text, ctx.tool_results,
            ctx.trace, citation_result, context=ctx.context,
        )
    )

    # 非阻塞：Agent 自省對話 (用本地推理)
    if ctx.tool_results and ctx.ai:
        asyncio.create_task(
            self_talk(
                ctx.question, ctx.answer_text,
                ctx.tools_used, ctx.tool_results,
                ctx.ai, ctx.db,
            )
        )

    return events
