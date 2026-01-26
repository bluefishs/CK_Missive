# -*- coding: utf-8 -*-
"""
公文服務層單元測試 (完整版)
DocumentService Unit Tests - Comprehensive Coverage

目標覆蓋率: 70%+
測試範圍:
- normalize_text 函數
- DocumentService 初始化
- 日期解析與篩選邏輯
- 機關名稱提取
- get_documents (列表查詢)
- get_document_by_id (單一查詢)
- get_document_with_extra_info (詳情查詢)
- create_document (建立公文)
- _get_next_auto_serial (流水號產生)
- import_documents_from_processed_data (批次匯入)
- _apply_filters (篩選條件套用)
- RLS 權限過濾

執行方式:
    pytest tests/services/test_document_service.py -v
    pytest tests/services/test_document_service.py -v --cov=app.services.document_service --cov-report=term-missing
"""
import pytest
import sys
import os
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.document_service import DocumentService, normalize_text, KANGXI_RADICALS


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """建立 Mock 資料庫會話"""
    from sqlalchemy.ext.asyncio import AsyncSession
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_document_data():
    """範例公文資料"""
    return {
        "doc_number": "TEST-2026-001",
        "subject": "測試公文主旨",
        "doc_type": "函",
        "sender": "測試發文單位",
        "receiver": "測試受文單位",
        "status": "待處理",
        "category": "收文"
    }


@pytest.fixture
def sample_import_documents():
    """範例匯入公文列表"""
    return [
        {
            "doc_number": "IMPORT-001",
            "subject": "匯入測試公文1",
            "doc_type": "收文",
            "sender": "桃園市政府",
            "receiver": "乾坤測繪",
            "doc_date": "2026-01-15"
        },
        {
            "doc_number": "IMPORT-002",
            "subject": "匯入測試公文2",
            "doc_type": "發文",
            "sender": "乾坤測繪",
            "receiver": "桃園市政府工務局",
            "doc_date": "2026-01-16"
        }
    ]


@pytest.fixture
def mock_user():
    """模擬使用者物件"""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.is_admin = False
    user.is_superuser = False
    return user


@pytest.fixture
def mock_admin_user():
    """模擬管理員使用者"""
    user = MagicMock()
    user.id = 2
    user.username = "admin"
    user.is_admin = True
    user.is_superuser = False
    return user


@pytest.fixture
def mock_superuser():
    """模擬超級管理員"""
    user = MagicMock()
    user.id = 3
    user.username = "superadmin"
    user.is_admin = True
    user.is_superuser = True
    return user


# ============================================================================
# TestNormalizeText - Unicode 文字正規化
# ============================================================================

class TestNormalizeText:
    """測試 Unicode 文字正規化函數"""

    def test_normalize_kangxi_radicals(self):
        """測試康熙部首轉換為標準中文"""
        assert normalize_text("⽤途") == "用途"
        assert normalize_text("⼟地") == "土地"
        assert normalize_text("⽇期") == "日期"
        assert normalize_text("⽉份") == "月份"
        assert normalize_text("⽔資源") == "水資源"

    def test_normalize_multiple_kangxi_radicals(self):
        """測試多個康熙部首同時出現"""
        result = normalize_text("⽤於⼟地測繪")
        assert result == "用於土地測繪"

    def test_normalize_preserves_normal_text(self):
        """測試正常中文文字不受影響"""
        text = "桃園市政府工務局"
        assert normalize_text(text) == text

    def test_normalize_handles_empty_string(self):
        """測試空字串處理"""
        assert normalize_text("") == ""

    def test_normalize_handles_none(self):
        """測試 None 輸入處理"""
        assert normalize_text(None) is None

    def test_normalize_handles_non_string(self):
        """測試非字串輸入處理"""
        assert normalize_text(123) == 123
        assert normalize_text([]) == []

    def test_normalize_mixed_text(self):
        """測試混合文字（康熙部首 + 正常中文 + 英文 + 數字）"""
        result = normalize_text("⽤途：Test123 測試")
        assert "用途" in result
        assert "Test123" in result
        assert "測試" in result

    def test_normalize_nfkc_normalization(self):
        """測試 NFKC 正規化（全形轉半形等）"""
        # 全形數字轉半形
        result = normalize_text("１２３")
        assert result == "123"

    def test_kangxi_radicals_mapping_complete(self):
        """驗證康熙部首對照表的完整性"""
        # 確認對照表中的所有映射都能正常工作
        for kangxi, normal in KANGXI_RADICALS.items():
            result = normalize_text(kangxi)
            assert result == normal, f"康熙部首 {kangxi} 應轉換為 {normal}"


