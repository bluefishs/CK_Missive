# -*- coding: utf-8 -*-
"""replace_work_types 整批重建清空作業歸屬 — 回歸鎖定（2026-08-28）

原實作是整批 DELETE 後重建：id 全換，而 `taoyuan_work_records.work_type_id`
的 FK 是 ondelete='SET NULL' ⇒ 任何人存一次派工單基本資料（前端每次儲存
都送 work_type 字串，即使沒改），該單所有作業紀錄的「所屬作業」歸屬
就全部被清空。dispatch 179 的 7 月紀錄歸屬變 NULL 就是這樣來的。

鎖定的語意：
  1. 名稱清單沒變 ⇒ 既有列 id 保留 ⇒ 作業紀錄的 FK 完好
  2. 真的移除某類別 ⇒ 只有那一類被刪、其歸屬被 SET NULL（正確語意）
"""
from datetime import date

import pytest
from sqlalchemy import select

from app.extended.models.taoyuan import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchWorkType,
    TaoyuanWorkRecord,
)
from app.repositories.taoyuan import DispatchOrderRepository

WT_01 = "01.地上物查估作業"
WT_02 = "02.土地協議市價查估作業"


async def _work_types_of(db, dispatch_id):
    result = await db.execute(
        select(TaoyuanDispatchWorkType)
        .where(TaoyuanDispatchWorkType.dispatch_order_id == dispatch_id)
        .order_by(TaoyuanDispatchWorkType.sort_order)
    )
    return result.scalars().all()


@pytest.mark.asyncio
async def test_same_name_list_preserves_ids_and_record_fk(db_session):
    order = TaoyuanDispatchOrder(dispatch_no="TEST-RWT-REGRESSION-001")
    db_session.add(order)
    await db_session.flush()

    repo = DispatchOrderRepository(db_session)
    await repo.replace_work_types(order.id, [WT_01, WT_02])
    await db_session.flush()

    rows = await _work_types_of(db_session, order.id)
    ids_before = {r.work_type: r.id for r in rows}
    wt01_id = ids_before[WT_01]

    record = TaoyuanWorkRecord(
        dispatch_order_id=order.id,
        work_type_id=wt01_id,
        milestone_type="other",
        record_date=date(2026, 8, 28),
    )
    db_session.add(record)
    await db_session.flush()

    # 模擬「存一次派工單基本資料」：同樣的清單再同步一次
    await repo.replace_work_types(order.id, [WT_01, WT_02])
    await db_session.flush()

    rows_after = await _work_types_of(db_session, order.id)
    ids_after = {r.work_type: r.id for r in rows_after}
    assert ids_after == ids_before, (
        "名稱沒變時 id 必須保留 —— id 換掉就是 SET NULL 清空歸屬的整批重建"
    )

    await db_session.refresh(record)
    assert record.work_type_id == wt01_id, (
        "作業紀錄的所屬作業歸屬不得因無關的派工單編輯而被清空"
    )


@pytest.mark.asyncio
async def test_removed_type_is_deleted_and_kept_type_survives(db_session):
    order = TaoyuanDispatchOrder(dispatch_no="TEST-RWT-REGRESSION-002")
    db_session.add(order)
    await db_session.flush()

    repo = DispatchOrderRepository(db_session)
    await repo.replace_work_types(order.id, [WT_01, WT_02])
    await db_session.flush()

    rows = await _work_types_of(db_session, order.id)
    wt01_id = next(r.id for r in rows if r.work_type == WT_01)

    record = TaoyuanWorkRecord(
        dispatch_order_id=order.id,
        work_type_id=wt01_id,
        milestone_type="other",
        record_date=date(2026, 8, 28),
    )
    db_session.add(record)
    await db_session.flush()

    # 真的移除 02 —— 01 保留原 id，02 被刪
    await repo.replace_work_types(order.id, [WT_01])
    await db_session.flush()

    rows_after = await _work_types_of(db_session, order.id)
    assert [r.work_type for r in rows_after] == [WT_01]
    assert rows_after[0].id == wt01_id

    await db_session.refresh(record)
    assert record.work_type_id == wt01_id


@pytest.mark.asyncio
async def test_reorder_and_add_updates_sort_order(db_session):
    order = TaoyuanDispatchOrder(dispatch_no="TEST-RWT-REGRESSION-003")
    db_session.add(order)
    await db_session.flush()

    repo = DispatchOrderRepository(db_session)
    await repo.replace_work_types(order.id, [WT_01, WT_02])
    await db_session.flush()
    ids_before = {r.work_type: r.id for r in await _work_types_of(db_session, order.id)}

    # 順序對調＋新增一個 —— 既有兩個 id 不變、sort_order 更新
    await repo.replace_work_types(order.id, [WT_02, WT_01, "03.測試新增作業"])
    await db_session.flush()

    rows_after = await _work_types_of(db_session, order.id)
    assert [r.work_type for r in rows_after] == [WT_02, WT_01, "03.測試新增作業"]
    assert rows_after[0].id == ids_before[WT_02]
    assert rows_after[1].id == ids_before[WT_01]
