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
# R7 (5/08 v6.9): diary 寫入失敗計數，解 v3.0 洞察 11 silent skip 反模式
# error_type: file_io / wiki_lookup / metric_inc / unknown
MEM_DIARY_APPEND_FAILURES = "memory_diary_append_failures_total"
MEM_PATTERN_EXTRACT_RUNS = "memory_pattern_extract_runs_total"
MEM_CRYSTAL_APPLIED = "memory_crystal_applied_total"
# F19 (5/04): synthesis fact_check 偵測到 LLM 編造數字計數（啟動就註冊）
SYNTHESIS_UNSOURCED_NUMBERS = "agent_synthesis_unsourced_numbers_total"

# ───── M1 v7.0 Gauges (5/04 v3.0 覆盤洞察 14) ─────
# 取代「成熟度 %」作為新 baseline
M1_CHANNEL_DIVERSITY = "v7_channel_diversity"
M1_REF_DENSITY_DIARY = "v7_reference_density_diary_pct"
M1_REF_DENSITY_CRITIQUE = "v7_reference_density_critique_pct"
M1_SOUL_DRIFT_LINES = "v7_soul_drift_lines"
# M4 (5/04 補完)：provider fidelity 從 fidelity_log.jsonl 讀
M1_PROVIDER_FIDELITY_GAP = "v7_provider_fidelity_gap_pct"


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
        # R7 (5/08): 失敗計數 — 啟動就註冊（避免「首次失敗前完全不暴露」silent gap，同 F19 模式）
        self.diary_append_failures = Counter(
            MEM_DIARY_APPEND_FAILURES,
            "Diary append failures by error type "
            "(file_io / wiki_lookup / metric_inc / unknown)",
            ["error_type"],
            registry=reg,
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
        # F19 fact_check counter — 啟動就註冊，避免「動態建立」造成 metric
        # 在第一次觸發前完全不暴露的問題。
        self.synthesis_unsourced_numbers = Counter(
            SYNTHESIS_UNSOURCED_NUMBERS,
            "Numbers in synthesis answer not found in tool results "
            "(potential LLM hallucination, F19/v3.0 洞察 12)",
            registry=reg,
        )

        # M1 v7.0 gauges (5/04 v3.0 覆盤洞察 14 取代「成熟度 %」)
        self.v7_channel_diversity = Gauge(
            M1_CHANNEL_DIVERSITY,
            "Distinct channels with diary entries last 7 days "
            "(target: 4 = line+telegram+web+discord)",
            registry=reg,
        )
        self.v7_ref_density_diary = Gauge(
            M1_REF_DENSITY_DIARY,
            "Diary entries with KG entity tag, percentage (target: ≥50)",
            registry=reg,
        )
        self.v7_ref_density_critique = Gauge(
            M1_REF_DENSITY_CRITIQUE,
            "Critique entries with KG entity tag, percentage (target: ≥80)",
            registry=reg,
        )
        self.v7_soul_drift = Gauge(
            M1_SOUL_DRIFT_LINES,
            "SOUL.md line count diff Missive vs AaaP mirror (target: ≤5)",
            registry=reg,
        )
        # M4 (5/04 補完)：provider fidelity gap (max - min) percentage points
        self.v7_provider_fidelity_gap = Gauge(
            M1_PROVIDER_FIDELITY_GAP,
            "Provider fidelity gap (max-min %) across providers from "
            "fidelity_log.jsonl last 24h (target: ≤10 pp)",
            ["aggregation"],  # latest / 24h_avg
            registry=reg,
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

        # M1 v7.0 metrics (best-effort，失敗不影響原 metrics)
        try:
            self._refresh_v7_metrics(wiki_memory_dir)
        except Exception:
            pass

    def _refresh_v7_metrics(self, wiki_memory_dir: Path) -> None:
        """M1 v7.0 4 個新指標（5/04 v3.0 覆盤洞察 14）。

        從 disk 計算：
        - channel diversity (diary 7d session 含 line/telegram/web/discord)
        - reference density diary (含 entity tag 比例)
        - reference density critique (含 entity 引用比例)
        - SOUL drift (Missive vs AaaP line diff)
        """
        import re
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=7)

        # ── channel diversity (diary 7d) ──
        diary_dir = wiki_memory_dir / "diary"
        channels: set = set()
        if diary_dir.exists():
            for f in diary_dir.glob("20*.md"):
                try:
                    if date.fromisoformat(f.stem) < cutoff:
                        continue
                except ValueError:
                    continue
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                for ch in ("line", "telegram", "web", "discord", "mcp", "hermes"):
                    if re.search(rf"session.*{ch}:", text):
                        channels.add(ch)
        self.v7_channel_diversity.set(len(channels))

        # ── reference density (diary entries with entity tag) ──
        if diary_dir.exists():
            total_entries = 0
            with_entity = 0
            for f in diary_dir.glob("20*.md"):
                try:
                    if date.fromisoformat(f.stem) < cutoff:
                        continue
                except ValueError:
                    continue
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                entries = re.findall(r"^## \d{2}:\d{2}:\d{2}", text, re.MULTILINE)
                total_entries += len(entries)
                with_entity += len(re.findall(r"\*\*entities\*\*:", text))
            pct = (with_entity / total_entries * 100) if total_entries else 0.0
            self.v7_ref_density_diary.set(round(pct, 1))

        # ── reference density (critique entries with entity) ──
        critique_dir = wiki_memory_dir / "critiques"
        if critique_dir.exists():
            crit_total = 0
            crit_with_entity = 0
            for f in critique_dir.glob("critique-*.md"):
                m = re.search(r"critique-(\d{8})", f.name)
                if not m:
                    continue
                try:
                    dt = date(
                        int(m.group(1)[:4]),
                        int(m.group(1)[4:6]),
                        int(m.group(1)[6:8]),
                    )
                    if dt < cutoff:
                        continue
                except ValueError:
                    continue
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                crit_total += 1
                if re.search(r"entit(?:y|ies)|kg_entity_id|實體", text, re.IGNORECASE):
                    crit_with_entity += 1
            pct_crit = (crit_with_entity / crit_total * 100) if crit_total else 0.0
            self.v7_ref_density_critique.set(round(pct_crit, 1))

        # ── SOUL drift (Missive vs AaaP) ──
        # wiki_memory_dir 是 wiki/memory/，往上走兩層到 project root
        project_root = wiki_memory_dir.parent.parent
        soul_a = project_root / "wiki" / "SOUL.md"
        soul_b = project_root.parent / "CK_AaaP" / "runbooks" / "hermes-stack" / "SOUL.md"
        if soul_a.exists() and soul_b.exists():
            try:
                a_lines = len(soul_a.read_text(encoding="utf-8").splitlines())
                b_lines = len(soul_b.read_text(encoding="utf-8").splitlines())
                self.v7_soul_drift.set(abs(a_lines - b_lines))
            except Exception:
                pass

        # ── M4 provider fidelity gap (從 fidelity_log.jsonl 讀) ──
        try:
            self._refresh_provider_fidelity(wiki_memory_dir)
        except Exception:
            pass

    def _refresh_provider_fidelity(self, wiki_memory_dir: Path) -> None:
        """M4 (5/04 補完)：讀 wiki/memory/evolutions/fidelity_log.jsonl
        計各 provider 24h average fidelity，gap = max - min。
        """
        import json as _json
        from datetime import datetime, timedelta, timezone as _tz

        log_path = wiki_memory_dir / "evolutions" / "fidelity_log.jsonl"
        if not log_path.exists():
            return  # 留 0 (cron 沒跑或 placeholder)

        cutoff = datetime.now(_tz.utc) - timedelta(hours=24)
        by_provider: Dict[str, list] = {}
        try:
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = _json.loads(line)
                        ts = datetime.fromisoformat(rec.get("ts", "").replace("Z", "+00:00"))
                        if ts < cutoff:
                            continue
                        prov = rec.get("provider")
                        fid = rec.get("fidelity")
                        if prov and fid is not None:
                            by_provider.setdefault(prov, []).append(float(fid))
                    except Exception:
                        continue
        except Exception:
            return

        if len(by_provider) < 2:
            return  # 至少 2 provider 才有 gap

        avg_by_prov = {p: sum(v) / len(v) for p, v in by_provider.items() if v}
        if not avg_by_prov:
            return
        max_fid = max(avg_by_prov.values())
        min_fid = min(avg_by_prov.values())
        gap_pp = (max_fid - min_fid) * 100  # percentage points
        self.v7_provider_fidelity_gap.labels(aggregation="24h_avg").set(round(gap_pp, 1))

        # 也記 latest（每 provider 最新一筆）
        try:
            latest_by_prov: Dict[str, float] = {}
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = _json.loads(line)
                        prov = rec.get("provider")
                        fid = rec.get("fidelity")
                        if prov and fid is not None:
                            latest_by_prov[prov] = float(fid)  # 後讀者覆蓋先讀者
                    except Exception:
                        continue
            if len(latest_by_prov) >= 2:
                latest_gap = (max(latest_by_prov.values()) - min(latest_by_prov.values())) * 100
                self.v7_provider_fidelity_gap.labels(aggregation="latest").set(round(latest_gap, 1))
        except Exception:
            pass


_instance: Optional[MemoryWikiMetrics] = None


def get_memory_wiki_metrics() -> MemoryWikiMetrics:
    global _instance
    if _instance is None:
        _instance = MemoryWikiMetrics()
    return _instance
