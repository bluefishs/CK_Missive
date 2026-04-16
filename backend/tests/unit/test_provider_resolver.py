# -*- coding: utf-8 -*-
"""Provider Resolver TDD — 決定 shadow_logger 的 provider 標籤。

規則（由高到低優先，Hermes era）：
  1. X-Provider header 顯式指定 → 直接採用
  2. channel=hermes → gemma-hermes
  3. channel=openclaw → haiku-openclaw (歷史相容)
  4. channel=line/telegram/discord → gemma-hermes (Hermes 取代 OpenClaw, ADR-0014)
  5. channel=mcp/web → gemma-local
  6. 其他 → unknown
"""
from __future__ import annotations

import pytest


def test_explicit_header_wins():
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel="hermes", headers={"X-Provider": "custom-model"}) == "custom-model"


def test_hermes_channel_maps_to_gemma():
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel="hermes", headers={}) == "gemma-hermes"


def test_openclaw_channel_maps_to_haiku():
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel="openclaw", headers={}) == "haiku-openclaw"


@pytest.mark.parametrize("ch", ["line", "telegram", "discord"])
def test_messaging_channels_route_via_hermes(ch):
    """ADR-0014: LINE/Telegram/Discord 現走 Hermes Agent"""
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel=ch, headers={}) == "gemma-hermes"


@pytest.mark.parametrize("ch", ["mcp", "web"])
def test_direct_channels_return_local(ch):
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel=ch, headers={}) == "gemma-local"


@pytest.mark.parametrize("ch", [None, "unknown-x"])
def test_unknown_channels_return_unknown(ch):
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel=ch, headers={}) == "unknown"


def test_case_insensitive_header():
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel="hermes", headers={"x-provider": "foo"}) == "foo"
