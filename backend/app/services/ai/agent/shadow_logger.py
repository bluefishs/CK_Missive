# -*- coding: utf-8 -*-
"""
Shadow Logger — 被動記錄 /ai/agent/query_sync 的 trace，用於 Haiku vs Gemma 基線評估。

設計原則：
  - 完全被動、不阻塞主流程（async fire-and-forget）
  - 寫 SQLite 單檔（logs/shadow_trace.db），不動 Postgres
  - 任何寫入錯誤都 log warning、絕不拋出
  - 預設 30% 取樣率，避免量大時 IO 壓力
  - question/answer 入庫前做 PII 遮罩（身分證/電話/email）

啟用：
  SHADOW_ENABLED=1 SHADOW_SAMPLE_RATIO=0.3

報告：
  node scripts/checks/shadow-baseline-report.cjs

Version: 1.1.0
Created: 2026-04-14
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parents[4] / "logs" / "shadow_trace.db"
_LOCK = threading.Lock()
_ENABLED: Optional[bool] = None  # lazy — 首次呼叫時從 env 讀取
_SAMPLE_RATIO: Optional[float] = None
_RETENTION_DAYS = int(os.getenv("SHADOW_RETENTION_DAYS", "30"))


_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_trace (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    channel       TEXT,
    provider      TEXT,
    question      TEXT,
    answer        TEXT,
    success       INTEGER NOT NULL DEFAULT 1,
    latency_ms    INTEGER,
    tools_used    TEXT,
    sources_count INTEGER,
    error_code    TEXT,
    session_id    TEXT,
    request_id    TEXT
);
CREATE INDEX IF NOT EXISTS idx_trace_ts ON query_trace(ts);
CREATE INDEX IF NOT EXISTS idx_trace_channel ON query_trace(channel);
CREATE INDEX IF NOT EXISTS idx_trace_provider ON query_trace(provider);
"""


def _migrate_add_provider_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration — 既有 DB 升級時補 provider 欄位。"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(query_trace)")}
    if "provider" not in cols:
        conn.execute("ALTER TABLE query_trace ADD COLUMN provider TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_provider ON query_trace(provider)")


# PII 遮罩 regex（最小集，不追求完美）
_PII_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"[A-Z][12]\d{8}"), "[ID]"),                       # 台灣身分證
    (re.compile(r"09\d{2}[- ]?\d{3}[- ]?\d{3}"), "[PHONE]"),      # 手機
    (re.compile(r"0\d{1,2}[- ]?\d{6,8}"), "[TEL]"),                # 市話
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),          # email
]


def _mask_pii(text: str) -> str:
    if not text:
        return text
    for pat, repl in _PII_PATTERNS:
        text = pat.sub(repl, text)
    return text


def _ensure_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.executescript(_SCHEMA)
            _migrate_add_provider_column(conn)


@contextmanager
def _conn():
    with _LOCK:
        conn = sqlite3.connect(_DB_PATH, timeout=5.0)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _get_enabled() -> bool:
    global _ENABLED
    if _ENABLED is None:
        _ENABLED = os.getenv("SHADOW_ENABLED", "0") == "1"
    return _ENABLED


def _get_sample_ratio() -> float:
    global _SAMPLE_RATIO
    if _SAMPLE_RATIO is None:
        _SAMPLE_RATIO = float(os.getenv("SHADOW_SAMPLE_RATIO", "0.3"))
    return _SAMPLE_RATIO


def is_enabled() -> bool:
    return _get_enabled()


def _write_sync(row: Dict[str, Any]) -> None:
    """同步寫入 — 只該被 async task 呼叫。"""
    try:
        _ensure_db()
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO query_trace
                (ts, channel, provider, question, answer, success, latency_ms,
                 tools_used, sources_count, error_code, session_id, request_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row.get("ts") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    row.get("channel"),
                    row.get("provider"),
                    _mask_pii((row.get("question") or "")[:2000]),
                    _mask_pii((row.get("answer") or "")[:4000]),
                    1 if row.get("success", True) else 0,
                    row.get("latency_ms"),
                    json.dumps(row.get("tools_used") or [], ensure_ascii=False),
                    row.get("sources_count"),
                    row.get("error_code"),
                    row.get("session_id"),
                    row.get("request_id"),
                ),
            )
    except Exception as e:
        logger.warning("shadow_logger write failed: %s", e)


def purge_expired() -> int:
    """刪除超過保留期的 trace，回傳刪除筆數。供排程器呼叫。

    VACUUM 必須在 transaction 外執行（SQLite 限制），故分兩階段。
    """
    try:
        _ensure_db()
        with _conn() as conn:
            cur = conn.execute(
                "DELETE FROM query_trace WHERE ts < datetime('now', ?)",
                (f"-{_RETENTION_DAYS} days",),
            )
            deleted = cur.rowcount
        # VACUUM 必須在 autocommit 模式下、且不可在進行中的交易內
        with _LOCK:
            vac = sqlite3.connect(_DB_PATH, isolation_level=None, timeout=5.0)
            try:
                vac.execute("VACUUM")
            finally:
                vac.close()
        return deleted
    except Exception as e:
        logger.warning("shadow_logger purge failed: %s", e)
        return 0


async def log_trace(
    *,
    channel: Optional[str],
    question: str,
    answer: str,
    success: bool,
    latency_ms: int,
    provider: Optional[str] = None,
    tools_used: Optional[List[str]] = None,
    sources_count: Optional[int] = None,
    error_code: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Fire-and-forget 紀錄一筆 trace。取樣不通過則直接跳過。

    provider: 推論提供者標籤（如 haiku-openclaw / gemma-hermes / groq-llama）
              供 Hermes 遷移期 A/B 比對用。若未指定，由 env ``SHADOW_DEFAULT_PROVIDER`` 決定。
    """
    if not _get_enabled():
        return
    # 合成基線（synthetic-*）永遠 100% 記錄，不受取樣率限制
    is_synthetic = session_id and str(session_id).startswith("synthetic-")
    if not is_synthetic and random.random() > _get_sample_ratio():
        return
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channel": channel,
        "provider": provider or os.getenv("SHADOW_DEFAULT_PROVIDER", "unknown"),
        "question": question,
        "answer": answer,
        "success": success,
        "latency_ms": latency_ms,
        "tools_used": tools_used,
        "sources_count": sources_count,
        "error_code": error_code,
        "session_id": session_id,
        "request_id": request_id,
    }
    try:
        await asyncio.to_thread(_write_sync, row)
    except Exception as e:
        logger.warning("shadow_logger async dispatch failed: %s", e)