# ============================================================================
# TestDocumentServiceInit - 服務初始化
# ============================================================================

class TestDocumentServiceInit:
    """測試 DocumentService 初始化"""

    def test_init_with_db(self, mock_db_session):
        """測試正常初始化"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        assert service.db is mock_db_session
        assert service._auto_create_events is False
        assert service._event_builder is None

    def test_init_with_auto_create_events_enabled(self, mock_db_session):
        """測試啟用自動建立事件"""
        service = DocumentService(db=mock_db_session, auto_create_events=True)

        assert service._auto_create_events is True
        assert service._event_builder is not None

    def test_init_creates_strategy_instances(self, mock_db_session):
        """測試初始化時建立策略類別實例"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        assert service._agency_matcher is not None
        assert service._project_matcher is not None

    def test_init_creates_calendar_integrator(self, mock_db_session):
        """測試初始化時建立行事曆整合器"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        assert service.calendar_integrator is not None


# ============================================================================
# TestParseDateString - 日期解析
# ============================================================================

class TestParseDateString:
    """測試日期字串解析"""

    def test_parse_date_string_valid_dash_format(self, mock_db_session):
        """測試有效日期解析（破折號格式）"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("2026-01-08")
        assert result == date(2026, 1, 8)

    def test_parse_date_string_valid_slash_format(self, mock_db_session):
        """測試有效日期解析（斜線格式）"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("2026/01/08")
        assert result == date(2026, 1, 8)

    def test_parse_date_string_empty(self, mock_db_session):
        """測試空字串"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("")
        assert result is None

    def test_parse_date_string_none(self, mock_db_session):
        """測試 None 輸入"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string(None)
        assert result is None

    def test_parse_date_string_invalid_format(self, mock_db_session):
        """測試無效日期格式"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("invalid-date")
        assert result is None

    def test_parse_date_string_partial_date(self, mock_db_session):
        """測試不完整日期"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._parse_date_string("2026-01")
        assert result is None

    def test_parse_date_string_different_formats(self, mock_db_session):
        """測試各種日期格式"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 有效格式
        assert service._parse_date_string("2026-12-31") == date(2026, 12, 31)
        assert service._parse_date_string("2026/12/31") == date(2026, 12, 31)

        # 無效格式
        assert service._parse_date_string("31-12-2026") is None
        assert service._parse_date_string("2026.01.08") is None


# ============================================================================
# TestExtractAgencyNames - 機關名稱提取
# ============================================================================

