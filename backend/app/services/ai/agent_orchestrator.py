"""
Agentic 文件檢索引擎 — 主編排模組

借鑑 OpenClaw 智能體模式，實現多步工具呼叫：
1. 意圖預處理 → 規則引擎 + 同義詞擴展
2. LLM 規劃 → 選擇工具 + 參數（Few-shot 引導）
3. Tool Loop (最多 MAX_ITERATIONS 輪):
   - 執行工具
   - 規則式自我修正 (5 策略)
4. 合成最終回答 (SSE 串流)

Tools:
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking
- search_entities: 知識圖譜實體搜尋
- get_entity_detail: 實體詳情 (關係+關聯公文)
- find_similar: 語意相似公文
- get_statistics: 圖譜 / 公文統計
- search_dispatch_orders: 派工單搜尋 (桃園工務局)

Architecture (v2.0.0 — 模組化重構):
- agent_chitchat.py:  閒聊偵測 + LLM 對話 + 回應清理
- agent_tools.py:     工具定義 + 6 個工具實作 (AgentToolExecutor)
- agent_planner.py:   意圖前處理 + LLM 規劃 + 自動修正 (AgentPlanner)
- agent_synthesis.py: 答案合成 + thinking 過濾 + context 建構 (AgentSynthesizer)
- agent_utils.py:     parse_json_safe, sse
- agent_orchestrator.py: 本檔 — 主編排流程 (AgentOrchestrator)

Version: 2.3.0 - SSE 即時串流 + asyncio.Queue 事件管道
Created: 2026-02-26
Updated: 2026-02-28 - v2.2.0 並行化：intent+planning gather + 工具並行執行
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.services.ai.ai_config import get_ai_config
from app.services.ai.embedding_manager import EmbeddingManager

from app.services.ai.agent_chitchat import (
    is_chitchat,
    get_smart_fallback,
    clean_chitchat_response,
    CHAT_SYSTEM_PROMPT,
)
from app.services.ai.agent_tools import AgentToolExecutor, VALID_TOOL_NAMES
from app.services.ai.agent_planner import AgentPlanner
from app.services.ai.agent_synthesis import (
    AgentSynthesizer,
    summarize_tool_result,
)
from app.services.ai.agent_utils import sse

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

    async def stream_agent_query(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Agentic 串流問答 — SSE event generator

        1. LLM 規劃 → 選擇工具
        2. 執行工具 → 收集結果
        3. 評估 → 需要更多工具則迭代
        4. 最終合成 → SSE 串流回答
        """
        t0 = time.time()
        step_index = 0
        all_sources: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        tools_used: List[str] = []

        try:
            # ── 閒聊短路：跳過工具規劃 + RAG 向量檢索，僅用 LLM 自然對話 ──
            if is_chitchat(question):
                async for event in self._stream_chitchat(question, history, t0):
                    yield event
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

            # Step 1: Planning
            yield sse(
                type="thinking",
                step="分析問題，規劃查詢策略...",
                step_index=step_index,
            )
            step_index += 1

            # 並行：意圖前處理（需 db）+ LLM 工具規劃（不需 db）
            hints, plan = await asyncio.gather(
                self._planner.preprocess_question(question, self.db),
                self._planner.plan_tools(question, history, {}),
            )

            # 後合併：將前處理 hints 注入 LLM 生成的 plan
            if hints and plan:
                sanitized_q = question.replace("{", "（").replace("}", "）")
                sanitized_q = sanitized_q.replace("```", "").replace("<", "（").replace(">", "）")
                sanitized_q = sanitized_q[:500]
                plan = self._planner._merge_hints_into_plan(plan, hints, sanitized_q)

            if not plan or not plan.get("tool_calls"):
                yield sse(
                    type="thinking",
                    step="無需查詢工具，直接回答...",
                    step_index=step_index,
                )
                step_index += 1

                async for event in self._fallback_rag(question, history, t0):
                    yield event
                return

            # Step 2-3: Tool Loop（即時串流 + 整體超時保護）
            actual_iterations = 0
            event_queue: asyncio.Queue = asyncio.Queue()

            async def _run_tool_loop():
                nonlocal actual_iterations, step_index
                result = await self._execute_tool_loop(
                    question, plan, tool_results, tools_used,
                    all_sources, step_index, event_queue,
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

            model_used = "ollama"
            try:
                async for token in self._synthesizer.synthesize_answer(
                    question, tool_results, history
                ):
                    yield sse(type="token", token=token)
            except Exception as e:
                logger.error("Agent synthesis failed: %s", e)
                yield sse(
                    type="token",
                    token="AI 回答生成失敗，請參考上方查詢結果與來源文件。",
                )
                model_used = "fallback"

            latency_ms = int((time.time() - t0) * 1000)
            yield sse(
                type="done",
                latency_ms=latency_ms,
                model=model_used,
                tools_used=list(set(tools_used)),
                iterations=actual_iterations,
            )

            logger.info(
                "Agent query completed: %d tools, %d sources, %dms",
                len(tools_used),
                len(all_sources),
                latency_ms,
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
    ) -> Dict[str, Any]:
        """
        執行工具迴圈（最多 MAX_ITERATIONS 輪）。

        SSE 事件即時推送至 event_queue，供 stream_agent_query 即時 yield。

        Returns:
            {"iterations": int, "step_index": int}
        """
        iterations = 0

        for iteration in range(self.config.agent_max_iterations):
            iterations = iteration + 1
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
                    step_index=step_index,
                ))
                step_index += 1

                result = await self._execute_tool(tool_name, params)

                summary = summarize_tool_result(tool_name, result)
                await event_queue.put(sse(
                    type="tool_result",
                    tool=tool_name,
                    summary=summary,
                    count=result.get("count", 0),
                    step_index=step_index,
                ))
                step_index += 1

                tool_results.append({
                    "tool": tool_name,
                    "params": params,
                    "result": result,
                })
                tools_used.append(tool_name)
                self._collect_sources(tool_name, result, all_sources)
            else:
                # 多工具 — 並行執行（每工具獨立 db session）
                # 先發送所有 tool_call 事件
                for call in valid_calls:
                    await event_queue.put(sse(
                        type="tool_call",
                        tool=call.get("name", ""),
                        params=call.get("params", {}),
                        step_index=step_index,
                    ))
                    step_index += 1

                # 並行執行
                results = await self._tools.execute_parallel(
                    valid_calls, self.config.agent_tool_timeout,
                )

                # 批次發送 tool_result 事件
                for call, result in zip(valid_calls, results):
                    tool_name = call.get("name", "")
                    params = call.get("params", {})
                    summary = summarize_tool_result(tool_name, result)
                    await event_queue.put(sse(
                        type="tool_result",
                        tool=tool_name,
                        summary=summary,
                        count=result.get("count", 0),
                        step_index=step_index,
                    ))
                    step_index += 1

                    tool_results.append({
                        "tool": tool_name,
                        "params": params,
                        "result": result,
                    })
                    tools_used.append(tool_name)
                    self._collect_sources(tool_name, result, all_sources)

            # 評估是否需要更多工具呼叫
            replan = self._planner.evaluate_and_replan(question, tool_results)
            if replan and replan.get("tool_calls"):
                await event_queue.put(sse(
                    type="thinking",
                    step=replan.get("reasoning", "自動修正中..."),
                    step_index=step_index,
                ))
                step_index += 1
                plan = replan
            else:
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
        """執行單個工具，回傳結果 dict"""
        try:
            tt = self.config.agent_tool_timeout
            result = await asyncio.wait_for(
                self._tools.execute(tool_name, params),
                timeout=tt,
            )
            return result
        except asyncio.TimeoutError:
            tt = self.config.agent_tool_timeout
            logger.warning("Tool %s timed out (%ds)", tool_name, tt)
            return {"error": f"工具執行超時 ({tt}s)", "count": 0}
        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            return {"error": str(e), "count": 0}

    # ========================================================================
    # 來源收集
    # ========================================================================

    @staticmethod
    def _collect_sources(
        tool_name: str,
        result: Dict[str, Any],
        all_sources: List[Dict[str, Any]],
    ) -> None:
        """從工具結果收集來源文件"""
        if tool_name in ("search_documents", "find_similar") and result.get("documents"):
            for doc in result["documents"]:
                if not any(s.get("document_id") == doc.get("id") for s in all_sources):
                    all_sources.append({
                        "document_id": doc.get("id"),
                        "doc_number": doc.get("doc_number", ""),
                        "subject": doc.get("subject", ""),
                        "doc_type": doc.get("doc_type", ""),
                        "category": doc.get("category", ""),
                        "sender": doc.get("sender", ""),
                        "receiver": doc.get("receiver", ""),
                        "doc_date": doc.get("doc_date", ""),
                        "similarity": doc.get("similarity", 0),
                    })

    # ========================================================================
    # 閒聊對話 — 輕量 LLM 串流（跳過工具規劃 + 向量檢索）
    # ========================================================================

    async def _stream_chitchat(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]],
        t0: float,
    ) -> AsyncGenerator[str, None]:
        """閒聊模式 — 僅 1 次 LLM 呼叫，自然語言回應"""
        yield sse(type="thinking", step="正在回覆您...", step_index=0)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        ]
        if history:
            for turn in history[-(self.config.rag_max_history_turns * 2):]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        model_used = "chat"
        try:
            raw = await self.ai.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=150,
                task_type="chat",
            )
            answer = clean_chitchat_response(raw, question)
            yield sse(type="token", token=answer)
        except Exception as e:
            logger.warning("Chitchat failed: %s", e)
            yield sse(
                type="token",
                token=get_smart_fallback(question),
            )
            model_used = "fallback"

        yield sse(
            type="done",
            latency_ms=int((time.time() - t0) * 1000),
            model=model_used,
            tools_used=[],
            iterations=0,
        )

    # ========================================================================
    # Fallback RAG (無工具直接回答)
    # ========================================================================

    async def _fallback_rag(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]],
        t0: float,
    ) -> AsyncGenerator[str, None]:
        """回退到基本 RAG 管線"""
        from app.services.ai.rag_query_service import RAGQueryService

        svc = RAGQueryService(self.db)
        async for event in svc.stream_query(
            question=question,
            history=history,
        ):
            yield event
