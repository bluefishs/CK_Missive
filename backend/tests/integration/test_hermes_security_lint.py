# -*- coding: utf-8 -*-
"""Hermes 端點結構守門 — 資安政策回歸測試。

防止未來新增 Hermes 端點時誤用 GET 或遺漏 service token。
"""
from __future__ import annotations

import pytest


@pytest.fixture
def hermes_routes():
    from app.api.endpoints.hermes_acp import router
    return router.routes


def test_all_hermes_routes_are_post_only(hermes_routes):
    """資安政策：Hermes 端點必須全 POST。"""
    for route in hermes_routes:
        methods = getattr(route, "methods", set())
        assert methods == {"POST"}, (
            f"{route.path} methods={methods} 違反 POST-only 政策"
        )


def test_all_hermes_routes_require_service_token(hermes_routes):
    """每個 hermes 端點必須依賴 _verify_service_token。"""
    from app.api.endpoints.hermes_acp import _verify_service_token

    for route in hermes_routes:
        deps = []
        if hasattr(route, "dependant"):
            deps = [d.call for d in route.dependant.dependencies]
        assert _verify_service_token in deps, (
            f"{route.path} 缺 service token 依賴"
        )


def test_hermes_router_paths_match_manifest(hermes_routes):
    """router 路徑必須與 manifest hermes 區塊對齊（ADR-0014 contract）。"""
    from app.api.endpoints.ai.tools_manifest import TOOL_MANIFEST

    advertised = {
        TOOL_MANIFEST["hermes"]["acp_endpoint"],
        TOOL_MANIFEST["hermes"]["feedback_endpoint"],
    }
    # hermes router 以 /hermes 為 prefix，完整路徑要加 /api
    actual = {f"/api{r.path}" for r in hermes_routes}
    assert advertised.issubset(actual), (
        f"manifest advertises {advertised} but router has {actual}"
    )
