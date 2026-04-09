"""
Agent Router — 輕量路由層

在 LLM 規劃前攔截可直接路由的查詢，降低 50%+ 查詢的延遲。

路由優先級：
1. Chitchat 短路 — is_chitchat() (已有)
2. Pattern Match — 歷史成功模式 (confidence >= threshold)
2.5. Gemma 4 語意意圖分類 — 輕量 LLM 單次呼叫
3. Fallthrough → LLM Planning（現有流程）

設計原則：
- 只在高信心時攔截（寧可多走 LLM，不可規劃錯誤）
- 所有路由決策記錄至 AgentTrace
- 降級工具自動過濾
- Layer 1~2 路由決策 < 10ms（零 LLM 呼叫）
- Layer 2.5 Gemma 4 為增強層，失敗不影響現有流程

Version: 1.1.0
Created: 2026-03-14
Updated: 2026-04-05 - v1.1.0 新增 Gemma 4 語意意圖分類 (Layer 2.5)
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

    route_type: str  # "chitchat" | "pattern" | "gemma4" | "llm"
    plan: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    latency_ms: float = 0.0
    source: str = ""
    suggested_context: Optional[str] = None  # 建議的角色 context
    gemma4_intent: Optional[Dict[str, Any]] = None  # Gemma 4 意圖分類結果


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

        # 工程/道路名稱搜尋（含路名但無派工單號 → 搜尋派工單+公文）
        _ROAD_KW = ("路", "街", "工程", "拓寬", "開闢", "新闢", "查估", "測量")
        if any(kw in question for kw in _ROAD_KW) and not _dispatch_match:
            return RouteDecision(
                route_type="pattern",
                confidence=0.9,
                latency_ms=(time.time() - t0) * 1000,
                source="road_search_rule",
                plan={"tool_calls": [
                    {"name": "search_dispatch_orders", "params": {"search": question[:50]}},
                    {"name": "search_documents", "params": {"keywords": [question[:30]], "limit": 5}},
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

        # ── Layer 2.5: Gemma 4 語意意圖分類 ──
        gemma4_result = await self._classify_intent_gemma4(question)
        if gemma4_result and gemma4_result.get("confidence", 0) >= 0.8:
            intent = gemma4_result.get("intent", "")
            suggested_tools = gemma4_result.get("suggested_tools", [])

            # 高信心意圖 → 使用 Gemma 4 建議的工具（若有）
            if suggested_tools:
                tool_calls = [
                    {"name": t, "params": {}} for t in suggested_tools[:3]
                ]
                # 過濾降級工具
                tool_calls = await self._filter_degraded_tools(
                    [tc["name"] for tc in tool_calls],
                    {},
                )
                if tool_calls:
                    return RouteDecision(
                        route_type="gemma4",
                        plan={"tool_calls": tool_calls},
                        confidence=gemma4_result["confidence"],
                        latency_ms=(time.time() - t0) * 1000,
                        source=f"gemma4_intent:{intent}",
                        suggested_context=self._intent_to_context(intent),
                        gemma4_intent=gemma4_result,
                    )

        # ── Layer 2.75: 規則意圖偵測 → 建議角色 context ──
        suggested = self._detect_context(question)

        # ── Layer 2.8: 自適應角色升級 — 弱域自動提升到全能角色 ──
        if suggested and suggested != "agent":
            try:
                from app.services.ai.agent_intelligence_state import (
                    get_domain_readiness, get_active_critical_signals,
                )
                from app.core.redis_client import get_redis
                _redis = await get_redis()
                if _redis:
                    readiness = await get_domain_readiness(None, _redis, suggested)
                    criticals = await get_active_critical_signals(_redis)
                    critical_domains = [s.get("type", "") for s in criticals]
                    has_domain_critical = any(suggested in d for d in critical_domains)

                    if readiness < 0.5 or has_domain_critical:
                        logger.info(
                            "Router 角色升級: %s → agent (readiness=%.2f, critical=%s)",
                            suggested, readiness, has_domain_critical,
                        )
                        suggested = "agent"
            except Exception as e:
                logger.debug("Adaptive role escalation skipped: %s", e)

        # 若 Gemma 4 有結果但信心不足，仍附帶意圖資訊給 LLM 規劃參考
        gemma4_hint = gemma4_result if gemma4_result else None

        # ── Layer 3: Fallthrough → LLM ──
        return RouteDecision(
            route_type="llm",
            latency_ms=(time.time() - t0) * 1000,
            source="fallthrough",
            suggested_context=suggested or (
                self._intent_to_context(gemma4_result.get("intent", ""))
                if gemma4_result else None
            ),
            gemma4_intent=gemma4_hint,
        )

    async def _classify_intent_gemma4(self, question: str) -> Optional[dict]:
        """Layer 2.5: Gemma 4 semantic intent classification.

        Classifies query into: document | dispatch | project | vendor | finance |
        entity | graph | statistics | tender | system | chitchat

        Returns: {"intent": str, "confidence": float, "suggested_tools": [str]}
        """
        try:
            from app.core.ai_connector import get_ai_connector

            ai = get_ai_connector()
            prompt = (
                "將以下查詢分類為一個意圖類別，以 JSON 回覆：\n"
                f"查詢: {question[:200]}\n\n"
                "類別: document(公文), dispatch(派工), project(專案), "
                "vendor(廠商), finance(財務), entity(實體), graph(圖譜), "
                "statistics(統計), tender(標案), system(系統), chitchat(閒聊)\n\n"
                '回覆格式: {"intent": "類別", "confidence": 0.0-1.0, '
                '"suggested_tools": ["tool1", "tool2"]}'
            )
            result = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
                task_type="classify",
            )
            from app.services.ai.agent_utils import parse_json_safe

            parsed = parse_json_safe(result)
            if parsed and parsed.get("intent"):
                logger.debug(
                    "Gemma4 intent: %s (confidence=%.2f)",
                    parsed.get("intent"),
                    parsed.get("confidence", 0),
                )
                return parsed
        except Exception as e:
            logger.debug("Gemma4 intent classification failed: %s", e)
        return None

    @staticmethod
    def _intent_to_context(intent: str) -> Optional[str]:
        """Map Gemma 4 intent to router context."""
        _INTENT_CONTEXT_MAP = {
            "document": "doc",
            "dispatch": "dispatch",
            "project": "pm",
            "vendor": "erp",
            "finance": "erp",
            "entity": "doc",
            "graph": "dev",
            "statistics": None,
            "tender": None,
            "system": "dev",
            "chitchat": None,
        }
        return _INTENT_CONTEXT_MAP.get(intent)

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
