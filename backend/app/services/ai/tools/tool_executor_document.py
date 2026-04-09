"""
Document parsing tool executor — PDF/DOCX/TXT/Image text extraction for RAG.

Provides:
- parse_document: Extract text from a document's attachments by document_id.
- OCR support for scanned PDFs and image files (PNG/JPG/TIFF/BMP).

Version: 2.0.0
Created: 2026-03-16
Updated: 2026-03-16 - v2.0.0 Add OCR capability (Tesseract + Pillow)
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Maximum characters returned in tool result (prevent oversized context)
MAX_EXTRACT_CHARS = 5000

# Minimum chars per page to consider a PDF as having usable text (below = image-only)
_MIN_TEXT_CHARS_PER_PAGE = 50

# Resolve the uploads base directory once
_UPLOADS_BASE: str | None = None

# OCR availability flag (lazy-checked once)
_OCR_AVAILABLE: bool | None = None


def _get_uploads_base() -> str:
    """Resolve attachment storage path (same logic as main.py / endpoints)."""
    global _UPLOADS_BASE
    if _UPLOADS_BASE is None:
        try:
            from app.core.config import settings
            _UPLOADS_BASE = getattr(settings, "ATTACHMENT_STORAGE_PATH", None) or ""
        except Exception:
            _UPLOADS_BASE = ""
        if not _UPLOADS_BASE:
            _UPLOADS_BASE = os.getenv("ATTACHMENT_STORAGE_PATH", "uploads")
    return _UPLOADS_BASE


def _is_ocr_available() -> bool:
    """Check whether pytesseract + Tesseract binary are available."""
    global _OCR_AVAILABLE
    if _OCR_AVAILABLE is not None:
        return _OCR_AVAILABLE
    try:
        import pytesseract  # noqa: F401
        pytesseract.get_tesseract_version()
        _OCR_AVAILABLE = True
    except Exception:
        _OCR_AVAILABLE = False
    return _OCR_AVAILABLE


def _extract_text_ocr(file_path: str) -> str:
    """
    Extract text from an image file using Tesseract OCR.

    Supports: PNG, JPG, JPEG, TIFF, BMP.
    Language: Traditional Chinese + English (chi_tra+eng).
    Falls back gracefully if Tesseract is not installed.
    Includes EXIF rotation correction and 30s timeout.
    """
    if not _is_ocr_available():
        return "[OCR 不可用] 請安裝 Tesseract OCR 以啟用掃描文件文字提取。"

    import pytesseract
    from PIL import Image, ImageOps

    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)  # Fix EXIF rotation
    try:
        text = pytesseract.image_to_string(img, lang="chi_tra+eng", timeout=30)
    except pytesseract.TesseractError:
        # Fallback: try without Chinese language pack
        try:
            text = pytesseract.image_to_string(img, lang="eng", timeout=30)
        except pytesseract.TesseractError as e:
            return f"[OCR 錯誤] {str(e)[:200]}"
    return text.strip()


def _ocr_pdf_page(page, page_number: int = 0) -> str:
    """
    Run OCR on a single pdfplumber page by rendering it to an image.

    Returns extracted text, a placeholder on failure, or empty string if OCR unavailable.
    Includes 30s timeout per page and EXIF rotation correction.
    """
    if not _is_ocr_available():
        return ""

    import pytesseract
    from PIL import ImageOps

    try:
        page_image = page.to_image(resolution=300)
        # pdfplumber PageImage has .original attribute (PIL Image)
        pil_img = page_image.original
        pil_img = ImageOps.exif_transpose(pil_img)  # Fix EXIF rotation
        try:
            text = pytesseract.image_to_string(
                pil_img, lang="chi_tra+eng", timeout=30,
            )
        except pytesseract.TesseractError:
            text = pytesseract.image_to_string(
                pil_img, lang="eng", timeout=30,
            )
        return text.strip()
    except Exception as e:
        logger.warning("OCR failed for page %d: %s", page_number + 1, e)
        return f"[OCR failed for page {page_number + 1}]"


def _extract_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using pdfplumber.

    If a page yields very little text (< _MIN_TEXT_CHARS_PER_PAGE chars),
    attempt OCR on that page's rendered image as a fallback.
    """
    import pdfplumber  # lazy import — only needed when parsing PDF

    texts: list[str] = []
    ocr_used = False
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            if len(page_text.strip()) < _MIN_TEXT_CHARS_PER_PAGE:
                # Likely a scanned/image page — try OCR
                ocr_text = _ocr_pdf_page(page, page_number=i)
                if ocr_text:
                    texts.append(ocr_text)
                    ocr_used = True
                elif page_text.strip():
                    texts.append(page_text)
            else:
                texts.append(page_text)

    result = "\n".join(texts)
    if ocr_used:
        result = "[部分頁面使用 OCR 提取]\n" + result
    return result


def _extract_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document  # already in requirements.txt

    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def _extract_txt(file_path: str) -> str:
    """Read plain text file."""
    path = Path(file_path)
    return path.read_text(encoding="utf-8", errors="replace")


