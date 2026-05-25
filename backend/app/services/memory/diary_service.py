# -*- coding: utf-8 -*-
"""Diary Service — 每日日記（Muse 風格連續性核心）

2026-04-19 Memory Wiki Phase 1 新建。

路徑：`wiki/memory/diary/YYYY-MM-DD.md`（台灣時區）
格式：每筆 entry 是一個 markdown block，含 timestamp/question/answer/tools/latency

特性：
- append-only（不覆寫舊 entry）
- asyncio.Lock 防併發寫衝突
- 啟動讀 yesterday 提供連續性脈絡
- read_yesterday 有 fallback：若昨日無檔，往前找最近 3 天

Usage:
    from app.services.memory.diary_service import get_diary_service
    diary = get_diary_service()
    await diary.ensure_today_header()
    await diary.append_entry(question="...", answer="...", ...)
    yesterday_summary = await diary.summarize_yesterday_for_context()
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

from app.core.paths import WIKI_MEMORY_DIARY_DIR as DIARY_DIR  # v6.10 P1-E SSOT
DIARY_DIR.mkdir(parents=True, exist_ok=True)


def today_date() -> date:
    return datetime.now(TZ_TAIPEI).date()


def yesterday_date() -> date:
    return today_date() - timedelta(days=1)


def _diary_path(d: date) -> Path:
    return DIARY_DIR / f"{d.isoformat()}.md"


class DiaryService:
    """Agent 的每日日記（Episodic memory file layer）。"""

    _instance: Optional["DiaryService"] = None
    _write_lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "DiaryService":
        if cls._instance is None:
            cls._instance = DiaryService()
        return cls._instance

    # ────────── Write ──────────

    async def ensure_today_header(self) -> Path:
        """確保今日 diary 檔存在（首次寫入時建 header）。"""
        today = today_date()
        path = _diary_path(today)
        if path.exists():
            return path

        now = datetime.now(TZ_TAIPEI)
        header = f"""---
title: Agent 日記 {today.isoformat()}
type: diary
date: {today.isoformat()}
weekday: {today.strftime('%A')}
agent_writable: true
tags: [memory, diary]
---

# Agent 日記 — {today.isoformat()} ({today.strftime('%A')})

開機時間：{now.isoformat()}

<!-- 以下由 Agent 每次 session 結束後 append -->

"""
        async with self._write_lock:
            if not path.exists():
                path.write_text(header, encoding="utf-8")
                logger.info("Diary header created: %s", path.name)
        return path

    async def append_entry(
        self,
        *,
        question: str,
        answer: str,
        tools_used: Optional[List[str]] = None,
        success: bool = True,
        latency_ms: Optional[int] = None,
        session_id: Optional[str] = None,
        channel: Optional[str] = None,
        route_type: Optional[str] = None,
    ) -> None:
        """追加一筆日記 entry（fire-and-forget，失敗只 log 不 raise）。

        v6.5 I2：每筆 entry 加 entities 行（NER 抽 question + answer），
        補 KG ↔ Memory Wiki ❺ 弱連結。reuse critic 的 NER pattern（人名暱稱
        /案件編號/派工單號）。grep `entities.*老蕭` 即可統計提及次數。

        R7 (v6.9 / 2026-05-08)：解 v3.0 洞察 11 silent skip 反模式
        - file_io 失敗 retry 1 次（檔案系統 transient 錯誤）
        - 各種失敗源（file_io / wiki_lookup / metric_inc）獨立計數，配 alert rule
        - 不再 fire-and-forget 全 silent — 失敗 reason 進 Prometheus 配 LINE watchdog
        """
        try:
            path = await self.ensure_today_header()
            now = datetime.now(TZ_TAIPEI)

            # PII 輕度遮罩（複用 shadow_logger 模式）
            q_masked = self._mask_pii(question)[:500]
            a_masked = self._mask_pii(answer)[:800]

            status_emoji = "✅" if success else "❌"
            tools_str = ", ".join(tools_used) if tools_used else "(none)"

            # Phase 7 整合：本筆 Q 在 wiki 的命中頁（前 2 名），用雙向連結
            # R7：wiki_lookup 失敗獨立計數，但不阻斷主寫入路徑
            wiki_links: List[str] = []
            try:
                wiki_links = await self._lookup_wiki_entities(question)
            except Exception as e:
                logger.warning("Diary wiki_lookup failed (non-blocking): %s", e)
                self._inc_failure("wiki_lookup")

            wiki_line = ""
            if wiki_links:
                wiki_line = "\n**wiki**: " + " · ".join(
                    f"[[{w}]]" for w in wiki_links
                )

            # v6.5 I2：NER entity 抽取（補 ❺ KG ↔ Memory 連結）
            ner_entities = self._extract_ner_entities(f"{question} {answer}")
            entities_line = ""
            if ner_entities:
                entities_line = "\n**entities**: " + ", ".join(
                    f"`{e}`" for e in ner_entities
                )

            entry = f"""
