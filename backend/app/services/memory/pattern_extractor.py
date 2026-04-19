# -*- coding: utf-8 -*-
"""Pattern Extractor — 從 agent_query_traces 萃取成功模式與失敗模式

2026-04-19 Memory Wiki Phase 2 新建。

職責：
- 每日掃 trace → 按 tool_sequence 聚合 → 成功率 > 80% 且 count >= 3 → 寫 patterns/
- 失敗率 > 50% → 寫 failures/ + 自動生成 defensive_rule
- pattern/failure 作為 markdown wiki 頁面（一切皆 wiki）

設計決策（簡單優先）：
- pattern template = hash(sorted(tool_sequence))，避免 NLP
- 不用 LLM 做 template clustering（省 token，deterministic）
- 失敗 defensive_rule 用模板生成（非 LLM）
- LLM 升級留給未來（當資料量大時）

Usage:
    from app.services.memory.pattern_extractor import PatternExtractor
    extractor = PatternExtractor(db)
    result = await extractor.extract_daily_patterns(date.today())
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

PATTERNS_DIR = Path(__file__).resolve().parents[4] / "wiki" / "memory" / "patterns"
FAILURES_DIR = Path(__file__).resolve().parents[4] / "wiki" / "memory" / "failures"

# 閾值
SUCCESS_RATE_THRESHOLD = 0.8
MIN_HIT_COUNT = 3
FAILURE_RATE_THRESHOLD = 0.5
MIN_FAILURE_COUNT = 2


@dataclass
class PatternRecord:
    """一個 pattern — tool_sequence + 成功統計。"""
    template_hash: str
    tool_sequence: List[str]
    hit_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    example_questions: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.hit_count if self.hit_count > 0 else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failure_count / self.hit_count if self.hit_count > 0 else 0.0


@dataclass
class FailureRecord:
    """一個 failure mode — tool_sequence 失敗率高的模式。"""
    signature: str  # unique identifier
    tool_sequence: List[str]
    failure_count: int = 0
    hit_count: int = 0
    example_questions: List[str] = field(default_factory=list)
    common_error: str = ""

    @property
    def failure_rate(self) -> float:
        return self.failure_count / self.hit_count if self.hit_count > 0 else 0.0


@dataclass
class ExtractResult:
    patterns: List[PatternRecord] = field(default_factory=list)
    failures: List[FailureRecord] = field(default_factory=list)
    total_traces_scanned: int = 0
    saved_pattern_files: int = 0
    saved_failure_files: int = 0
    duration_ms: int = 0


# ────────── Helper ──────────

def _template_hash(tool_seq: List[str]) -> str:
    """從 tool_sequence 生成短 hash。"""
    key = "|".join(sorted(tool_seq))
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:10]


def _tools_to_domains(tool_seq: List[str]) -> List[str]:
    """複用 agent_capability_tracker 的 TOOL_DOMAIN_MAP。"""
    try:
        from app.services.ai.agent.agent_capability_tracker import TOOL_DOMAIN_MAP
        domains = set()
        for tool in tool_seq:
            d = TOOL_DOMAIN_MAP.get(tool)
            if d:
                domains.add(d)
        return sorted(domains)
    except Exception:
        return []


def _normalize_question_snippet(text: str, max_len: int = 60) -> str:
    """把 question 縮短 + PII 遮罩供 example 展示用。"""
    if not text:
        return ""
    text = re.sub(r"[A-Z][12]\d{8}", "[ID]", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", text)
    text = text.replace("\n", " ").strip()
    return text[:max_len]


# ────────── Main Service ──────────

class PatternExtractor:
    """從 AgentQueryTrace 萃取成功模式 + 失敗模式，寫入 memory wiki。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)

    async def extract_daily(self, target_date: Optional[date] = None) -> ExtractResult:
        """主入口：掃該日 traces 一次產出 patterns + failures。"""
        import time as _time
        t0 = _time.time()

        target_date = target_date or (datetime.now(TZ_TAIPEI).date() - timedelta(days=1))
        # 台灣時區的一天
        start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=TZ_TAIPEI)
        end_dt = start_dt + timedelta(days=1)

        # 讀 traces
        rows = (await self.db.execute(
            sa_text(
                "SELECT question, tools_used, citation_verified, answer_length, "
                "       route_type, total_ms "
                "FROM agent_query_traces "
                "WHERE created_at >= :s AND created_at < :e"
            ),
            {"s": start_dt, "e": end_dt},
        )).all()

        result = ExtractResult(total_traces_scanned=len(rows))
        if not rows:
            logger.info("No traces for %s", target_date)
            return result

        # 聚合 by tool_sequence hash
        by_template: Dict[str, PatternRecord] = {}
        for (question, tools_used, citation_verified, answer_length, route_type, total_ms) in rows:
            tools = self._parse_tools(tools_used)
            if not tools:
                continue  # 無工具呼叫不算 pattern

            t_hash = _template_hash(tools)
            rec = by_template.get(t_hash)
            if rec is None:
                rec = PatternRecord(
                    template_hash=t_hash,
                    tool_sequence=sorted(tools),
                    domains=_tools_to_domains(tools),
                )
                by_template[t_hash] = rec

            rec.hit_count += 1
            # 定義成功：有 citation 或 answer_length > 50 且 route!='error'
            success = (
                (citation_verified or 0) > 0
                or ((answer_length or 0) > 50 and route_type not in ("error", "fallback"))
            )
            if success:
                rec.success_count += 1
            else:
                rec.failure_count += 1

            rec.avg_latency_ms = (
                (rec.avg_latency_ms * (rec.hit_count - 1) + (total_ms or 0)) / rec.hit_count
            )
            if len(rec.example_questions) < 3 and question:
                snippet = _normalize_question_snippet(question)
                if snippet and snippet not in rec.example_questions:
                    rec.example_questions.append(snippet)

        # 分類成 pattern / failure
        for rec in by_template.values():
            if rec.hit_count >= MIN_HIT_COUNT and rec.success_rate >= SUCCESS_RATE_THRESHOLD:
                result.patterns.append(rec)
            elif rec.hit_count >= MIN_FAILURE_COUNT and rec.failure_rate >= FAILURE_RATE_THRESHOLD:
                result.failures.append(self._to_failure(rec))

        # 寫檔
        for p in result.patterns:
            if self._write_pattern(p, target_date):
                result.saved_pattern_files += 1
        for f in result.failures:
            if self._write_failure(f, target_date):
                result.saved_failure_files += 1

        result.duration_ms = int((_time.time() - t0) * 1000)
        logger.info(
            "PatternExtractor: scanned=%d patterns=%d failures=%d (saved p=%d f=%d) in %dms",
            result.total_traces_scanned,
            len(result.patterns), len(result.failures),
            result.saved_pattern_files, result.saved_failure_files,
            result.duration_ms,
        )
        return result

    @staticmethod
    def _parse_tools(tools_used: Any) -> List[str]:
        if tools_used is None:
            return []
        if isinstance(tools_used, str):
            try:
                tools_used = json.loads(tools_used)
            except Exception:
                return []
        if isinstance(tools_used, list):
            return [t for t in tools_used if isinstance(t, str)]
        return []

    @staticmethod
    def _to_failure(rec: PatternRecord) -> FailureRecord:
        return FailureRecord(
            signature=rec.template_hash,
            tool_sequence=rec.tool_sequence,
            failure_count=rec.failure_count,
            hit_count=rec.hit_count,
            example_questions=list(rec.example_questions),
            common_error=f"成功率僅 {rec.success_rate:.0%}，共 {rec.failure_count} 次失敗",
        )

    # ────────── Write wiki pages ──────────

    def _write_pattern(self, p: PatternRecord, target_date: date) -> bool:
        path = PATTERNS_DIR / f"pattern-{p.template_hash}.md"
        try:
            # 若檔案已存在，merge 統計（跨日累積）
            existing_stats = self._read_existing_stats(path)
            merged_hit = p.hit_count + existing_stats.get("hit_count", 0)
            merged_success = p.success_count + existing_stats.get("success_count", 0)
            merged_failure = p.failure_count + existing_stats.get("failure_count", 0)

            content = f"""---
type: agent_memory
memory_type: pattern
template_hash: {p.template_hash}
tool_sequence: {json.dumps(p.tool_sequence, ensure_ascii=False)}
domains: {json.dumps(p.domains, ensure_ascii=False)}
hit_count: {merged_hit}
success_count: {merged_success}
failure_count: {merged_failure}
success_rate: {merged_success / merged_hit:.3f}
avg_latency_ms: {p.avg_latency_ms:.0f}
first_seen: {existing_stats.get("first_seen", target_date.isoformat())}
last_seen: {target_date.isoformat()}
crystallization_candidate: {merged_hit >= 5 and merged_success / merged_hit >= 0.95}
tags: [memory, pattern, {", ".join(p.domains) if p.domains else "multi_domain"}]
---

# Pattern {p.template_hash}

## Tool sequence

{", ".join(f"`{t}`" for t in p.tool_sequence)}

## 統計

- **觸發次數**：{merged_hit}（累計）
- **成功率**：{merged_success / merged_hit:.1%}
- **平均延遲**：{p.avg_latency_ms:.0f}ms
- **涉及領域**：{", ".join(p.domains) if p.domains else "(混合)"}

## 典型問法

{chr(10).join(f"- {q}" for q in p.example_questions) if p.example_questions else "- (尚無示例)"}

## 結晶候選

{"✅ 符合結晶門檻（hit >= 5, success >= 95%），等待 Phase 3 crystallizer 掃描。" if merged_hit >= 5 and merged_success / merged_hit >= 0.95 else "❌ 尚未達到結晶門檻。"}

---

_由 pattern_extractor 自動產生，最後更新：{target_date.isoformat()}_
"""
            path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.warning("Pattern write failed (%s): %s", p.template_hash, e)
            return False

    def _write_failure(self, f: FailureRecord, target_date: date) -> bool:
        path = FAILURES_DIR / f"failure-{f.signature}.md"
        try:
            # 失敗模式也 merge
            existing_stats = self._read_existing_stats(path)
            merged_hit = f.hit_count + existing_stats.get("hit_count", 0)
            merged_failure = f.failure_count + existing_stats.get("failure_count", 0)

            defensive_rule = self._generate_defensive_rule(f.tool_sequence, f.common_error)

            content = f"""---
type: agent_memory
memory_type: failure
signature: {f.signature}
tool_sequence: {json.dumps(f.tool_sequence, ensure_ascii=False)}
hit_count: {merged_hit}
failure_count: {merged_failure}
failure_rate: {merged_failure / merged_hit:.3f}
active: true
first_seen: {existing_stats.get("first_seen", target_date.isoformat())}
last_seen: {target_date.isoformat()}
tags: [memory, failure, defensive]
---

# Failure Mode {f.signature}

## Tool sequence（問題組合）

{", ".join(f"`{t}`" for t in f.tool_sequence)}

## 失敗統計

- **觸發次數**：{merged_hit}
- **失敗次數**：{merged_failure}
- **失敗率**：{merged_failure / merged_hit:.1%}
- **症狀**：{f.common_error}

## 典型問法

{chr(10).join(f"- {q}" for q in f.example_questions) if f.example_questions else "- (無)"}

## 🛡️ Defensive Rule（planner 將自動注入）

{defensive_rule}

---

_由 pattern_extractor 自動產生。此規則將在 agent_planner 規劃階段作為「失敗教訓」注入，提醒 LLM 避開此組合。設 `active: false` 可關閉。_
"""
            path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.warning("Failure write failed (%s): %s", f.signature, e)
            return False

    def _read_existing_stats(self, path: Path) -> dict:
        """讀既有檔的 frontmatter 數字（供累積統計）。"""
        if not path.exists():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
            fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not fm_match:
                return {}
            fm = fm_match.group(1)
            stats: dict = {}
            for key in ("hit_count", "success_count", "failure_count"):
                m = re.search(rf"^{key}:\s*(\d+)", fm, re.MULTILINE)
                if m:
                    stats[key] = int(m.group(1))
            fs_match = re.search(r"^first_seen:\s*(\S+)", fm, re.MULTILINE)
            if fs_match:
                stats["first_seen"] = fs_match.group(1).strip()
            return stats
        except Exception:
            return {}

    @staticmethod
    def _generate_defensive_rule(tool_seq: List[str], error_hint: str) -> str:
        """規則式生成防禦建議（非 LLM）。"""
        tools_str = " + ".join(f"`{t}`" for t in tool_seq)
        return (
            f"**觸發**：規劃包含 {tools_str} 的組合\n\n"
            f"**歷史問題**：{error_hint}\n\n"
            f"**建議**：\n"
            f"- 優先考慮單獨使用其中一個工具而非全部組合\n"
            f"- 若查詢涉及多 domain，優先用 `search_across_graphs` 統一查詢\n"
            f"- 必要時先 `get_statistics` 確認資料存在再深入查詢"
        )
