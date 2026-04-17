# -*- coding: utf-8 -*-
"""
TDD: KG Statistics Prometheus Gauge

驗證：
1. kg_entities_total gauge 設定正確
2. kg_edges_total gauge 設定正確
3. update_from_counts 批次更新
"""
import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    return CollectorRegistry()


def test_kg_entity_gauge(registry):
    from app.core.kg_stats_metrics import KGStatsMetrics

    metrics = KGStatsMetrics(registry=registry)
    metrics.set_entity_count(2504)

    from app.core.kg_stats_metrics import KG_ENTITIES_METRIC
    g = registry._names_to_collectors.get(KG_ENTITIES_METRIC)
    assert g is not None
    samples = g.collect()[0].samples
    assert any(s.value == 2504 for s in samples)


def test_kg_edge_gauge(registry):
    from app.core.kg_stats_metrics import KGStatsMetrics

    metrics = KGStatsMetrics(registry=registry)
    metrics.set_edge_count(5800)

    from app.core.kg_stats_metrics import KG_EDGES_METRIC
    g = registry._names_to_collectors.get(KG_EDGES_METRIC)
    samples = g.collect()[0].samples
    assert any(s.value == 5800 for s in samples)


def test_update_from_counts(registry):
    from app.core.kg_stats_metrics import KGStatsMetrics

    metrics = KGStatsMetrics(registry=registry)
    metrics.update_from_counts(entities=1000, edges=3000, wiki_pages=220)

    from app.core.kg_stats_metrics import KG_WIKI_METRIC
    g = registry._names_to_collectors.get(KG_WIKI_METRIC)
    samples = g.collect()[0].samples
    assert any(s.value == 220 for s in samples)
