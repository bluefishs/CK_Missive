"""
Agent Router — 輕量路由層

在 LLM 規劃前攔截可直接路由的查詢，降低 50%+ 查詢的延遲。

路由優先級：
1. Chitchat 短路 — is_chitchat() (已有)
2. Pattern Match — 歷史成功模式 (confidence >= threshold)
3. Fallthrough → LLM Planning（現有流程）

設計原則：
- 只在高信心時攔截（寧可多走 LLM，不可規劃錯誤）
- 所有路由決策記錄至 AgentTrace
- 降級工具自動過濾
- 路由決策 < 10ms（零 LLM 呼叫）

Version: 1.0.0
Created: 2026-03-14
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.ai.agent_chitchat import is_chitchat

logger = logging.getLogger(__name__)


@dataclass
class RouteDecision:
    """路由決策結果"""

    route_type: str  # "chitchat" | "pattern" | "llm"
    plan: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    latency_ms: float = 0.0
    source: str = ""
    suggested_context: Optional[str] = None  # 建議的角色 context


class AgentRouter:
    """
    輕量路由層 — 規劃前攔截器。

    路由流程：
    1. is_chitchat → chitchat 短路
    2. PatternLearner.match → 歷史模式命中
    3. fallthrough → LLM 規劃（現有流程）
    """

    def __init__(
        self,
        pattern_threshold: float = 0.8,
    ):
        self._pattern_threshold = pattern_threshold

    async def route(
        self,
        question: str,
        hints: Optional[Dict] = None,
        context: Optional[str] = None,
    ) -> RouteDecision:
        """
        決定查詢路由。

        Returns:
            RouteDecision with route_type:
            - "chitchat": 閒聊，跳過所有工具
            - "pattern": 歷史模式命中，使用學習到的 plan
            - "llm": 需要 LLM 規劃
        """
        t0 = time.time()

        # ── Layer 1: 閒聊短路 ──
        if is_chitchat(question, context=context):
            return RouteDecision(
                route_type="chitchat",
                confidence=1.0,
                latency_ms=(time.time() - t0) * 1000,
                source="is_chitchat()",
            )

        # ── Layer 1.5: 規則引擎快速路由 — 跳過 LLM Planning ──
        import re as _re

        # 派工單查詢（「派工單013」「找派工單號005」）
        _dispatch_match = _re.search(r'派工單[號]?\s*(\d{2,4})', question)
        if _dispatch_match:
            no = _dispatch_match.group(1)
            return RouteDecision(
                route_type="pattern",
                confidence=1.0,
                latency_ms=(time.time() - t0) * 1000,
                source=f"dispatch_rule:{no}",
                plan={"tool_calls": [
                    {"name": "search_dispatch_orders", "params": {"dispatch_no": no}},
                    {"name": "find_correspondence", "params": {"dispatch_id": 0}},
                ]},
                suggested_context="dispatch",
            )

        # 派工進度彙整（「派工進度」「進度彙整」）
        if any(kw in question for kw in ("派工進度", "進度彙整", "派工彙整")):
            return RouteDecision(
                route_type="pattern",
                confidence=1.0,
                latency_ms=(time.time() - t0) * 1000,
                source="dispatch_progress_rule",
                plan={"tool_calls": [
                    {"name": "get_dispatch_progress", "params": {}},
                ]},
                suggested_context="dispatch",
            )

        _STATS_KW = ("多少筆", "總數", "有幾筆", "共有", "共幾", "總共")
        _HEALTH_KW = ("系統狀態", "系統健康", "健康檢查", "服務狀態")
        if any(kw in question for kw in _STATS_KW):
            return RouteDecision(
                route_type="pattern",
                confidence=1.0,
                latency_ms=(time.time() - t0) * 1000,
                source="stats_shortcut",
                plan={"tool_calls": [{"name": "get_statistics", "params": {}}]},
            )
        if any(kw in question for kw in _HEALTH_KW):
            return RouteDecision(
                route_type="pattern",
                confidence=1.0,
                latency_ms=(time.time() - t0) * 1000,
                source="health_shortcut",
                plan={"tool_calls": [{"name": "get_system_health", "params": {}}]},
            )

        # ── Layer 2: Pattern Match ──
        try:
            from app.services.ai.agent_pattern_learner import get_pattern_learner

            learner = get_pattern_learner()
            matched = await learner.match(question, hints, top_k=1)

            if matched:
                pattern = matched[0]
                if pattern.hit_count >= 2 and pattern.success_rate >= self._pattern_threshold:
                    # 過濾降級工具
                    tool_calls = await self._filter_degraded_tools(
                        pattern.tool_sequence, pattern.params_template
                    )

                    if tool_calls:
                        plan = {"tool_calls": tool_calls}
                        latency = (time.time() - t0) * 1000
                        logger.info(
                            "Router: pattern match '%s' (hits=%d, %.1fms)",
                            pattern.template[:50],
                            pattern.hit_count,
                            latency,
                        )
                        return RouteDecision(
                            route_type="pattern",
                            plan=plan,
                            confidence=pattern.success_rate,
                            latency_ms=latency,
                            source=f"pattern:{pattern.template[:30]}",
                        )

        except Exception as e:
            logger.debug("Router pattern match failed: %s", e)

        # ── Layer 2.5: 意圖偵測 → 建議角色 context ──
        suggested = self._detect_context(question)

        # ── Layer 3: Fallthrough → LLM ──
        return RouteDecision(
            route_type="llm",
            latency_ms=(time.time() - t0) * 1000,
            source="fallthrough",
            suggested_context=suggested,
        )

    @staticmethod
    def _detect_context(question: str) -> Optional[str]:
        """根據問題關鍵字推薦角色 context（採用 OpenClaw 3-layer 模式）"""
        _DISPATCH_KW = ("派工", "派工單", "逾期", "進度彙整", "派工進度", "工程進度", "查估")
        _DOC_KW = ("公文", "文號", "來函", "發文", "收文", "函覆")
        _ERP_KW = ("請款", "報銷", "發票", "帳本", "預算", "費用", "財務")
        _DEV_KW = ("程式碼", "API", "架構", "schema", "endpoint", "函數", "模組")

        if any(kw in question for kw in _DISPATCH_KW):
            return "dispatch"
        if any(kw in question for kw in _ERP_KW):
            return "agent"  # ERP 工具在全域角色中
        if any(kw in question for kw in _DOC_KW):
            return "doc"
        if any(kw in question for kw in _DEV_KW):
            return "dev"
        return None

    async def _filter_degraded_tools(
        self,
        tool_sequence: List[str],
        params_template: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """過濾掉被降級的工具"""
        try:
            from app.services.ai.agent_tool_monitor import get_tool_monitor

            monitor = get_tool_monitor()
            degraded = await monitor.get_degraded_tools()

            tool_calls = []
            for tool_name in tool_sequence:
                if tool_name in degraded:
                    logger.info("Router: skipping degraded tool %s", tool_name)
                    continue
                params = params_template.get(tool_name, {})
                tool_calls.append({"name": tool_name, "params": params})

            return tool_calls

        except Exception:
            # 無法取得降級資訊時，保留全部工具
            return [
                {"name": name, "params": params_template.get(name, {})}
                for name in tool_sequence
            ]
