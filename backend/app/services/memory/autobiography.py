# -*- coding: utf-8 -*-
"""Autobiography Generator — Agent 週自傳（第一人稱成長敘述）

2026-04-19 Memory Wiki Phase 4。

流程：
1. collect_week_signals - 聚合本週量能 (traces/patterns/crystals/failures)
2. generate_narrative - LLM 第一人稱寫 200-400 字
3. validate_narrative - 品質閘
4. persist_autobiography - 寫 wiki/memory/evolutions/YYYY-WNN.md
5. push_to_telegram - Telegram 通知
6. update_soul_growth - SOUL.md 成長段落自動追加（agent_writable）

延續今天早上晨報 narrative 的設計血脈。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
EVOLUTIONS_DIR = PROJECT_ROOT / "wiki" / "memory" / "evolutions"
PATTERNS_DIR = PROJECT_ROOT / "wiki" / "memory" / "patterns"
FAILURES_DIR = PROJECT_ROOT / "wiki" / "memory" / "failures"
CRYSTALS_DIR = PROJECT_ROOT / "wiki" / "memory" / "crystals"


@dataclass
class WeekSignals:
    week_id: str
    week_start: date
    week_end: date
    total_queries: int = 0
    success_count: int = 0
    chitchat_count: int = 0
    avg_latency_ms: float = 0.0
    top_tools: List[Dict[str, Any]] = field(default_factory=list)
    top_domains: List[str] = field(default_factory=list)
    new_patterns_count: int = 0
    active_failures_count: int = 0
    crystals_count: int = 0
    prev_week_total: int = 0  # 供比較
    # ADR-0022 Phase 7 整合：本週最常命中的 wiki 實體（供週自傳敘事用）
    top_wiki_pages: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_queries if self.total_queries > 0 else 0.0

    @property
    def vs_prev_week_pct(self) -> float:
        if self.prev_week_total == 0:
            return 0.0
        return (self.total_queries - self.prev_week_total) / self.prev_week_total * 100


_SYSTEM_PROMPT = """你是 CK 助理（小乾）的週自傳編輯。你要用第一人稱寫一份週自傳給老闆（Aaron）。

**寫作準則（必守）**：
- 繁體中文，200-400 字
- 開頭直呼「Aaron」
- 結構：這週我做了什麼 → 最印象深刻的一題 → 學到的教訓 → 下週想做到什麼
- 第一人稱（我、本週、這個月...）
- 必須引用具體數字（處理了 N 筆 query、成功率 XX%、新學會 M 個模式）
- 真誠、有溫度，像日記而不是報表
- 失敗不隱瞞：「這週我搞砸了 X 件...」