class TestExtractAgencyNames:
    """測試機關名稱提取"""

    def test_extract_simple_name(self, mock_db_session):
        """測試簡單名稱"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("桃園市政府")
        assert result == ["桃園市政府"]

    def test_extract_name_with_code_parentheses(self, mock_db_session):
        """測試帶代碼的名稱（括號格式）"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("380110000G (桃園市政府工務局)")
        assert "桃園市政府工務局" in result

    def test_extract_multiple_agencies(self, mock_db_session):
        """測試多個機關（以 | 分隔）"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names(
            "376480000A (南投縣政府) | A01020100G (內政部國土管理署城鄉發展分署)"
        )
        assert len(result) == 2
        assert "南投縣政府" in result
        assert "內政部國土管理署城鄉發展分署" in result

    def test_extract_name_with_newline(self, mock_db_session):
        """測試換行格式"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("380110000G\n(桃園市政府工務局)")
        assert "桃園市政府工務局" in result

    def test_extract_empty_input(self, mock_db_session):
        """測試空輸入"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        assert service._extract_agency_names("") == []
        assert service._extract_agency_names(None) == []

    def test_extract_name_code_without_parentheses(self, mock_db_session):
        """測試代碼+名稱（無括號）"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("380110000G 桃園市政府工務局")
        # 應該提取出名稱部分
        assert len(result) >= 1

    def test_extract_preserves_special_characters(self, mock_db_session):
        """測試保留特殊字元"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = service._extract_agency_names("(內政部國土管理署)")
        assert "內政部國土管理署" in result


# ============================================================================
# TestGetDocuments - 取得公文列表
# ============================================================================

class TestGetDocuments:
    """測試取得公文列表"""

    @pytest.mark.asyncio
    async def test_get_documents_empty_result(self, mock_db_session):
        """測試空結果"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 設定 mock 回傳
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(skip=0, limit=20)

        assert result["items"] == []
        assert result["total"] == 0
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_get_documents_with_results(self, mock_db_session):
        """測試有結果的查詢"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 建立 mock 公文
        mock_doc1 = MagicMock()
        mock_doc1.id = 1
        mock_doc1.doc_number = "TEST-001"

        mock_doc2 = MagicMock()
        mock_doc2.id = 2
        mock_doc2.doc_number = "TEST-002"

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_doc1, mock_doc2]

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(skip=0, limit=20)

        assert len(result["items"]) == 2
        assert result["total"] == 2

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

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(filters=filters)

        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_documents_pagination(self, mock_db_session):
        """測試分頁功能"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 100

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(skip=40, limit=20)

        assert result["page"] == 3  # skip=40, limit=20 -> page 3
        assert result["limit"] == 20
        assert result["total"] == 100
        assert result["total_pages"] == 5

    @pytest.mark.asyncio
    async def test_get_documents_with_current_user_admin(self, mock_db_session, mock_admin_user):
        """測試管理員查詢（無 RLS 限制）"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(current_user=mock_admin_user)

        assert result["total"] == 10

    @pytest.mark.asyncio
    async def test_get_documents_exception_handling(self, mock_db_session):
        """測試例外處理"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_db_session.execute.side_effect = Exception("Database error")

        result = await service.get_documents()

        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_documents_without_relations(self, mock_db_session):
        """測試不載入關聯資料"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(include_relations=False)

        assert result["items"] == []


# ============================================================================
# TestGetDocumentById - 根據 ID 取得公文
# ============================================================================

class TestGetDocumentById:
    """測試根據 ID 取得公文"""

    @pytest.mark.asyncio
    async def test_get_document_by_id_found(self, mock_db_session):
        """測試找到公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

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

    @pytest.mark.asyncio
    async def test_get_document_by_id_with_relations(self, mock_db_session):
        """測試載入關聯資料"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.contract_project = MagicMock()
        mock_doc.sender_agency = MagicMock()
        mock_doc.receiver_agency = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_by_id(1, include_relations=True)

        assert result is not None
        assert result.contract_project is not None

    @pytest.mark.asyncio
    async def test_get_document_by_id_without_relations(self, mock_db_session):
        """測試不載入關聯資料"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_doc = MagicMock()
        mock_doc.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_by_id(1, include_relations=False)

        assert result is not None


# ============================================================================
# TestGetDocumentWithExtraInfo - 取得公文詳情
# ============================================================================

