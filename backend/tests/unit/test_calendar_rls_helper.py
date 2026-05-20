"""P0-A (2026-05-19) — CalendarRepository._alias_user_filter unit test

鎖定 RLSPort 真活接通（首個 Port 真 caller）：
1. helper 真實調用 DefaultRLSAdapter.expand_alias（不是空殼）
2. 返回的條件含 .in_(alias_group) 而非 == user_id
3. assigned_user_id + created_by 兩 column 都套 alias 展開

對應 ADR-0036 Bounded Context Contract Layer + ADR-0025 Identity Unification +
RETRO_20260519 §6 P0-A + LESSONS L29 dict-key drift / L38 平時保險反模式。

防 ADR-0025 第三次 dormant — 同人多帳號分支查行事曆應雙向可見。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.calendar_repository import CalendarRepository


@pytest.mark.asyncio
async def test_alias_user_filter_uses_rls_port_expand_alias():
    """驗證 helper 真實調用 DefaultRLSAdapter.expand_alias（非空殼）"""
    mock_db = MagicMock()
    repo = CalendarRepository(mock_db)

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

    # 4. 兩個 column 都應參與
    assert "assigned_user_id" in cond_str
    assert "created_by" in cond_str


@pytest.mark.asyncio
async def test_alias_user_filter_lazy_rls_singleton():
    """rls adapter 應 lazy init 一次後重用（避 N 次 DB session 浪費）"""
    mock_db = MagicMock()
    repo = CalendarRepository(mock_db)
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
    repo = CalendarRepository(mock_db)

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
async def test_alias_user_filter_includes_owner_less_events():
    """v6.10.1 急救：owner-less 事件（created_by + assigned_user_id 皆 NULL）
    必納入結果 — 否則 90% 業務事件對所有 user 大規模 dormant。

    觸發案例：公文 2479 對應事件 1081 用戶看不到。
    """
    mock_db = MagicMock()
    repo = CalendarRepository(mock_db)

    with patch(
        "app.services.contracts.adapters.rls_default.DefaultRLSAdapter.expand_alias",
        new=AsyncMock(return_value={42}),
    ):
        condition = await repo._alias_user_filter(user_id=42)

    cond_str = str(condition.compile(compile_kwargs={"literal_binds": True}))
    # 必含 IS NULL 條件對應「公開事件」業務語意
    upper = cond_str.upper()
    assert "IS NULL" in upper, (
        f"Expected IS NULL fallback for owner-less events, got: {cond_str}"
    )
    # 必同時對 assigned_user_id 與 created_by 兩欄都 NULL 才算公開
    assert cond_str.count("IS NULL") >= 2, (
        "需 assigned_user_id IS NULL AND created_by IS NULL 雙條件"
    )
