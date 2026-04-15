# -*- coding: utf-8 -*-
"""TunnelGuard allowlist TDD — ADR-0014/0015/0016 對齊。

經 Cloudflare Tunnel 進入的機器流量，必須能達到：
  - webhook（LINE/Discord/Telegram）
  - Hermes ACP + feedback
  - Manifest + agent query_sync
  - health probe

人員流量（UI、admin）仍被擋，需走 CF Access 或內網。
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("path", [
    "/api/health",
    "/api/health/detailed",
    "/api/line/webhook",
    "/api/discord/webhook",
    "/api/discord/interactions",
    "/api/telegram/webhook",
    "/api/hermes/acp",
    "/api/hermes/feedback",
    "/api/ai/agent/tools",
    "/api/ai/agent/query_sync",
    "/api/public/anything",
])
def test_machine_paths_allowed_through_tunnel(path):
    from app.core.tunnel_guard import _path_allowed
    assert _path_allowed(path), f"{path} 應允許 tunnel 存取（機器流量）"


@pytest.mark.parametrize("path", [
    "/",
    "/api/documents",
    "/api/users",
    "/api/admin/settings",
    "/api/ai/stats/patterns",
    "/docs",
])
def test_human_paths_blocked_through_tunnel(path):
    from app.core.tunnel_guard import _path_allowed
    assert not _path_allowed(path), f"{path} 不該允許 tunnel 直接存取（走 CF Access）"
