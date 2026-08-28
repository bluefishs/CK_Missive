# -*- coding: utf-8 -*-
"""
Inference Provider ContextVar — 紀錄當前請求最後一次成功推理的實體 provider。

解決 shadow_logger 的 provider 欄位只反映「channel 標籤」（如 ``gemma-local``、
``gemma-hermes``）而不是實體 LLM（``groq`` / ``ollama`` / ``nvidia``）的問題。

使用方式：
    ai_connector 在 record_completion 時呼叫 ``set_actual_provider(provider)``；
    shadow_logger.log_trace 若 caller 未明確傳入 ``actual_llm_provider``，
    會自動從 ContextVar 讀當前請求的實體 provider 寫入。

## ⚠️ 2026-08-28：原本存「值」，而那讓它空了 27 天

原檔頭寫著「ContextVar 天生 request-scoped，不會跨請求污染」—— 那句是對的，
但它**漏掉了子任務這個但書**，而那正是它失效的原因：

    合成 `synthesize_answer` 跑在 `agent_orchestrator.py` 的
    `asyncio.create_task(_run_tool_loop())` **子任務**裡，
    `set_actual_provider` 因此在該子任務的 **context 副本**中執行。

實測 ContextVar 的三種傳播（六行腳本，2026-08-28）：

    async generator 內設值  → 父層讀到 groq   ✓ 會傳
    create_task     內設值  → 父層讀到 None   ✗
    gather          內設值  → 父層讀到 None   ✗

⇒ 父層的 `fire_shadow_trace` 永遠讀到 None。
   實際後果：`actual_llm_provider` 自 2026-08-01 起全空，
   而同期 `shadow_baseline` 一直報紅卻**指不出是哪個 LLM**。

## 修法：ContextVar 存**可變容器**而不是值

子任務拿到的是同一個 dict **物件**（context 複製的是參照），
所以子任務改它，父層看得到。這是 ContextVar 跨任務回傳的標準作法。

⚠️ **失敗時退回現況、不會更糟**：若 `init_provider_holder()` 沒被呼叫，
`set_actual_provider` 會就地建一個 holder —— 行為與修法前相同（只有同 context 看得到），
不會拋錯、也不會寫入錯的 provider。

⚠️ 仍然 request-scoped、不跨請求污染：holder 由 `init_provider_holder()`
在每個請求各自建立，兩個請求拿到的是不同的 dict。
（這也是**不用 `connector._last_provider`** 的原因 —— 那是連線器的實例屬性，
併發請求會互相蓋掉，而錯的歸因比沒有歸因更難察覺。）
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

#: 存**可變容器**而非值 —— 見上方說明。None 代表這個 context 還沒初始化過。
_CTX: ContextVar[Optional[dict]] = ContextVar("actual_llm_provider_holder", default=None)

_KEY = "provider"


def init_provider_holder() -> None:
    """在請求進入時（**且必須在建立子任務之前**）呼叫一次。

    之後子任務內的 `set_actual_provider` 才寫得回父層看得到的地方。
    重複呼叫會重置為 None —— 一個請求呼叫一次即可。
    """
    _CTX.set({_KEY: None})


def set_actual_provider(provider: Optional[str]) -> None:
    """設當前請求的實體 LLM provider。

    沒有 holder 時就地建一個 —— 行為退回修法前（只有同 context 可見），
    不拋錯。這讓「忘了呼叫 init」的後果是「沒有歸因」而不是「壞掉」。
    """
    holder = _CTX.get()
    if holder is None:
        holder = {_KEY: None}
        _CTX.set(holder)
    holder[_KEY] = provider


def get_actual_provider() -> Optional[str]:
    """讀當前請求最後成功推理的實體 provider，未設定時回 None。"""
    holder = _CTX.get()
    return holder.get(_KEY) if holder else None


def reset_actual_provider() -> None:
    """明確清空（單元測試用）。"""
    _CTX.set(None)
