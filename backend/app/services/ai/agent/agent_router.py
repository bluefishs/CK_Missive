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

from app.services.ai.agent.agent_chitchat import is_chitchat

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

    # v6.13 (2026-06-01) LN2 修法：gemma4 意圖 → 確定性真實工具映射。
    # 取代 LLM suggested_tools（常幻覺中文描述詞如 '發票管理'/'付款追蹤' 不存在於
    # registry → executor 0 tools → silent 空回應）。工具名已對 registry 45 工具驗證。
    _INTENT_TOOL_MAP = {
        "document": ["search_documents", "find_correspondence"],
        "dispatch": ["search_dispatch_orders", "get_dispatch_progress"],
        "project": ["search_projects", "get_project_progress"],
        "vendor": ["get_vendor_detail", "search_erp_entities"],
        "finance": ["get_unpaid_billings", "get_financial_summary", "get_expense_overview"],
        "entity": ["search_entities", "get_entity_detail"],
        "graph": ["search_across_graphs"],
        "statistics": ["get_statistics"],
        "tender": ["search_tender"],
        "system": ["get_system_health"],
    }

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

        # ── Layer 1.55: 「[實體]相關公文」文件搜尋慣用語守衛（防 1.6 誤觸）──
        # 2026-06-09：failure-a18f229167「桃園市工務局相關公文」誤觸 search_across_graphs
        # 6/6 fail。「相關+公文類名詞」是單一文件搜尋（related documents），非真跨域關聯。
        # 必須在 Layer 1.6 之前攔截（否則 agency+doc+相關 三命中 → 誤判跨域）。
        if _re.search(r'相關\s*(公文|函|發文|收文|文件|文號)', question):
            return RouteDecision(
                route_type="pattern",
                confidence=0.85,
                latency_ms=(time.time() - t0) * 1000,
                source="doc_related_filter_rule",
                plan={"tool_calls": [
                    {"name": "search_documents", "params": {"keywords": [question[:30]], "limit": 10}},
                ]},
                suggested_context="doc",
            )

        # ── Layer 1.6: Cross-Graph 跨域查詢 fast-path ──
        # 2026-05-16 retro 改善 1：search_across_graphs 7d 0% 使用率 — KG 跨域查詢
        # 完全 dead capability。加觸發規則：query 同時含「2+ 領域關鍵字」或顯式跨域語意。
        _DOMAIN_SIGNALS = {
            "dispatch": ("派工", "派工單", "工單", "測量", "測釘"),
            "doc": ("公文", "函", "發文", "收文", "文號"),
            "project": ("專案", "工程", "案件", "標案"),
            "vendor": ("廠商", "委託", "協力", "承攬"),
            "finance": ("費用", "報銷", "請款", "發票", "預算", "帳本"),
            "agency": ("機關", "政府", "市政府", "鄉公所", "縣政府", "工務局"),
            "tender": ("投標", "決標", "底價", "得標", "公告"),
        }
        _CROSS_LINK_KW = ("相關", "關聯", "跨", "之間", "與", "以及", "同時", "牽涉")
        domain_hits = [d for d, kws in _DOMAIN_SIGNALS.items() if any(k in question for k in kws)]
        has_link = any(kw in question for kw in _CROSS_LINK_KW)
        if len(domain_hits) >= 2 or (len(domain_hits) >= 1 and has_link):
            # 帶 2+ domain 或「1+ domain + 連結詞」→ 觸發跨域 KG 查詢
            return RouteDecision(
                route_type="pattern",
                confidence=0.9,
                latency_ms=(time.time() - t0) * 1000,
                source=f"cross_graph_rule:{','.join(domain_hits)}",
                plan={"tool_calls": [
                    {"name": "search_across_graphs", "params": {
                        "query": question[:80],
                        "domains": domain_hits[:3],  # 限 top 3
                        "limit": 10,
                    }},
                ]},
                suggested_context="agent",
            )

        # ── Layer 1.7: finance / tender 單領域確定性快路由（LN1, 2026-06-03）──
        # 缺口修：finance/tender 原無 Layer 1.5 快規則 → 僅靠 Layer 2.5 gemma4 intent
        # （confidence 不穩）→「未付請款」常誤落 search_documents（V6_14 議程 #1 真因）。
        # 此處已過 Layer 1.6 cross-graph（2+ domain / 帶連結詞已被攔），剩單領域明確意圖。
        # 工具名同 _INTENT_TOOL_MAP["finance"/"tender"]（SSOT）；意圖細分使每次只跑 1 工具
        # （對 synthesis 35s budget 友善）。adr-anti-half-wired SOP 守則 4：限定詞雙字、禁單字
        # OR；test_agent_router 加正/負向鎖 false-positive。
        _FINANCE_KW = (
            "未付", "應付", "未收", "應收", "請款", "帳款",
            "財務彙總", "費用報銷", "報銷單", "未請款",
        )
        _TENDER_KW = ("標案", "投標", "決標", "得標", "底價", "招標", "採購案")
        if any(kw in question for kw in _FINANCE_KW):
            if "報銷" in question:
                _fin = ["get_expense_overview"]
            elif any(k in question for k in ("彙總", "概況", "財務狀況", "總覽")):
                _fin = ["get_financial_summary"]
            else:
                _fin = ["get_unpaid_billings"]
            return RouteDecision(
                route_type="pattern",
                confidence=0.9,
                latency_ms=(time.time() - t0) * 1000,
                source="finance_rule",
                plan={"tool_calls": [{"name": t, "params": {}} for t in _fin]},
                suggested_context="agent",
            )
        if any(kw in question for kw in _TENDER_KW):
            return RouteDecision(
                route_type="pattern",
                confidence=0.9,
                latency_ms=(time.time() - t0) * 1000,
                source="tender_rule",
                plan={"tool_calls": [
                    {"name": t, "params": {}} for t in self._INTENT_TOOL_MAP["tender"]
                ]},
                suggested_context="agent",
            )

        # ── Layer 2: Pattern Match ──
        try:
            from app.services.ai.agent.agent_pattern_learner import get_pattern_learner

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
            # LN2 修法：用確定性 intent→真實工具映射，不用 LLM 幻覺的 suggested_tools
            suggested_tools = self._INTENT_TOOL_MAP.get(intent, [])

            # 高信心意圖 → 使用確定性映射的真實工具（若有）
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
                from app.services.ai.agent.agent_intelligence_state import (
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
            from app.services.ai.core.agent_utils import parse_json_safe

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
        """根據問題關鍵字推薦角色 context（3-layer 關鍵字匹配）"""
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
            from app.services.ai.agent.agent_tool_monitor import get_tool_monitor

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
