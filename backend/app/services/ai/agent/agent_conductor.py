"""
Conductor Agent — Parallel sub-task orchestration.

When a query spans multiple domains (e.g., "比較桃園工務局的派工數量和公文數量"),
the Conductor:
1. Decomposes into independent sub-tasks
2. Assigns each to a specialized role (DOC/DISPATCH/PM/ERP/GRAPH)
3. Executes sub-tasks in parallel via asyncio.gather
4. Merges results into a unified response

Activation: Triggered by AgentSupervisor when multi_domain=True.
Replaces the sequential execute_subtasks in AgentSupervisor with
truly isolated parallel execution using independent DB sessions.

Version: 1.0.0
Created: 2026-03-16
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ConductorSubTask:
    """A single sub-task to be executed in parallel."""
    role: str                           # Role context: doc, pm, erp, dispatch
    question: str                       # The sub-question for this role
    tools: List[str] = field(default_factory=list)  # Preferred tool names
    status: str = "pending"             # pending, running, done, error
    result: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    error: Optional[str] = None


@dataclass
class ConductorResult:
    """Merged result from parallel sub-task execution."""
    merged_results: List[Dict[str, Any]]
    total_ms: int
    sub_task_count: int
    succeeded: int
    failed: int
    contexts_used: List[str]


# Role -> default tool calls mapping
_ROLE_DEFAULT_TOOLS: Dict[str, List[Dict[str, Any]]] = {
    "doc": [
        {"name": "search_documents", "params": {"keywords": [], "limit": 5}},
    ],
    "pm": [
        {"name": "search_projects", "params": {"keywords": [], "limit": 5}},
    ],
    "erp": [
        {"name": "get_contract_summary", "params": {}},
    ],
    "dispatch": [
        {"name": "search_dispatch_orders", "params": {"keywords": [], "limit": 5}},
    ],
}


class AgentConductor:
    """
    Conductor Agent — orchestrates parallel sub-task execution.

    Each sub-task runs in an independent DB session with its own tool executor,
    ensuring full isolation. One sub-task failure does not block others.

    Usage:
        conductor = AgentConductor()
        result = await conductor.execute_parallel(sub_tasks, db, config)
    """

    def __init__(
        self,
        timeout_per_task: float = 15.0,
        max_concurrent: int = 5,
    ):
        self._timeout_per_task = timeout_per_task
        self._max_concurrent = max_concurrent

    async def execute_parallel(
        self,
        sub_tasks: List[Dict[str, Any]],
        db: AsyncSession,
        config: Any,
    ) -> ConductorResult:
        """
        Execute sub-tasks in parallel and merge results.

        Each sub_task dict: {"role": str, "question": str, "tools": list[str]}

        Args:
            sub_tasks: List of sub-task definitions.
            db: Primary DB session (used as template for creating new sessions).
            config: AI config object.

        Returns:
            ConductorResult with merged results and metadata.
        """
        t0 = time.time()

        if not sub_tasks:
            return ConductorResult(
                merged_results=[],
                total_ms=0,
                sub_task_count=0,
                succeeded=0,
                failed=0,
                contexts_used=[],
            )

        # Convert dicts to ConductorSubTask objects
        tasks = []
        for st in sub_tasks:
            tasks.append(ConductorSubTask(
                role=st.get("role", "doc"),
                question=st.get("question", ""),
                tools=st.get("tools", []),
            ))

        # Limit concurrency
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def _guarded_execute(task: ConductorSubTask) -> ConductorSubTask:
            async with semaphore:
                return await self._execute_sub_task(task, config)

        # Execute all sub-tasks in parallel with error isolation
        completed = await asyncio.gather(
            *[_guarded_execute(t) for t in tasks],
            return_exceptions=True,
        )

        # Collect results
        finished_tasks: List[ConductorSubTask] = []
        for item in completed:
            if isinstance(item, Exception):
                logger.error("Conductor sub-task exception: %s", item)
                error_task = ConductorSubTask(
                    role="unknown",
                    question="",
                    status="error",
                    error=str(item),
                )
                finished_tasks.append(error_task)
            elif isinstance(item, ConductorSubTask):
                finished_tasks.append(item)

        # Merge results
        merged = self._merge_results(finished_tasks)
        total_ms = int((time.time() - t0) * 1000)

        succeeded = sum(1 for t in finished_tasks if t.status == "done")
        failed = sum(1 for t in finished_tasks if t.status == "error")
        contexts_used = list(dict.fromkeys(
            t.role for t in finished_tasks if t.status == "done"
        ))

        return ConductorResult(
            merged_results=merged,
            total_ms=total_ms,
            sub_task_count=len(sub_tasks),
            succeeded=succeeded,
            failed=failed,
            contexts_used=contexts_used,
        )

    async def _execute_sub_task(
        self,
        task: ConductorSubTask,
        config: Any,
    ) -> ConductorSubTask:
        """
        Execute a single sub-task with role-specific tool filtering.

        Each sub-task creates its own DB session for full isolation.
        """
        task.status = "running"
        t0 = time.time()

        try:
            from app.db.database import AsyncSessionLocal
            from app.services.ai.agent.agent_tools import AgentToolExecutor
            from app.services.ai.core.embedding_manager import EmbeddingManager
            from app.services.ai.core.base_ai_service import get_ai_connector
            from app.services.ai.tools.tool_registry import get_tool_registry

            ai = get_ai_connector()
            emb = EmbeddingManager()
            registry = get_tool_registry()

            # Get tools available for this role's context
            available_tools = registry.get_valid_names_for_context(task.role)

            # Build tool calls: prefer explicit tools, fall back to role defaults
            tool_calls = self._build_tool_calls(task, available_tools)

            if not tool_calls:
                task.status = "done"
                task.result = {"items": [], "count": 0, "role": task.role}
                task.latency_ms = int((time.time() - t0) * 1000)
                return task

            # Execute with independent DB session
            async with AsyncSessionLocal() as session:
                executor = AgentToolExecutor(session, ai, emb, config)
                results = await asyncio.wait_for(
                    executor.execute_parallel(tool_calls, self._timeout_per_task),
                    timeout=self._timeout_per_task + 5,  # Outer safety margin
                )

            # Flatten results
            all_items: List[Dict[str, Any]] = []
            total_count = 0
            for call, result in zip(tool_calls, results):
                tool_name = call.get("name", "")
                count = result.get("count", 0)
                total_count += count

                # Extract items from different result formats
                items = (
                    result.get("documents")
                    or result.get("entities")
                    or result.get("orders")
                    or result.get("projects")
                    or result.get("vendors")
                    or result.get("items")
                    or []
                )
                for item in items:
                    if isinstance(item, dict):
                        item["_source_tool"] = tool_name
                        item["_source_role"] = task.role
                        all_items.append(item)

                # If result is a summary/stats (no list items), include as-is
                if not items and count == 0 and "error" not in result:
                    all_items.append({
                        "_source_tool": tool_name,
                        "_source_role": task.role,
                        "_summary": True,
                        **{k: v for k, v in result.items()
                           if k not in ("count", "documents", "entities", "orders")},
                    })

            task.status = "done"
            task.result = {
                "items": all_items,
                "count": total_count,
                "role": task.role,
                "tools_executed": [c.get("name") for c in tool_calls],
            }
            task.latency_ms = int((time.time() - t0) * 1000)

        except asyncio.TimeoutError:
            logger.warning(
                "Conductor sub-task [%s] timed out after %.1fs",
                task.role, self._timeout_per_task,
            )
            task.status = "error"
            task.error = f"Sub-task timeout ({self._timeout_per_task:.0f}s)"
            task.result = {"items": [], "count": 0, "error": task.error}
            task.latency_ms = int((time.time() - t0) * 1000)

        except Exception as e:
            logger.error("Conductor sub-task [%s] failed: %s", task.role, e)
            task.status = "error"
            task.error = str(e)
            task.result = {"items": [], "count": 0, "error": task.error}
            task.latency_ms = int((time.time() - t0) * 1000)

        return task

    def _build_tool_calls(
        self,
        task: ConductorSubTask,
        available_tools: set,
    ) -> List[Dict[str, Any]]:
        """Build tool calls for a sub-task, filtering by available tools."""
        calls: List[Dict[str, Any]] = []

        if task.tools:
            # Use explicitly specified tools
            for tool_name in task.tools:
                if tool_name in available_tools:
                    params = self._default_params_for_tool(tool_name, task.question)
                    calls.append({"name": tool_name, "params": params})
        else:
            # Fall back to role defaults
            defaults = _ROLE_DEFAULT_TOOLS.get(task.role, [])
            for default_call in defaults:
                if default_call["name"] in available_tools:
                    params = dict(default_call.get("params", {}))
                    # Inject question as keywords if applicable
                    if "keywords" in params:
                        keywords = [
                            w for w in task.question.split() if len(w) >= 2
                        ][:5]
                        params["keywords"] = keywords or [task.question[:20]]
                    calls.append({"name": default_call["name"], "params": params})

        return calls

    @staticmethod
    def _default_params_for_tool(
        tool_name: str,
        question: str,
    ) -> Dict[str, Any]:
        """Generate default params for a tool based on the question."""
        keywords = [w for w in question.split() if len(w) >= 2][:5]
        if not keywords:
            keywords = [question[:20]]

        if tool_name in ("search_documents", "search_dispatch_orders", "search_entities"):
            return {"keywords": keywords, "limit": 5}
        elif tool_name in ("search_projects", "search_vendors"):
            return {"keywords": keywords, "limit": 5}
        elif tool_name == "get_contract_summary":
            return {}
        elif tool_name == "get_statistics":
            return {}
        return {"keywords": keywords}

    def _merge_results(
        self,
        tasks: List[ConductorSubTask],
    ) -> List[Dict[str, Any]]:
        """
        Merge parallel results, deduplicate, and sort by relevance.

        Deduplication key: entity ID (id field) or doc_number.
        """
        merged: List[Dict[str, Any]] = []
        seen_ids: set = set()

        for task in tasks:
            if task.status != "done":
                continue

            items = task.result.get("items", [])
            for item in items:
                # Compute dedup key
                dedup_key = self._get_dedup_key(item)
                if dedup_key and dedup_key in seen_ids:
                    continue
                if dedup_key:
                    seen_ids.add(dedup_key)
                merged.append(item)

        # Sort: items with similarity score first (descending),
        # then by presence of id
        merged.sort(
            key=lambda x: (
                -x.get("similarity", 0),
                -1 if x.get("id") else 0,
            ),
        )

        return merged

    @staticmethod
    def _get_dedup_key(item: Dict[str, Any]) -> Optional[str]:
        """Get a deduplication key for an item."""
        if item.get("_summary"):
            return None  # Don't dedup summary items

        item_id = item.get("id")
        doc_number = item.get("doc_number")
        entity_name = item.get("name") or item.get("entity_name")

        if item_id:
            return f"id:{item_id}"
        if doc_number:
            return f"doc:{doc_number}"
        if entity_name:
            return f"entity:{entity_name}"
        return None


def build_conductor_subtasks_from_domains(
    question: str,
    domains: List[str],
) -> List[Dict[str, Any]]:
    """
    Convert domain list from AgentSupervisor.detect_domains()
    into ConductorSubTask dicts.

    This is the bridge between the existing Supervisor domain detection
    and the new Conductor parallel execution.
    """
    sub_tasks: List[Dict[str, Any]] = []
    for domain in domains:
        sub_tasks.append({
            "role": domain,
            "question": question,
            "tools": [],  # Use role defaults
        })
    return sub_tasks
