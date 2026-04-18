"""
Agentic 文件檢索引擎 — 主編排模組

流程: 意圖預處理 → LLM 規劃 → Tool Loop → 合成回答 (SSE 串流)

子模組:
- agent_post_processing.py: 後處理 (引用核實/記憶/追蹤/學習/進化)
- agent_streaming_helpers.py: 閒聊串流 + Fallback RAG
- agent_planner.py / agent_tools.py / agent_synthesis.py: 規劃/工具/合成

Version: 2.6.0 - 模組化拆分 (post_processing + streaming_helpers)
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.services.sender_context import SenderContext

from app.core.ai_connector import get_ai_connector
from app.services.ai.core.ai_config import get_ai_config
from app.services.ai.core.embedding_manager import EmbeddingManager

from app.services.ai.agent.agent_tools import AgentToolExecutor, VALID_TOOL_NAMES
from app.services.ai.agent.agent_planner import AgentPlanner, AgentWorkingMemory
from app.services.ai.agent.agent_synthesis import AgentSynthesizer
from app.services.ai.tools.tool_result_formatter import summarize_tool_result
from app.services.ai.agent.agent_tool_loop import AgentToolLoop
from app.services.ai.agent.agent_roles import get_role_profile
from app.services.ai.agent.agent_trace import AgentTrace
from app.services.ai.agent.agent_router import AgentRouter
from app.services.ai.agent.agent_tool_monitor import get_tool_monitor
from app.services.ai.agent.agent_pattern_learner import get_pattern_learner
from app.services.ai.agent.agent_summarizer import get_summarizer
from app.services.ai.agent.agent_supervisor import AgentSupervisor
from app.services.ai.core.agent_utils import sse, sanitize_history, collect_sources, compute_adaptive_timeout
from app.services.ai.agent.agent_conversation_memory import get_conversation_memory
from app.services.ai.tools.tool_chain_resolver import enrich_plan_with_chain
from app.services.ai.misc.user_preference_extractor import (
    load_preferences,
    format_preferences_for_prompt,
)
from app.services.ai.agent.agent_post_processing import (
    PostProcessingContext,
    run_post_synthesis,
)
from app.services.ai.agent.agent_streaming_helpers import (
    stream_chitchat,
    stream_fallback_rag,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agentic 文件檢索引擎

    SSE 事件格式：
      data: {"type":"thinking","step":"...","step_index":N}
      data: {"type":"tool_call","tool":"...","params":{...},"step_index":N}
      data: {"type":"tool_result","tool":"...","summary":"...","count":N,"step_index":N}
      data: {"type":"sources","sources":[...],"retrieval_count":N}
      data: {"type":"token","token":"字"}
      data: {"type":"done","latency_ms":N,"model":"...","tools_used":[...],"iterations":N}
      data: {"type":"error","error":"..."}
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = get_ai_connector()
        self.config = get_ai_config()
        self.embedding_mgr = EmbeddingManager()

        # 複用服務層速率限制器
        from app.services.ai.core.base_ai_service import get_rate_limiter
        self._rate_limiter = get_rate_limiter(self.config)

        # 組合專責模組
        self._planner = AgentPlanner(self.ai, self.config)
        self._tools = AgentToolExecutor(self.db, self.ai, self.embedding_mgr, self.config)
        self._synthesizer = AgentSynthesizer(self.ai, self.config)

        # 自適應超時（預設值，會在 tool loop 中動態更新）
        self._adaptive_tool_timeout: float = float(self.config.agent_tool_timeout)

        # 工具迴圈委派
        self._tool_loop = AgentToolLoop(
            self._tools, self._planner, self.config, self._adaptive_tool_timeout,
        )

    async def _flush_trace_lightweight(self, trace: "AgentTrace") -> None:
        """輕量 trace 持久化 — 用於 chitchat/rate-limited/fallback 等短路路徑"""
        trace.finish()
        trace.log_summary()
        try:
            asyncio.create_task(trace.flush_to_monitor())
            asyncio.create_task(trace.flush_to_db(self.db))
        except Exception as e:
            logger.warning("Lightweight trace flush failed: %s", e)

    async def _update_self_model(
        self,
        question: str,
        tools_used: List[str],
        success: bool,
    ) -> None:
        """Lightweight capability tracking via Redis pipeline (single round-trip)."""
        try:
            from app.core.redis_client import get_redis
            from app.services.ai.agent.agent_router import AgentRouter
            redis = await get_redis()
            if redis:
                context = AgentRouter._detect_context(question) or "general"
                pipe = redis.pipeline()
                pipe.hincrby("agent:capability:queries", context, 1)
                if success:
                    pipe.hincrby("agent:capability:success", context, 1)
                for tool in tools_used:
                    pipe.hincrby("agent:tool:usage", tool, 1)
                await pipe.execute()
        except Exception:
            pass  # Non-critical, silently ignore

    async def stream_agent_query(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
        sender_context: Optional["SenderContext"] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Agentic 串流問答 — SSE event generator

        1. LLM 規劃 → 選擇工具
        2. 執行工具 → 收集結果
        3. 評估 → 需要更多工具則迭代
        4. 最終合成 → SSE 串流回答

        對話記憶：
        - session_id 存在時，從 Redis 載入歷史（忽略 request body 的 history）
        - 問答結束後自動將本輪追加至 Redis
        """
        t0 = time.time()
        step_index = 0
        all_sources: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        tools_used: List[str] = []

        # ── 結構化追蹤 ──
        trace = AgentTrace(
            question=question,
            context=context,
            query_id=session_id or "",
        )

        # ── 對話記憶：session_id 優先於 request body history ──
        conv_memory = get_conversation_memory() if session_id else None
        handoff_context = None
        if session_id and conv_memory:
            loaded = await conv_memory.load(session_id)
            if loaded:
                history = loaded

            # ── Session Handoff：檢查閒置交接 + 注入前次摘要 ──
            try:
                await conv_memory.check_and_generate_handoff(session_id)
                handoff = await conv_memory.get_session_handoff(session_id)
                if handoff:
                    parts = []
                    if handoff.get("active_topic"):
                        parts.append(f"主題: {handoff['active_topic']}")
                    if handoff.get("context_summary"):
                        parts.append(f"摘要: {handoff['context_summary']}")
                    if handoff.get("key_findings"):
                        findings = ", ".join(handoff["key_findings"][:5])
                        parts.append(f"關鍵發現: {findings}")
                    if handoff.get("pending_actions"):
                        actions = ", ".join(handoff["pending_actions"][:5])
                        parts.append(f"待辦: {actions}")
                    if handoff.get("last_question"):
                        parts.append(f"上次問題: {handoff['last_question']}")
                    if parts:
                        handoff_context = "【前次對話摘要】\n" + "\n".join(parts)
                    # Clear after consumption
                    await conv_memory.clear_session_handoff(session_id)
            except Exception as e:
                logger.debug("Session handoff check failed: %s", e)

        try:
            # ── 對話摘要壓縮 ──
            summarizer = get_summarizer()
            if history and summarizer.should_summarize(history):
                history = await summarizer.get_effective_history(
                    session_id or "", history,
                )

            # ── Session Handoff 注入：將前次摘要加入 context ──
            if handoff_context:
                context = f"{handoff_context}\n\n{context}" if context else handoff_context

            # ── Sender Context 注入：多通道身份識別 ──
            if sender_context:
                sender_xml = sender_context.to_xml()
                context = f"{sender_xml}\n\n{context}" if context else sender_xml

            # ── 種子資料冷啟動（非阻塞，僅首次） ──
            asyncio.create_task(get_pattern_learner().load_seeds_if_empty())

            # ── 路由層：chitchat / pattern / llm ──
            router = AgentRouter(
                pattern_threshold=self.config.router_pattern_threshold,
            )
            route = await router.route(question, context=context)
            trace.route_type = route.route_type
            route_span = trace.start_span("routing", route_type=route.route_type)
            route_span.finish(
                confidence=route.confidence,
                source=route.source,
            )

            # -- Chitchat 短路 --
            if route.route_type == "chitchat":
                trace.chitchat_detected = True
                chitchat_tokens: List[str] = []
                async for event in stream_chitchat(self.ai, self.config, question, history, t0, context):
                    if session_id and conv_memory and event.startswith("data: "):
                        try:
                            evt = json.loads(event[6:])
                            if evt.get("type") == "token":
                                chitchat_tokens.append(evt.get("token", ""))
                        except (json.JSONDecodeError, IndexError):
                            pass
                    yield event
                if session_id and conv_memory and chitchat_tokens:
                    answer_text = "".join(chitchat_tokens)
                    await conv_memory.save(session_id, question, answer_text, history or [])
                await self._flush_trace_lightweight(trace)
                return

            # 速率限制檢查
            allowed, wait_time = await self._rate_limiter.acquire()
            if not allowed:
                trace.route_type = "rate_limited"
                yield sse(
                    type="error",
                    error=f"AI 服務請求過於頻繁，請等待 {int(wait_time):.0f} 秒後重試。",
                    code="RATE_LIMITED",
                )
                yield sse(
                    type="done",
                    latency_ms=int((time.time() - t0) * 1000),
                    model="rate_limited",
                    tools_used=[],
                    iterations=0,
                )
                await self._flush_trace_lightweight(trace)
                return

            # Step 0: 發送角色身份（router 建議的 context 優先於外部傳入的 None）
            effective_context = context or route.suggested_context
            role = get_role_profile(effective_context)
            trace.role_identity = role.identity
            yield sse(
                type="role",
                identity=role.identity,
                context=role.context,
            )

            # Step 0.5: 載入使用者偏好（非阻塞）
            user_pref_text = ""
            if session_id:
                try:
                    prefs = await load_preferences(session_id)
                    user_pref_text = format_preferences_for_prompt(prefs)
                except Exception:
                    pass

            # Step 1: Planning（Router 可能已提供 plan）
            hints = None
            plan = route.plan  # pattern 路由時有值，llm 路由時為 None

            if route.route_type == "pattern":
                yield sse(
                    type="thinking",
                    step=f"快速路由: {route.source}",
                    step_index=step_index,
                )
                step_index += 1
                plan_span = trace.start_span("planning", route="pattern")
                # 非阻塞取 hints（供後續 learn 使用相同正規化）
                hints = await self._planner.preprocess_question(question, self.db)
                plan_span.finish(
                    tool_count=len(plan.get("tool_calls", [])) if plan else 0,
                )
            else:
                # LLM 規劃
                yield sse(
                    type="thinking",
                    step="分析問題，規劃查詢策略...",
                    step_index=step_index,
                )
                step_index += 1

                plan_span = trace.start_span("planning", route="llm")

                # 過濾歷史：只保留最近 2 輪，避免閒聊歷史干擾規劃
                planning_history = history[-4:] if history else None

                # 並行：意圖前處理 + LLM 工具規劃
                # 注意：兩者都用 DB，必須各自 session（asyncpg 不允許同一 connection 併發）
                from app.db.database import run_with_fresh_session
                hints, plan = await asyncio.gather(
                    self._planner.preprocess_question(question, self.db),
                    run_with_fresh_session(
                        lambda db: self._planner.plan_tools(
                            question, planning_history, context=context, db=db,
                        )
                    ),
                )

                # 後合併：將前處理 hints 注入 LLM 生成的 plan
                if hints and plan:
                    sanitized_q = question.replace("{", "（").replace("}", "）")
                    sanitized_q = sanitized_q.replace("```", "").replace("<", "（").replace(">", "）")
                    sanitized_q = sanitized_q[:500]
                    plan = self._planner._merge_hints_into_plan(plan, hints, sanitized_q)

                # 過濾降級工具
                if plan and plan.get("tool_calls"):
                    try:
                        degraded = await get_tool_monitor().get_degraded_tools()
                        if degraded:
                            plan["tool_calls"] = [
                                c for c in plan["tool_calls"]
                                if c.get("name", "") not in degraded
                            ]
                            if degraded:
                                logger.info(
                                    "Filtered degraded tools from LLM plan: %s",
                                    degraded,
                                )
                    except Exception:
                        pass

                plan_span.finish(
                    hint_count=len(hints) if hints else 0,
                    tool_count=len(plan.get("tool_calls", [])) if plan else 0,
                )

            # ── Supervisor 多域擴展：偵測跨域問題並補充工具呼叫 ──
            supervisor = AgentSupervisor(self.db)
            if supervisor.is_multi_domain(question):
                domains = supervisor.detect_domains(question)
                trace.multi_domain = True
                # 確保 plan 存在
                if not plan:
                    plan = {"tool_calls": []}
                existing_tools = {c.get("name") for c in plan.get("tool_calls", [])}
                from app.services.ai.agent.agent_supervisor import _get_default_calls
                for domain in domains:
                    for call in _get_default_calls(domain, question):
                        if call["name"] not in existing_tools:
                            plan["tool_calls"].append(call)
                            existing_tools.add(call["name"])
                yield sse(
                    type="thinking",
                    step=f"跨域協調：{', '.join(domains)}",
                    step_index=step_index,
                )
                step_index += 1

            if not plan or not plan.get("tool_calls"):
                yield sse(
                    type="thinking",
                    step="無需查詢工具，直接回答...",
                    step_index=step_index,
                )
                step_index += 1

                async for event in stream_fallback_rag(self.db, question, history):
                    yield event
                await self._flush_trace_lightweight(trace)
                return

            # Step 2-3: Tool Loop（即時串流 + 整體超時保護）
            # 自適應超時 (Phase 8): 根據工具數量和問題長度動態調整
            planned_tool_count = len(plan.get("tool_calls", [])) if plan else 0
            self._adaptive_tool_timeout = compute_adaptive_timeout(
                self.config.agent_tool_timeout,
                planned_tool_count,
                len(question),
            )
            actual_iterations = 0
            event_queue: asyncio.Queue = asyncio.Queue()

            async def _run_tool_loop():
                nonlocal actual_iterations, step_index
                result = await self._execute_tool_loop(
                    question, plan, tool_results, tools_used,
                    all_sources, step_index, event_queue,
                    context=context, trace=trace,
                )
                actual_iterations = result["iterations"]
                step_index = result["step_index"]

            loop_task = asyncio.create_task(_run_tool_loop())
            deadline = time.time() + self.config.agent_stream_timeout
            try:
                while True:
                    if loop_task.done():
                        while not event_queue.empty():
                            yield event_queue.get_nowait()
                        if not loop_task.cancelled() and loop_task.exception():
                            raise loop_task.exception()
                        break
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        loop_task.cancel()
                        st = self.config.agent_stream_timeout
                        logger.warning("Agent stream timed out after %ds", st)
                        yield sse(
                            type="error",
                            error=f"查詢處理超時（{st}s），已取得部分結果。",
                            code="STREAM_TIMEOUT",
                        )
                        break
                    try:
                        event = await asyncio.wait_for(
                            event_queue.get(), timeout=min(remaining, 0.5),
                        )
                        yield event
                    except asyncio.TimeoutError:
                        continue
            except asyncio.CancelledError:
                pass

            # Step 4: 發送所有來源
            yield sse(
                type="sources",
                sources=all_sources,
                retrieval_count=len(all_sources),
            )

            # Step 5: 合成最終回答 (SSE 串流)
            yield sse(
                type="thinking",
                step="綜合分析結果，生成回答...",
                step_index=step_index,
            )
            step_index += 1

            synth_span = trace.start_span("synthesis")
            model_used = getattr(self.ai, '_last_provider', None) or "unknown"
            answer_tokens: List[str] = []
            try:
                async for token in self._synthesizer.synthesize_answer(
                    question, tool_results, history, context=context
                ):
                    answer_tokens.append(token)
                    yield sse(type="token", token=token)
                # Update model_used with actual provider after synthesis
                model_used = getattr(self.ai, '_last_provider', None) or model_used
                synth_span.finish()
            except Exception as e:
                logger.error("Agent synthesis failed: %s", e)
                fallback_msg = "AI 回答生成失敗，請參考上方查詢結果與來源文件。"
                answer_tokens.append(fallback_msg)
                yield sse(type="token", token=fallback_msg)
                model_used = "fallback"
                synth_span.finish(status="error")

            # ── 後處理：引用核實 + 自省 + 記憶 + 追蹤 + 學習 + 進化 ──
            answer_text = "".join(answer_tokens)
            pp_ctx = PostProcessingContext(
                question=question,
                answer_text=answer_text,
                tool_results=tool_results,
                tools_used=tools_used,
                hints=hints,
                model_used=model_used,
                trace=trace,
                session_id=session_id,
                history=history,
                t0=t0,
                actual_iterations=actual_iterations,
                config=self.config,
                conv_memory=conv_memory,
                summarizer=summarizer,
                db=self.db,
                ai=self.ai,
                context=context,
            )
            pp_events = await run_post_synthesis(pp_ctx)
            for pp_event in pp_events:
                yield pp_event

            latency_ms = int((time.time() - t0) * 1000)
            yield sse(
                type="done",
                latency_ms=latency_ms,
                model=model_used,
                provider=getattr(self.ai, '_last_provider', None) or model_used,
                tools_used=list(set(tools_used)),
                iterations=actual_iterations,
                providers_available=[p["name"] for p in self.ai.available_providers],
            )

            # Post-query self-model update (async, non-blocking)
            asyncio.create_task(
                self._update_self_model(
                    question=question,
                    tools_used=list(set(tools_used)),
                    success=(model_used != "error"),
                )
            )

            # Wiki auto-ingest: 停用自動寫入 — wiki 內容需人工或 Agent 明確判斷
            # 若需啟用: wiki_ingest Agent tool 可主動調用

        except Exception as e:
            logger.error("Agent orchestrator error: %s", e, exc_info=True)
            trace.route_type = getattr(trace, "route_type", None) or "error"
            yield sse(
                type="error",
                error="AI 服務暫時無法處理您的請求，請稍後再試。",
                code="SERVICE_ERROR",
            )
            yield sse(
                type="done",
                latency_ms=int((time.time() - t0) * 1000),
                model="error",
                tools_used=list(set(tools_used)),
                iterations=0,
            )
            await self._flush_trace_lightweight(trace)

    # ========================================================================
    # 工具迴圈（委派至 AgentToolLoop）
    # ========================================================================

    async def _execute_tool_loop(
        self,
        question: str,
        plan: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        tools_used: List[str],
        all_sources: List[Dict[str, Any]],
        step_index: int,
        event_queue: asyncio.Queue,
        context: Optional[str] = None,
        trace: Optional[AgentTrace] = None,
    ) -> Dict[str, Any]:
        """委派至 AgentToolLoop.execute_loop"""
        # 同步引用（允許測試 mock 替換 _tools/_planner）
        self._tool_loop._tools = self._tools
        self._tool_loop._planner = self._planner
        return await self._tool_loop.execute_loop(
            question, plan, tool_results, tools_used, all_sources,
            step_index, event_queue, context=context, trace=trace,
        )

    async def _wiki_auto_ingest(
        self,
        question: str,
        answer: str,
        tools_used: List[str],
    ) -> None:
        """將有價值的 Agent 回答自動寫入 wiki (非阻塞, fire-and-forget)"""
        try:
            from app.services.wiki_service import get_wiki_service
            svc = get_wiki_service()
            title = question[:60].strip()
            tags = list(set(tools_used))[:5]
            await svc.save_synthesis(
                title=title,
                content_md=f"## 問題\n\n{question}\n\n## 分析\n\n{answer}",
                sources=[f"agent:{','.join(tools_used)}"],
                tags=tags,
            )
            await svc.rebuild_index()
            logger.debug("Wiki auto-ingest: %s", title)
        except Exception as e:
            logger.debug("Wiki auto-ingest failed (non-critical): %s", e)

    async def _execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """委派至 AgentToolLoop.execute_tool (保留相容性)"""
        self._tool_loop._tools = self._tools
        return await self._tool_loop.execute_tool(tool_name, params)

