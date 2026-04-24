# -*- coding: utf-8 -*-
"""ADR-0026: WorkRecord ↔ Calendar 同步 regression tests.

聚焦 helper 函數邏輯的單元測試（不走完整 DB fixture，避免 migration 依賴）。
端到端同步測試在 E2E 階段補。
"""
from __future__ import annotations

import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def _mk_work_record(**kwargs):
    defaults = dict(
        id=100,
        dispatch_order_id=149,
        document_id=None,
        incoming_doc_id=None,
        outgoing_doc_id=None,
        deadline_date=date(2026, 5, 3),
        work_category='meeting_record',
        description='會議紀錄',
        notes=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_category_label_map_covers_common_categories():
    from app.services.taoyuan.work_record_calendar_sync import CATEGORY_LABELS
    # v5.8.1：label 統一為短版（title 模板「【動詞+類別】」用），符合 common/calendar_title_template.py
    assert CATEGORY_LABELS['meeting_record'] == '會議紀錄'
    assert CATEGORY_LABELS['dispatch_notice'] == '派工通知'
    assert CATEGORY_LABELS['work_result'] == '成果'
    assert CATEGORY_LABELS['survey_notice'] == '會勘通知'


@pytest.mark.asyncio
async def test_sync_skips_when_no_deadline_and_no_existing():
    """無 deadline 且無既有 event → no-op 回 None。"""
    from app.services.taoyuan.work_record_calendar_sync import sync_work_record_to_calendar

    db = MagicMock()
    # scalar_one_or_none 回 None（無既有）
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=exec_result)

    wr = _mk_work_record(deadline_date=None)
    result = await sync_work_record_to_calendar(db, wr, actor_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_sync_cancels_event_when_deadline_cleared():
    """deadline 被清除 → 既有 event 標 cancelled。"""
    from app.services.taoyuan.work_record_calendar_sync import sync_work_record_to_calendar

    db = MagicMock()
    existing = SimpleNamespace(id=55, status='pending', google_sync_status='synced')
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=exec_result)

    wr = _mk_work_record(deadline_date=None)
    result = await sync_work_record_to_calendar(db, wr, actor_id=1)
    assert result is existing
    assert existing.status == 'cancelled'
    assert existing.google_sync_status == 'pending'


@pytest.mark.asyncio
async def test_cancel_work_record_calendar_marks_cancelled():
    from app.services.taoyuan.work_record_calendar_sync import cancel_work_record_calendar

    db = MagicMock()
    existing = SimpleNamespace(id=77, status='pending', google_sync_status='synced')
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=exec_result)

    changed = await cancel_work_record_calendar(db, 100)
    assert changed is True
    assert existing.status == 'cancelled'


@pytest.mark.asyncio
async def test_cancel_skips_when_no_event():
    from app.services.taoyuan.work_record_calendar_sync import cancel_work_record_calendar

    db = MagicMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=exec_result)

    changed = await cancel_work_record_calendar(db, 100)
    assert changed is False


@pytest.mark.asyncio
async def test_cancel_idempotent_when_already_cancelled():
    from app.services.taoyuan.work_record_calendar_sync import cancel_work_record_calendar

    db = MagicMock()
    existing = SimpleNamespace(id=77, status='cancelled', google_sync_status='synced')
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=exec_result)

    changed = await cancel_work_record_calendar(db, 100)
    assert changed is False
