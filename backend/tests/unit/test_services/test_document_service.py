# -*- coding: utf-8 -*-
"""
公文服務層單元測試
DocumentService Unit Tests

使用 Mock 資料庫測試 DocumentService 的核心方法

執行方式:
    pytest tests/unit/test_services/test_document_service.py -v
"""
import pytest
import sys
import os
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.document_service import DocumentService, normalize_text


class TestNormalizeText:
    """測試 Unicode 文字正規化"""

    def test_normalize_kangxi_radicals(self):
        """測試康熙部首轉換"""
        # 康熙部首 -> 標準中文
        assert normalize_text("⽤途") == "用途"
        assert normalize_text("⼟地") == "土地"
        assert normalize_text("⽇期") == "日期"

    def test_normalize_preserves_normal_text(self):
        """測試正常文字不受影響"""
        text = "桃園市政府工務局"
        assert normalize_text(text) == text

    def test_normalize_handles_empty_input(self):
        """測試空輸入處理"""
        assert normalize_text("") == ""
        assert normalize_text(None) is None

    def test_normalize_handles_mixed_text(self):
        """測試混合文字"""
        result = normalize_text("⽤於⼟地測繪")
        assert "用於土地測繪" == result


class TestDocumentServiceInit:
    """測試 DocumentService 初始化"""

    def test_init_with_db(self, mock_db_session):
        """測試正常初始化"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        assert service.db is mock_db_session
        assert service._auto_create_events is False

    def test_init_with_auto_create_events(self, mock_db_session):
        """測試啟用自動建立事件"""
        service = DocumentService(db=mock_db_session, auto_create_events=True)

        assert service._auto_create_events is True
        assert service._event_builder is not None


class TestDocumentServiceFilters:
    """測試公文服務篩選邏輯"""

    def test_parse_date_string_valid(self, mock_db_session):
        """測試有效日期解析"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("2026-01-08")
        assert result == date(2026, 1, 8)

    def test_parse_date_string_with_slash(self, mock_db_session):
        """測試斜線分隔日期"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("2026/01/08")
        assert result == date(2026, 1, 8)

    def test_parse_date_string_empty(self, mock_db_session):
        """測試空日期"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("")
        assert result is None

    def test_parse_date_string_invalid(self, mock_db_session):
        """測試無效日期"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("invalid-date")
        assert result is None


class TestExtractAgencyNames:
    """測試機關名稱提取"""

    def test_extract_simple_name(self, mock_db_session):
        """測試簡單名稱提取"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("桃園市政府")
        assert result == ["桃園市政府"]

    def test_extract_name_with_code(self, mock_db_session):
        """測試帶代碼的名稱"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("380110000G (桃園市政府工務局)")
        assert "桃園市政府工務局" in result

    def test_extract_multiple_agencies(self, mock_db_session):
        """測試多個機關"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names(
            "376480000A (南投縣政府) | A01020100G (內政部國土管理署城鄉發展分署)"
        )
        assert len(result) == 2
        assert "南投縣政府" in result
        assert "內政部國土管理署城鄉發展分署" in result

    def test_extract_empty_input(self, mock_db_session):
        """測試空輸入"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("")
        assert result == []

        result = service._extract_agency_names(None)
        assert result == []


class TestGetDocuments:
    """測試取得公文列表"""

    @pytest.mark.asyncio
    async def test_get_documents_empty_result(self, mock_db_session):
        """測試空結果"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 設定 mock 回傳空結果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # 計數查詢 mock
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(skip=0, limit=20)

        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_documents_with_filters(self, mock_db_session):
        """測試帶有篩選條件"""
        from app.schemas.document import DocumentFilter

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        filters = DocumentFilter(
            doc_type="函",
            year=2026,
            keyword="測試"
        )

        # 設定 mock
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(filters=filters)

        # 確認 execute 被呼叫（表示查詢有執行）
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_documents_pagination(self, mock_db_session):
        """測試分頁參數"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 100
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(skip=20, limit=20)

        # 確認分頁資訊正確
        assert result["page"] == 2  # skip=20, limit=20 -> page 2
        assert result["limit"] == 20


class TestGetDocumentById:
    """測試根據 ID 取得公文"""

    @pytest.mark.asyncio
    async def test_get_document_by_id_found(self, mock_db_session):
        """測試找到公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 建立 mock 公文
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.doc_number = "TEST-001"
        mock_doc.subject = "測試主旨"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_by_id(1)

        assert result is mock_doc
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_document_by_id_not_found(self, mock_db_session):
        """測試找不到公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_by_id(999)

        assert result is None


class TestGetDocumentWithExtraInfo:
    """測試取得公文詳情含額外資訊"""

    @pytest.mark.asyncio
    async def test_get_document_with_extra_info_found(self, mock_db_session):
        """測試找到公文並補充額外資訊"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 建立 mock 公文
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.doc_number = "TEST-001"
        mock_doc.subject = "測試主旨"
        mock_doc.__dict__ = {
            'id': 1,
            'doc_number': 'TEST-001',
            'subject': '測試主旨'
        }

        # Mock 關聯資料
        mock_project = MagicMock()
        mock_project.project_name = "測試專案"
        mock_doc.contract_project = mock_project

        mock_sender_agency = MagicMock()
        mock_sender_agency.agency_name = "桃園市政府"
        mock_doc.sender_agency = mock_sender_agency

        mock_receiver_agency = MagicMock()
        mock_receiver_agency.agency_name = "乾坤測繪"
        mock_doc.receiver_agency = mock_receiver_agency

        mock_doc.attachments = []

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_with_extra_info(1)

        assert result is not None
        assert result['contract_project_name'] == "測試專案"
        assert result['sender_agency_name'] == "桃園市政府"
        assert result['receiver_agency_name'] == "乾坤測繪"
        assert result['attachment_count'] == 0

    @pytest.mark.asyncio
    async def test_get_document_with_extra_info_not_found(self, mock_db_session):
        """測試找不到公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_with_extra_info(999)

        assert result is None


class TestGetNextAutoSerial:
    """測試流水號產生"""

    @pytest.mark.asyncio
    async def test_get_next_auto_serial_receive_first(self, mock_db_session):
        """測試第一筆收文流水號"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service._get_next_auto_serial("收文")

        assert result == "R0001"

    @pytest.mark.asyncio
    async def test_get_next_auto_serial_send_first(self, mock_db_session):
        """測試第一筆發文流水號"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service._get_next_auto_serial("發文")

        assert result == "S0001"

    @pytest.mark.asyncio
    async def test_get_next_auto_serial_increment(self, mock_db_session):
        """測試流水號遞增"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "R0050"
        mock_db_session.execute.return_value = mock_result

        result = await service._get_next_auto_serial("收文")

        assert result == "R0051"


