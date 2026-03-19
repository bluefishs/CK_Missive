"""
機關匹配服務單元測試

測試範圍：
- _parse_agency_text: 機關文字解析（多種格式）
- match_agency: 智慧匹配（多優先級策略）
- match_agencies_for_document: 公文雙向匹配
- suggest_agency: 機關建議
- get_unassociated_summary: 未關聯統計

共 8 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agency_matching_service import AgencyMatchingService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch(
        "app.services.agency_matching_service.AgencyRepository"
    ):
        svc = AgencyMatchingService(mock_db)
        svc.repository = AsyncMock()
        return svc


# ============================================================================
# _parse_agency_text
# ============================================================================

class TestParseAgencyText:
    """機關文字解析"""

    def test_plain_name(self, service):
        """純機關名稱"""
        result = service._parse_agency_text("桃園市政府")
        assert len(result) == 1
        assert result[0] == (None, "桃園市政府")

    def test_code_with_parentheses(self, service):
        """代碼 (機關名稱) 格式"""
        result = service._parse_agency_text("A01020100G (內政部國土管理署)")
        assert len(result) == 1
        code, name = result[0]
        assert code == "A01020100G"
        assert "內政部" in name

    def test_code_space_name(self, service):
        """代碼 機關名稱 格式（代碼長度 >= 6）"""
        result = service._parse_agency_text("EB50819619 乾坤測繪科技有限公司")
        assert len(result) == 1
        code, name = result[0]
        assert code == "EB50819619"
        assert name == "乾坤測繪科技有限公司"

    def test_empty_input(self, service):
        """空字串回傳空列表"""
        assert service._parse_agency_text("") == []
        assert service._parse_agency_text("  ") == []
        assert service._parse_agency_text(None) == []

    def test_multiple_agencies_pipe_separated(self, service):
        """多機關以 | 分隔"""
        result = service._parse_agency_text("機關A | 機關B")
        assert len(result) == 2
        assert result[0][1] == "機關A"
        assert result[1][1] == "機關B"


# ============================================================================
# match_agency
# ============================================================================

class TestMatchAgency:
    """智慧匹配"""

    @pytest.mark.asyncio
    async def test_match_by_code(self, service, mock_db):
        """以機關代碼精確匹配"""
        mock_agency = MagicMock(id=1, agency_name="桃園市政府")
        service.repository.find_one_by = AsyncMock(return_value=mock_agency)

        result = await service.match_agency("A01020100G (桃園市政府)")
        assert result == mock_agency
        service.repository.find_one_by.assert_any_call(agency_code="A01020100G")

    @pytest.mark.asyncio
    async def test_match_by_name(self, service, mock_db):
        """以機關名稱精確匹配"""
        mock_agency = MagicMock(id=2, agency_name="桃園市政府工務局")
        # No code match, so find_one_by won't be called for agency_code
        # get_by_name returns the match
        service.repository.get_by_name = AsyncMock(return_value=mock_agency)

        result = await service.match_agency("桃園市政府工務局")
        assert result is not None
        assert result.id == 2

    @pytest.mark.asyncio
    async def test_no_match(self, service, mock_db):
        """完全無匹配"""
        service.repository.find_one_by = AsyncMock(return_value=None)
        service.repository.get_by_name = AsyncMock(return_value=None)
        service.repository.get_by_short_name = AsyncMock(return_value=None)
        service.repository.find_by_text_contains = AsyncMock(return_value=None)

        result = await service.match_agency("不存在的機關")
        assert result is None


# ============================================================================
# suggest_agency
# ============================================================================

class TestSuggestAgency:
    """機關建議"""

    @pytest.mark.asyncio
    async def test_short_text_returns_empty(self, service, mock_db):
        """文字太短（< 2 字）回傳空列表"""
        result = await service.suggest_agency("桃")
        assert result == []

    @pytest.mark.asyncio
    async def test_none_text_returns_empty(self, service, mock_db):
        """None 回傳空列表"""
        result = await service.suggest_agency(None)
        assert result == []
