# -*- coding: utf-8 -*-
"""
Entity Resolution Benchmark — 效能基準報告產生器

追蹤 entity resolver 各階段（exact/fuzzy/semantic/create）的
處理量、延遲和命中率，用於效能瓶頸分析。

Usage:
    bench = EntityResolutionBenchmark()
    bench.record_stage("exact", count=100, duration_ms=5.0, hit_count=80)
    report = bench.get_report()
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class _StageRecord:
    name: str
    count: int
    duration_ms: float
    hit_count: int


class EntityResolutionBenchmark:
    """Entity Resolution 效能基準報告。"""

    def __init__(self):
        self._stages: List[_StageRecord] = []

    def record_stage(
        self,
        name: str,
        count: int,
        duration_ms: float,
        hit_count: int,
    ):
        self._stages.append(_StageRecord(
            name=name, count=count,
            duration_ms=duration_ms, hit_count=hit_count,
        ))

    def get_report(self) -> Dict[str, Any]:
        stages = []
        total_entities = self._stages[0].count if self._stages else 0
        total_duration = sum(s.duration_ms for s in self._stages)

        for s in self._stages:
            stages.append({
                "name": s.name,
                "count": s.count,
                "duration_ms": round(s.duration_ms, 2),
                "hit_count": s.hit_count,
                "hit_rate": round(s.hit_count / s.count, 3) if s.count > 0 else 0,
                "avg_ms_per_entity": round(s.duration_ms / s.count, 2) if s.count > 0 else 0,
            })

        return {
            "stages": stages,
            "summary": {
                "total_entities": total_entities,
                "total_duration_ms": round(total_duration, 2),
                "stages_count": len(stages),
            },
        }