## {now.strftime('%H:%M:%S')} — {status_emoji} [{route_type or 'query'}] {channel or '-'}

**Q**: {q_masked}

**A**: {a_masked}

**tools**: `{tools_str}` | **latency**: {latency_ms or '?'}ms | **session**: `{(session_id or '-')[:20]}`{wiki_line}{entities_line}

"""
            # R7：file IO 失敗 retry 1 次
            await self._write_with_retry(path, entry)

            # Prometheus: diary append success counter（失敗也計數，避免 silent）
            try:
                from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                get_memory_wiki_metrics().diary_appends.inc()
            except Exception as e:
                logger.warning("Diary metric inc failed (non-blocking): %s", e)
                self._inc_failure("metric_inc")

        except Exception as e:
            # R7：取代 fire-and-forget silent — 失敗來源計數，配 watchdog alert
            logger.error("Diary append failed: %s", e, exc_info=True)
            self._inc_failure("file_io" if isinstance(e, (OSError, IOError)) else "unknown")

    async def _write_with_retry(self, path: Path, entry: str, *, retries: int = 1) -> None:
        """寫入失敗 retry 1 次（解檔案系統 transient 錯誤）。

        R7 (v6.9)：原 fire-and-forget 對 transient 失敗無防禦，
        加 1 次 retry + 0.1s 短等可解大部分 EAGAIN/EBUSY 案例。
        最終仍失敗時 raise，由 caller append_entry 的 except 捕獲計數。
        """
        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                async with self._write_lock:
                    with path.open("a", encoding="utf-8") as f:
                        f.write(entry)
                return
            except (OSError, IOError) as e:
                last_err = e
                if attempt < retries:
                    logger.warning(
                        "Diary write attempt %d/%d failed: %s — retrying",
                        attempt + 1, retries + 1, e,
                    )
                    await asyncio.sleep(0.1)
        if last_err is not None:
            raise last_err

    @staticmethod
    def _inc_failure(error_type: str) -> None:
        """記錄失敗到 Prometheus counter（best-effort，counter 本身失敗不 raise）。

        R7 (v6.9)：error_type ∈ {file_io / wiki_lookup / metric_inc / unknown}
        對應 alerts.yml DiaryAppendFailures rule。

        關鍵設計：直接從 global REGISTRY 取 counter，不經過 get_memory_wiki_metrics()。
        理由：metric_inc 失敗 case 中 get_memory_wiki_metrics 本身已壞，
        若 _inc_failure 也走它就 chicken-and-egg → 計數器永遠無法記錄該失敗。
        """
        try:
            from prometheus_client import REGISTRY
            counter = REGISTRY._names_to_collectors.get(
                "memory_diary_append_failures_total"
            )
            if counter is not None:
                counter.labels(error_type=error_type).inc()
        except Exception:
            # counter 註冊失敗（極罕見）也不能再 raise，否則陷入無限失敗循環
            pass

    @staticmethod
    async def _lookup_wiki_entities(question: str) -> List[str]:
        """抓 question 最像的 2 個 wiki 頁（best-effort，失敗回空）。

        Phase 7 整合：讓 diary 成為雙向入口 — 從日記能跳回 wiki 頁，
        以後可在 wiki 頁反查「此實體最近哪幾天被提及」。
        """
        try:
            from app.services.wiki.service import get_wiki_service
            hits = await get_wiki_service().search_wiki(question, limit=2)
            return [h.get("path") or h.get("filename", "?") for h in hits if h.get("path") or h.get("filename")]
        except Exception:
            return []

    @staticmethod
    def _mask_pii(text: str) -> str:
        if not text:
            return text
        # 台灣身分證 / 手機 / email
        text = re.sub(r"[A-Z][12]\d{8}", "[ID]", text)
        text = re.sub(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", "[PHONE]", text)
        text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", text)
        return text

    # v6.5 I2：NER entity 抽取（reuse self_evaluator / critic pattern）
    # 為避免 circular import 採 inline copy；pattern 同步以 LESSONS_REGISTRY 追蹤
    _NER_PATTERNS = [
        r'(?:承辦人|聯絡人|窗口|案件承辦)\s*[:：]?\s*([一-鿿]{1,4})',
        r'((?:老|小)[一-鿿])',
        r'(\d{2,3}[-_]\w{2,5})',
        r'(\d{2,3}年_派工單號\d+)',
    ]

    @classmethod
    def _extract_ner_entities(cls, text: str, cap: int = 5) -> List[str]:
        """從文字抽具名 entity（去重，最多 cap 個）。"""
        if not text:
            return []
        extracted: List[str] = []
        for pattern in cls._NER_PATTERNS:
            for m in re.finditer(pattern, text):
                ent = m.group(1) if m.groups() else m.group(0)
                ent = ent.strip()
                if ent and ent not in extracted:
                    extracted.append(ent)
                    if len(extracted) >= cap:
                        return extracted
        return extracted

    # ────────── Read ──────────

    async def read_today(self) -> Optional[str]:
        """讀今日 diary 全文。"""
        path = _diary_path(today_date())
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Diary read today failed: %s", e)
            return None

    async def read_yesterday(self) -> Optional[str]:
        """讀昨日 diary 全文。若無，往前找最近 3 天內有資料的檔案。"""
        for days_back in range(1, 4):
            target = today_date() - timedelta(days=days_back)
            path = _diary_path(target)
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    if len(content.strip()) > 50:
                        return content
                except Exception:
                    continue
        return None

    async def summarize_yesterday_for_context(self, max_chars: int = 800) -> str:
        """為 agent startup prompt 生成「昨日回顧」摘要（純截斷，不 call LLM 避免啟動延遲）。

        取昨日最後 3 筆 entry，加上頂部 header，總長 ≤ max_chars。
        """
        content = await self.read_yesterday()
        if not content:
            return ""

        # 抽取 frontmatter 後的 body
        body = re.sub(r"^---.*?---\s*", "", content, count=1, flags=re.DOTALL)

        # 切成 entries（以 ## 為分隔）
        entries = re.split(r"(?=^##\s)", body, flags=re.MULTILINE)
        entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("##")]

        # 取最後 3 筆
        last_entries = entries[-3:]

        summary = "【昨日回顧】\n" + "\n\n".join(last_entries)
        if len(summary) > max_chars:
            summary = summary[:max_chars].rstrip() + "..."
        return summary

    async def stats(self) -> dict:
        """回傳日記統計（用於健康檢查 / Dashboard）。"""
        files = list(DIARY_DIR.glob("*.md"))
        total_entries = 0
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
                total_entries += text.count("\n## ")  # 粗估
            except Exception:
                pass
        return {
            "diary_days": len(files),
            "total_entries_approx": total_entries,
            "latest_file": str(max(files, key=lambda p: p.stat().st_mtime).name) if files else None,
            "today_exists": _diary_path(today_date()).exists(),
        }


def get_diary_service() -> DiaryService:
    """Singleton 入口。"""
    return DiaryService.get_instance()
