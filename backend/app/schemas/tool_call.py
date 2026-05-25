"""Tool call schemas — plan side vs execution side 分離 + 統一讀 helper。

歷史 / 動機
==========
L29 事件（v6.9, 2026-05-09）：「坤哥自我成長中斷」第二次（L21 後）
  agent_self_evaluator.py:281 用 ``tool.get("name")`` 但 execution side 寫 ``{"tool", "params", "result"}``
  → domain_scores 寫不進 Redis → evolution trigger 永不觸發
  → silent except 蓋住失敗 → 4+ 天沒人察覺

設計拆分
========
* :class:`ToolPlanCall` — LLM Planner 端產出（agent_router.py:353 +
  agent_orchestrator.py + agent_plan_enricher / agent_tool_loop 讀取）。
  欄位：``name`` + ``params``
* :class:`ToolExecutionResult` — Tool Loop 執行完寫入（agent_tool_loop.py:312,381）。
  欄位：``tool`` + ``params`` + ``result``
* :func:`tool_name_of` — 統一讀 helper：接 dict / Pydantic / ToolCall 任一形式，
  雙 key fallback（先 ``tool`` 後 ``name``）。

不破壞既有結構
==============
本檔僅 *引入* schema + helper。**不** 立即把 plan / execution 端 dict 改為
Pydantic model — 兩處 dict 結構維持原樣（避免破壞下游 serialize / deserialize）。
helper 只統一「讀取」side，未來可漸進遷移寫入端。

ADR-0028 合規
=============
任何 dict 解析失敗都走 logger.error + return ``""``，禁止 silent except。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class ToolPlanCall(BaseModel):
    """LLM Planner 端產出的 tool call。

    來源：``agent_router.plan_tools()`` 等 planner。
    結構：``{"name": "<tool_name>", "params": {...}}``
    """

    name: str = Field(..., description="工具名稱（canonical name）")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具參數")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolPlanCall":
        return cls(
            name=str(d.get("name", "")),
            params=d.get("params") or {},
        )


class ToolExecutionResult(BaseModel):
    """Tool Loop 執行完成寫入的 result。

    來源：``agent_tool_loop._execute_*`` ``tool_results.append(...)``
    結構：``{"tool": "<tool_name>", "params": {...}, "result": {...}}``
    """

    tool: str = Field(..., description="工具名稱（canonical name）")
    params: Dict[str, Any] = Field(default_factory=dict, description="執行時參數")
    result: Optional[Any] = Field(default=None, description="執行結果（任意結構）")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolExecutionResult":
        return cls(
            tool=str(d.get("tool", "")),
            params=d.get("params") or {},
            result=d.get("result"),
        )


def tool_name_of(call: Union[Dict[str, Any], ToolPlanCall, ToolExecutionResult, str, None]) -> str:
    """讀取 tool name 的統一 helper。

    接受四種輸入：

    * ``dict`` — 含 ``"tool"`` 或 ``"name"``（雙 key fallback；preferred ``tool`` first）
    * :class:`ToolPlanCall` — 回 ``.name``
    * :class:`ToolExecutionResult` — 回 ``.tool``
    * ``str`` — 視為已是 name，直接回（trim 後）
    * ``None`` / 其他 — 回 ``""``

    使用點
    ------
    * ``agent_self_evaluator.py`` domain_score 寫入 — 取代 inline 雙 key fallback
    * 任何「不確定 tool list 元素形式」的迭代（plan vs execution mixed）

    為什麼 ``tool`` 優先 ``name`` 後備
    --------------------------------
    execution side 寫 ``tool`` 是 newer schema；舊版本可能用 ``name``，所以
    雙 key fallback 是「漸進遷移」的相容措施。Plan side 元素用 ``name`` 不會走到
    這個 helper（plan-side 應該用 ``ToolPlanCall.from_dict(d).name``）。
    """
    if call is None:
        return ""
    if isinstance(call, str):
        return call.strip()
    if isinstance(call, ToolPlanCall):
        return call.name
    if isinstance(call, ToolExecutionResult):
        return call.tool
    if isinstance(call, dict):
        return str(call.get("tool") or call.get("name") or "").strip()
    return ""


__all__ = [
    "ToolPlanCall",
    "ToolExecutionResult",
    "tool_name_of",
]
