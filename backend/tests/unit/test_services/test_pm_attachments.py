# -*- coding: utf-8 -*-
"""
PM 案件附件端點單元測試
PM Case Attachments API Unit Tests

測試 pm/attachments.py 的 upload/list/download/delete 4 個端點邏輯

執行方式:
    pytest tests/unit/test_services/test_pm_attachments.py -v
"""
import hashlib
import os
import sys
import uuid
from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.api.endpoints.pm.attachments import (
    _validate_extension,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    upload_quotation_files,
    list_quotation_attachments,
    download_quotation_attachment,
    delete_quotation_attachment,
)


# ============================================================================
# _validate_extension 測試
# ============================================================================

class TestValidateExtension:
    """檔案副檔名驗證"""

    @pytest.mark.parametrize("filename,expected", [
        ("report.pdf", True),
        ("data.xlsx", True),
        ("image.jpg", True),
        ("photo.jpeg", True),
        ("presentation.pptx", True),
        ("archive.zip", True),
        ("document.doc", True),
        ("document.docx", True),
        ("image.png", True),
        ("image.gif", True),
        ("archive.rar", True),
        ("archive.7z", True),
        ("document.odt", True),
        ("spreadsheet.ods", True),
    ])
    def test_allowed_extensions(self, filename, expected):
        assert _validate_extension(filename) == expected

    @pytest.mark.parametrize("filename", [
        "script.exe",
        "malware.bat",
        "shell.sh",
        "code.py",
        "page.html",
        "data.json",
        "config.yaml",
        "binary.bin",
        "",
    ])
    def test_rejected_extensions(self, filename):
        assert _validate_extension(filename) is False

    def test_case_insensitive(self):
        assert _validate_extension("REPORT.PDF") is True
        assert _validate_extension("Data.XLSX") is True
        assert _validate_extension("IMAGE.JPG") is True


# ============================================================================
# upload 端點測試
# ============================================================================

