"""
DocumentRepository 單元測試

測試公文 Repository 的查詢、篩選、統計等方法。
使用 mock AsyncSession，不需要實際資料庫連線。

@version 1.0.0
@date 2026-02-07
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repository import DocumentRepository
from app.extended.models import OfficialDocument, DocumentAttachment


class TestDocumentRepositoryBasicCRUD:
    """DocumentRepository 基礎 CRUD 測試"""

    @pytest.fixture
    def mock_db(self):
        """建立模擬的資料庫 session"""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """建立 DocumentRepository 實例"""
        return DocumentRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db):
        """測試 get_by_id - 找到公文"""
        mock_doc = MagicMock(spec=OfficialDocument)
        mock_doc.id = 1
        mock_doc.subject = "測試公文"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.subject == "測試公文"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        """測試 get_by_id - 公文不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(999)

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document(self, repo, mock_db):
        """測試建立公文"""
        create_data = {
            "doc_number": "TEST-2026-001",
            "subject": "新建測試公文",
            "doc_type": "收文",
            "sender": "桃園市政府",
            "receiver": "乾坤測繪有限公司",
            "status": "待處理",
            "category": "收文",
        }

        result = await repo.create(create_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document(self, repo, mock_db):
        """測試更新公文"""
        mock_doc = MagicMock(spec=OfficialDocument)
        mock_doc.id = 1
        mock_doc.subject = "原始主旨"
        mock_doc.status = "待處理"

        # get_by_id 呼叫
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        update_data = {"subject": "更新後主旨", "status": "已辦畢"}
        result = await repo.update(1, update_data)

        assert result is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document_not_found(self, repo, mock_db):
        """測試更新不存在的公文"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.update(999, {"subject": "更新"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_document(self, repo, mock_db):
        """測試刪除公文"""
        mock_doc = MagicMock(spec=OfficialDocument)
        mock_doc.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        result = await repo.delete(1)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_doc)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, repo, mock_db):
        """測試刪除不存在的公文"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.delete(999)

        assert result is False
        mock_db.delete.assert_not_called()


class TestDocumentRepositoryQueries:
    """DocumentRepository 公文特定查詢測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return DocumentRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_doc_number_found(self, repo, mock_db):
        """測試根據文號查詢 - 找到"""
        mock_doc = MagicMock(spec=OfficialDocument)
        mock_doc.doc_number = "府工測字第1140001234號"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_doc_number("府工測字第1140001234號")

        assert result is not None
        assert result.doc_number == "府工測字第1140001234號"

    @pytest.mark.asyncio
    async def test_get_by_doc_number_not_found(self, repo, mock_db):
        """測試根據文號查詢 - 不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_doc_number("不存在的文號")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_auto_serial(self, repo, mock_db):
        """測試根據流水序號查詢"""
        mock_doc = MagicMock(spec=OfficialDocument)
        mock_doc.auto_serial = "R0001"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_auto_serial("R0001")

        assert result is not None
        assert result.auto_serial == "R0001"

    @pytest.mark.asyncio
    async def test_filter_documents_by_type(self, repo, mock_db):
        """測試依公文類型篩選"""
        mock_docs = [
            MagicMock(spec=OfficialDocument, id=1, doc_type="收文"),
            MagicMock(spec=OfficialDocument, id=2, doc_type="收文"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_type("收文")

        assert len(result) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_documents_by_status(self, repo, mock_db):
        """測試依處理狀態篩選"""
        mock_docs = [
            MagicMock(spec=OfficialDocument, id=1, status="待處理"),
            MagicMock(spec=OfficialDocument, id=3, status="待處理"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_status("待處理")

        assert len(result) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_date_range(self, repo, mock_db):
        """測試依日期範圍查詢"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=i) for i in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_date_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        assert len(result) == 3
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_date_range_with_type(self, repo, mock_db):
        """測試依日期範圍加類型篩選"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=1, doc_type="收文")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_date_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            doc_type="收文",
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_project(self, repo, mock_db):
        """測試依專案 ID 查詢關聯公文"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=i) for i in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_project(project_id=10)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_agency_as_sender(self, repo, mock_db):
        """測試依機關查詢 - 作為發文機關"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=1)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_agency(agency_id=5, as_sender=True)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_agency_as_receiver(self, repo, mock_db):
        """測試依機關查詢 - 作為受文機關"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_agency(agency_id=5, as_sender=False)

        assert len(result) == 1


class TestDocumentRepositorySearch:
    """DocumentRepository 搜尋功能測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return DocumentRepository(mock_db)

    @pytest.mark.asyncio
    async def test_search_documents(self, repo, mock_db):
        """測試搜尋公文"""
        mock_docs = [
            MagicMock(spec=OfficialDocument, id=1, subject="桃園市政府函"),
            MagicMock(spec=OfficialDocument, id=2, subject="桃園市工務局函"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.search("桃園", repo.SEARCH_FIELDS)

        assert len(result) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents_empty_term(self, repo, mock_db):
        """測試搜尋 - 空搜尋詞回傳全部"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=i) for i in range(5)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.search("", repo.SEARCH_FIELDS)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_search_documents_no_match(self, repo, mock_db):
        """測試搜尋 - 無匹配結果"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await repo.search("不存在的關鍵字", repo.SEARCH_FIELDS)

        assert len(result) == 0


class TestDocumentRepositoryFilterDocuments:
    """DocumentRepository 進階篩選測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return DocumentRepository(mock_db)

    @pytest.mark.asyncio
    async def test_filter_documents_all_params(self, repo, mock_db):
        """測試進階篩選 - 所有參數"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=1)]

        # filter_documents 呼叫 2 次 execute: 一次計數, 一次資料
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_docs

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        documents, total = await repo.filter_documents(
            doc_type="收文",
            status="待處理",
            category="收文",
            project_id=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            search="桃園",
            skip=0,
            limit=20,
        )

        assert len(documents) == 1
        assert total == 1
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_filter_documents_no_params(self, repo, mock_db):
        """測試進階篩選 - 無篩選條件"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=i) for i in range(5)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_docs

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        documents, total = await repo.filter_documents()

        assert len(documents) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_filter_documents_sort_asc(self, repo, mock_db):
        """測試進階篩選 - 升序排列"""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        documents, total = await repo.filter_documents(
            sort_by="doc_date",
            sort_order="asc",
        )

        assert total == 0
        assert documents == []


class TestDocumentRepositorySerialNumber:
    """DocumentRepository 流水序號測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return DocumentRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_next_serial_number_first(self, repo, mock_db):
        """測試取得下一個流水序號 - 首次建立"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_next_serial_number("收文", year=2026)

        assert result == "R0001"

    @pytest.mark.asyncio
    async def test_get_next_serial_number_increment(self, repo, mock_db):
        """測試取得下一個流水序號 - 遞增"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = "R0005"
        mock_db.execute.return_value = mock_result

        result = await repo.get_next_serial_number("收文", year=2026)

        assert result == "R0006"

    @pytest.mark.asyncio
    async def test_get_next_serial_number_outgoing(self, repo, mock_db):
        """測試取得下一個流水序號 - 發文使用 S 前綴"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = "S0010"
        mock_db.execute.return_value = mock_result

        result = await repo.get_next_serial_number("發文", year=2026)

        assert result == "S0011"

    @pytest.mark.asyncio
    async def test_check_serial_exists(self, repo, mock_db):
        """測試檢查流水序號是否存在"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        result = await repo.check_serial_exists("R0001")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_serial_not_exists(self, repo, mock_db):
        """測試檢查流水序號不存在"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await repo.check_serial_exists("R9999")

        assert result is False


class TestDocumentRepositoryAttachments:
    """DocumentRepository 附件查詢測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return DocumentRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_attachments(self, repo, mock_db):
        """測試取得公文附件列表"""
        mock_attachments = [
            MagicMock(spec=DocumentAttachment, id=1),
            MagicMock(spec=DocumentAttachment, id=2),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_attachments
        mock_db.execute.return_value = mock_result

        result = await repo.get_attachments(document_id=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_attachment_count(self, repo, mock_db):
        """測試取得公文附件數量"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db.execute.return_value = mock_result

        result = await repo.get_attachment_count(document_id=1)

        assert result == 3

    @pytest.mark.asyncio
    async def test_get_attachment_count_zero(self, repo, mock_db):
        """測試取得公文附件數量 - 無附件"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await repo.get_attachment_count(document_id=999)

        assert result == 0
