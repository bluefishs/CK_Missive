# -*- coding: utf-8 -*-
"""
WorkRecordService 單元測試

測試範圍:
- CRUD 操作 (create, get, update, delete)
- 刪除時清理孤兒子紀錄
- 批次更新 + 同一派工單驗證
- 鏈式防環檢查
- 自動填入日期
- 自動關聯公文到派工單

測試策略:
- Mock WorkRecordRepository + AsyncSession
- 使用 AsyncMock 模擬非同步方法

v1.0.0 - 2026-02-17
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.taoyuan.work_record_service import WorkRecordService


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_db():
    """建立 Mock 資料庫 session"""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_repository():
    """建立 Mock WorkRecordRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_with_docs = AsyncMock()
    repo.list_by_dispatch_order = AsyncMock(return_value=([], 0))
    repo.list_by_project = AsyncMock(return_value=([], 0))
    repo.get_max_sort_order = AsyncMock(return_value=0)
    repo.get_workflow_summary = AsyncMock(return_value={
        "milestones_completed": 0,
        "current_stage": None,
        "total_incoming_docs": 0,
        "total_outgoing_docs": 0,
        "work_records": [],
    })
    return repo


@pytest.fixture
def service(mock_db, mock_repository):
    """建立 WorkRecordService 並注入 mock"""
    svc = WorkRecordService(mock_db)
    svc.repository = mock_repository
    return svc


# ============================================================
# get_record
# ============================================================

class TestGetRecord:
    @pytest.mark.asyncio
    async def test_delegates_to_repository(self, service, mock_repository):
        mock_record = MagicMock(id=1)
        mock_repository.get_with_docs.return_value = mock_record

        result = await service.get_record(1)

        assert result == mock_record
        mock_repository.get_with_docs.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_repository):
        mock_repository.get_with_docs.return_value = None
        result = await service.get_record(999)
        assert result is None


# ============================================================
# list_by_dispatch_order
# ============================================================

class TestListByDispatchOrder:
    @pytest.mark.asyncio
    async def test_returns_items_and_total(self, service, mock_repository):
        mock_items = [MagicMock(id=1), MagicMock(id=2)]
        mock_repository.list_by_dispatch_order.return_value = (mock_items, 2)

        items, total = await service.list_by_dispatch_order(
            dispatch_order_id=1, page=1, limit=50
        )

        assert len(items) == 2
        assert total == 2
        mock_repository.list_by_dispatch_order.assert_called_once_with(1, 1, 50)


# ============================================================
# create_record
# ============================================================

class TestCreateRecord:
    @pytest.mark.asyncio
    async def test_basic_create(self, service, mock_db):
        """基礎建立：確保 model_dump + db.add + flush 流程"""
        from app.schemas.taoyuan.workflow import WorkRecordCreate
        data = WorkRecordCreate(
            dispatch_order_id=1,
            milestone_type='other',
            record_date=date(2026, 1, 15),
            status='in_progress',
        )

        # mock db.get for potential lookups
        mock_db.get = AsyncMock(return_value=None)

        result = await service.create_record(data)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_auto_fill_date_from_document(self, service, mock_db):
        """document_id 存在時自動填入 record_date"""
        from app.schemas.taoyuan.workflow import WorkRecordCreate

        mock_doc = MagicMock()
        mock_doc.doc_date = date(2026, 2, 10)

        mock_db.get = AsyncMock(return_value=mock_doc)

        # 建立 mock execute result for _auto_link_document
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1  # 已關聯
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = WorkRecordCreate(
            dispatch_order_id=1,
            document_id=100,
            milestone_type='other',
            status='in_progress',
            # 不設定 record_date，讓自動填入
        )

        await service.create_record(data)

        # 確認有呼叫 db.get(OfficialDocument, 100)
        assert mock_db.get.called

    @pytest.mark.asyncio
    async def test_default_milestone_type_to_other(self, service, mock_db):
        """未提供 milestone_type 時預設為 'other'"""
        from app.schemas.taoyuan.workflow import WorkRecordCreate
        data = WorkRecordCreate(
            dispatch_order_id=1,
            status='in_progress',
            record_date=date(2026, 1, 15),
        )

        mock_db.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()

        await service.create_record(data)

        # 驗證 db.add 被呼叫時，record 的 milestone_type = 'other'
        added_record = mock_db.add.call_args[0][0]
        assert added_record.milestone_type == 'other'


