# -*- coding: utf-8 -*-
"""
統一案號編碼服務單元測試
CaseCodeService Unit Tests

使用 Mock 資料庫測試案號產生、驗證、解析

執行方式:
    pytest tests/unit/test_services/test_case_code_service.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.case_code_service import (
    CaseCodeService,
    MODULE_CODES,
    PM_CATEGORY_CODES,
    ERP_CATEGORY_CODES,
    DISPATCH_CATEGORY_CODES,
    GENERAL_CATEGORY_CODES,
    MODULE_CATEGORIES,
)


# ============================================================================
# Constants Tests
# ============================================================================

class TestConstants:
    """Module and category constant tests"""

    def test_module_codes(self):
        assert MODULE_CODES["pm"] == "PM"
        assert MODULE_CODES["erp"] == "FN"
        assert MODULE_CODES["dispatch"] == "DP"
        assert MODULE_CODES["general"] == "GN"

    def test_pm_categories(self):
        assert "01" in PM_CATEGORY_CODES
        assert PM_CATEGORY_CODES["01"] == "委辦招標"

    def test_erp_categories(self):
        assert "01" in ERP_CATEGORY_CODES
        assert ERP_CATEGORY_CODES["01"] == "報價單"

    def test_dispatch_categories(self):
        assert "01" in DISPATCH_CATEGORY_CODES

    def test_general_categories(self):
        assert "01" in GENERAL_CATEGORY_CODES

    def test_module_categories_mapping(self):
        assert MODULE_CATEGORIES["PM"] is PM_CATEGORY_CODES
        assert MODULE_CATEGORIES["FN"] is ERP_CATEGORY_CODES
        assert MODULE_CATEGORIES["DP"] is DISPATCH_CATEGORY_CODES
        assert MODULE_CATEGORIES["GN"] is GENERAL_CATEGORY_CODES


# ============================================================================
# generate_case_code() Tests
# ============================================================================

class TestGenerateCaseCode:
    """generate_case_code() tests"""

    @pytest.mark.asyncio
    async def test_generate_pm_code(self, mock_db_session):
        """Format: CK{year}_PM_{cat}_{serial}"""
        service = CaseCodeService(mock_db_session)

        # Mock _find_next_serial to return 1
        service._find_next_serial = AsyncMock(return_value=1)

        result = await service.generate_case_code("pm", 2025, "01")

        assert result == "CK2025_PM_01_001"
        service._find_next_serial.assert_awaited_once_with("CK2025_PM_01_")

    @pytest.mark.asyncio
    async def test_generate_erp_code(self, mock_db_session):
        """Format: CK{year}_FN_{cat}_{serial}"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=5)

        result = await service.generate_case_code("erp", 2025, "01")

        assert result == "CK2025_FN_01_005"

    @pytest.mark.asyncio
    async def test_generate_dispatch_code(self, mock_db_session):
        """Dispatch module code generation"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=1)

        result = await service.generate_case_code("dispatch", 2025, "02")

        assert result == "CK2025_DP_02_001"

    @pytest.mark.asyncio
    async def test_generate_general_code(self, mock_db_session):
        """General module code generation"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=3)

        result = await service.generate_case_code("general", 2025, "01")

        assert result == "CK2025_GN_01_003"

    @pytest.mark.asyncio
    async def test_minguo_year_conversion(self, mock_db_session):
        """Year <= 1911 should be treated as minguo and converted"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=1)

        result = await service.generate_case_code("pm", 114, "01")

        # 114 + 1911 = 2025
        assert result == "CK2025_PM_01_001"

    @pytest.mark.asyncio
    async def test_western_year_preserved(self, mock_db_session):
        """Year > 1911 should be preserved as-is"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=1)

        result = await service.generate_case_code("pm", 2026, "01")

        assert result == "CK2026_PM_01_001"

    @pytest.mark.asyncio
    async def test_unknown_module_raises(self, mock_db_session):
        """Unknown module raises ValueError"""
        service = CaseCodeService(mock_db_session)

        with pytest.raises(ValueError, match="未知模組"):
            await service.generate_case_code("unknown", 2025, "01")

    @pytest.mark.asyncio
    async def test_default_category(self, mock_db_session):
        """Empty category defaults to 01"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=1)

        result = await service.generate_case_code("pm", 2025, "")

        assert "_01_" in result

    @pytest.mark.asyncio
    async def test_case_insensitive_module(self, mock_db_session):
        """Module name is case-insensitive"""
        service = CaseCodeService(mock_db_session)
        service._find_next_serial = AsyncMock(return_value=1)

        result = await service.generate_case_code("PM", 2025, "01")

        assert result.startswith("CK2025_PM_")


# ============================================================================
# _find_next_serial() Tests
# ============================================================================

class TestFindNextSerial:
    """_find_next_serial() cross-table serial search"""

    @pytest.mark.asyncio
    async def test_cross_table_serial(self, mock_db_session):
        """Serial increments across both PM and ERP tables"""
        # First call (PM query) returns CK2025_PM_01_003
        # Second call (ERP query) returns CK2025_PM_01_005
        pm_result = MagicMock()
        pm_result.scalar.return_value = "CK2025_PM_01_003"
        erp_result = MagicMock()
        erp_result.scalar.return_value = "CK2025_PM_01_005"

        mock_db_session.execute = AsyncMock(side_effect=[pm_result, erp_result])

        service = CaseCodeService(mock_db_session)
        result = await service._find_next_serial("CK2025_PM_01_")

        # max(3, 5) + 1 = 6
        assert result == 6

    @pytest.mark.asyncio
    async def test_serial_no_existing(self, mock_db_session):
        """No existing codes means serial = 1"""
        pm_result = MagicMock()
        pm_result.scalar.return_value = None
        erp_result = MagicMock()
        erp_result.scalar.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[pm_result, erp_result])

        service = CaseCodeService(mock_db_session)
        result = await service._find_next_serial("CK2025_PM_01_")

        assert result == 1

    @pytest.mark.asyncio
    async def test_serial_only_pm_exists(self, mock_db_session):
        """Only PM table has existing code"""
        pm_result = MagicMock()
        pm_result.scalar.return_value = "CK2025_PM_01_010"
        erp_result = MagicMock()
        erp_result.scalar.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[pm_result, erp_result])

        service = CaseCodeService(mock_db_session)
        result = await service._find_next_serial("CK2025_PM_01_")

        assert result == 11

    @pytest.mark.asyncio
    async def test_serial_only_erp_exists(self, mock_db_session):
        """Only ERP table has existing code"""
        pm_result = MagicMock()
        pm_result.scalar.return_value = None
        erp_result = MagicMock()
        erp_result.scalar.return_value = "CK2025_PM_01_007"

        mock_db_session.execute = AsyncMock(side_effect=[pm_result, erp_result])

        service = CaseCodeService(mock_db_session)
        result = await service._find_next_serial("CK2025_PM_01_")

        assert result == 8


# ============================================================================
# validate_case_code() Tests
# ============================================================================

class TestValidateCaseCode:
    """validate_case_code() tests"""

    @pytest.mark.asyncio
    async def test_validate_valid_code(self, mock_db_session):
        """Valid code passes"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_PM_01_001") is True

    @pytest.mark.asyncio
    async def test_validate_valid_erp_code(self, mock_db_session):
        """Valid ERP code passes"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_FN_01_005") is True

    @pytest.mark.asyncio
    async def test_validate_invalid_wrong_parts(self, mock_db_session):
        """Wrong number of parts fails"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_PM_01") is False

    @pytest.mark.asyncio
    async def test_validate_invalid_prefix(self, mock_db_session):
        """Missing CK prefix fails"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("XX2025_PM_01_001") is False

    @pytest.mark.asyncio
    async def test_validate_invalid_non_numeric_year(self, mock_db_session):
        """Non-numeric year fails"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CKabcd_PM_01_001") is False

    @pytest.mark.asyncio
    async def test_validate_invalid_module(self, mock_db_session):
        """Invalid module code fails"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_XX_01_001") is False

    @pytest.mark.asyncio
    async def test_validate_invalid_category_length(self, mock_db_session):
        """Category must be exactly 2 digits"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_PM_1_001") is False

    @pytest.mark.asyncio
    async def test_validate_invalid_serial_length(self, mock_db_session):
        """Serial must be exactly 3 digits"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_PM_01_01") is False

    @pytest.mark.asyncio
    async def test_validate_invalid_non_numeric_serial(self, mock_db_session):
        """Non-numeric serial fails"""
        service = CaseCodeService(mock_db_session)
        assert await service.validate_case_code("CK2025_PM_01_abc") is False


# ============================================================================
# parse_case_code() Tests
# ============================================================================

class TestParseCaseCode:
    """parse_case_code() static method tests"""

    def test_parse_pm_code(self):
        """Parsing PM code extracts all components"""
        result = CaseCodeService.parse_case_code("CK2025_PM_01_001")

        assert result is not None
        assert result["year"] == 2025
        assert result["module"] == "PM"
        assert result["module_name"] == "pm"
        assert result["category"] == "01"
        assert result["category_name"] == "委辦招標"
        assert result["serial"] == 1
        assert result["formatted"] == "CK2025_PM_01_001"

    def test_parse_erp_code(self):
        """Parsing ERP code extracts all components"""
        result = CaseCodeService.parse_case_code("CK2025_FN_01_005")

        assert result is not None
        assert result["module"] == "FN"
        assert result["module_name"] == "erp"
        assert result["category_name"] == "報價單"
        assert result["serial"] == 5

    def test_parse_dispatch_code(self):
        """Parsing dispatch code"""
        result = CaseCodeService.parse_case_code("CK2025_DP_02_010")

        assert result is not None
        assert result["module"] == "DP"
        assert result["module_name"] == "dispatch"
        assert result["category"] == "02"
        assert result["category_name"] == "土地查估"
        assert result["serial"] == 10

    def test_parse_general_code(self):
        """Parsing general code"""
        result = CaseCodeService.parse_case_code("CK2025_GN_01_003")

        assert result is not None
        assert result["module"] == "GN"
        assert result["module_name"] == "general"

    def test_parse_invalid_format(self):
        """Invalid format returns None"""
        assert CaseCodeService.parse_case_code("INVALID") is None

    def test_parse_wrong_parts_count(self):
        """Wrong number of parts returns None"""
        assert CaseCodeService.parse_case_code("CK2025_PM_01") is None

    def test_parse_non_numeric_year(self):
        """Non-numeric year returns None"""
        assert CaseCodeService.parse_case_code("CKabcd_PM_01_001") is None

    def test_parse_unknown_module(self):
        """Unknown module returns 'unknown' for module_name"""
        result = CaseCodeService.parse_case_code("CK2025_XX_01_001")

        assert result is not None
        assert result["module_name"] == "unknown"

    def test_parse_unknown_category(self):
        """Unknown category returns '未定義' for category_name"""
        result = CaseCodeService.parse_case_code("CK2025_PM_88_001")

        assert result is not None
        assert result["category_name"] == "未定義"


# ============================================================================
# check_duplicate() Tests
# ============================================================================

class TestCheckDuplicate:
    """check_duplicate() tests"""

    @pytest.mark.asyncio
    async def test_check_duplicate_found_in_pm(self, mock_db_session):
        """Finds existing code in PM table"""
        pm_result = MagicMock()
        pm_result.scalar.return_value = 1  # count = 1

        mock_db_session.execute = AsyncMock(return_value=pm_result)

        service = CaseCodeService(mock_db_session)
        result = await service.check_duplicate("CK2025_PM_01_001")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_duplicate_found_in_erp(self, mock_db_session):
        """Finds existing code in ERP table (PM empty)"""
        pm_result = MagicMock()
        pm_result.scalar.return_value = 0
        erp_result = MagicMock()
        erp_result.scalar.return_value = 1

        mock_db_session.execute = AsyncMock(side_effect=[pm_result, erp_result])

        service = CaseCodeService(mock_db_session)
        result = await service.check_duplicate("CK2025_FN_01_001")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_duplicate_not_found(self, mock_db_session):
        """No duplicate returns False"""
        pm_result = MagicMock()
        pm_result.scalar.return_value = 0
        erp_result = MagicMock()
        erp_result.scalar.return_value = 0

        mock_db_session.execute = AsyncMock(side_effect=[pm_result, erp_result])

        service = CaseCodeService(mock_db_session)
        result = await service.check_duplicate("CK2025_PM_01_999")

        assert result is False


# ============================================================================
# get_module_categories() Tests
# ============================================================================

class TestGetModuleCategories:
    """get_module_categories() static method tests"""

    def test_pm_categories(self):
        result = CaseCodeService.get_module_categories("pm")
        assert result == PM_CATEGORY_CODES

    def test_erp_categories(self):
        result = CaseCodeService.get_module_categories("erp")
        assert result == ERP_CATEGORY_CODES

    def test_dispatch_categories(self):
        result = CaseCodeService.get_module_categories("dispatch")
        assert result == DISPATCH_CATEGORY_CODES

    def test_general_categories(self):
        result = CaseCodeService.get_module_categories("general")
        assert result == GENERAL_CATEGORY_CODES

    def test_unknown_returns_empty(self):
        result = CaseCodeService.get_module_categories("unknown")
        assert result == {}