class TestCreateDocument:
    """測試建立公文"""

    @pytest.mark.asyncio
    async def test_create_document_success(self, mock_db_session, sample_document_data):
        """測試成功建立公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # Mock 相關方法
        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                mock_agency.return_value = 1
                mock_project.return_value = 1

                # Mock 文件建立後
                mock_new_doc = MagicMock()
                mock_new_doc.id = 1
                mock_new_doc.receive_date = None

                mock_db_session.refresh = AsyncMock()

                result = await service.create_document(sample_document_data, current_user_id=1)

                # 確認 add 和 commit 被呼叫
                assert mock_db_session.add.called
                assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_create_document_rollback_on_error(self, mock_db_session, sample_document_data):
        """測試建立失敗時回滾"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # Mock commit 拋出錯誤
        mock_db_session.commit.side_effect = Exception("Database error")

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                mock_agency.return_value = 1
                mock_project.return_value = 1

                result = await service.create_document(sample_document_data, current_user_id=1)

                # 確認 rollback 被呼叫
                assert mock_db_session.rollback.called
                assert result is None


class TestImportDocuments:
    """測試公文匯入"""

    @pytest.mark.asyncio
    async def test_import_documents_empty_list(self, mock_db_session):
        """測試匯入空列表"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = await service.import_documents_from_processed_data([])

        assert result.total_rows == 0
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_import_documents_skip_duplicate(self, mock_db_session):
        """測試跳過重複公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # Mock 找到已存在的公文
        mock_result = MagicMock()
        mock_existing_doc = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_doc
        mock_db_session.execute.return_value = mock_result

        docs_to_import = [
            {"doc_number": "EXISTING-001", "subject": "已存在的公文"}
        ]

        result = await service.import_documents_from_processed_data(docs_to_import)

        assert result.total_rows == 1
        assert result.skipped_count == 1
        assert result.success_count == 0


class TestApplyFilters:
    """測試篩選條件套用"""

    def test_apply_filters_doc_type(self, mock_db_session):
        """測試公文類型篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 建立基本查詢
        from app.extended.models import OfficialDocument
        query = select(OfficialDocument)

        filters = DocumentFilter(doc_type="函")
        result_query = service._apply_filters(query, filters)

        # 確認查詢有被修改（添加了 where 條件）
        assert result_query is not query or str(result_query) != str(query)

    def test_apply_filters_year(self, mock_db_session):
        """測試年度篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        from app.extended.models import OfficialDocument
        query = select(OfficialDocument)

        filters = DocumentFilter(year=2026)
        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_keyword(self, mock_db_session):
        """測試關鍵字篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        from app.extended.models import OfficialDocument
        query = select(OfficialDocument)

        filters = DocumentFilter(keyword="測繪")
        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_date_range(self, mock_db_session):
        """測試日期範圍篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        from app.extended.models import OfficialDocument
        query = select(OfficialDocument)

        filters = DocumentFilter(
            date_from="2026-01-01",
            date_to="2026-12-31"
        )
        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_delivery_method_valid(self, mock_db_session):
        """測試有效發文形式篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        from app.extended.models import OfficialDocument
        query = select(OfficialDocument)

        filters = DocumentFilter(delivery_method="電子交換")
        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_delivery_method_invalid(self, mock_db_session):
        """測試無效發文形式篩選（會被忽略）"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        from app.extended.models import OfficialDocument
        query = select(OfficialDocument)

        # 無效的發文形式會被記錄警告但不會拋出錯誤
        filters = DocumentFilter(delivery_method="無效形式")
        result_query = service._apply_filters(query, filters)

        assert result_query is not None