# ============================================================
# delete_record (含孤兒清理)
# ============================================================

class TestDeleteRecord:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None
        result = await service.delete_record(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_clears_orphan_children(self, service, mock_db, mock_repository):
        """刪除紀錄時清理子紀錄的 parent_record_id"""
        mock_record = MagicMock(id=5)
        mock_repository.get_by_id.return_value = mock_record

        # mock update result (2 orphaned children)
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.delete_record(5)

        assert result == 2
        mock_db.delete.assert_called_once_with(mock_record)

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_children(self, service, mock_db, mock_repository):
        mock_record = MagicMock(id=3)
        mock_repository.get_by_id.return_value = mock_record

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.delete_record(3)
        assert result == 0


# ============================================================
# verify_records_same_dispatch
# ============================================================

class TestVerifyRecordsSameDispatch:
    @pytest.mark.asyncio
    async def test_empty_list_passes(self, service):
        """空列表不拋錯"""
        await service.verify_records_same_dispatch([])

    @pytest.mark.asyncio
    async def test_same_dispatch_passes(self, service, mock_db):
        """所有紀錄屬於同一派工單 → 通過"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [1]
        mock_db.execute = AsyncMock(return_value=mock_result)

        await service.verify_records_same_dispatch([10, 20, 30])

    @pytest.mark.asyncio
    async def test_different_dispatch_raises(self, service, mock_db):
        """紀錄分屬不同派工單 → ValueError"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [1, 2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="不可跨派工單"):
            await service.verify_records_same_dispatch([10, 20])

    @pytest.mark.asyncio
    async def test_nonexistent_records_raises(self, service, mock_db):
        """指定的紀錄不存在 → ValueError"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="不存在"):
            await service.verify_records_same_dispatch([999])


# ============================================================
# _check_chain_cycle
# ============================================================

class TestCheckChainCycle:
    @pytest.mark.asyncio
    async def test_no_cycle_passes(self, service, mock_db):
        """無循環 → 通過"""
        parent = MagicMock()
        parent.dispatch_order_id = 1
        parent.parent_record_id = None

        mock_db.get = AsyncMock(return_value=parent)

        # 不應拋錯
        await service._check_chain_cycle(parent_id=10, dispatch_order_id=1)

    @pytest.mark.asyncio
    async def test_parent_not_found_raises(self, service, mock_db):
        """parent 不存在 → ValueError"""
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="前序紀錄不存在"):
            await service._check_chain_cycle(parent_id=999, dispatch_order_id=1)

    @pytest.mark.asyncio
    async def test_different_dispatch_raises(self, service, mock_db):
        """parent 屬於不同派工單 → ValueError"""
        parent = MagicMock()
        parent.dispatch_order_id = 2  # 不同派工單
        parent.parent_record_id = None

        mock_db.get = AsyncMock(return_value=parent)

        with pytest.raises(ValueError, match="不屬於同一派工單"):
            await service._check_chain_cycle(parent_id=10, dispatch_order_id=1)


# ============================================================
# update_batch
# ============================================================

class TestUpdateBatch:
    @pytest.mark.asyncio
    async def test_empty_ids_returns_zero(self, service):
        result = await service.update_batch([], batch_no=1, batch_label="第1批")
        assert result == 0

    @pytest.mark.asyncio
    async def test_updates_records(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.update_batch(
            [1, 2, 3], batch_no=1, batch_label="第1批結案"
        )
        assert result == 3
