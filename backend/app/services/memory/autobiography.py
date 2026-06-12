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

from app.core.paths import PROJECT_ROOT  # v6.10 P1-E SSOT
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
        #
        # P0-4 修法（2026-05-20，RETRO_20260519 §12.3 環節 4）：
        # 原 except Exception → logger.debug 吞所有錯誤；改為：
        # - TimeoutError → warning（預期可容忍）
        # - 其他 → error + exc_info + counter（根因追蹤）
        # - 加 schema 驗證偵測 wiki.search_wiki dict key drift（L29 同型反模式預防）
        # - 加空 hits warning（wiki service OK 但無結果）
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
            from app.services.wiki.service import get_wiki_service
            wiki = get_wiki_service()
            seen_paths: set = set()
            expected_keys = {"path", "title"}  # P0-4：schema drift 偵測
            for (q,) in top_questions_rows:
                if not q:
                    continue
                hits = await wiki.search_wiki(q, limit=2)
                for h in hits:
                    # P0-4：schema validation 防 wiki service 返回 key 漂移
                    missing = expected_keys - set(h.keys())
                    if missing:
                        logger.warning(
                            "WikiService.search_wiki schema mismatch: "
                            "missing %s, got keys=%s", missing, list(h.keys()),
                        )
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
            # P0-4：空結果可見化（wiki service OK 但本週查詢無命中）
            if not signals.top_wiki_pages and top_questions_rows:
                logger.warning(
                    "Autobiography: top_wiki_pages empty after lookup "
                    "(wiki service OK but no hits for %d queries)",
                    len(top_questions_rows),
                )
        except asyncio.TimeoutError as e:
            logger.warning(
                "Autobiography wiki lookup timeout (Phase 7): %s", e,
            )
            try:
                from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                get_memory_wiki_metrics().diary_append_failures.labels(
                    error_type="wiki_lookup",
                ).inc()
            except Exception:
                pass
        except Exception as e:
            # ADR-0028 錯誤合約化：原 silent debug 改為 error + exc_info
            logger.error(
                "Autobiography wiki lookup failed (unexpected): %s",
                e, exc_info=True,
            )
            try:
                from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                get_memory_wiki_metrics().diary_append_failures.labels(
                    error_type="wiki_lookup",
                ).inc()
            except Exception:
                pass

        return signals

    @staticmethod
    def _parse_tools(tools_used: Any) -> List[str]:
        """解析 tools_used（57e：委派 memory/_utils.parse_tools SSOT）"""
        from app.services.memory._utils import parse_tools
        return parse_tools(tools_used)

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
        path.write_text(content, encoding="utf-8", newline="\n")
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

            # v6.6 Phase A3 5a：SOUL changelog 推 LINE（人格演化的鄭重感）
            try:
                await self._notify_owner_soul_changelog(
                    week_id=signals.week_id, highlight=highlight_short,
                )
            except Exception as e:
                logger.warning("SOUL changelog notify failed (non-blocking): %s", e)

            return True
        except Exception as e:
            logger.warning("SOUL 成長追加失敗: %s", e)
            return False

    @staticmethod
    async def _notify_owner_soul_changelog(
        *, week_id: str, highlight: str,
    ) -> None:
        """v6.6 Phase A3 5a：SOUL.md「我的成長」append 後推 LINE owner。

        坤哥第一人稱訊息：「📜 我的人格更新了一段」— 體感「演化的鄭重感」。
        SOUL 是人格 SSOT，每次改是「成長事件」，不該悄悄發生。

        ENV 共用 LINE_ADMIN_USER_ID + LINE_GROWTH_NOTIFY_ENABLED。
        """
        import os
        if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
            return
        line_user_id = os.getenv("LINE_ADMIN_USER_ID")
        if not line_user_id:
            return

        text = (
            f"📜 我的人格更新了一段\n"
            f"\n"
            f"🗓 {week_id}\n"
            f"💭 亮點：{highlight}\n"
            f"\n"
            f"這條成長已寫入我的 SOUL.md，"
            f"04:45 cron 會同步到跨通道（LINE/Telegram/Discord）。\n"
            f"完整紀錄：wiki/SOUL.md「我的成長」"
        )

        try:
            from app.services.integration.line_bot import LineBotService
            line_bot = LineBotService()
            if not line_bot.enabled:
                return
            ok = await line_bot.push_message(line_user_id, text)
            if ok:
                logger.info("SOUL changelog notify pushed: week=%s", week_id)
            else:
                logger.warning("SOUL changelog notify returned False: %s", week_id)
        except Exception as e:
            logger.error(
                "SOUL changelog notify error: %s",
                e, exc_info=True,
            )

    # ────────── Telegram ──────────

    async def push_to_telegram(self, signals: WeekSignals, narrative: str) -> bool:
        admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
        if not admin_chat_id:
            return False
        try:
            from app.services.integration.telegram_bot import get_telegram_bot_service
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

    async def push_to_line(self, signals: WeekSignals, narrative: str) -> bool:
        """v6.3 體感型輸出：每週日 18:00 推週成長卡片到 LINE owner。

        ADR-0027：LINE 為 owner 主推送通道（Telegram 個人號 4/21 封禁後）。
        ENV：
        - LINE_ADMIN_USER_ID 未設 → silent skip
        - LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉
        """
        if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
            return False
        line_user_id = os.getenv("LINE_ADMIN_USER_ID")
        if not line_user_id:
            return False
        try:
            from app.services.integration.line_bot import LineBotService
            line_bot = LineBotService()
            if not line_bot.enabled:
                return False
            # LINE 不支援 markdown，純文字
            msg = (
                f"📖 我的週成長 {signals.week_id}\n"
                f"\n"
                f"{narrative}\n"
                f"\n"
                f"───\n"
                f"本週 {signals.total_queries} 筆查詢 | "
                f"成功率 {signals.success_rate:.0%} | "
                f"結晶 {signals.crystals_count} 個"
            )
            ok = await line_bot.push_message(line_user_id, msg[:4000])
            if ok:
                logger.info("Autobiography LINE pushed: week=%s", signals.week_id)
            return ok
        except Exception as e:
            logger.error(
                "Autobiography LINE push failed (體感斷鏈): %s",
                e, exc_info=True,
            )
            return False

    # ────────── Main ──────────

    async def run(self, week_end: Optional[date] = None) -> Dict[str, Any]:
        """一鍵執行：collect → generate → persist → SOUL update → 信念演化 propose → Telegram。"""
        signals = await self.collect_week_signals(week_end)

        narrative = await self.generate_narrative(signals)
        if not narrative:
            logger.warning("Autobiography LLM 失敗，使用純模板 fallback")
            narrative = self._fallback_narrative(signals)

        path = self.persist_autobiography(signals, narrative)
        soul_updated = await self.update_soul_growth(signals, narrative)

        # v5.17 Gap 5: 4 信念演化 propose（累積 4 週觀察才觸發，archetypal safety）
        belief_proposal_id = await self._propose_belief_evolution_if_signal(signals)

        # v6.3：雙通道推送（LINE 為主，Telegram 為備援）— ADR-0027
        tg_pushed = await self.push_to_telegram(signals, narrative)
        line_pushed = await self.push_to_line(signals, narrative)

        return {
            "week_id": signals.week_id,
            "path": str(path),
            "soul_updated": soul_updated,
            "belief_proposal_id": belief_proposal_id,
            "telegram_pushed": tg_pushed,
            "line_pushed": line_pushed,
            "total_queries": signals.total_queries,
            "narrative_chars": len(narrative),
        }

    async def _propose_belief_evolution_if_signal(
        self, current_signals: "WeekSignals",
    ) -> Optional[str]:
        """v5.17 Gap 5：偵測信念演化跡象 → propose 寫進「我的成長」段落。

        設計哲學（雙閘安全）：
        - SOUL 4 信念是 source_of_truth=human，agent **不直接改**
        - 但 agent 可以**觀察累積跡象 + propose**「考慮某信念可能需修」
        - 寫進 proposals/，owner 透過 ProposalsTab 批准

        觸發條件（archetypal safety — 至少 4 週累積才考慮）：
        - 連續 3+ 週 success_rate < 0.5（暗示「穩定即信任」需修）
        - 連續 4+ 週 active_failures ≥ 5（暗示「異常即訊號」未發揮作用）

        v5.17 預期狀態：「架構就位等資料」（evolutions/ 不足 4 週時不觸發）。
        """
        try:
            # 收集前 4 週 evolutions frontmatter
            past_signals = self._collect_past_week_signals(weeks_back=4)
            if len(past_signals) < 3:
                logger.debug(
                    "Belief evolution check skipped: only %d past weeks",
                    len(past_signals),
                )
                return None

            # 檢測連續趨勢
            trigger_reasons: List[str] = []
            recent_rates = [s.get("success_rate", 1.0) for s in past_signals[:3]]
            if all(r < 0.5 for r in recent_rates):
                trigger_reasons.append(
                    f"連續 3 週 success_rate < 0.5（{recent_rates}）— 「穩定即信任」"
                    f"信念可能需修：穩定不等於對的時候"
                )

            recent_failures = [s.get("active_failures", 0) for s in past_signals[:4]]
            if len(recent_failures) >= 4 and all(f >= 5 for f in recent_failures):
                trigger_reasons.append(
                    f"連續 4 週 active_failures ≥ 5（{recent_failures}）— 「異常即訊號」"
                    f"信念可能需修：訊號發出但無人接收"
                )

            if not trigger_reasons:
                return None

            # 觸發 propose（寫進 「我的成長」 agent_writable section）
            from app.services.memory.soul_loader import get_soul_loader
            soul = get_soul_loader()
            new_text = (
                f"### 信念演化觀察（{current_signals.week_id}）\n\n"
                "經過數週累積，以下指標暗示核心信念可能需要修正：\n\n"
                + "\n".join(f"- {r}" for r in trigger_reasons)
                + "\n\n_此為 agent 觀察結果，是否實際修改 4 信念由 owner 決定。_"
            )
            reason = (
                f"autobiography 累積 {len(past_signals)} 週觀察觸發。"
                f"trigger: {trigger_reasons[0][:60]}..."
            )
            proposal_id = await soul.propose_section_update(
                section_title="我的成長",
                new_text=new_text,
                reason=reason,
                proposed_by="autobiography_belief_check",
            )
            if proposal_id:
                logger.info(
                    "Belief evolution proposal: %s (triggers=%d)",
                    proposal_id, len(trigger_reasons),
                )
            return proposal_id
        except Exception as e:
            logger.warning("Belief evolution check failed: %s", e)
            return None

    def _collect_past_week_signals(self, weeks_back: int = 4) -> List[Dict[str, Any]]:
        """從 evolutions/*.md frontmatter 收集前 N 週 signals。"""
        import re
        results: List[Dict[str, Any]] = []
        if not EVOLUTIONS_DIR.exists():
            return results

        # 取最新 N 個檔案（按 mtime DESC）
        files = sorted(
            EVOLUTIONS_DIR.glob("20*-W*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:weeks_back]

        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
                m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if not m:
                    continue
                fm = m.group(1)
                signal = {}
                for key in ["week_id", "success_rate", "active_failures",
                           "new_patterns", "total_queries"]:
                    km = re.search(rf"^{key}:\s*(.+?)\s*$", fm, re.MULTILINE)
                    if km:
                        val = km.group(1).strip()
                        if key in ("success_rate",):
                            try:
                                val = float(val)
                            except ValueError:
                                continue
                        elif key in ("active_failures", "new_patterns", "total_queries"):
                            try:
                                val = int(val)
                            except ValueError:
                                continue
                        signal[key] = val
                if signal:
                    results.append(signal)
            except Exception as e:
                logger.debug("collect_past_week_signals %s failed: %s", path.name, e)
        return results

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
