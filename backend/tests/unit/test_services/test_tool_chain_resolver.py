"""Tests for tool_chain_resolver — Chain-of-Tools parameter injection"""

import pytest
from app.services.ai.tools.tool_chain_resolver import (
    extract_chain_context,
    resolve_chain_params,
    enrich_plan_with_chain,
)


class TestExtractChainContext:
    def test_empty_results(self):
        ctx = extract_chain_context([])
        assert all(v == [] for v in ctx.values())

    def test_search_entities_extracts_ids_and_names(self):
        results = [{
            "tool": "search_entities",
            "result": {
                "count": 2,
                "entities": [
                    {"id": 10, "name": "桃園市政府", "entity_type": "org"},
                    {"id": 20, "name": "道路工程", "entity_type": "project"},
                ],
            },
        }]
        ctx = extract_chain_context(results)
        assert ctx["entity_ids"] == [10, 20]
        assert ctx["entity_names"] == ["桃園市政府", "道路工程"]
        assert ctx["agency_names"] == ["桃園市政府"]

    def test_search_documents_extracts_doc_ids_and_senders(self):
        results = [{
            "tool": "search_documents",
            "result": {
                "count": 1,
                "documents": [
                    {"id": 100, "sender": "工務局", "subject": "道路修繕"},
                ],
            },
        }]
        ctx = extract_chain_context(results)
        assert ctx["document_ids"] == [100]
        assert ctx["agency_names"] == ["工務局"]

    def test_search_dispatch_orders_extracts_dispatch_and_project(self):
        results = [{
            "tool": "search_dispatch_orders",
            "result": {
                "count": 1,
                "dispatch_orders": [
                    {"id": 5, "contract_project_id": 30, "project_name": "路面修復"},
                ],
            },
        }]
        ctx = extract_chain_context(results)
        assert ctx["dispatch_ids"] == [5]
        assert ctx["project_ids"] == [30]
        assert ctx["project_names"] == ["路面修復"]

    def test_skips_error_results(self):
        results = [{
            "tool": "search_entities",
            "result": {"error": "timeout", "count": 0},
        }]
        ctx = extract_chain_context(results)
        assert ctx["entity_ids"] == []

    def test_deduplicates_values(self):
        results = [
            {
                "tool": "search_entities",
                "result": {
                    "count": 1,
                    "entities": [{"id": 10, "name": "A"}],
                },
            },
            {
                "tool": "search_entities",
                "result": {
                    "count": 1,
                    "entities": [{"id": 10, "name": "A"}],
                },
            },
        ]
        ctx = extract_chain_context(results)
        assert ctx["entity_ids"] == [10]
        assert ctx["entity_names"] == ["A"]

    def test_multi_tool_aggregation(self):
        results = [
            {
                "tool": "search_dispatch_orders",
                "result": {
                    "count": 1,
                    "dispatch_orders": [{"id": 1, "project_name": "測量"}],
                },
            },
            {
                "tool": "search_entities",
                "result": {
                    "count": 1,
                    "entities": [{"id": 50, "name": "測量案", "entity_type": "project"}],
                },
            },
        ]
        ctx = extract_chain_context(results)
        assert ctx["dispatch_ids"] == [1]
        assert ctx["entity_ids"] == [50]
        assert ctx["project_names"] == ["測量"]


