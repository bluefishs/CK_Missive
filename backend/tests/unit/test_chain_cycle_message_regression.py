# -*- coding: utf-8 -*-
"""防環錯誤訊息要指向使用者能改的東西（2026-08-07 回歸鎖）。

owner 實測：編輯作業紀錄 #8（id=369）時把「前序紀錄」選成 #9 或 #10，
後端回 400「鏈式紀錄存在循環: record_id=369」。

**那個判斷是對的** —— 不能把自己的下游設成前序。但訊息裡的 369 是
**使用者正在編輯的那一筆**，不是他挑的那個選項，於是完全無從得知該怎麼辦。

兩層都修了：
  · 前端：前序紀錄下拉排除自己的**下游**（原本只排除自己），
    所以那些必然失敗的選項一開始就不會出現
  · 後端（本測試鎖）：訊息改為指出「不能設為 #<挑的那個>」並說明原因

這支鎖後者。純字串比對很脆，所以只斷言兩件必要的事：
指出**被挑選的那個 id**，且不再只丟出被編輯的 id。
"""
from __future__ import annotations

import pytest


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    """回傳固定的祖先鏈，不碰真的資料庫。"""

    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _query):
        return _FakeResult(self._rows)


@pytest.mark.asyncio
async def test_cycle_message_names_the_selected_parent():
    """挑到自己的下游時，訊息要說「不能把前序設為 #<那個>」。"""
    from app.repositories.taoyuan.work_record_repository import WorkRecordRepository

    # 祖先鏈：從 388 往上是 388 → 369 → 349，而 369 正是被編輯的那筆
    rows = [(388, 2, 1), (369, 2, 2), (349, 2, 3)]
    repo = WorkRecordRepository(_FakeDB(rows))

    with pytest.raises(ValueError) as ei:
        await repo.check_chain_cycle(
            parent_id=388, dispatch_order_id=2, exclude_id=369,
        )
    msg = str(ei.value)
    assert "388" in msg, f"訊息要指出使用者挑的那個選項，實際：{msg}"
    assert "前序" in msg, f"訊息要說是哪個欄位的問題，實際：{msg}"


@pytest.mark.asyncio
async def test_valid_parent_passes():
    """正向：合法的前序不得被擋（否則上面那支只是「永遠會拋」而無鑑別力）。"""
    from app.repositories.taoyuan.work_record_repository import WorkRecordRepository

    rows = [(349, 2, 1), (50, 2, 2), (49, 2, 3)]
    repo = WorkRecordRepository(_FakeDB(rows))
    await repo.check_chain_cycle(parent_id=349, dispatch_order_id=2, exclude_id=369)


@pytest.mark.asyncio
async def test_cross_dispatch_parent_still_blocked():
    """跨派工單的前序仍要擋 —— 這條檢查不能因為改訊息而失效。"""
    from app.repositories.taoyuan.work_record_repository import WorkRecordRepository

    rows = [(999, 7, 1)]
    repo = WorkRecordRepository(_FakeDB(rows))
    with pytest.raises(ValueError) as ei:
        await repo.check_chain_cycle(parent_id=999, dispatch_order_id=2, exclude_id=369)
    assert "不屬於同一派工單" in str(ei.value)
