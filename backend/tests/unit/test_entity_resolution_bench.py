# -*- coding: utf-8 -*-
"""
Entity Resolution 效能基準測試

不連 DB — 測量解析器各階段的邏輯效能：
1. exact_match 查詢結構正確
2. semantic_match 查詢含 HNSW ef_search
3. resolve_entities_batch 批次邏輯（mock DB）
4. EntityResolutionBenchmark 報告格式
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch


class TestEntityResolutionBenchmark:
    """Entity Resolution 基準報告產生器"""

    def test_benchmark_report_structure(self):
        """基準報告應包含 stages 和 summary"""
        from app.core.entity_resolution_benchmark import EntityResolutionBenchmark

        bench = EntityResolutionBenchmark()
        bench.record_stage("exact", count=100, duration_ms=5.0, hit_count=80)
        bench.record_stage("fuzzy", count=20, duration_ms=15.0, hit_count=12)
        bench.record_stage("semantic", count=8, duration_ms=50.0, hit_count=5)
        bench.record_stage("create", count=3, duration_ms=10.0, hit_count=3)

        report = bench.get_report()
        assert "stages" in report
        assert len(report["stages"]) == 4
        assert "summary" in report
        assert report["summary"]["total_entities"] == 100
        assert report["summary"]["total_duration_ms"] == 80.0

    def test_benchmark_hit_rate(self):
        """各階段命中率應正確計算"""
        from app.core.entity_resolution_benchmark import EntityResolutionBenchmark

        bench = EntityResolutionBenchmark()
        bench.record_stage("exact", count=100, duration_ms=5.0, hit_count=80)

        report = bench.get_report()
        exact = report["stages"][0]
        assert exact["hit_rate"] == 0.8

    def test_benchmark_empty(self):
        """無紀錄時報告不應 crash"""
        from app.core.entity_resolution_benchmark import EntityResolutionBenchmark

        bench = EntityResolutionBenchmark()
        report = bench.get_report()
        assert report["summary"]["total_entities"] == 0
        assert len(report["stages"]) == 0

    def test_benchmark_avg_duration(self):
        """平均延遲應正確計算"""
        from app.core.entity_resolution_benchmark import EntityResolutionBenchmark

        bench = EntityResolutionBenchmark()
        bench.record_stage("exact", count=50, duration_ms=100.0, hit_count=50)

        report = bench.get_report()
        assert report["stages"][0]["avg_ms_per_entity"] == 2.0  # 100/50