class TestResolveChainParams:
    def test_get_entity_detail_auto_fills_entity_id(self):
        tc = {"name": "get_entity_detail", "params": {}}
        ctx = {"entity_ids": [10, 20], "entity_names": [], "document_ids": [],
               "dispatch_ids": [], "project_ids": [], "project_names": [],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result["entity_id"] == 10

    def test_get_entity_detail_preserves_existing_param(self):
        tc = {"name": "get_entity_detail", "params": {"entity_id": 99}}
        ctx = {"entity_ids": [10], "entity_names": [], "document_ids": [],
               "dispatch_ids": [], "project_ids": [], "project_names": [],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result["entity_id"] == 99

    def test_navigate_graph_auto_fills_source_target(self):
        tc = {"name": "navigate_graph", "params": {}}
        ctx = {"entity_ids": [10, 20], "entity_names": [], "document_ids": [],
               "dispatch_ids": [], "project_ids": [], "project_names": [],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result["source_id"] == 10
        assert result["target_id"] == 20

    def test_find_correspondence_auto_fills_dispatch_id(self):
        tc = {"name": "find_correspondence", "params": {}}
        ctx = {"entity_ids": [], "entity_names": [], "document_ids": [],
               "dispatch_ids": [5], "project_ids": [], "project_names": [],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result["dispatch_id"] == 5

    def test_find_similar_auto_fills_document_id(self):
        tc = {"name": "find_similar", "params": {}}
        ctx = {"entity_ids": [], "entity_names": [], "document_ids": [100],
               "dispatch_ids": [], "project_ids": [], "project_names": [],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result["document_id"] == 100

    def test_search_entities_fills_query_from_project_names(self):
        tc = {"name": "search_entities", "params": {}}
        ctx = {"entity_ids": [], "entity_names": [], "document_ids": [],
               "dispatch_ids": [], "project_ids": [], "project_names": ["道路工程"],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result["query"] == "道路工程"

    def test_unknown_tool_returns_original_params(self):
        tc = {"name": "unknown_tool", "params": {"foo": "bar"}}
        ctx = {"entity_ids": [1], "entity_names": [], "document_ids": [],
               "dispatch_ids": [], "project_ids": [], "project_names": [],
               "agency_names": [], "keywords": []}
        result = resolve_chain_params(tc, ctx)
        assert result == {"foo": "bar"}


class TestEnrichPlanWithChain:
    def test_no_results_returns_plan_unchanged(self):
        plan = {"tool_calls": [{"name": "search_documents", "params": {}}]}
        result = enrich_plan_with_chain(plan, [])
        assert result == plan

    def test_no_tool_calls_returns_plan_unchanged(self):
        plan = {"tool_calls": []}
        results = [{"tool": "search_entities", "result": {"count": 1, "entities": [{"id": 1}]}}]
        result = enrich_plan_with_chain(plan, results)
        assert result["tool_calls"] == []

    def test_full_chain_enrichment(self):
        plan = {
            "reasoning": "取得實體詳情",
            "tool_calls": [
                {"name": "get_entity_detail", "params": {}},
            ],
        }
        results = [{
            "tool": "search_entities",
            "result": {
                "count": 1,
                "entities": [{"id": 42, "name": "桃園市政府", "entity_type": "org"}],
            },
        }]
        enriched = enrich_plan_with_chain(plan, results)
        assert enriched["tool_calls"][0]["params"]["entity_id"] == 42

    def test_chain_does_not_overwrite_explicit_params(self):
        plan = {
            "tool_calls": [
                {"name": "get_entity_detail", "params": {"entity_id": 99}},
            ],
        }
        results = [{
            "tool": "search_entities",
            "result": {
                "count": 1,
                "entities": [{"id": 42, "name": "Test"}],
            },
        }]
        enriched = enrich_plan_with_chain(plan, results)
        assert enriched["tool_calls"][0]["params"]["entity_id"] == 99

    def test_multi_tool_chain(self):
        plan = {
            "tool_calls": [
                {"name": "find_correspondence", "params": {}},
                {"name": "search_entities", "params": {}},
            ],
        }
        results = [{
            "tool": "search_dispatch_orders",
            "result": {
                "count": 1,
                "dispatch_orders": [
                    {"id": 7, "project_name": "道路修繕", "contract_project_id": 30},
                ],
            },
        }]
        enriched = enrich_plan_with_chain(plan, results)
        assert enriched["tool_calls"][0]["params"]["dispatch_id"] == 7
        assert enriched["tool_calls"][1]["params"]["query"] == "道路修繕"
