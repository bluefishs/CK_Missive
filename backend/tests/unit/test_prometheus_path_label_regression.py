# -*- coding: utf-8 -*-
"""Prometheus `path` 標籤必須是路由樣板，不是原始 URL（2026-08-04 回歸鎖）。

背景：原本標籤直接用 `scope["path"]`，造成
  1. 基數無上限 —— 每份公文/每張派工單各一條 time series（實測 16467 條）
  2. 價值層判定失效 —— 零流量清單裡是 `/documents-enhanced/2645/detail` 這種**實例路徑**，
     它是 0 只代表「這 7 天沒人開 2645」，回答不了「這個能力還有沒有人用」

這支測試鎖住還原邏輯本身；壞掉時症狀是**指標看起來仍然正常**，
所以必須有測試，不能靠人眼看 /metrics。
"""
from __future__ import annotations

import pytest

from app.core.prometheus_middleware import UNMATCHED_PATH_LABEL, _route_template


def _scope(path_params=None, endpoint=object()):
    s = {"type": "http"}
    if path_params is not None:
        s["path_params"] = path_params
    if endpoint is not None:
        s["endpoint"] = endpoint
    return s


class TestRouteTemplate:
    def test_single_param_is_templated(self):
        got = _route_template(
            _scope({"doc_id": 2645}), "/api/documents-enhanced/2645/detail",
        )
        assert got == "/api/documents-enhanced/{doc_id}/detail"

    def test_multiple_params_all_templated(self):
        got = _route_template(
            _scope({"project_id": 24, "user_id": 7}),
            "/api/project-staff/project/24/user/7/list",
        )
        assert got == "/api/project-staff/project/{project_id}/user/{user_id}/list"

    def test_route_without_params_unchanged(self):
        assert _route_template(_scope({}), "/api/health") == "/api/health"

    def test_unmatched_path_collapses_to_single_label(self):
        """404/掃描器路徑不得各佔一條 series —— 這正是基數爆炸的來源之一。"""
        got = _route_template(_scope(path_params=None, endpoint=None), "/wp-admin/x.php")
        assert got == UNMATCHED_PATH_LABEL

    def test_param_value_equal_to_static_segment_only_replaces_own_segment(self):
        """整段比對而非字串取代：值剛好等於別的片段時不得誤傷。

        `/api/detail/detail` 這種路徑，若用 str.replace 會把兩段都換掉。
        """
        got = _route_template(_scope({"name": "detail"}), "/api/detail/detail")
        # 兩段都等於參數值時，整段比對會一致地替換 —— 重點是**不會**產生
        # 半個片段被換掉的破碎結果（如 `/api/{name}/{name}x`）。
        assert got.count("{name}") == 2
        assert "{name}x" not in got

    def test_catch_all_path_param_spanning_segments(self):
        """`:path` 型參數的值跨多個片段 —— 這是實測踩到的那一個。

        `/api/documents-enhanced/880/detail` 的 404 其實是被 SPA catch-all
        `/{spa_path:path}` 接走的，param 值 = `api/documents-enhanced/880/detail`。
        整段比對接不住 → 若不處理就照原樣記錄，基數問題原封不動。
        """
        got = _route_template(
            _scope({"spa_path": "api/documents-enhanced/880/detail"}),
            "/api/documents-enhanced/880/detail",
        )
        assert got == "/{spa_path}"

    def test_mixed_multi_and_single_segment_params(self):
        got = _route_template(
            _scope({"rest": "a/b", "doc_id": 7}),
            "/api/x/7/a/b",
        )
        assert got == "/api/x/{doc_id}/{rest}"

    def test_numeric_and_string_params_both_handled(self):
        """path_params 的值可能是 int（已被 convertor 轉型），比對前需轉字串。"""
        assert _route_template(
            _scope({"n": 151}), "/api/taoyuan-dispatch/dispatch/151/detail",
        ) == "/api/taoyuan-dispatch/dispatch/{n}/detail"


@pytest.mark.asyncio
async def test_middleware_labels_use_template_not_raw_url():
    """端到端：middleware 實際打進 counter 的標籤必須是樣板。"""
    from prometheus_client import CollectorRegistry
    from app.core.prometheus_middleware import PrometheusMiddleware

    async def fake_app(scope, receive, send):
        # 模擬 Starlette Router 匹配後寫回 scope
        scope["endpoint"] = fake_app
        scope["path_params"] = {"doc_id": 2645}
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    registry = CollectorRegistry()
    mw = PrometheusMiddleware(fake_app, registry=registry)
    scope = {"type": "http", "path": "/api/documents-enhanced/2645/detail",
             "method": "GET"}

    async def receive():
        return {"type": "http.request"}

    sent = []

    async def send(m):
        sent.append(m)

    await mw(scope, receive, send)

    labels = {
        s.labels["path"]
        for m in registry.collect() if m.name == "http_requests"
        for s in m.samples
    }
    assert "/api/documents-enhanced/{doc_id}/detail" in labels
    assert "/api/documents-enhanced/2645/detail" not in labels
