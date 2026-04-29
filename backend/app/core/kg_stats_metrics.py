# -*- coding: utf-8 -*-
"""
KG Statistics Prometheus Metrics — Knowledge Growth Governance

暴露知識圖譜核心統計到 /metrics，供 Grafana 追蹤實體/邊/Wiki/embedding 成長趨勢。

v2.0.0（2026-04-29，v5.10.2 #7）：加入 embedding 治理 metrics
領域：knowledge growth governance —
  從「月度 fitness audit」升級為「即時 Prometheus 觀測」，
  讓 Grafana dashboard 能 alert「embedding coverage < 95%」。

Metrics:
- kg_entities_total (Gauge)            — 全 KG entities
- kg_edges_total (Gauge)               — 全 KG entity relations
- kg_wiki_pages_total (Gauge)          — LLM Wiki pages
- kg_entities_embedded_total (Gauge)   — 有 embedding 的 entities (v2.0)
- kg_embedding_coverage_ratio (Gauge)  — embedded / total（0.0~1.0）(v2.0)
"""
from typing import Optional

from prometheus_client import Gauge, CollectorRegistry, REGISTRY

KG_ENTITIES_METRIC = "kg_entities_total"
KG_EDGES_METRIC = "kg_edges_total"
KG_WIKI_METRIC = "kg_wiki_pages_total"
KG_EMBEDDED_METRIC = "kg_entities_embedded_total"
KG_COVERAGE_METRIC = "kg_embedding_coverage_ratio"


class KGStatsMetrics:
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.entities = Gauge(KG_ENTITIES_METRIC, "Total KG canonical entities", registry=reg)
        self.edges = Gauge(KG_EDGES_METRIC, "Total KG entity relationships", registry=reg)
        self.wiki_pages = Gauge(KG_WIKI_METRIC, "Total LLM Wiki pages", registry=reg)
        # v2.0 embedding 治理 metrics
        self.embedded = Gauge(
            KG_EMBEDDED_METRIC,
            "KG canonical entities with pgvector embedding",
            registry=reg,
        )
        self.coverage_ratio = Gauge(
            KG_COVERAGE_METRIC,
            "KG embedding coverage ratio (embedded / total, 0.0~1.0)",
            registry=reg,
        )

    def set_entity_count(self, count: int):
        self.entities.set(count)

    def set_edge_count(self, count: int):
        self.edges.set(count)

    def update_from_counts(self, entities: int = 0, edges: int = 0, wiki_pages: int = 0):
        self.entities.set(entities)
        self.edges.set(edges)
        self.wiki_pages.set(wiki_pages)

    def update_embedding_stats(self, total: int, embedded: int):
        """v2.0：更新 embedding 治理 gauge（會同步更新 entities total）"""
        self.entities.set(total)
        self.embedded.set(embedded)
        if total > 0:
            self.coverage_ratio.set(embedded / total)
        else:
            self.coverage_ratio.set(0)

    async def refresh_from_db(self, db) -> dict:
        """v2.0：從 DB 抓最新統計並更新所有 KG gauge

        回傳：{"total": N, "embedded": M, "coverage": 0.xxx, "edges": K, "wiki_pages": W}
        供 caller 也能 log / report，不只是 set gauge。
        """
        from sqlalchemy import text as _sql

        result = await db.execute(_sql(
            "SELECT COUNT(*) AS total, "
            "COUNT(embedding) AS embedded "
            "FROM canonical_entities"
        ))
        row = result.first()
        total = int(row.total or 0)
        embedded = int(row.embedded or 0)

        edge_row = await db.execute(_sql("SELECT COUNT(*) FROM entity_relations"))
        edges = int(edge_row.scalar() or 0)

        # wiki_pages 從 wiki/ 子目錄計檔案數（非 DB 物件，留 caller 算或 0）
        self.update_embedding_stats(total, embedded)
        self.edges.set(edges)
        coverage = embedded / total if total > 0 else 0
        return {
            "total": total,
            "embedded": embedded,
            "coverage": coverage,
            "edges": edges,
        }


_instance: Optional[KGStatsMetrics] = None


def get_kg_stats_metrics() -> KGStatsMetrics:
    global _instance
    if _instance is None:
        _instance = KGStatsMetrics()
    return _instance
