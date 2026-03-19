"""
Unit tests for DocumentToolExecutor (parse_document tool).
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.tool_executor_document import (
    DocumentToolExecutor,
    _extract_txt,
    _extract_text_ocr,
    _is_ocr_available,
    _SUPPORTED_EXTENSIONS,
    MAX_EXTRACT_CHARS,
    _MIN_TEXT_CHARS_PER_PAGE,
)


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def executor(mock_db):
    return DocumentToolExecutor(
        db=mock_db,
        ai_connector=MagicMock(),
        embedding_mgr=MagicMock(),
        config=MagicMock(),
    )


class TestParseDocumentParams:
    """Parameter validation tests."""

    @pytest.mark.asyncio
    async def test_missing_document_id(self, executor):
        result = await executor.parse_document({})
        assert result["error"] == "缺少 document_id 參數"
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_invalid_document_id(self, executor):
        result = await executor.parse_document({"document_id": "abc"})
        assert "必須為整數" in result["error"]
        assert result["count"] == 0


class TestParseDocumentNoAttachments:
    """Test behavior when document has no attachments."""

    @pytest.mark.asyncio
    async def test_no_attachments(self, executor, mock_db):
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await executor.parse_document({"document_id": 1})
        assert "沒有附件" in result["error"]
        assert result["count"] == 0


class TestParseDocumentExtraction:
    """Test text extraction from various file types."""

    def _make_attachment(self, file_name, file_path, mime_type="application/pdf"):
        att = MagicMock()
        att.file_name = file_name
        att.original_name = file_name
        att.file_path = file_path
        att.mime_type = mime_type
        return att

    @pytest.mark.asyncio
    async def test_unsupported_format(self, executor, mock_db):
        att = self._make_attachment("archive.zip", "docs/archive.zip", "application/zip")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att]
        mock_db.execute.return_value = mock_result

        result = await executor.parse_document({"document_id": 1})
        assert result["count"] == 0
        assert result["attachments"][0]["status"] == "skipped"
        assert "不支援" in result["attachments"][0]["reason"]

    @pytest.mark.asyncio
    async def test_missing_file(self, executor, mock_db):
        att = self._make_attachment("doc.pdf", "/nonexistent/path/doc.pdf")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att]
        mock_db.execute.return_value = mock_result

        with patch("app.services.ai.tool_executor_document._get_uploads_base", return_value="/tmp"):
            result = await executor.parse_document({"document_id": 1})
        assert result["count"] == 0
        assert result["attachments"][0]["status"] == "error"
        assert "不存在" in result["attachments"][0]["reason"]

    @pytest.mark.asyncio
    async def test_txt_extraction(self, executor, mock_db, tmp_path):
        # Create a temp text file
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello World\nLine 2", encoding="utf-8")

        att = self._make_attachment("test.txt", str(txt_file), "text/plain")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att]
        mock_db.execute.return_value = mock_result

        with patch("app.services.ai.tool_executor_document._get_uploads_base", return_value=str(tmp_path)):
            result = await executor.parse_document({"document_id": 1})

        assert result["count"] == 1
        assert result["attachments"][0]["status"] == "ok"
        assert "Hello World" in result["attachments"][0]["text"]

    @pytest.mark.asyncio
    async def test_truncation(self, executor, mock_db, tmp_path):
        # Create a file larger than MAX_EXTRACT_CHARS
        txt_file = tmp_path / "big.txt"
        txt_file.write_text("A" * (MAX_EXTRACT_CHARS + 1000), encoding="utf-8")

        att = self._make_attachment("big.txt", str(txt_file), "text/plain")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att]
        mock_db.execute.return_value = mock_result

        with patch("app.services.ai.tool_executor_document._get_uploads_base", return_value=str(tmp_path)):
            result = await executor.parse_document({"document_id": 1})

        assert result["count"] == 1
        assert result["attachments"][0]["truncated"] is True
        assert result["total_chars"] == MAX_EXTRACT_CHARS

    @pytest.mark.asyncio
    async def test_multiple_attachments(self, executor, mock_db, tmp_path):
        # Two text files
        f1 = tmp_path / "a.txt"
        f1.write_text("Content A", encoding="utf-8")
        f2 = tmp_path / "b.txt"
        f2.write_text("Content B", encoding="utf-8")

        att1 = self._make_attachment("a.txt", str(f1))
        att2 = self._make_attachment("b.txt", str(f2))

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att1, att2]
        mock_db.execute.return_value = mock_result

        with patch("app.services.ai.tool_executor_document._get_uploads_base", return_value=str(tmp_path)):
            result = await executor.parse_document({"document_id": 1})

        assert result["count"] == 2
        assert result["document_id"] == 1


class TestExtractTxt:
    """Direct unit tests for _extract_txt."""

    def test_reads_utf8(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("中文測試\nLine 2", encoding="utf-8")
        text = _extract_txt(str(f))
        assert "中文測試" in text
        assert "Line 2" in text


class TestSupportedExtensions:
    """Verify supported file extensions."""

    def test_pdf_supported(self):
        assert ".pdf" in _SUPPORTED_EXTENSIONS

    def test_docx_supported(self):
        assert ".docx" in _SUPPORTED_EXTENSIONS

    def test_txt_supported(self):
        assert ".txt" in _SUPPORTED_EXTENSIONS

    def test_md_supported(self):
        assert ".md" in _SUPPORTED_EXTENSIONS

    def test_png_supported(self):
        assert ".png" in _SUPPORTED_EXTENSIONS

    def test_jpg_supported(self):
        assert ".jpg" in _SUPPORTED_EXTENSIONS

    def test_jpeg_supported(self):
        assert ".jpeg" in _SUPPORTED_EXTENSIONS

    def test_tiff_supported(self):
        assert ".tiff" in _SUPPORTED_EXTENSIONS

    def test_bmp_supported(self):
        assert ".bmp" in _SUPPORTED_EXTENSIONS


class TestOCRExtraction:
    """Tests for OCR text extraction (with mocked pytesseract)."""

    def test_ocr_unavailable_returns_message(self):
        """When OCR is not available, return a descriptive message."""
        with patch("app.services.ai.tool_executor_document._OCR_AVAILABLE", False):
            result = _extract_text_ocr("/fake/image.png")
        assert "OCR 不可用" in result
        assert "Tesseract" in result

    def test_ocr_extracts_text_from_image(self):
        """When OCR is available, extract text from image via pytesseract."""
        mock_image = MagicMock()
        # exif_transpose may call .copy(), so mock it to return self
        mock_image.copy.return_value = mock_image
        with (
            patch("app.services.ai.tool_executor_document._OCR_AVAILABLE", True),
            patch("app.services.ai.tool_executor_document._is_ocr_available", return_value=True),
            patch("PIL.Image.open", return_value=mock_image) as mock_open,
            patch("PIL.ImageOps.exif_transpose", return_value=mock_image),
            patch("pytesseract.image_to_string", return_value="  公文字號：桃工養字第1130001號  ") as mock_ocr,
        ):
            result = _extract_text_ocr("/fake/scan.png")

        mock_open.assert_called_once_with("/fake/scan.png")
        mock_ocr.assert_called_once_with(mock_image, lang="chi_tra+eng", timeout=30)
        assert "公文字號" in result
        assert result == "公文字號：桃工養字第1130001號"  # stripped

    def test_ocr_falls_back_to_english(self):
        """If chi_tra lang pack missing, fall back to eng only."""
        mock_image = MagicMock()

        import pytesseract as pt_mod

        call_count = 0

        def side_effect(img, lang="eng", timeout=30):
            nonlocal call_count
            call_count += 1
            if lang == "chi_tra+eng":
                raise pt_mod.TesseractError(status=1, message="chi_tra not found")
            return "English only text"

        with (
            patch("app.services.ai.tool_executor_document._OCR_AVAILABLE", True),
            patch("app.services.ai.tool_executor_document._is_ocr_available", return_value=True),
            patch("PIL.Image.open", return_value=mock_image),
            patch("pytesseract.image_to_string", side_effect=side_effect),
        ):
            result = _extract_text_ocr("/fake/scan.png")

        assert result == "English only text"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_ocr_image_attachment_integration(self, executor, mock_db, tmp_path):
        """Integration: parse_document handles .png via OCR extractor."""
        # Create a fake PNG file (just needs to exist for path check)
        png_file = tmp_path / "scan.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        att = MagicMock()
        att.file_name = "scan.png"
        att.original_name = "scan.png"
        att.file_path = str(png_file)
        att.mime_type = "image/png"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att]
        mock_db.execute.return_value = mock_result

        with (
            patch("app.services.ai.tool_executor_document._get_uploads_base", return_value=str(tmp_path)),
            patch("app.services.ai.tool_executor_document._is_ocr_available", return_value=True),
            patch("app.services.ai.tool_executor_document._OCR_AVAILABLE", True),
            patch("PIL.Image.open") as mock_img_open,
            patch("pytesseract.image_to_string", return_value="OCR 提取的文字內容"),
        ):
            result = await executor.parse_document({"document_id": 42})

        assert result["count"] == 1
        assert "OCR 提取的文字內容" in result["attachments"][0]["text"]


class TestPDFOCRFallback:
    """Tests for PDF OCR fallback on image-only pages."""

    def test_pdf_ocr_fallback_on_scanned_page(self):
        """When PDF page text is too short, OCR is attempted."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "AB"  # below threshold

        mock_page_image = MagicMock()
        mock_pil_img = MagicMock()
        mock_page_image.original = mock_pil_img
        mock_page.to_image.return_value = mock_page_image

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with (
            patch("pdfplumber.open", return_value=mock_pdf),
            patch("app.services.ai.tool_executor_document._is_ocr_available", return_value=True),
            patch("app.services.ai.tool_executor_document._OCR_AVAILABLE", True),
            patch("pytesseract.image_to_string", return_value="OCR extracted page text"),
        ):
            from app.services.ai.tool_executor_document import _extract_pdf
            result = _extract_pdf("/fake/scanned.pdf")

        assert "OCR extracted page text" in result
        assert "部分頁面使用 OCR 提取" in result

    def test_pdf_with_sufficient_text_skips_ocr(self):
        """When PDF has enough text, OCR is not triggered."""
        long_text = "A" * (_MIN_TEXT_CHARS_PER_PAGE + 10)
        mock_page = MagicMock()
        mock_page.extract_text.return_value = long_text

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with (
            patch("pdfplumber.open", return_value=mock_pdf),
            patch("app.services.ai.tool_executor_document._ocr_pdf_page") as mock_ocr_page,
        ):
            from app.services.ai.tool_executor_document import _extract_pdf
            result = _extract_pdf("/fake/normal.pdf")

        mock_ocr_page.assert_not_called()
        assert long_text in result
        assert "OCR" not in result


class TestToolRegistryInclusion:
    """Verify parse_document is registered in ToolRegistry."""

    def test_registered(self):
        from app.services.ai.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("parse_document")
        assert tool is not None
        assert tool.name == "parse_document"
        assert "document_id" in tool.parameters
        assert tool.contexts == ["doc"]

    def test_description_mentions_ocr(self):
        from app.services.ai.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("parse_document")
        assert "OCR" in tool.description or "圖片" in tool.description
