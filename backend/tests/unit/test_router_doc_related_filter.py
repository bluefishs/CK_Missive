# -*- coding: utf-8 -*-
"""
Router「[實體]相關公文」誤觸 cross-graph 修法 Regression（2026-06-09）

背景：failure-a18f229167（get_statistics+search_across_graphs 6/6 fail）典型問法
  「桃園市工務局相關公文」→ 工務局(agency)+公文(doc)+相關(cross-link) 三命中
  → Layer 1.6 誤判跨域查詢觸發 search_across_graphs → 6/6 失敗。
但「[機關]相關公文」實為單一文件搜尋慣用語（related documents），非真跨域關聯。

修法：Layer 1.6 前加精準守衛 — 「相關+公文類名詞」→ search_documents。
"""
import asyncio

import pytest

from app.services.ai.agent.agent_router import AgentRouter


def _route(q: str):
    return asyncio.run(AgentRouter().route(q))


class TestDocRelatedFilter:
    @pytest.mark.parametrize("q", [
        "桃園市工務局相關公文",
        "工務局相關函",
        "廠商相關公文有哪些",
    ])
    def test_related_docs_route_to_search_documents(self, q):
        d = _route(q)
        tools = [c["name"] for c in (d.plan or {}).get("tool_calls", [])]
        assert "search_across_graphs" not in tools, f"「相關公文」不應誤觸 cross-graph: {q!r} → {tools}"
        assert "search_documents" in tools, f"「相關公文」應路由 search_documents: {q!r} → {tools}"

    def test_genuine_cross_graph_preserved(self):
        """真跨域關聯（派工單與公文的關聯）仍走 search_across_graphs，不被守衛波及。"""
        d = _route("派工單與公文的關聯")
        tools = [c["name"] for c in (d.plan or {}).get("tool_calls", [])]
        assert "search_across_graphs" in tools, f"真跨域查詢不應被守衛攔走 → {tools}"
