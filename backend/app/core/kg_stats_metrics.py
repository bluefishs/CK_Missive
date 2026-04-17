# -*- coding: utf-8 -*-
"""
KG Statistics Prometheus Metrics

暴露知識圖譜核心統計到 /metrics，
供 Grafana 追蹤實體/邊/Wiki 成長趨勢。

Metrics:
- kg_entities_total (Gauge)
- kg_edges_total (Gauge)
- kg_wiki_pages_total (Gauge)
"""
from typing import Optional

from prometheus_client import Gauge, CollectorRegistry, REGISTRY

KG_ENTITIES_METRIC = "kg_entities_total"
KG_EDGES_METRIC = "kg_edges_total"
KG_WIKI_METRIC = "kg_wiki_pages_total"


class KGStatsMetrics:
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.entities = Gauge(KG_ENTITIES_METRIC, "Total KG canonical entities", registry=reg)
        self.edges = Gauge(KG_EDGES_METRIC, "Total KG entity relationships", registry=reg)
        self.wiki_pages = Gauge(KG_WIKI_METRIC, "Total LLM Wiki pages", registry=reg)

    def set_entity_count(self, count: int):
        self.entities.set(count)

    def set_edge_count(self, count: int):
        self.edges.set(count)

    def update_from_counts(self, entities: int = 0, edges: int = 0, wiki_pages: int = 0):
        self.entities.set(entities)
        self.edges.set(edges)
        self.wiki_pages.set(wiki_pages)


_instance: Optional[KGStatsMetrics] = None


def get_kg_stats_metrics() -> KGStatsMetrics:
    global _instance
    if _instance is None:
        _instance = KGStatsMetrics()
    return _instance
