# -*- coding: utf-8 -*-
"""Shadow Logger 單元測試。"""
from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """替換 _DB_PATH 到臨時目錄，重載模組。"""
    import importlib

    from app.services.ai.agent import shadow_logger as sl

    db = tmp_path / "shadow_trace.db"
    monkeypatch.setattr(sl, "_DB_PATH", db)
    monkeypatch.setattr(sl, "_ENABLED", True)
    monkeypatch.setattr(sl, "_SAMPLE_RATIO", 1.0)
    yield db, sl
    importlib.reload(sl)  # 還原全域旗標


def test_pii_mask_id_phone_email(tmp_db):
    _, sl = tmp_db
    text = "我是 A123456789 手機 0912-345-678 email foo@bar.com 市話 02-12345678"
    out = sl._mask_pii(text)
    assert "A123456789" not in out
    assert "0912-345-678" not in out
    assert "foo@bar.com" not in out
    assert "02-12345678" not in out
    assert "[ID]" in out and "[PHONE]" in out and "[EMAIL]" in out


def test_mask_preserves_non_pii():
    from app.services.ai.agent.shadow_logger import _mask_pii

    text = "查公文 123 號，案號 CK2026001"
    assert _mask_pii(text) == text


def test_disabled_noop(tmp_path, monkeypatch):
    from app.services.ai.agent import shadow_logger as sl

    db = tmp_path / "shadow_trace.db"
    monkeypatch.setattr(sl, "_DB_PATH", db)
    monkeypatch.setattr(sl, "_ENABLED", False)

    asyncio.run(sl.log_trace(
        channel="line", question="q", answer="a",
        success=True, latency_ms=100,
    ))
    assert not db.exists(), "disabled 時不該建 DB"


def test_sampling_zero_noop(tmp_path, monkeypatch):
    from app.services.ai.agent import shadow_logger as sl

    db = tmp_path / "shadow_trace.db"
    monkeypatch.setattr(sl, "_DB_PATH", db)
    monkeypatch.setattr(sl, "_ENABLED", True)
    monkeypatch.setattr(sl, "_SAMPLE_RATIO", 0.0)

    asyncio.run(sl.log_trace(
        channel="telegram", question="q", answer="a",
        success=True, latency_ms=100,
    ))
    assert not db.exists(), "ratio=0 時不該寫入"


def test_write_success(tmp_db):
    db, sl = tmp_db
    asyncio.run(sl.log_trace(
        channel="telegram",
        question="test A123456789",
        answer="ok",
        success=True,
        latency_ms=250,
        provider="gemma-hermes",
        tools_used=["search"],
        sources_count=3,
    ))
    assert db.exists()
    conn = sqlite3.connect(db)
    rows = list(conn.execute(
        "SELECT channel, provider, question, answer, success, latency_ms FROM query_trace"
    ))
    conn.close()
    assert len(rows) == 1
    channel, provider, q, a, ok, lat = rows[0]
    assert channel == "telegram"
    assert provider == "gemma-hermes"
    assert "A123456789" not in q  # PII 已遮罩
    assert "[ID]" in q
    assert ok == 1
    assert lat == 250


def test_provider_defaults_from_env(tmp_db, monkeypatch):
    db, sl = tmp_db
    monkeypatch.setenv("SHADOW_DEFAULT_PROVIDER", "haiku-openclaw")
    asyncio.run(sl.log_trace(
        channel="line", question="q", answer="a",
        success=True, latency_ms=100,
    ))
    conn = sqlite3.connect(db)
    (provider,) = conn.execute("SELECT provider FROM query_trace").fetchone()
    conn.close()
    assert provider == "haiku-openclaw"


def test_write_failure_silent(tmp_path, monkeypatch, caplog):
    """寫入失敗時不該 raise。"""
    from app.services.ai.agent import shadow_logger as sl

    bad = tmp_path / "nonexistent" / "readonly" / "shadow.db"
    monkeypatch.setattr(sl, "_DB_PATH", bad)
    monkeypatch.setattr(sl, "_ENABLED", True)
    monkeypatch.setattr(sl, "_SAMPLE_RATIO", 1.0)

    with patch.object(sl, "_ensure_db", side_effect=OSError("readonly")):
        asyncio.run(sl.log_trace(
            channel="x", question="q", answer="a",
            success=True, latency_ms=1,
        ))


def test_purge_expired(tmp_db):
    db, sl = tmp_db
    sl._ensure_db()
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO query_trace (ts, channel, success, latency_ms) VALUES (?,?,?,?)",
        ("2020-01-01T00:00:00+00:00", "old", 1, 100),
    )
    conn.execute(
        "INSERT INTO query_trace (ts, channel, success, latency_ms) VALUES (datetime('now'),?,?,?)",
        ("new", 1, 100),
    )
    conn.commit()
    conn.close()

    deleted = sl.purge_expired()
    assert deleted == 1

    conn = sqlite3.connect(db)
    remaining = list(conn.execute("SELECT channel FROM query_trace"))
    conn.close()
    assert len(remaining) == 1 and remaining[0][0] == "new"