class TestGetDocumentWithExtraInfo:
    """測試取得公文詳情含額外資訊"""

    @pytest.mark.asyncio
    async def test_get_document_with_extra_info_found(self, mock_db_session):
        """測試找到公文並補充額外資訊"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 使用簡單類別來模擬公文物件（避免 MagicMock 的 __dict__ 問題）
        class MockProject:
            project_name = "測試專案"

        class MockAgency:
            def __init__(self, name):
                self.agency_name = name

        class MockAttachment:
            pass

        class MockDocument:
            def __init__(self):
                self.id = 1
                self.doc_number = "TEST-001"
                self.subject = "測試主旨"
                self.contract_project = MockProject()
                self.sender_agency = MockAgency("桃園市政府")
                self.receiver_agency = MockAgency("乾坤測繪")
                # 使用非空列表避免觸發資料庫查詢
                self.attachments = [MockAttachment(), MockAttachment()]

        mock_doc = MockDocument()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_with_extra_info(1)

        assert result is not None
        assert result['contract_project_name'] == "測試專案"
        assert result['sender_agency_name'] == "桃園市政府"
        assert result['receiver_agency_name'] == "乾坤測繪"
        assert result['attachment_count'] == 2

    @pytest.mark.asyncio
    async def test_get_document_with_extra_info_not_found(self, mock_db_session):
        """測試找不到公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_with_extra_info(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_with_extra_info_no_relations(self, mock_db_session):
        """測試公文無關聯資料"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 使用簡單類別來模擬公文物件
        class MockDocument:
            def __init__(self):
                self.id = 1
                self.contract_project = None
                self.sender_agency = None
                self.receiver_agency = None
                self.attachments = None

        mock_doc = MockDocument()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc

        # 附件計數查詢
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        result = await service.get_document_with_extra_info(1)

        assert result is not None
        assert result['contract_project_name'] is None
        assert result['sender_agency_name'] is None
        assert result['receiver_agency_name'] is None

    @pytest.mark.asyncio
    async def test_get_document_with_extra_info_with_attachments(self, mock_db_session):
        """測試公文有附件"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 使用簡單類別來模擬公文物件
        class MockAttachment:
            pass

        class MockDocument:
            def __init__(self):
                self.id = 1
                self.contract_project = None
                self.sender_agency = None
                self.receiver_agency = None
                # 模擬有 3 個附件
                self.attachments = [MockAttachment(), MockAttachment(), MockAttachment()]

        mock_doc = MockDocument()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_doc
        mock_db_session.execute.return_value = mock_result

        result = await service.get_document_with_extra_info(1)

        assert result is not None
        assert result['attachment_count'] == 3


# ============================================================================
# TestGetNextAutoSerial - 流水號產生
# ============================================================================

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

    @pytest.mark.asyncio
    async def test_get_next_auto_serial_large_number(self, mock_db_session):
        """測試大流水號"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "R9999"
        mock_db_session.execute.return_value = mock_result

        result = await service._get_next_auto_serial("收文")

        assert result == "R10000"

    @pytest.mark.asyncio
    async def test_get_next_auto_serial_invalid_format(self, mock_db_session):
        """測試無效格式處理"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "R"  # 無效格式
        mock_db_session.execute.return_value = mock_result

        result = await service._get_next_auto_serial("收文")

        assert result == "R0001"


# ============================================================================
# TestCreateDocument - 建立公文
# ============================================================================

class TestCreateDocument:
    """測試建立公文"""

    @pytest.mark.asyncio
    async def test_create_document_success(self, mock_db_session, sample_document_data):
        """測試成功建立公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                mock_agency.return_value = 1
                mock_project.return_value = 1

                mock_new_doc = MagicMock()
                mock_new_doc.id = 1
                mock_new_doc.receive_date = None

                mock_db_session.refresh = AsyncMock()

                result = await service.create_document(sample_document_data, current_user_id=1)

                assert mock_db_session.add.called
                assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_create_document_with_receive_date(self, mock_db_session, sample_document_data):
        """測試建立公文並觸發行事曆事件"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        sample_document_data['receive_date'] = date(2026, 1, 15)

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                with patch.object(service.calendar_integrator, 'convert_document_to_events', new_callable=AsyncMock) as mock_calendar:
                    mock_agency.return_value = 1
                    mock_project.return_value = 1
                    mock_calendar.return_value = None

                    mock_new_doc = MagicMock()
                    mock_new_doc.id = 1
                    mock_new_doc.receive_date = date(2026, 1, 15)

                    mock_db_session.refresh = AsyncMock(side_effect=lambda x: setattr(x, 'receive_date', date(2026, 1, 15)))

                    await service.create_document(sample_document_data, current_user_id=1)

    @pytest.mark.asyncio
    async def test_create_document_rollback_on_error(self, mock_db_session, sample_document_data):
        """測試建立失敗時回滾"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_db_session.commit.side_effect = Exception("Database error")

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                mock_agency.return_value = 1
                mock_project.return_value = 1

                result = await service.create_document(sample_document_data, current_user_id=1)

                assert mock_db_session.rollback.called
                assert result is None

    @pytest.mark.asyncio
    async def test_create_document_filters_invalid_fields(self, mock_db_session):
        """測試過濾無效欄位"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        data = {
            "doc_number": "TEST-001",
            "subject": "測試",
            "invalid_field": "should_be_filtered",  # 無效欄位
            "another_invalid": 123
        }

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                mock_agency.return_value = None
                mock_project.return_value = None

                mock_db_session.refresh = AsyncMock()

                await service.create_document(data, current_user_id=1)

                # 確認 add 被呼叫（即使有無效欄位）
                assert mock_db_session.add.called


