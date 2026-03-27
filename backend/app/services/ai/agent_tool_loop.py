"""
Agent 工具迴圈 — ReAct Loop + Chain-of-Tools + 雙層評估

從 agent_orchestrator.py 提取，負責：
- 工具迴圈 (最多 MAX_ITERATIONS 輪)
- 單/多工具執行 (並行支援)
- 雙層評估 (auto_correct → ReAct LLM)
- 自適應超時

Version: 1.0.0 (拆分自 orchestrator v2.6.0)
Created: 2026-03-25
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.services.ai.agent_planner import AgentPlanner, AgentWorkingMemory
from app.services.ai.agent_tools import AgentToolExecutor, VALID_TOOL_NAMES
from app.services.ai.agent_synthesis import summarize_tool_result
from app.services.ai.agent_trace import AgentTrace
from app.services.ai.agent_utils import sse, collect_sources
from app.services.ai.tool_chain_resolver import enrich_plan_with_chain

logger = logging.getLogger(__name__)


class AgentToolLoop:
    """封裝工具迴圈邏輯，供 AgentOrchestrator 呼叫"""

    def __init__(
        self,
        tools: AgentToolExecutor,
        planner: AgentPlanner,
        config: Any,
        adaptive_tool_timeout: float,
    ):
        self._tools = tools
        self._planner = planner
        self.config = config
        self._adaptive_tool_timeout = adaptive_tool_timeout

    async def execute_loop(
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

            # 派工單場景精準化：plan 同時含 dispatch + documents 時，移除 documents
            # （派工單已含關聯公文，search_documents 只會引入 564 篇無關雜訊）
            # 純公文查詢（無 dispatch 工具）不受影響
            call_names = {c.get("name") for c in valid_calls}
            if "search_dispatch_orders" in call_names and "search_documents" in call_names:
                valid_calls = [c for c in valid_calls if c.get("name") != "search_documents"]
                logger.info("派工單場景：移除並行的 search_documents（使用關聯公文）")
            if not valid_calls:
                break

            if len(valid_calls) == 1:
                step_index = await self._execute_single_tool(
                    valid_calls[0], tool_results, tools_used, all_sources,
                    step_index, event_queue, memory, trace,
                    original_question=question,
                )
            else:
                step_index = await self._execute_parallel_tools(
                    valid_calls, tool_results, tools_used, all_sources,
                    step_index, event_queue, memory, trace,
                    original_question=question,
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

    async def _execute_single_tool(
        self,
        call: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        tools_used: List[str],
        all_sources: List[Dict[str, Any]],
        step_index: int,
        event_queue: asyncio.Queue,
        memory: AgentWorkingMemory,
        trace: Optional[AgentTrace] = None,
        original_question: str = "",
    ) -> int:
        """單一工具執行 — 使用既有 session"""
        tool_name = call.get("name", "")
        params = call.get("params", {})
        # 注入原始問題供工具做 LLM 幻覺校正
        if original_question:
            params["_original_question"] = original_question

        await event_queue.put(sse(
            type="tool_call",
            tool=tool_name,
            params=params,
            reasoning=call.get("reasoning", ""),
            step_index=step_index,
        ))
        step_index += 1

        tool_span = trace.start_span(f"tool:{tool_name}") if trace else None
        result = await self.execute_tool(tool_name, params)
        success = "error" not in result
        count = result.get("count", 0)
        if tool_span:
            tool_span.finish(status="ok" if success else "error", count=count)
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

        tool_results.append({"tool": tool_name, "params": params, "result": result})
        tools_used.append(tool_name)
        collect_sources(tool_name, result, all_sources)
        memory.add_observation(tool_name, count, summary)

        return step_index

    async def _execute_parallel_tools(
        self,
        valid_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        tools_used: List[str],
        all_sources: List[Dict[str, Any]],
        step_index: int,
        event_queue: asyncio.Queue,
        memory: AgentWorkingMemory,
        trace: Optional[AgentTrace] = None,
        original_question: str = "",
    ) -> int:
        """多工具並行執行 — 每工具獨立 db session"""
        for call in valid_calls:
            await event_queue.put(sse(
                type="tool_call",
                tool=call.get("name", ""),
                params=call.get("params", {}),
                reasoning=call.get("reasoning", ""),
                step_index=step_index,
            ))
            step_index += 1

        # 注入原始問題供工具做 LLM 幻覺校正
        if original_question:
            for call in valid_calls:
                call.setdefault("params", {})["_original_question"] = original_question

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

            tool_results.append({"tool": tool_name, "params": params, "result": result})
            tools_used.append(tool_name)
            collect_sources(tool_name, result, all_sources)
            memory.add_observation(tool_name, count, summary)

        return step_index

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """執行單個工具，回傳結果 dict（含 ToolResultGuard 守衛 + 自適應超時 + EVO-2 降級攔截）"""
        # EVO-2: 檢查工具降級狀態，避免呼叫已知失效的工具
        try:
            from app.services.ai.agent_tool_monitor import get_tool_monitor
            monitor = get_tool_monitor()
            if monitor and await monitor.is_degraded(tool_name):
                logger.warning("Tool %s is degraded (success_rate <30%%), skipping", tool_name)
                return {"error": f"工具 {tool_name} 暫時不可用（成功率過低）", "count": 0, "degraded": True}
        except Exception:
            pass  # monitor 不可用時不阻斷

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
