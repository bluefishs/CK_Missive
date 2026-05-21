"""P0-1 (2026-05-20) — NotificationRepository._alias_user_filter unit test

RLSPort 真活接通第 2 caller（calendar P0-A 後續），鎖定：
1. helper 真實調用 DefaultRLSAdapter.expand_alias（不是空殼）
2. 返回的條件含 .in_(alias_group) 而非 == user_id
3. user_id + recipient_id 兩 column 都套 alias 展開
4. lazy singleton 重用

對應：
- ADR-0036 Bounded Context Contract Layer（Port 從 1 → 2 caller）
- ADR-0025 Identity Unification（同人多帳號分支收不到通知 dormant 修法）
- RETRO_20260519 §12.5 建議 A「Single Caller Per Port 週度節奏」第 1 週目標
- LESSON L29 dict-key drift 反模式預防（schema validation）

防 ADR-0025 第三次 dormant — 同人多帳號分支收不到通知（比 calendar 影響更廣，
推播該收到的人沒收到 = 業務面 silent failure）。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.notification_repository import NotificationRepository


@pytest.mark.asyncio
async def test_alias_user_filter_uses_rls_port_expand_alias():
    """驗證 helper 真實調用 DefaultRLSAdapter.expand_alias（非空殼）"""
    mock_db = MagicMock()
    repo = NotificationRepository(mock_db)

    # mock DefaultRLSAdapter.expand_alias 回傳 alias group {1, 2, 3}
    fake_alias_group = {1, 2, 3}
    with patch(
        "app.services.contracts.adapters.rls_default.DefaultRLSAdapter.expand_alias",
        new=AsyncMock(return_value=fake_alias_group),
    ) as mock_expand:
        condition = await repo._alias_user_filter(user_id=1)

        # 1. expand_alias 真被呼叫（不是空殼）
        mock_expand.assert_awaited_once_with(1)

    # 2. 返回的 SQLAlchemy 條件物件存在（or_() 結果）
    assert condition is not None

    # 3. 條件 string 表示應含 IN 而非 ==（alias group 展開 evidence）
    cond_str = str(condition.compile(compile_kwargs={"literal_binds": True}))
    assert " IN " in cond_str.upper(), (
        f"Expected IN clause for alias expansion, got: {cond_str}"
    )

    # 4. 兩個 column 都應參與（user_id + recipient_id 通知雙向）
    assert "user_id" in cond_str
    assert "recipient_id" in cond_str


@pytest.mark.asyncio
async def test_alias_user_filter_lazy_rls_singleton():
    """rls adapter 應 lazy init 一次後重用（避 N 次 DB session 浪費）"""
    mock_db = MagicMock()
    repo = NotificationRepository(mock_db)
    assert repo._rls is None  # 初始尚未 init

    with patch(
        "app.services.contracts.adapters.rls_default.DefaultRLSAdapter.expand_alias",
        new=AsyncMock(return_value={1}),
    ):
        await repo._alias_user_filter(user_id=1)
        first_rls = repo._rls
        assert first_rls is not None  # 首次調用後 init

        await repo._alias_user_filter(user_id=2)
        assert repo._rls is first_rls  # 重複調用應重用同一 adapter


@pytest.mark.asyncio
async def test_alias_user_filter_single_user_no_alias():
    """無 alias group（單一帳號）情境 — 應仍走 IN clause 但只 1 個 user_id"""
    mock_db = MagicMock()
    repo = NotificationRepository(mock_db)

    # 單一 user 無 alias — expand_alias 應回 {user_id}
    with patch(
        "app.services.contracts.adapters.rls_default.DefaultRLSAdapter.expand_alias",
        new=AsyncMock(return_value={42}),
    ):
        condition = await repo._alias_user_filter(user_id=42)

    cond_str = str(condition.compile(compile_kwargs={"literal_binds": True}))
    # 即使單一 user 也走 IN（避免 == vs IN 分支 bug）
    assert " IN " in cond_str.upper()
    assert "42" in cond_str


@pytest.mark.asyncio
async def test_get_by_user_invokes_alias_filter():
    """get_by_user 必須調用 _alias_user_filter（非直接裸 user_id ==）

    防 ADR-0025 dormant 第三次：8 處公開查詢介面均應透過 helper。
    """
    from sqlalchemy import literal

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    # 模擬 count query 與 select query 兩次 execute
    fake_count_result = MagicMock()
    fake_count_result.scalar.return_value = 0
    fake_select_result = MagicMock()
    fake_select_result.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [fake_count_result, fake_select_result]

    repo = NotificationRepository(mock_db)

    # patch 須回傳合法 SQLAlchemy clause（用 literal(True) 模擬 alias filter result）
    with patch.object(
        repo, "_alias_user_filter",
        new=AsyncMock(return_value=literal(True)),
    ) as mock_filter:
        items, total = await repo.get_by_user(user_id=42)
        # get_by_user 應調用 helper（鎖定 8 處不可繞過 RLSPort）
        mock_filter.assert_awaited_once_with(42)

    assert items == []
    assert total == 0
