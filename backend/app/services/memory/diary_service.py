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

DIARY_DIR = Path(__file__).resolve().parents[4] / "wiki" / "memory" / "diary"
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
        """追加一筆日記 entry（fire-and-forget，失敗只 log 不 raise）。"""
        try:
            path = await self.ensure_today_header()
            now = datetime.now(TZ_TAIPEI)

            # PII 輕度遮罩（複用 shadow_logger 模式）
            q_masked = self._mask_pii(question)[:500]
            a_masked = self._mask_pii(answer)[:800]

            status_emoji = "✅" if success else "❌"
            tools_str = ", ".join(tools_used) if tools_used else "(none)"

            # Phase 7 整合：本筆 Q 在 wiki 的命中頁（前 2 名），用雙向連結
            wiki_links = await self._lookup_wiki_entities(question)
            wiki_line = ""
            if wiki_links:
                wiki_line = "\n**wiki**: " + " · ".join(
                    f"[[{w}]]" for w in wiki_links
                )

            entry = f"""
## {now.strftime('%H:%M:%S')} — {status_emoji} [{route_type or 'query'}] {channel or '-'}

**Q**: {q_masked}

**A**: {a_masked}

**tools**: `{tools_str}` | **latency**: {latency_ms or '?'}ms | **session**: `{(session_id or '-')[:20]}`{wiki_line}

"""
            async with self._write_lock:
                with path.open("a", encoding="utf-8") as f:
                    f.write(entry)

            # Prometheus: diary append counter（best-effort，失敗不 raise）
            try:
                from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                get_memory_wiki_metrics().diary_appends.inc()
            except Exception:
                pass

        except Exception as e:
            logger.warning("Diary append failed: %s", e)

    @staticmethod
    async def _lookup_wiki_entities(question: str) -> List[str]:
        """抓 question 最像的 2 個 wiki 頁（best-effort，失敗回空）。

        Phase 7 整合：讓 diary 成為雙向入口 — 從日記能跳回 wiki 頁，
        以後可在 wiki 頁反查「此實體最近哪幾天被提及」。
        """
        try:
            from app.services.wiki_service import get_wiki_service
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
