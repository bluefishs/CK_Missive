# -*- coding: utf-8 -*-
"""Provider Resolver TDD — 決定 shadow_logger 的 provider 標籤。

規則（由高到低優先）：
  1. X-Provider header 顯式指定 → 直接採用
  2. channel=hermes → gemma-hermes
  3. channel=openclaw → haiku-openclaw
  4. channel=line/telegram/discord 無 header → 視為 openclaw 轉介 → haiku-openclaw
  5. channel=mcp/web → 無法判斷 → unknown
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
def test_legacy_channels_route_via_openclaw(ch):
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel=ch, headers={}) == "haiku-openclaw"


@pytest.mark.parametrize("ch", ["mcp", "web", None, "unknown-x"])
def test_ambiguous_channels_return_unknown(ch):
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel=ch, headers={}) == "unknown"


def test_case_insensitive_header():
    from app.services.ai.agent.provider_resolver import resolve_provider

    assert resolve_provider(channel="hermes", headers={"x-provider": "foo"}) == "foo"