# Extension -> extractor mapping
_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".doc": _extract_docx,  # best-effort: python-docx can sometimes read .doc
    ".txt": _extract_txt,
    ".text": _extract_txt,
    ".csv": _extract_txt,
    ".log": _extract_txt,
    ".md": _extract_txt,
    # Image formats — OCR extraction
    ".png": _extract_text_ocr,
    ".jpg": _extract_text_ocr,
    ".jpeg": _extract_text_ocr,
    ".tiff": _extract_text_ocr,
    ".bmp": _extract_text_ocr,
}

_SUPPORTED_EXTENSIONS = set(_EXTRACTORS.keys())


async def _analyze_image_document(image_bytes: bytes, filename: str) -> dict:
    """Gemma 4 vision analysis for image-type documents.

    Returns structured info (doc_type, summary, entities) or a fallback dict.
    """
    try:
        from app.core.ai_connector import get_ai_connector
        ai = get_ai_connector()
        prompt = (
            f"分析此文件圖片 ({filename})。\n"
            "1. 文件類型 (公文/發票/合約/報告/其他)\n"
            "2. 主要內容摘要\n"
            "3. 關鍵資訊 (日期/金額/機關/人名)\n"
            "以 JSON 格式回覆：\n"
            '{"doc_type": "...", "summary": "...", "entities": [...]}'
        )
        result = await ai.vision_completion(prompt, image_bytes, max_tokens=512)
        from app.services.ai.core.agent_utils import parse_json_safe
        return parse_json_safe(result) or {"doc_type": "unknown", "summary": result[:500]}
    except Exception as e:
        logger.debug("Gemma 4 vision document analysis failed for %s: %s", filename, e)
        return None


class DocumentToolExecutor:
    """Document parsing tool executor."""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    async def parse_document(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from attachments of a given document.

        Params:
            document_id (int): The OfficialDocument ID.

        Returns a dict with extracted text (truncated to MAX_EXTRACT_CHARS).
        """
        from app.extended.models.document import DocumentAttachment

        document_id = params.get("document_id")
        if not document_id:
            return {"error": "缺少 document_id 參數", "count": 0}

        try:
            document_id = int(document_id)
        except (ValueError, TypeError):
            return {"error": f"document_id 必須為整數，收到: {document_id}", "count": 0}

        # Query attachments for this document
        result = await self.db.execute(
            select(DocumentAttachment)
            .where(DocumentAttachment.document_id == document_id)
            .order_by(DocumentAttachment.id)
        )
        attachments = result.scalars().all()

        if not attachments:
            return {
                "error": f"公文 ID={document_id} 沒有附件",
                "count": 0,
            }

        uploads_base = _get_uploads_base()
        extracted_parts: list[Dict[str, Any]] = []
        total_chars = 0

        for att in attachments:
            file_name = att.file_name or att.original_name or ""
            ext = Path(file_name).suffix.lower()

            if ext not in _SUPPORTED_EXTENSIONS:
                extracted_parts.append({
                    "file_name": file_name,
                    "status": "skipped",
                    "reason": f"不支援的格式: {ext}",
                })
                continue

            # Resolve full path
            file_path = att.file_path or ""
            if not os.path.isabs(file_path):
                file_path = os.path.join(uploads_base, file_path)

            if not os.path.isfile(file_path):
                extracted_parts.append({
                    "file_name": file_name,
                    "status": "error",
                    "reason": "檔案不存在",
                })
                continue

            try:
                # For image files, try Gemma 4 Vision first
                vision_result = None
                if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
                    try:
                        with open(file_path, "rb") as img_f:
                            img_bytes = img_f.read()
                        vision_result = await _analyze_image_document(img_bytes, file_name)
                    except Exception as ve:
                        logger.debug("Vision analysis skipped for %s: %s", file_name, ve)

                if vision_result and vision_result.get("summary"):
                    # Use vision result as structured text
                    text = (
                        f"[Gemma 4 Vision 分析]\n"
                        f"文件類型: {vision_result.get('doc_type', 'unknown')}\n"
                        f"摘要: {vision_result['summary']}\n"
                    )
                    entities = vision_result.get("entities")
                    if entities:
                        text += f"關鍵資訊: {', '.join(str(e) for e in entities)}\n"
                else:
                    # Fallback to existing extractor (Tesseract for images)
                    extractor = _EXTRACTORS[ext]
                    text = extractor(file_path)

                # Truncate if total would exceed limit
                remaining = MAX_EXTRACT_CHARS - total_chars
                if remaining <= 0:
                    extracted_parts.append({
                        "file_name": file_name,
                        "status": "skipped",
                        "reason": "已達文字上限",
                    })
                    continue

                truncated = len(text) > remaining
                text = text[:remaining]
                total_chars += len(text)

                extracted_parts.append({
                    "file_name": file_name,
                    "status": "ok",
                    "text": text,
                    "char_count": len(text),
                    "truncated": truncated,
                })
            except Exception as e:
                logger.warning("Failed to extract %s: %s", file_name, e)
                extracted_parts.append({
                    "file_name": file_name,
                    "status": "error",
                    "reason": str(e)[:200],
                })

        ok_count = sum(1 for p in extracted_parts if p.get("status") == "ok")

        return {
            "document_id": document_id,
            "attachments": extracted_parts,
            "count": ok_count,
            "total_chars": total_chars,
        }
