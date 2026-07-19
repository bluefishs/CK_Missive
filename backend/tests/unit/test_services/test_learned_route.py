"""
tool_combo 確定性路由（#1）TDD 測試 — 純函式層。

技能系統評估：graduated tool_combo（業務查詢→工具，avg_hit 18）目前只注入 prompt，
未接確定性路由。本測試鎖定純函式 match_learned_route：高相似度匹配乾淨模式 → 直呼工具，
噪音/不相關 → None（fallthrough LLM）。保守閾值防誤路由（核心價值＝不路由錯）。

RED-GREEN-REFACTOR。相關 skill_value_audit.py / AI_ROLE_REPOSITIONING.md §技能樹評估。
"""
import pytest

from app.services.ai.agent.agent_router import (
    extract_tool_and_query,
    match_learned_route,
)


# 乾淨 graduated tool_combo 的 source_question（工具內嵌括號）
CLEAN_ROUTES_RAW = [
    "查詢廠商應付帳款（get_vendor_detail），到期日近者優先",
    "列出所有資產（list_assets）並顯示資產統計",
    "未付請款清單（get_unpaid_billings）",
]


def _build_routes():
    routes = []
    for s in CLEAN_ROUTES_RAW:
        tool, query = extract_tool_and_query(s)
        routes.append({"tool": tool, "query": query, "hit": 20})
    return routes


class TestExtractToolAndQuery:
    def test_extract_valid_tool_from_paren(self):
        tool, query = extract_tool_and_query("查詢廠商應付帳款（get_vendor_detail），到期日近者優先")
        assert tool == "get_vendor_detail"
        # 工具括號被剝除，保留人類查詢
        assert "get_vendor_detail" not in query
        assert "查詢廠商應付帳款" in query

    def test_no_tool_returns_none(self):
        tool, query = extract_tool_and_query("幫我")  # 噪音、無工具
        assert tool is None


class TestMatchLearnedRoute:
    def test_matches_similar_query_to_tool(self):
        """「查廠商應付帳款」應匹配「查詢廠商應付帳款…」→ get_vendor_detail。"""
        routes = _build_routes()
        result = match_learned_route("查廠商應付帳款", routes)
        assert result is not None
        assert result["tool"] == "get_vendor_detail"

    def test_matches_asset_query(self):
        routes = _build_routes()
        result = match_learned_route("列出所有資產", routes)
        assert result is not None
        assert result["tool"] == "list_assets"

    def test_unrelated_query_returns_none(self):
        """不相關查詢不路由（fallthrough LLM）。"""
        routes = _build_routes()
        assert match_learned_route("今天天氣如何", routes) is None

    def test_empty_or_short_query_returns_none(self):
        routes = _build_routes()
        assert match_learned_route("", routes) is None
        assert match_learned_route("你好", routes) is None

    def test_conservative_threshold_prevents_weak_match(self):
        """部分重疊但低於保守閾值 → 不路由（寧可走 LLM 不誤路由）。"""
        routes = _build_routes()
        # 只沾一個詞，不足以確定性路由
        assert match_learned_route("資產是什麼意思", routes, threshold=0.7) is None

    def test_empty_routes_returns_none(self):
        assert match_learned_route("查廠商應付帳款", []) is None
