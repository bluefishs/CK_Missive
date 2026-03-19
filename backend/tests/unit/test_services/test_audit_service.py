"""
審計服務單元測試

測試範圍：
- CRITICAL_FIELDS: 關鍵欄位定義
- detect_changes: 變更偵測
- is_critical_change: 關鍵變更判定
- get_critical_fields: 取得關鍵欄位
- log_change: 審計日誌記錄 (async, mocked DB)
- log_document_change: 公文變更便捷方法
- log_auth_event: 認證事件審計

共 7 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.audit_service import (
    AuditService,
    CRITICAL_FIELDS,
    detect_changes,
)


# ============================================================================
# detect_changes
# ============================================================================

class TestDetectChanges:
    """變更偵測測試"""

    def test_detects_changed_fields(self):
        old = {"subject": "舊主旨", "status": "pending"}
        new = {"subject": "新主旨", "status": "pending"}
        changes = detect_changes(old, new)
        assert "subject" in changes
        assert changes["subject"]["old"] == "舊主旨"
        assert changes["subject"]["new"] == "新主旨"
        assert "status" not in changes

    def test_no_changes_returns_empty(self):
        old = {"subject": "相同", "status": "ok"}
        new = {"subject": "相同", "status": "ok"}
        changes = detect_changes(old, new)
        assert changes == {}

    def test_skips_private_fields(self):
        old = {"_internal": "old", "name": "same"}
        new = {"_internal": "new", "name": "same"}
        changes = detect_changes(old, new)
        assert "_internal" not in changes

    def test_none_to_none_ignored(self):
        old = {"field": None}
        new = {"field": None}
        changes = detect_changes(old, new)
        assert changes == {}


# ============================================================================
# is_critical_change / get_critical_fields
# ============================================================================

class TestCriticalFields:
    """關鍵欄位判定測試"""

    def test_critical_change_detected(self):
        assert AuditService.is_critical_change(
            "documents", {"subject": {"old": "A", "new": "B"}}
        ) is True

    def test_non_critical_change(self):
        assert AuditService.is_critical_change(
            "documents", {"some_field": {"old": "A", "new": "B"}}
        ) is False

    def test_get_critical_fields_exists(self):
        fields = AuditService.get_critical_fields("documents")
        assert "subject" in fields
        assert "doc_number" in fields

    def test_get_critical_fields_unknown_table(self):
        fields = AuditService.get_critical_fields("nonexistent_table")
        assert fields == {}


# ============================================================================
# CRITICAL_FIELDS constant
# ============================================================================

class TestCriticalFieldsConstant:
    """關鍵欄位定義測試"""

    def test_documents_has_expected_fields(self):
        assert "subject" in CRITICAL_FIELDS["documents"]
        assert "doc_number" in CRITICAL_FIELDS["documents"]
        assert "status" in CRITICAL_FIELDS["documents"]

    def test_contract_projects_has_expected_fields(self):
        assert "project_name" in CRITICAL_FIELDS["contract_projects"]


# ============================================================================
# log_change (async, mock DB)
# ============================================================================

class TestLogChange:
    """審計日誌記錄測試"""

    @pytest.mark.asyncio
    async def test_log_change_success(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.database.AsyncSessionLocal", return_value=mock_session):
            result = await AuditService.log_change(
                table_name="documents",
                record_id=1,
                action="UPDATE",
                changes={"subject": {"old": "A", "new": "B"}},
                user_id=1,
                user_name="admin",
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_log_change_db_failure(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute.side_effect = Exception("DB error")

        with patch("app.db.database.AsyncSessionLocal", return_value=mock_session):
            result = await AuditService.log_change(
                table_name="documents",
                record_id=1,
                action="UPDATE",
                changes={"subject": {"old": "A", "new": "B"}},
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_log_change_session_creation_failure(self):
        with patch(
            "app.db.database.AsyncSessionLocal",
            side_effect=Exception("Connection failed"),
        ):
            result = await AuditService.log_change(
                table_name="documents",
                record_id=1,
                action="CREATE",
                changes={"subject": {"old": None, "new": "新公文"}},
            )
        assert result is False
