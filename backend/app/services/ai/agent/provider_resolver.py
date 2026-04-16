# -*- coding: utf-8 -*-
"""
Provider Resolver — 決定 Shadow Logger trace 的 provider 標籤。

用於 Hermes 遷移期 A/B 比對（ADR-0014）：
  - Telegram/Discord → Hermes (Gemma) → Missive → gemma-hermes
  - Web → Missive 直連 → gemma-local

呼叫者可透過 HTTP header ``X-Provider`` 覆蓋自動判斷。
"""
from __future__ import annotations

from typing import Mapping, Optional

_DEFAULT = "unknown"

_CHANNEL_PROVIDER_MAP = {
    "hermes": "gemma-hermes",
    "telegram": "gemma-hermes",
    "discord": "gemma-hermes",
    "line": "gemma-hermes",
    "web": "gemma-local",
    "mcp": "gemma-local",
    # 歷史相容 — 舊日誌可能帶此標籤
    "openclaw": "haiku-openclaw",
}


def _normalize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


def resolve_provider(
    *,
    channel: Optional[str],
    headers: Mapping[str, str],
) -> str:
    """回傳 provider 標籤，供 shadow_logger.log_trace(provider=...) 使用。"""
    norm = _normalize_headers(headers or {})
    explicit = norm.get("x-provider")
    if explicit:
        return explicit

    if channel and channel in _CHANNEL_PROVIDER_MAP:
        return _CHANNEL_PROVIDER_MAP[channel]

    return _DEFAULT
