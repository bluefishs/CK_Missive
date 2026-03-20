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
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.services.ai.ai_config import get_ai_config
from app.services.ai.embedding_manager import EmbeddingManager

from app.services.ai.agent_tools import AgentToolExecutor, VALID_TOOL_NAMES
from app.services.ai.agent_planner import AgentPlanner, AgentWorkingMemory
from app.services.ai.agent_synthesis import (
    AgentSynthesizer,
    summarize_tool_result,
)
from app.services.ai.agent_roles import get_role_profile
from app.services.ai.agent_trace import AgentTrace
from app.services.ai.agent_router import AgentRouter
from app.services.ai.agent_tool_monitor import get_tool_monitor
from app.services.ai.agent_pattern_learner import get_pattern_learner
from app.services.ai.agent_summarizer import get_summarizer
from app.services.ai.agent_supervisor import AgentSupervisor
from app.services.ai.agent_utils import sse, sanitize_history, collect_sources, compute_adaptive_timeout
from app.services.ai.agent_conversation_memory import get_conversation_memory
from app.services.ai.tool_chain_resolver import enrich_plan_with_chain
from app.services.ai.user_preference_extractor import (
    load_preferences,
    format_preferences_for_prompt,
)
from app.services.ai.agent_post_processing import (
    PostProcessingContext,
    run_post_synthesis,
)
from app.services.ai.agent_streaming_helpers import (
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
        from app.services.ai.base_ai_service import get_rate_limiter
        self._rate_limiter = get_rate_limiter(self.config)

        # 組合專責模組
        self._planner = AgentPlanner(self.ai, self.config)
        self._tools = AgentToolExecutor(self.db, self.ai, self.embedding_mgr, self.config)
        self._synthesizer = AgentSynthesizer(self.ai, self.config)

        # 自適應超時（預設值，會在 tool loop 中動態更新）
        self._adaptive_tool_timeout: float = float(self.config.agent_tool_timeout)

    async def stream_agent_query(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
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
        if session_id and conv_memory:
            loaded = await conv_memory.load(session_id)
            if loaded:
                history = loaded

        try:
            # ── 對話摘要壓縮 ──
            summarizer = get_summarizer()
            if history and summarizer.should_summarize(history):
                history = await summarizer.get_effective_history(
                    session_id or "", history,
                )

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
                trace.finish()
                trace.log_summary()
                return

            # 速率限制檢查
            allowed, wait_time = await self._rate_limiter.acquire()
            if not allowed:
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
                return

            # Step 0: 發送角色身份
            role = get_role_profile(context)
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

                # 並行：意圖前處理（需 db）+ LLM 工具規劃（不需 db）
                hints, plan = await asyncio.gather(
                    self._planner.preprocess_question(question, self.db),
                    self._planner.plan_tools(question, planning_history, context=context, db=self.db),
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
                from app.services.ai.agent_supervisor import _get_default_calls
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
                trace.finish()
                trace.log_summary()
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

        except Exception as e:
            logger.error("Agent orchestrator error: %s", e, exc_info=True)
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

    # ========================================================================
    # 工具迴圈（整體超時保護用）
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
        """
        執行工具迴圈（最多 MAX_ITERATIONS 輪）。

        雙層評估策略：
        1. 快速路徑：規則式 auto_correct（0ms，覆蓋常見情境）
        2. 慢路徑：ReAct LLM 推理（~500ms，處理複雜場景）

        SSE 事件即時推送至 event_queue，供 stream_agent_query 即時 yield。

        Returns:
            {"iterations": int, "step_index": int}
        """
        iterations = 0
        memory = AgentWorkingMemory()

        for iteration in range(self.config.agent_max_iterations):
            iterations = iteration + 1

            # Chain-of-Tools: 注入前輪結果中的 ID/名稱到本輪工具參數
            if iteration > 0 and tool_results:
                plan = enrich_plan_with_chain(plan, tool_results)

            calls = plan.get("tool_calls", [])

            # 過濾有效工具
            valid_calls = [
                c for c in calls if c.get("name", "") in VALID_TOOL_NAMES
            ]
            if not valid_calls:
                break

            if len(valid_calls) == 1:
                # 單一工具 — 使用既有 session（省 session 開銷）
                call = valid_calls[0]
                tool_name = call.get("name", "")
                params = call.get("params", {})

                await event_queue.put(sse(
                    type="tool_call",
                    tool=tool_name,
                    params=params,
                    reasoning=call.get("reasoning", ""),  # Intent transparency
                    step_index=step_index,
                ))
                step_index += 1

                tool_span = trace.start_span(f"tool:{tool_name}") if trace else None
                result = await self._execute_tool(tool_name, params)
                success = "error" not in result
                count = result.get("count", 0)
                if tool_span:
                    tool_span.finish(
                        status="ok" if success else "error",
                        count=count,
                    )
                if trace:
                    trace.record_tool_call(tool_name, success, count)

                summary = summarize_tool_result(tool_name, result)
                await event_queue.put(sse(
                    type="tool_result",
                    tool=tool_name,
                    summary=summary,
                    count=count,
                    step_index=step_index,
                ))
                step_index += 1

                tool_results.append({
                    "tool": tool_name,
                    "params": params,
                    "result": result,
                })
                tools_used.append(tool_name)
                collect_sources(tool_name, result, all_sources)

                # 更新工作記憶
                memory.add_observation(
                    tool_name, count, summary,
                )
            else:
                # 多工具 — 並行執行（每工具獨立 db session）
                for call in valid_calls:
                    await event_queue.put(sse(
                        type="tool_call",
                        tool=call.get("name", ""),
                        params=call.get("params", {}),
                        reasoning=call.get("reasoning", ""),  # Intent transparency
                        step_index=step_index,
                    ))
                    step_index += 1

                results = await self._tools.execute_parallel(
                    valid_calls, self._adaptive_tool_timeout,
                )

                for call, result in zip(valid_calls, results):
                    tool_name = call.get("name", "")
                    params = call.get("params", {})
                    success = "error" not in result
                    count = result.get("count", 0)
                    if trace:
                        trace.record_tool_call(tool_name, success, count)
                    summary = summarize_tool_result(tool_name, result)
                    await event_queue.put(sse(
                        type="tool_result",
                        tool=tool_name,
                        summary=summary,
                        count=count,
                        step_index=step_index,
                    ))
                    step_index += 1

                    tool_results.append({
                        "tool": tool_name,
                        "params": params,
                        "result": result,
                    })
                    tools_used.append(tool_name)
                    collect_sources(tool_name, result, all_sources)

                    # 更新工作記憶
                    memory.add_observation(
                        tool_name, count, summary,
                    )

            # ── 雙層評估：快速路徑 → 慢路徑 ──

            # Layer 1: 規則式 auto_correct（快速路徑，0ms）
            replan = self._planner.evaluate_and_replan(question, tool_results)
            if replan and replan.get("tool_calls"):
                if trace:
                    trace.record_correction(replan.get("reasoning", "auto_correct"))
                await event_queue.put(sse(
                    type="thinking",
                    step=replan.get("reasoning", "自動修正中..."),
                    step_index=step_index,
                ))
                step_index += 1
                plan = replan
                continue

            # Layer 2: ReAct LLM 推理（慢路徑，僅在快速路徑未觸發時）
            # 條件：結果不足（<3 筆）且尚有迭代配額
            if (
                memory.total_results < 3
                and iteration < self.config.agent_max_iterations - 1
            ):
                react_plan = await self._planner.react(
                    question, tool_results, memory, context=context,
                )
                if react_plan and react_plan.get("tool_calls"):
                    if trace:
                        trace.record_react(
                            react_plan.get("action", "continue"),
                            react_plan.get("confidence", 0),
                        )
                    await event_queue.put(sse(
                        type="react",
                        step=react_plan.get("reasoning", "深度推理中..."),
                        confidence=react_plan.get("confidence", 0),
                        action=react_plan.get("action", "continue"),
                        step_index=step_index,
                    ))
                    step_index += 1
                    plan = react_plan
                    continue

            # 兩層都未觸發 → 結果充分，結束迴圈
            break

        return {
            "iterations": iterations,
            "step_index": step_index,
        }

    # ========================================================================
    # 工具執行
    # ========================================================================

    async def _execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """執行單個工具，回傳結果 dict（含 ToolResultGuard 守衛 + 自適應超時）"""
        try:
            tt = self._adaptive_tool_timeout
            result = await asyncio.wait_for(
                self._tools.execute(tool_name, params),
                timeout=tt,
            )
            return result
        except asyncio.TimeoutError:
            tt = self._adaptive_tool_timeout
            logger.warning("Tool %s timed out (%.1fs)", tool_name, tt)
            raw = {"error": f"工具執行超時 ({tt:.0f}s)", "count": 0}
            if self.config.tool_guard_enabled:
                from app.services.ai.agent_tools import ToolResultGuard
                return ToolResultGuard.guard(tool_name, params, raw)
            return raw
        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            raw = {"error": "工具執行失敗", "count": 0}
            if self.config.tool_guard_enabled:
                from app.services.ai.agent_tools import ToolResultGuard
                return ToolResultGuard.guard(tool_name, params, raw)
            return raw

