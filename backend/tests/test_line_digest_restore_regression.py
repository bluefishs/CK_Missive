# -*- coding: utf-8 -*-
"""digest 送不出去時必須放回佇列 — 回歸鎖定（2026-08-29）

`drain_digest()` 是「讀取後立刻 delete」，而真正的送出在幾十行之後
（scheduler Step 4）。中間失敗——最現實的是 LINE 月配額用罄
（`_call_line_api` 對 429 monthly limit 短路、直接回 False）——
那批主題摘要已從 Redis 刪掉，**永久遺失且無痕跡**。

CK_Website 2026-08-29 在他們 Worker 的 `flushDigest` 找到同族缺陷
（`await send()` 之後無條件前進 cursor）並提醒掃自己的送出路徑，
掃出了這一條。共同形狀：**呼叫的返回被當成對方收到**。

鎖定語意：
  1. 回填後條目仍在（不會因為 drain 過就消失）
  2. 回填保留原內容（topic/text 不被改寫）
  3. 空清單不做事（不製造假象）
"""
import pytest

from app.services.integration import line_digest_buffer as buf


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    """走 in-memory 路徑：不碰 Redis，也不污染正式晨報緩衝區。

    ⚠️ `CK_NOTIFY_TEST_ISOLATION` 是本 repo 既有約定 —— 手動觸發正式 job
    未帶它時，告警會進正式緩衝區（memory 檔已記過這個教訓）。
    """
    monkeypatch.setenv("CK_NOTIFY_TEST_ISOLATION", "1")
    buf._memory_buffer.clear()
    yield
    buf._memory_buffer.clear()


@pytest.mark.asyncio
async def test_drain_then_restore_keeps_items():
    await buf.queue_digest("吹哨者", "測試主題 A")
    await buf.queue_digest("cron健康", "測試主題 B")

    drained = await buf.drain_digest()
    assert len(drained) == 2, "drain 應取出兩則"
    assert await buf.drain_digest() == [], "drain 之後佇列必須是空的（這正是危險所在）"

    # 送出失敗 → 回填
    n = await buf.restore_digest(drained)
    assert n == 2

    again = await buf.drain_digest()
    assert len(again) == 2, "回填後條目必須還在——否則就是永久遺失"
    assert {i["topic"] for i in again} == {"吹哨者", "cron健康"}
    assert {i["text"] for i in again} == {"測試主題 A", "測試主題 B"}


@pytest.mark.asyncio
async def test_restore_empty_is_noop():
    assert await buf.restore_digest([]) == 0
    assert await buf.drain_digest() == []