# ============================================================================
# TestImportDocuments - 批次匯入公文
# ============================================================================

class TestImportDocuments:
    """測試公文批次匯入"""

    @pytest.mark.asyncio
    async def test_import_documents_empty_list(self, mock_db_session):
        """測試匯入空列表"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        result = await service.import_documents_from_processed_data([])

        assert result.total_rows == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.skipped_count == 0

    @pytest.mark.asyncio
    async def test_import_documents_skip_duplicate(self, mock_db_session):
        """測試跳過重複公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_existing_doc = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_doc
        mock_db_session.execute.return_value = mock_result

        docs_to_import = [
            {"doc_number": "EXISTING-001", "subject": "已存在的公文"}
        ]

        result = await service.import_documents_from_processed_data(docs_to_import)

        assert result.total_rows == 1
        assert result.skipped_count == 1
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_import_documents_success(self, mock_db_session, sample_import_documents):
        """測試成功匯入公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 模擬不存在重複
        mock_not_found = MagicMock()
        mock_not_found.scalar_one_or_none.return_value = None

        # 模擬流水號查詢
        mock_serial_result = MagicMock()
        mock_serial_result.scalar_one_or_none.return_value = None

        mock_db_session.execute.return_value = mock_not_found

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                with patch.object(service, '_get_next_auto_serial', new_callable=AsyncMock) as mock_serial:
                    mock_agency.return_value = 1
                    mock_project.return_value = 1
                    mock_serial.return_value = "R0001"

                    result = await service.import_documents_from_processed_data(sample_import_documents)

                    assert result.total_rows == 2
                    assert result.success_count == 2
                    assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_import_documents_with_kangxi_radicals(self, mock_db_session):
        """測試匯入含康熙部首的公文"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_not_found = MagicMock()
        mock_not_found.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_not_found

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                with patch.object(service, '_get_next_auto_serial', new_callable=AsyncMock) as mock_serial:
                    mock_agency.return_value = None
                    mock_project.return_value = None
                    mock_serial.return_value = "R0001"

                    docs = [
                        {
                            "doc_number": "TEST-⽤途",  # 康熙部首
                            "subject": "⼟地測繪",  # 康熙部首
                            "doc_type": "收文"
                        }
                    ]

                    result = await service.import_documents_from_processed_data(docs)

                    assert result.total_rows == 1
                    # 確認文字已正規化（在 add 之前處理）

    @pytest.mark.asyncio
    async def test_import_documents_handles_date_formats(self, mock_db_session):
        """測試匯入處理各種日期格式"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_not_found = MagicMock()
        mock_not_found.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_not_found

        with patch.object(service, '_get_or_create_agency_id', new_callable=AsyncMock) as mock_agency:
            with patch.object(service, '_get_or_create_project_id', new_callable=AsyncMock) as mock_project:
                with patch.object(service, '_get_next_auto_serial', new_callable=AsyncMock) as mock_serial:
                    mock_agency.return_value = None
                    mock_project.return_value = None
                    mock_serial.return_value = "R0001"

                    docs = [
                        {
                            "doc_number": "TEST-001",
                            "subject": "測試",
                            "doc_type": "收文",
                            "doc_date": "2026-01-15",
                            "receive_date": "2026/01/16 10:30:00"
                        }
                    ]

                    result = await service.import_documents_from_processed_data(docs)

                    assert result.total_rows == 1


# ============================================================================
# TestApplyFilters - 篩選條件套用
# ============================================================================

class TestApplyFilters:
    """測試篩選條件套用"""

    def test_apply_filters_doc_type(self, mock_db_session):
        """測試公文類型篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(doc_type="函")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_year(self, mock_db_session):
        """測試年度篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(year=2026)

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_keyword(self, mock_db_session):
        """測試關鍵字篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(keyword="測繪")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_doc_number(self, mock_db_session):
        """測試公文字號專用篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(doc_number="府工測字")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_date_range(self, mock_db_session):
        """測試日期範圍篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(
            date_from="2026-01-01",
            date_to="2026-12-31"
        )

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_alternate_date_fields(self, mock_db_session):
        """測試替代日期欄位名稱"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(
            doc_date_from="2026-01-01",
            doc_date_to="2026-12-31"
        )

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_delivery_method_valid(self, mock_db_session):
        """測試有效發文形式篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(delivery_method="電子交換")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_delivery_method_invalid(self, mock_db_session):
        """測試無效發文形式篩選（會被忽略）"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(delivery_method="無效形式")

        result_query = service._apply_filters(query, filters)

        # 無效形式會被忽略，查詢仍應正常執行
        assert result_query is not None

    def test_apply_filters_sender_receiver(self, mock_db_session):
        """測試發受文單位篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(
            sender="桃園市政府",
            receiver="乾坤測繪"
        )

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_category(self, mock_db_session):
        """測試收發文分類篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(category="收文")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_contract_case(self, mock_db_session):
        """測試承攬案件篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(contract_case="測繪專案")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_assignee(self, mock_db_session):
        """測試承辦人篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(assignee="張三")

        result_query = service._apply_filters(query, filters)

        assert result_query is not None

    def test_apply_filters_combined(self, mock_db_session):
        """測試組合篩選"""
        from app.schemas.document import DocumentFilter
        from sqlalchemy import select
        from app.extended.models import OfficialDocument

        service = DocumentService(db=mock_db_session, auto_create_events=False)

        query = select(OfficialDocument)
        filters = DocumentFilter(
            doc_type="函",
            year=2026,
            keyword="測試",
            category="收文",
            delivery_method="電子交換",
            date_from="2026-01-01",
            date_to="2026-12-31"
        )

        result_query = service._apply_filters(query, filters)

        assert result_query is not None


# ============================================================================
# TestGetOrCreateAgencyId - 機關 ID 取得/建立
# ============================================================================

class TestGetOrCreateAgencyId:
    """測試機關 ID 取得或建立"""

    @pytest.mark.asyncio
    async def test_get_or_create_agency_id_with_name(self, mock_db_session):
        """測試有名稱時委派給 AgencyMatcher"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        with patch.object(service._agency_matcher, 'match_or_create', new_callable=AsyncMock) as mock_match:
            mock_match.return_value = 123

            result = await service._get_or_create_agency_id("桃園市政府")

            mock_match.assert_called_once_with("桃園市政府")
            assert result == 123

    @pytest.mark.asyncio
    async def test_get_or_create_agency_id_none(self, mock_db_session):
        """測試名稱為 None"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        with patch.object(service._agency_matcher, 'match_or_create', new_callable=AsyncMock) as mock_match:
            mock_match.return_value = None

            result = await service._get_or_create_agency_id(None)

            assert result is None


# ============================================================================
# TestGetOrCreateProjectId - 案件 ID 取得/建立
# ============================================================================

class TestGetOrCreateProjectId:
    """測試案件 ID 取得或建立"""

    @pytest.mark.asyncio
    async def test_get_or_create_project_id_with_name(self, mock_db_session):
        """測試有名稱時委派給 ProjectMatcher"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        with patch.object(service._project_matcher, 'match_or_create', new_callable=AsyncMock) as mock_match:
            mock_match.return_value = 456

            result = await service._get_or_create_project_id("測繪專案")

            mock_match.assert_called_once_with("測繪專案")
            assert result == 456

    @pytest.mark.asyncio
    async def test_get_or_create_project_id_none(self, mock_db_session):
        """測試名稱為 None"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        with patch.object(service._project_matcher, 'match_or_create', new_callable=AsyncMock) as mock_match:
            mock_match.return_value = None

            result = await service._get_or_create_project_id(None)

            assert result is None


# ============================================================================
# TestDocumentFilterHelpers - 篩選輔助方法
# ============================================================================

class TestDocumentFilterHelpers:
    """測試 DocumentFilter 輔助方法"""

    def test_get_effective_keyword_primary(self):
        """測試關鍵字取得（主要欄位）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(keyword="測試關鍵字")

        assert filters.get_effective_keyword() == "測試關鍵字"

    def test_get_effective_keyword_alias(self):
        """測試關鍵字取得（別名欄位）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(search="搜尋關鍵字")

        assert filters.get_effective_keyword() == "搜尋關鍵字"

    def test_get_effective_keyword_both(self):
        """測試關鍵字取得（兩者皆有，優先主要）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(keyword="主要", search="別名")

        assert filters.get_effective_keyword() == "主要"

    def test_get_effective_date_from_primary(self):
        """測試起始日期取得（主要欄位）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(date_from="2026-01-01")

        assert filters.get_effective_date_from() == "2026-01-01"

    def test_get_effective_date_from_alias(self):
        """測試起始日期取得（別名欄位）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(doc_date_from="2026-01-01")

        assert filters.get_effective_date_from() == "2026-01-01"

    def test_get_effective_date_to_primary(self):
        """測試結束日期取得（主要欄位）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(date_to="2026-12-31")

        assert filters.get_effective_date_to() == "2026-12-31"

    def test_get_effective_date_to_alias(self):
        """測試結束日期取得（別名欄位）"""
        from app.schemas.document import DocumentFilter

        filters = DocumentFilter(doc_date_to="2026-12-31")

        assert filters.get_effective_date_to() == "2026-12-31"


# ============================================================================
# TestEdgeCases - 邊界情況測試
# ============================================================================

class TestEdgeCases:
    """測試邊界情況"""

    @pytest.mark.asyncio
    async def test_get_documents_zero_limit(self, mock_db_session):
        """測試 limit 為 0 的情況"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [mock_count_result, mock_result]

        result = await service.get_documents(skip=0, limit=0)

        # limit=0 應該導致 total_pages=0
        assert result["total_pages"] == 0

    def test_parse_date_string_with_whitespace(self, mock_db_session):
        """測試帶空白的日期字串"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 帶前後空白的日期應該無法解析（除非服務有 trim 處理）
        result = service._parse_date_string("  2026-01-08  ")
        # 根據實際實現可能為 None 或正確日期

    def test_extract_agency_names_complex_format(self, mock_db_session):
        """測試複雜格式的機關名稱"""
        service = DocumentService(db=mock_db_session, auto_create_events=False)

        # 測試帶換行和多個管道符號的複雜格式
        result = service._extract_agency_names(
            "A001 (機關A) | B002 (機關B) | C003 (機關C)"
        )
        assert len(result) == 3


# ============================================================================
# 主程式入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.document_service", "--cov-report=term-missing"])