class TestUploadQuotationFiles:
    """上傳報價紀錄附件"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 1
        return user

    def _make_upload_file(self, filename="report.pdf", content=b"test content", content_type="application/pdf"):
        file = AsyncMock()
        file.filename = filename
        file.content_type = content_type
        file.read = AsyncMock(return_value=content)
        return file

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    async def test_upload_single_file(self, mock_file_open, mock_makedirs, mock_db, mock_user):
        files = [self._make_upload_file()]

        result = await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=files,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["total_uploaded"] == 1
        assert len(result["files"]) == 1
        assert result["files"][0]["file_name"] == "report.pdf"
        assert len(result["errors"]) == 0
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    async def test_upload_multiple_files(self, mock_file_open, mock_makedirs, mock_db, mock_user):
        files = [
            self._make_upload_file("report1.pdf"),
            self._make_upload_file("report2.xlsx"),
        ]

        result = await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=files,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["total_uploaded"] == 2
        assert len(result["errors"]) == 0
        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_upload_rejected_extension(self, mock_db, mock_user):
        files = [self._make_upload_file("script.exe")]

        result = await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=files,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["total_uploaded"] == 0
        assert len(result["errors"]) == 1
        assert "不支援" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_upload_empty_filename(self, mock_db, mock_user):
        file = self._make_upload_file(filename="")

        result = await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=[file],
            db=mock_db,
            current_user=mock_user,
        )

        assert result["total_uploaded"] == 0
        assert "檔案名稱為空" in result["errors"]

    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, mock_db, mock_user):
        # 建立一個超過 50MB 的假內容
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        files = [self._make_upload_file(content=large_content)]

        result = await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=files,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["total_uploaded"] == 0
        assert any("檔案過大" in e for e in result["errors"])

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    async def test_upload_mixed_valid_and_invalid(self, mock_file_open, mock_makedirs, mock_db, mock_user):
        files = [
            self._make_upload_file("valid.pdf"),
            self._make_upload_file("invalid.exe"),
            self._make_upload_file("valid2.docx"),
        ]

        result = await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=files,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["total_uploaded"] == 2
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    async def test_upload_checksum_computed(self, mock_file_open, mock_makedirs, mock_db, mock_user):
        content = b"test file content for checksum"
        expected_checksum = hashlib.sha256(content).hexdigest()
        files = [self._make_upload_file(content=content)]

        await upload_quotation_files(
            case_code="CK2025_PM_01_001",
            files=files,
            db=mock_db,
            current_user=mock_user,
        )

        # 驗證 add 的物件有正確的 checksum
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.checksum == expected_checksum


# ============================================================================
# list 端點測試
# ============================================================================

class TestListQuotationAttachments:
    """列出報價紀錄附件"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 1
        return user

    def _make_attachment(self, att_id=1, original_name="report.pdf"):
        att = MagicMock()
        att.id = att_id
        att.file_name = f"abc12345_{original_name}"
        att.original_name = original_name
        att.file_size = 1024
        att.mime_type = "application/pdf"
        att.notes = None
        att.uploaded_by = 1
        att.created_at = datetime(2026, 3, 25, 10, 0, 0)
        return att

    @pytest.mark.asyncio
    async def test_list_returns_attachments(self, mock_db, mock_user):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            self._make_attachment(1, "report.pdf"),
            self._make_attachment(2, "quotation.xlsx"),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_quotation_attachments(
            case_code="CK2025_PM_01_001",
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["attachments"]) == 2
        assert result["attachments"][0]["file_name"] == "report.pdf"

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_db, mock_user):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_quotation_attachments(
            case_code="CK2025_PM_99_999",
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["total"] == 0
        assert result["attachments"] == []


# ============================================================================
# download 端點測試
# ============================================================================

class TestDownloadQuotationAttachment:
    """下載報價紀錄附件"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 1
        return user

    @pytest.mark.asyncio
    async def test_download_not_found(self, mock_db, mock_user):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await download_quotation_attachment(
                attachment_id=999,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 404
        assert "附件不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.path.exists", return_value=False)
    async def test_download_file_missing(self, mock_exists, mock_db, mock_user):
        att = MagicMock()
        att.file_path = "/tmp/missing.pdf"
        att.original_name = "report.pdf"
        att.mime_type = "application/pdf"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = att
        mock_db.execute = AsyncMock(return_value=mock_result)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await download_quotation_attachment(
                attachment_id=1,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 404
        assert "檔案已遺失" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.path.exists", return_value=True)
    @patch("app.api.endpoints.pm.attachments.FileResponse")
    async def test_download_success(self, mock_file_response, mock_exists, mock_db, mock_user):
        att = MagicMock()
        att.file_path = "/tmp/report.pdf"
        att.original_name = "report.pdf"
        att.file_name = "abc_report.pdf"
        att.mime_type = "application/pdf"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = att
        mock_db.execute = AsyncMock(return_value=mock_result)

        await download_quotation_attachment(
            attachment_id=1,
            db=mock_db,
            current_user=mock_user,
        )

        mock_file_response.assert_called_once_with(
            path="/tmp/report.pdf",
            filename="report.pdf",
            media_type="application/pdf",
        )


# ============================================================================
# delete 端點測試
# ============================================================================

class TestDeleteQuotationAttachment:
    """刪除報價紀錄附件"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 1
        return user

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db, mock_user):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await delete_quotation_attachment(
                attachment_id=999,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.path.exists", return_value=True)
    @patch("app.api.endpoints.pm.attachments.os.remove")
    async def test_delete_success(self, mock_remove, mock_exists, mock_db, mock_user):
        att = MagicMock()
        att.id = 1
        att.file_path = "/tmp/report.pdf"

        # 第一次 execute: select, 第二次: delete
        mock_select_result = MagicMock()
        mock_select_result.scalar_one_or_none.return_value = att
        mock_delete_result = MagicMock()
        mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_delete_result])

        result = await delete_quotation_attachment(
            attachment_id=1,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["deleted_id"] == 1
        mock_remove.assert_called_once_with("/tmp/report.pdf")
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.path.exists", return_value=True)
    @patch("app.api.endpoints.pm.attachments.os.remove", side_effect=OSError("Permission denied"))
    async def test_delete_file_removal_fails_gracefully(self, mock_remove, mock_exists, mock_db, mock_user):
        att = MagicMock()
        att.id = 2
        att.file_path = "/tmp/locked.pdf"

        mock_select_result = MagicMock()
        mock_select_result.scalar_one_or_none.return_value = att
        mock_delete_result = MagicMock()
        mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_delete_result])

        # 即使檔案刪除失敗，DB 記錄仍應刪除
        result = await delete_quotation_attachment(
            attachment_id=2,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.api.endpoints.pm.attachments.os.path.exists", return_value=False)
    async def test_delete_missing_file_still_deletes_record(self, mock_exists, mock_db, mock_user):
        att = MagicMock()
        att.id = 3
        att.file_path = "/tmp/already_gone.pdf"

        mock_select_result = MagicMock()
        mock_select_result.scalar_one_or_none.return_value = att
        mock_delete_result = MagicMock()
        mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_delete_result])

        result = await delete_quotation_attachment(
            attachment_id=3,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["deleted_id"] == 3
