# -*- coding: utf-8 -*-
"""
Inference Provider ContextVar — 紀錄當前請求最後一次成功推理的實體 provider。

解決 shadow_logger 的 provider 欄位只反映「channel 標籤」（如 ``gemma-local``、
``gemma-hermes``）而不是實體 LLM（``groq`` / ``ollama`` / ``nvidia``）的問題。

使用方式：
    ai_connector 在 record_completion 時呼叫 ``set_actual_provider(provider)``；
    shadow_logger.log_trace 若 caller 未明確傳入 ``actual_llm_provider``，
    會自動從 ContextVar 讀當前請求的實體 provider 寫入。

ContextVar 天生 request-scoped（FastAPI 每個 request 有自己的 context），
不會跨請求污染。
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_CTX: ContextVar[Optional[str]] = ContextVar("actual_llm_provider", default=None)


def set_actual_provider(provider: Optional[str]) -> None:
    """設當前請求的實體 LLM provider。"""
    _CTX.set(provider)


def get_actual_provider() -> Optional[str]:
    """讀當前請求最後成功推理的實體 provider，未設定時回 None。"""
    return _CTX.get()


def reset_actual_provider() -> None:
    """明確清空（單元測試用）。"""
    _CTX.set(None)
