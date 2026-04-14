# -*- coding: utf-8 -*-
"""
Provider Resolver — 決定 Shadow Logger trace 的 provider 標籤。

用於 Hermes 遷移期 A/B 比對（ADR-0014）：
  - 舊路徑：LINE/TG/Discord → OpenClaw (Haiku) → Missive   → haiku-openclaw
  - 新路徑：Telegram/Discord → Hermes (Gemma)   → Missive   → gemma-hermes

呼叫者可透過 HTTP header ``X-Provider`` 覆蓋自動判斷。
"""
from __future__ import annotations

from typing import Mapping, Optional

_DEFAULT = "unknown"

_CHANNEL_PROVIDER_MAP = {
    "hermes": "gemma-hermes",
    "openclaw": "haiku-openclaw",
    # OpenClaw 為 LINE/TG/Discord 的 gateway，流量仍走 Haiku
    "line": "haiku-openclaw",
    "telegram": "haiku-openclaw",
    "discord": "haiku-openclaw",
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
