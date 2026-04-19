# -*- coding: utf-8 -*-
"""
Memory Wiki Prometheus Metrics (ADR-0022 Phase 6)

暴露助理記憶系統狀態到 /metrics，供 Grafana 追蹤：
- 日記連續性（如果助理突然停寫 = Agent 閉環斷了）
- Pattern 成長 / 結晶候選比率（學習曲線）
- 待決 proposal 積壓（如果 pending > 10 = user 沒來審）

Gauges（由 scheduler job 定期更新 + endpoint 觸發時 refresh）：
- memory_diary_days_total
- memory_patterns_total / memory_patterns_crystallization_candidates
- memory_failures_active_total
- memory_proposals_pending / memory_proposals_total
- memory_crystals_total
- memory_autobiographies_total

Counters（fire-and-forget inc）：
- memory_diary_appends_total       每次 append_entry 成功 +1
- memory_pattern_extract_runs_total 每次 cron job 跑完 +1（with status label）
- memory_crystal_applied_total     每次 crystal apply OK +1
"""
from pathlib import Path
from typing import Optional

from prometheus_client import Counter, Gauge, CollectorRegistry, REGISTRY

# ───── Gauges ─────
MEM_DIARY_DAYS = "memory_diary_days_total"
MEM_PATTERNS = "memory_patterns_total"
MEM_FAILURES = "memory_failures_total"
MEM_CRYSTALS = "memory_crystals_total"
MEM_PROPOSALS_TOTAL = "memory_proposals_total"
MEM_PROPOSALS_PENDING = "memory_proposals_pending"
MEM_AUTOBIOS = "memory_autobiographies_total"

# ───── Counters ─────
MEM_DIARY_APPENDS = "memory_diary_appends_total"
MEM_PATTERN_EXTRACT_RUNS = "memory_pattern_extract_runs_total"
MEM_CRYSTAL_APPLIED = "memory_crystal_applied_total"


class MemoryWikiMetrics:
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY

        # Gauges
        self.diary_days = Gauge(
            MEM_DIARY_DAYS, "Total diary days written", registry=reg,
        )
        self.patterns = Gauge(
            MEM_PATTERNS, "Total success patterns extracted", registry=reg,
        )
        self.failures = Gauge(
            MEM_FAILURES, "Total failure records (active + inactive)", registry=reg,
        )
        self.crystals = Gauge(
            MEM_CRYSTALS, "Total approved crystals (yaml edits applied)", registry=reg,
        )
        self.proposals_total = Gauge(
            MEM_PROPOSALS_TOTAL, "Total proposals (pending + applied + rejected)", registry=reg,
        )
        self.proposals_pending = Gauge(
            MEM_PROPOSALS_PENDING, "Proposals awaiting admin approval", registry=reg,
        )
        self.autobiographies = Gauge(
            MEM_AUTOBIOS, "Total weekly autobiographies written", registry=reg,
        )

        # Counters
        self.diary_appends = Counter(
            MEM_DIARY_APPENDS, "Diary entry appends", registry=reg,
        )
        self.pattern_extract_runs = Counter(
            MEM_PATTERN_EXTRACT_RUNS,
            "Pattern extractor cron runs",
            ["status"],  # ok / error
            registry=reg,
        )
        self.crystal_applied = Counter(
            MEM_CRYSTAL_APPLIED, "Crystal apply successes", registry=reg,
        )

    def refresh_from_disk(self, wiki_memory_dir: Path) -> None:
        """讀 wiki/memory/* 當下檔數更新 gauges。"""
        def _count(subdir: str, pattern: str = "*.md") -> int:
            d = wiki_memory_dir / subdir
            if not d.exists():
                return 0
            return len([f for f in d.glob(pattern) if not f.name.startswith(".")])

        def _count_pending_proposals() -> int:
            d = wiki_memory_dir / "proposals"
            if not d.exists():
                return 0
            cnt = 0
            for p in d.glob("*.md"):
                try:
                    if "status: pending" in p.read_text(encoding="utf-8"):
                        cnt += 1
                except Exception:
                    pass
            return cnt

        self.diary_days.set(_count("diary"))
        self.patterns.set(_count("patterns", "pattern-*.md"))
        self.failures.set(_count("failures", "failure-*.md"))
        self.crystals.set(_count("crystals", "crystal-*.md"))
        self.proposals_total.set(_count("proposals"))
        self.proposals_pending.set(_count_pending_proposals())
        self.autobiographies.set(_count("evolutions", "20*-W*.md"))


_instance: Optional[MemoryWikiMetrics] = None


def get_memory_wiki_metrics() -> MemoryWikiMetrics:
    global _instance
    if _instance is None:
        _instance = MemoryWikiMetrics()
    return _instance
