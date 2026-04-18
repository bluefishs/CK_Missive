# -*- coding: utf-8 -*-
"""
TDD: run_with_fresh_session — 並行 DB 操作防護

驗證：
1. 回傳值正確
2. 例外時 rollback
3. 多個 fresh session 彼此獨立（不共用 connection）

背景：2026-04-19 asyncpg "another operation is in progress" race —
原因為 asyncio.gather 多 task 共用同一 session，asyncpg connection 不允許併發。
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_returns_fn_result():
    from app.db.database import run_with_fresh_session

    session_mock = MagicMock()
    session_mock.commit = AsyncMock()
    session_mock.rollback = AsyncMock()
    session_mock.close = AsyncMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=False)

    async def _fn(db):
        assert db is session_mock
        return "payload"

    with patch("app.db.database.AsyncSessionLocal", return_value=session_mock):
        result = await run_with_fresh_session(_fn)

    assert result == "payload"
    session_mock.commit.assert_awaited_once()
    session_mock.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_rolls_back_on_exception():
    from app.db.database import run_with_fresh_session

    session_mock = MagicMock()
    session_mock.commit = AsyncMock()
    session_mock.rollback = AsyncMock()
    session_mock.close = AsyncMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=False)

    async def _fail(db):
        raise RuntimeError("boom")

    with patch("app.db.database.AsyncSessionLocal", return_value=session_mock):
        with pytest.raises(RuntimeError, match="boom"):
            await run_with_fresh_session(_fail)

    session_mock.rollback.assert_awaited_once()
    session_mock.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_parallel_gather_uses_independent_sessions():
    """核心保證：gather 中 N 個 task 各自持有不同 session instance。
    asyncpg "another operation in progress" race 的根本解法。"""
    from app.db.database import run_with_fresh_session

    created_sessions = []

    def _make_session():
        s = MagicMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        s.close = AsyncMock()
        s.__aenter__ = AsyncMock(return_value=s)
        s.__aexit__ = AsyncMock(return_value=False)
        created_sessions.append(s)
        return s

    async def _task(label: str):
        async def _inner(db):
            # 模擬 DB 操作需要非零延遲以確保 task 真的並行
            await asyncio.sleep(0.01)
            return (label, id(db))
        return await run_with_fresh_session(_inner)

    with patch("app.db.database.AsyncSessionLocal", side_effect=_make_session):
        results = await asyncio.gather(_task("A"), _task("B"), _task("C"))

    # 三個 task 拿到三個不同的 session instance
    assert len(created_sessions) == 3
    session_ids = {r[1] for r in results}
    assert len(session_ids) == 3, f"Expected 3 distinct sessions, got {session_ids}"
    # 每個 session 都有 commit 一次
    for s in created_sessions:
        s.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_partial_failure_does_not_poison_siblings():
    """gather 中一個失敗不影響其他 task 的 session commit。"""
    from app.db.database import run_with_fresh_session

    created_sessions = []

    def _make_session():
        s = MagicMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        s.close = AsyncMock()
        s.__aenter__ = AsyncMock(return_value=s)
        s.__aexit__ = AsyncMock(return_value=False)
        created_sessions.append(s)
        return s

    async def _ok(db):
        return "ok"

    async def _fail(db):
        raise ValueError("boom")

    with patch("app.db.database.AsyncSessionLocal", side_effect=_make_session):
        results = await asyncio.gather(
            run_with_fresh_session(_ok),
            run_with_fresh_session(_fail),
            return_exceptions=True,
        )

    assert results[0] == "ok"
    assert isinstance(results[1], ValueError)
    # 成功那個 commit，失敗那個 rollback
    assert created_sessions[0].commit.await_count == 1
    assert created_sessions[1].rollback.await_count == 1