**禁止**：
- 簡體字（的、這、為、時、說、發、過、個、樣、們、見 等一律用正體）
- 發明數字（只能用提供的 signals 內容）
- 空洞話術（「持續精進」「穩健成長」）
- token / api key / URL
- 模糊詞過多（可能、大概、或許）
"""


class AutobiographyGenerator:
    """Agent 週自傳生成器。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        EVOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)

    # ────────── Signals ──────────

    async def collect_week_signals(
        self, week_end: Optional[date] = None,
    ) -> WeekSignals:
        """收集本週量能（預設：今日往前 7 天）。"""
        week_end = week_end or datetime.now(TZ_TAIPEI).date()
        week_start = week_end - timedelta(days=6)
        year, wn, _ = week_start.isocalendar()
        week_id = f"{year}-W{wn:02d}"

        signals = WeekSignals(week_id=week_id, week_start=week_start, week_end=week_end)

        # 本週 traces
        s_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=TZ_TAIPEI)
        e_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time(), tzinfo=TZ_TAIPEI)
        rows = (await self.db.execute(
            sa_text(
                "SELECT tools_used, route_type, citation_verified, answer_length, total_ms "
                "FROM agent_query_traces WHERE created_at >= :s AND created_at < :e"
            ),
            {"s": s_dt, "e": e_dt},
        )).all()

        signals.total_queries = len(rows)
        latency_sum = 0
        tool_counter: Dict[str, int] = {}

        for (tools_used, route_type, citation_verified, answer_length, total_ms) in rows:
            if route_type == "chitchat":
                signals.chitchat_count += 1
            # Success 判定
            if (citation_verified or 0) > 0 or ((answer_length or 0) > 50 and route_type not in ("error", "fallback")):
                signals.success_count += 1
            latency_sum += total_ms or 0

            # Tools
            tools = self._parse_tools(tools_used)
            for t in tools:
                tool_counter[t] = tool_counter.get(t, 0) + 1

        if signals.total_queries:
            signals.avg_latency_ms = latency_sum / signals.total_queries

        signals.top_tools = [
            {"name": t, "count": n}
            for t, n in sorted(tool_counter.items(), key=lambda x: -x[1])[:5]
        ]

        # Previous week
        prev_s = s_dt - timedelta(days=7)
        prev_e = s_dt
        prev_count = (await self.db.execute(
            sa_text(
                "SELECT COUNT(*) FROM agent_query_traces "
                "WHERE created_at >= :s AND created_at < :e"
            ),
            {"s": prev_s, "e": prev_e},
        )).scalar() or 0
        signals.prev_week_total = int(prev_count)

        # Patterns（新增的檔案：7 日內 mtime）
        if PATTERNS_DIR.exists():
            now_ts = datetime.now().timestamp()
            seven_days = 7 * 86400
            signals.new_patterns_count = sum(
                1 for p in PATTERNS_DIR.glob("pattern-*.md")
                if now_ts - p.stat().st_mtime < seven_days
            )
        if FAILURES_DIR.exists():
            signals.active_failures_count = sum(
                1 for p in FAILURES_DIR.glob("failure-*.md")
                if "active: true" in p.read_text(encoding="utf-8", errors="ignore")
            )
        if CRYSTALS_DIR.exists():
            signals.crystals_count = len(list(CRYSTALS_DIR.glob("crystal-*.md")))

        # ── Phase 7 整合：抓本週最常命中的 wiki 實體（給週自傳敘事血肉）──
        # 取本週 3 句最長 question（通常代表最有份量的案子），用 wiki search
        # 找最相關頁，避免 LLM 敘事只剩乾巴巴的數字。
        try:
            top_questions_rows = (await self.db.execute(
                sa_text(
                    "SELECT question FROM agent_query_traces "
                    "WHERE created_at >= :s AND created_at < :e "
                    "  AND route_type != 'chitchat' "
                    "ORDER BY LENGTH(question) DESC LIMIT 3"
                ),
                {"s": s_dt, "e": e_dt},
            )).all()
            from app.services.wiki_service import get_wiki_service
            wiki = get_wiki_service()
            seen_paths: set = set()
            for (q,) in top_questions_rows:
                if not q:
                    continue
                hits = await wiki.search_wiki(q, limit=2)
                for h in hits:
                    path = h.get("path") or h.get("filename")
                    if path and path not in seen_paths:
                        seen_paths.add(path)
                        signals.top_wiki_pages.append({
                            "path": path,
                            "title": h.get("title") or path,
                        })
                    if len(signals.top_wiki_pages) >= 3:
                        break
                if len(signals.top_wiki_pages) >= 3:
                    break
        except Exception as e:
            logger.debug("top_wiki_pages lookup failed: %s", e)

        return signals

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

    # ────────── Narrative ──────────

    async def generate_narrative(self, signals: WeekSignals) -> Optional[str]:
        """呼叫 LLM 產 narrative。失敗回 None，caller fallback 純模板。"""
        timeout_s = int(os.getenv("AUTOBIOGRAPHY_TIMEOUT", "60"))

        signals_text = self._format_signals_for_prompt(signals)

        try:
            from app.core.ai_connector import get_ai_connector
            ai = get_ai_connector()
            result = await asyncio.wait_for(
                ai.chat_completion(
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"本週 ({signals.week_id}) 信號：\n\n"
                                f"{signals_text}\n\n"
                                f"請以第一人稱寫一份週自傳給Aaron，250-350 字。"
                                f"結構：這週做了什麼 → 印象深刻 → 學到什麼 → 下週想做什麼。"
                            ),
                        },
                    ],
                    temperature=0.4,
                    max_tokens=700,
                    task_type="summary",
                ),
                timeout=timeout_s,
            )
            if not result:
                return None
            narrative = result.strip()
            # 移除 thinking tags 殘餘
            if "<think>" in narrative or "<start_of_thinking>" in narrative:
                logger.warning("Autobiography contains thinking tags, skip")
                return None
            # Validation
            from app.services.memory.narrative_validator import validate_narrative
            v = validate_narrative(narrative)
            if not v.ok:
                logger.warning("Autobiography validation failed: %s", v.reasons)
                return None
            return narrative
        except asyncio.TimeoutError:
            logger.warning("Autobiography LLM timed out after %ds", timeout_s)
            return None
        except Exception as e:
            logger.warning("Autobiography LLM failed: %s", e)
            return None

    @staticmethod
    def _format_signals_for_prompt(s: WeekSignals) -> str:
        tools_str = ", ".join(
            f"{t['name']}({t['count']})" for t in s.top_tools[:3]
        ) or "(無)"
        vs_prev = ""
        if s.prev_week_total > 0:
            sign = "+" if s.vs_prev_week_pct >= 0 else ""
            vs_prev = f"（vs 上週 {s.prev_week_total} 筆，{sign}{s.vs_prev_week_pct:.0f}%）"
        wiki_str = ""
        if s.top_wiki_pages:
            titles = "、".join(p.get("title", "?") for p in s.top_wiki_pages[:3])
            wiki_str = f"\n- 本週陪伴最深的三個實體（wiki）：{titles}"
        return (
            f"- 週期：{s.week_start} 至 {s.week_end}\n"
            f"- 處理查詢：{s.total_queries} 筆{vs_prev}\n"
            f"- 成功率：{s.success_rate:.0%}\n"
            f"- 平均延遲：{s.avg_latency_ms:.0f}ms\n"
            f"- 閒聊比例：{s.chitchat_count}/{s.total_queries}\n"
            f"- 最常用工具：{tools_str}\n"
            f"- 新學會模式：{s.new_patterns_count} 個\n"
            f"- 進行中失敗模式：{s.active_failures_count} 個\n"
            f"- 已結晶為規則：累計 {s.crystals_count} 個{wiki_str}"
        )

    # ────────── Persist ──────────

    def persist_autobiography(
        self, signals: WeekSignals, narrative: str,
    ) -> Path:
        """寫 wiki/memory/evolutions/YYYY-WNN.md。"""
        path = EVOLUTIONS_DIR / f"{signals.week_id}.md"
        content = f"""---
type: agent_memory
memory_type: autobiography
week_id: {signals.week_id}
week_start: {signals.week_start.isoformat()}
week_end: {signals.week_end.isoformat()}
total_queries: {signals.total_queries}
success_rate: {signals.success_rate:.3f}
vs_prev_week_pct: {signals.vs_prev_week_pct:.1f}
avg_latency_ms: {signals.avg_latency_ms:.0f}
new_patterns: {signals.new_patterns_count}
active_failures: {signals.active_failures_count}
crystals: {signals.crystals_count}
generated_at: {datetime.now(TZ_TAIPEI).isoformat()}
tags: [memory, autobiography, evolution]
---

# Agent 週自傳 — {signals.week_id}

{narrative}

---

## Raw Signals

```json
{json.dumps({
    "total_queries": signals.total_queries,
    "success_count": signals.success_count,
    "chitchat_count": signals.chitchat_count,
    "avg_latency_ms": signals.avg_latency_ms,
    "top_tools": signals.top_tools,
    "new_patterns_count": signals.new_patterns_count,
    "active_failures_count": signals.active_failures_count,
    "crystals_count": signals.crystals_count,
    "prev_week_total": signals.prev_week_total,
}, ensure_ascii=False, indent=2)}
```
"""
        path.write_text(content, encoding="utf-8")
        return path

    # ────────── SOUL 成長追加 ──────────

    async def update_soul_growth(self, signals: WeekSignals, narrative: str) -> bool:
        """將本週亮點自動追加到 SOUL.md 的「我的成長」agent-writable 區段。

        直接改 wiki/SOUL.md（這是 agent_writable section 允許的）。
        保留最新 10 筆，舊的輪替。
        """
        from app.services.memory.soul_loader import SOUL_PATH
        if not SOUL_PATH.exists():
            return False

        try:
            text = SOUL_PATH.read_text(encoding="utf-8")
            # 取 narrative 第一段作為週亮點（50-100 字）
            first_para = narrative.split("\n\n")[0].strip()
            highlight_short = first_para[:120] + ("..." if len(first_para) > 120 else "")

            new_entry = (
                f"- **{signals.week_id}** ({signals.week_start} ~ {signals.week_end}): "
                f"{highlight_short} "
                f"(queries={signals.total_queries}, success={signals.success_rate:.0%})\n"
            )

            # 找到 "## 我的成長" 區段
            pattern = re.compile(
                r"(## 我的成長\s*\n<!-- [^>]+-->\s*\n)(.*?)(?=\n##\s|\Z)",
                re.DOTALL,
            )
            match = pattern.search(text)
            if not match:
                logger.warning("SOUL.md 無 '我的成長' 區段")
                return False

            header = match.group(1)
            body = match.group(2)

            # 移除 placeholder 或舊條目
            body_lines = [line for line in body.splitlines() if line.strip() and not line.startswith("_待")]
            # 保留最新 10 筆
            existing_entries = [line for line in body_lines if line.startswith("- **")]
            # 若當週已有記錄，先移除
            existing_entries = [e for e in existing_entries if signals.week_id not in e]
            # 新增放最前
            existing_entries.insert(0, new_entry.rstrip())
            # 保留 10 筆
            existing_entries = existing_entries[:10]

            new_body = "\n".join(existing_entries) + "\n"
            new_section = header + new_body

            new_text = text[:match.start()] + new_section + text[match.end():]
            SOUL_PATH.write_text(new_text, encoding="utf-8")
            logger.info("SOUL.md 成長段落已追加 %s", signals.week_id)
            return True
        except Exception as e:
            logger.warning("SOUL 成長追加失敗: %s", e)
            return False

    # ────────── Telegram ──────────

    async def push_to_telegram(self, signals: WeekSignals, narrative: str) -> bool:
        admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
        if not admin_chat_id:
            return False
        try:
            from app.services.telegram_bot_service import get_telegram_bot_service
            msg = (
                f"📖 *Agent 週自傳 {signals.week_id}*\n\n"
                f"{narrative}\n\n"
                f"───\n"
                f"本週 {signals.total_queries} 筆查詢 | 成功率 {signals.success_rate:.0%} | "
                f"結晶 {signals.crystals_count} 個"
            )
            await get_telegram_bot_service().push_message(int(admin_chat_id), msg[:4000])
            return True
        except Exception as e:
            logger.warning("Autobiography Telegram push failed: %s", e)
            return False

    # ────────── Main ──────────

    async def run(self, week_end: Optional[date] = None) -> Dict[str, Any]:
        """一鍵執行：collect → generate → persist → SOUL update → Telegram。"""
        signals = await self.collect_week_signals(week_end)

        narrative = await self.generate_narrative(signals)
        if not narrative:
            logger.warning("Autobiography LLM 失敗，使用純模板 fallback")
            narrative = self._fallback_narrative(signals)

        path = self.persist_autobiography(signals, narrative)
        soul_updated = await self.update_soul_growth(signals, narrative)
        pushed = await self.push_to_telegram(signals, narrative)

        return {
            "week_id": signals.week_id,
            "path": str(path),
            "soul_updated": soul_updated,
            "telegram_pushed": pushed,
            "total_queries": signals.total_queries,
            "narrative_chars": len(narrative),
        }

    @staticmethod
    def _fallback_narrative(s: WeekSignals) -> str:
        """LLM 失敗時用的純模板（含數字、無 LLM 胡扯風險）。"""
        return (
            f"Aaron，本週（{s.week_start} ~ {s.week_end}）我總共處理了 {s.total_queries} 筆查詢，"
            f"成功率 {s.success_rate:.0%}。其中閒聊 {s.chitchat_count} 筆，"
            f"其餘是實際業務查詢。平均延遲 {s.avg_latency_ms:.0f} 毫秒。\n\n"
            f"本週我新學會 {s.new_patterns_count} 個查詢模式，"
            f"還有 {s.active_failures_count} 個失敗模式需要注意。"
            f"累積結晶為規則的有 {s.crystals_count} 個。\n\n"
            f"下週會繼續累積資料、嘗試更快回應。（本週 LLM 敘述生成失敗，以純統計版本呈現）"
        )
