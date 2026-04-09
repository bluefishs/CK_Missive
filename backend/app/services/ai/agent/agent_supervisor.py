"""
Agent Supervisor — 多 Agent 協調編排

當複合型問題跨越多個領域（公文 + 專案 + ERP），Supervisor 負責：
1. 意圖拆解：將複合問題拆為子任務
2. 並行委派：將子任務分配到對應 Agent 上下文
3. 結果合併：將多個 Agent 結果合成統一回覆

依賴：
- AgentPlanner: 規劃子任務
- AgentToolExecutor: 執行工具
- AgentSynthesizer: 合成答案
- ToolRegistry: 上下文篩選工具

Version: 1.0.0
Created: 2026-03-15
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    """子任務定義"""
    context: str                          # agent 上下文: doc, pm, erp
    question: str                         # 子問題
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"               # pending, running, done, error


@dataclass
class SupervisorResult:
    """Supervisor 編排結果"""
    subtasks: List[SubTask]
    merged_context: str                   # 合併後的工具結果摘要
    total_tool_calls: int
    contexts_used: List[str]


# 域關鍵字 → context 映射
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "doc": [
        "公文", "收文", "發文", "函", "書函", "令", "公告",
        "文號", "機關", "文件", "簽",
    ],
    "pm": [
        "案件", "專案", "project", "進度", "里程碑", "工程",
        "逾期", "結案", "承攬", "委託",
    ],
    "erp": [
        "廠商", "vendor", "合約", "金額", "得標", "契約",
        "評等", "協力", "採購",
    ],
    "dispatch": [
        "派工", "dispatch", "派工單", "查估", "測量",
        "地形測量", "控制測量", "用地取得",
    ],
}


class AgentSupervisor:
    """
    Supervisor 多 Agent 編排

    Usage:
        supervisor = AgentSupervisor(db)
        result = await supervisor.orchestrate("這個案件的公文往來和廠商配合情況如何？")
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def detect_domains(self, question: str) -> List[str]:
        """
        偵測問題涉及的領域。

        回傳至少一個 context。如果偵測不到特定領域，預設為 ["doc"]。
        dispatch 保持獨立域（不再歸併到 doc），以支援多域並行。
        """
        q_lower = question.lower()
        detected: List[str] = []

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in q_lower:
                    if domain not in detected:
                        detected.append(domain)
                    break

        # 跨域觸發短語偵測 — 常見的多域組合查詢
        _CROSS_DOMAIN_PHRASES = [
            (["doc", "pm"], ["公文.*進度", "案件.*公文", "專案.*文號"]),
            (["doc", "erp"], ["公文.*廠商", "合約.*公文", "報價.*文"]),
            (["pm", "erp"], ["案件.*廠商", "進度.*金額", "專案.*報價", "預算.*進度"]),
            (["dispatch", "doc"], ["派工.*公文", "公文.*派工"]),
        ]
        import re
        for domains_pair, phrases in _CROSS_DOMAIN_PHRASES:
            for phrase in phrases:
                if re.search(phrase, q_lower):
                    for d in domains_pair:
                        if d not in detected:
                            detected.append(d)

        return detected if detected else ["doc"]

    def is_multi_domain(self, question: str) -> bool:
        """判斷是否需要多 Agent 協調"""
        return len(self.detect_domains(question)) >= 2

    async def decompose_question(
        self,
        question: str,
        domains: List[str],
    ) -> List[SubTask]:
        """
        將複合問題拆解為子任務。

        簡單策略：針對每個域生成聚焦的子問題。
        未來可用 LLM 拆解複雜意圖。
        """
        subtasks: List[SubTask] = []
        for domain in domains:
            # 每個域一個子任務，子問題 = 原始問題（讓各域 planner 自行解讀）
            subtasks.append(SubTask(
                context=domain,
                question=question,
            ))
        return subtasks

    async def execute_subtasks(
        self,
        subtasks: List[SubTask],
        tool_timeout: float = 10.0,
    ) -> List[SubTask]:
        """
        並行執行子任務。

        每個子任務使用對應 context 的工具集。
        """
        from app.services.ai.agent_tools import AgentToolExecutor
        from app.services.ai.ai_config import get_ai_config
        from app.services.ai.embedding_manager import EmbeddingManager
        from app.services.ai.base_ai_service import get_ai_connector
        from app.services.ai.tool_registry import get_tool_registry

        config = get_ai_config()
        ai = get_ai_connector()
        emb = EmbeddingManager()
        executor = AgentToolExecutor(self.db, ai, emb, config)
        registry = get_tool_registry()

        async def run_subtask(subtask: SubTask) -> SubTask:
            subtask.status = "running"
            try:
                # 取得此 context 的可用工具
                available_tools = registry.get_valid_names_for_context(subtask.context)

                # 預設搜尋工具
                default_calls = _get_default_calls(subtask.context, subtask.question)

                # 只執行此 context 可用的工具
                valid_calls = [
                    c for c in default_calls
                    if c["name"] in available_tools
                ]

                if valid_calls:
                    subtask.tool_calls = valid_calls
                    subtask.results = await executor.execute_parallel(
                        valid_calls, tool_timeout,
                    )

                subtask.status = "done"
            except Exception as e:
                logger.error("Subtask %s failed: %s", subtask.context, e)
                subtask.status = "error"
                subtask.results = [{"error": str(e), "count": 0}]

            return subtask

        # 並行執行所有子任務
        completed = await asyncio.gather(
            *[run_subtask(st) for st in subtasks],
            return_exceptions=True,
        )

        results: List[SubTask] = []
        for item in completed:
            if isinstance(item, Exception):
                logger.error("Subtask exception: %s", item)
            elif isinstance(item, SubTask):
                results.append(item)

        return results

    def merge_results(self, subtasks: List[SubTask]) -> str:
        """合併所有子任務結果為統一的 context 字串"""
        sections: List[str] = []

        context_labels = {
            "doc": "公文搜尋結果",
            "pm": "專案管理結果",
            "erp": "企業資源結果",
        }

        for st in subtasks:
            if st.status != "done":
                continue

            label = context_labels.get(st.context, st.context)
            section_parts: List[str] = [f"## {label}"]

            for result in st.results:
                if isinstance(result, dict):
                    # 移除空結果
                    count = result.get("count", 0)
                    if count == 0 and "error" not in result:
                        section_parts.append("(無結果)")
                        continue

                    # 精簡序列化
                    try:
                        section_parts.append(
                            json.dumps(result, ensure_ascii=False, default=str)[:2000]
                        )
                    except (TypeError, ValueError):
                        section_parts.append(str(result)[:2000])

            sections.append("\n".join(section_parts))

        return "\n\n".join(sections) if sections else "(所有子任務均無結果)"

    async def orchestrate(
        self,
        question: str,
        tool_timeout: float = 10.0,
        use_conductor: bool = True,
    ) -> SupervisorResult:
        """
        完整的 Supervisor 編排流程。

        1. 偵測領域
        2. 拆解子任務
        3. 並行執行（use_conductor=True 時使用 Conductor 模式）
        4. 合併結果
        """
        domains = self.detect_domains(question)

        if use_conductor and len(domains) >= 2:
            return await self._orchestrate_with_conductor(
                question, domains, tool_timeout,
            )

        # Fallback: legacy sequential execution
        subtasks = await self.decompose_question(question, domains)
        completed = await self.execute_subtasks(subtasks, tool_timeout)

        merged = self.merge_results(completed)
        total_calls = sum(len(st.tool_calls) for st in completed)

        return SupervisorResult(
            subtasks=completed,
            merged_context=merged,
            total_tool_calls=total_calls,
            contexts_used=domains,
        )

    async def _orchestrate_with_conductor(
        self,
        question: str,
        domains: List[str],
        tool_timeout: float,
    ) -> SupervisorResult:
        """
        Conductor 模式：真正的並行子任務執行。

        每個子任務在獨立 DB session 中執行，互不干擾。
        """
        from app.services.ai.agent_conductor import (
            AgentConductor,
            build_conductor_subtasks_from_domains,
        )
        from app.services.ai.ai_config import get_ai_config

        config = get_ai_config()
        conductor = AgentConductor(timeout_per_task=tool_timeout)
        sub_task_defs = build_conductor_subtasks_from_domains(question, domains)

        conductor_result = await conductor.execute_parallel(
            sub_task_defs, self.db, config,
        )

        # Convert conductor results back to SupervisorResult format
        # Build merged context string from conductor results
        sections: List[str] = []
        context_labels = {
            "doc": "公文搜尋結果",
            "pm": "專案管理結果",
            "erp": "企業資源結果",
            "dispatch": "派工查詢結果",
        }

        # Group results by role
        role_items: Dict[str, List] = {}
        for item in conductor_result.merged_results:
            role = item.get("_source_role", "unknown")
            role_items.setdefault(role, []).append(item)

        for role, items in role_items.items():
            label = context_labels.get(role, role)
            section_parts = [f"## {label}"]
            for item in items:
                try:
                    # Remove internal metadata before serializing
                    clean = {
                        k: v for k, v in item.items()
                        if not k.startswith("_")
                    }
                    section_parts.append(
                        json.dumps(clean, ensure_ascii=False, default=str)[:2000]
                    )
                except (TypeError, ValueError):
                    section_parts.append(str(item)[:2000])
            sections.append("\n".join(section_parts))

        merged_context = "\n\n".join(sections) if sections else "(所有子任務均無結果)"

        # Build dummy SubTask list for backward compatibility
        dummy_subtasks = [
            SubTask(
                context=role,
                question=question,
                status="done",
                results=[{"count": len(items)}],
            )
            for role, items in role_items.items()
        ]

        return SupervisorResult(
            subtasks=dummy_subtasks,
            merged_context=merged_context,
            total_tool_calls=conductor_result.succeeded,
            contexts_used=conductor_result.contexts_used,
        )


def _get_default_calls(context: str, question: str) -> List[Dict[str, Any]]:
    """依 context 產生預設工具呼叫"""
    if context == "doc":
        keywords = [w for w in question.split() if len(w) >= 2][:5]
        if not keywords:
            keywords = [question[:20]]
        return [
            {"name": "search_documents", "params": {"keywords": keywords, "limit": 5}},
        ]
    elif context == "pm":
        return [
            {"name": "search_projects", "params": {"keywords": [question[:30]], "limit": 5}},
        ]
    elif context == "erp":
        return [
            {"name": "get_contract_summary", "params": {}},
        ]
    return []
