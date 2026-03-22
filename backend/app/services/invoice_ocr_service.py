"""發票 OCR 自動辨識服務

使用 Tesseract OCR 從發票影像提取結構化資訊：
- 發票號碼 (2英文+8數字)
- 日期 (民國/西元)
- 金額 (含稅總額)
- 買方/賣方統編 (8碼)

Version: 1.0.0
Created: 2026-03-21
"""
import re
import logging
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# OCR availability (lazy-checked once)
_OCR_AVAILABLE: Optional[bool] = None


def _is_ocr_available() -> bool:
    global _OCR_AVAILABLE
    if _OCR_AVAILABLE is not None:
        return _OCR_AVAILABLE
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _OCR_AVAILABLE = True
    except Exception:
        _OCR_AVAILABLE = False
    return _OCR_AVAILABLE


class InvoiceOCRResult(BaseModel):
    """OCR 解析結果"""
    inv_num: Optional[str] = Field(None, description="發票號碼")
    date: Optional[date_type] = Field(None, description="開立日期")
    amount: Optional[Decimal] = Field(None, description="總金額")
    tax_amount: Optional[Decimal] = Field(None, description="稅額")
    buyer_ban: Optional[str] = Field(None, description="買方統編")
    seller_ban: Optional[str] = Field(None, description="賣方統編")
    raw_text: str = Field("", description="OCR 原始文字")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="辨識信心度")
    warnings: list[str] = Field(default_factory=list, description="解析警告")


# ============================================================================
# 正規表達式模式
# ============================================================================

# 發票號碼: 2 大寫英文 + 8 數字
_INV_NUM_PATTERN = re.compile(r'[A-Z]{2}\d{8}')

# 統編: 8 碼純數字 (非日期，需前後非數字)
_BAN_PATTERN = re.compile(r'(?<!\d)\d{8}(?!\d)')

# 民國日期: 1XX年XX月XX日 或 1XX/XX/XX
_ROC_DATE_PATTERN = re.compile(
    r'(\d{2,3})\s*[年/\-\.]\s*(\d{1,2})\s*[月/\-\.]\s*(\d{1,2})\s*日?'
)

# 西元日期: 20XX/XX/XX 或 20XX-XX-XX
_CE_DATE_PATTERN = re.compile(
    r'(20\d{2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{1,2})'
)

# 金額: 帶逗號或不帶的數字 (排除統編等短數字)
_AMOUNT_PATTERN = re.compile(r'(?:NT?\$?\s*|合\s*計\s*|總\s*[額計]\s*|金\s*額\s*)(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)')

# 稅額
_TAX_PATTERN = re.compile(r'(?:稅\s*額|營業稅)\s*[：:]*\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)')


class InvoiceOCRService:
    """發票影像 OCR 辨識服務"""

    def parse_image(self, file_path: str) -> InvoiceOCRResult:
        """從影像檔解析發票資訊

        Args:
            file_path: 影像檔路徑

        Returns:
            InvoiceOCRResult 結構化解析結果
        """
        if not _is_ocr_available():
            return InvoiceOCRResult(
                warnings=["Tesseract OCR 未安裝，無法辨識影像"]
            )

        raw_text = self._extract_text(file_path)
        if not raw_text:
            return InvoiceOCRResult(
                warnings=["影像辨識未提取到任何文字"]
            )

        return self._parse_text(raw_text)

    def _extract_text(self, file_path: str) -> str:
        """使用 Tesseract 提取文字"""
        import pytesseract
        from PIL import Image, ImageOps

        try:
            img = Image.open(file_path)
            img = ImageOps.exif_transpose(img)
            text = pytesseract.image_to_string(img, lang="chi_tra+eng", timeout=30)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR 提取失敗: {e}")
            try:
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img, lang="eng", timeout=30)
                return text.strip()
            except Exception:
                return ""

    def _parse_text(self, raw_text: str) -> InvoiceOCRResult:
        """從 OCR 文字中提取結構化發票資訊"""
        warnings: list[str] = []
        fields_found = 0

        # 1. 發票號碼
        inv_num = self._extract_inv_num(raw_text)
        if inv_num:
            fields_found += 1
        else:
            warnings.append("未偵測到發票號碼")

        # 2. 日期
        inv_date = self._extract_date(raw_text)
        if inv_date:
            fields_found += 1
        else:
            warnings.append("未偵測到發票日期")

        # 3. 金額
        amount = self._extract_amount(raw_text)
        if amount:
            fields_found += 1
        else:
            warnings.append("未偵測到金額")

        # 4. 稅額
        tax_amount = self._extract_tax(raw_text)

        # 5. 統編 (買方/賣方)
        buyer_ban, seller_ban = self._extract_bans(raw_text, inv_num)
        if buyer_ban:
            fields_found += 1
        if seller_ban:
            fields_found += 1

        # 信心度計算 (5 個核心欄位)
        confidence = min(fields_found / 5.0, 1.0)

        return InvoiceOCRResult(
            inv_num=inv_num,
            date=inv_date,
            amount=amount,
            tax_amount=tax_amount,
            buyer_ban=buyer_ban,
            seller_ban=seller_ban,
            raw_text=raw_text[:2000],
            confidence=round(confidence, 2),
            warnings=warnings,
        )

    def _extract_inv_num(self, text: str) -> Optional[str]:
        """提取發票號碼"""
        matches = _INV_NUM_PATTERN.findall(text)
        return matches[0] if matches else None

    def _extract_date(self, text: str) -> Optional[date_type]:
        """提取日期 (支援西元/民國，西元優先避免 20XX 被民國正規吃掉)"""
        # 西元日期優先 (20XX/MM/DD)
        m = _CE_DATE_PATTERN.search(text)
        if m:
            try:
                d = date_type(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                return d
            except (ValueError, OverflowError):
                pass

        # 民國日期 (1XX年MM月DD日)
        m = _ROC_DATE_PATTERN.search(text)
        if m:
            try:
                year = int(m.group(1))
                month = int(m.group(2))
                day = int(m.group(3))
                if year < 200:  # 民國年
                    year += 1911
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return date_type(year, month, day)
            except (ValueError, OverflowError):
                pass

        return None

    def _extract_amount(self, text: str) -> Optional[Decimal]:
        """提取金額"""
        matches = _AMOUNT_PATTERN.findall(text)
        if matches:
            try:
                val = matches[0].replace(",", "")
                amount = Decimal(val)
                if amount > 0:
                    return amount
            except InvalidOperation:
                pass

        # 退路: 找最大的數字 (> 10, 排除統編)
        all_nums = re.findall(r'\d{1,3}(?:,\d{3})+|\d{4,}', text)
        candidates = []
        for n in all_nums:
            clean = n.replace(",", "")
            if len(clean) == 8:  # 可能是統編，跳過
                continue
            try:
                val = Decimal(clean)
                if val > 10:
                    candidates.append(val)
            except InvalidOperation:
                pass

        return max(candidates) if candidates else None

    def _extract_tax(self, text: str) -> Optional[Decimal]:
        """提取稅額"""
        m = _TAX_PATTERN.search(text)
        if m:
            try:
                val = m.group(1).replace(",", "")
                return Decimal(val)
            except InvalidOperation:
                pass
        return None

    def _extract_bans(self, text: str, inv_num: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """提取買方/賣方統編

        策略: 找出所有 8 碼數字，先做上下文匹配 (買方/賣方關鍵字)，
        再排除與發票號碼尾碼重複且無上下文標記的統編。
        """
        # 找出所有 8 碼數字及其位置
        all_matches = list(_BAN_PATTERN.finditer(text))

        buyer_ban = None
        seller_ban = None
        unmatched = []

        inv_digits = inv_num[2:] if inv_num else None

        for m in all_matches:
            ban = m.group()
            idx = m.start()
            # 只看統編前方 10 個字元的上下文，避免誤匹配遠處關鍵字
            before = text[max(0, idx - 10):idx]

            if re.search(r'買[方受]', before):
                buyer_ban = ban
            elif re.search(r'賣[方出]|營業人', before):
                seller_ban = ban
            else:
                # 無上下文標記，且與發票號碼尾碼相同 → 跳過
                if inv_digits and ban == inv_digits:
                    continue
                if ban not in {buyer_ban, seller_ban}:
                    unmatched.append(ban)

        # 去重
        seen = {buyer_ban, seller_ban}
        unique_unmatched = []
        for b in unmatched:
            if b not in seen:
                seen.add(b)
                unique_unmatched.append(b)

        # 按順序補齊 (台灣發票格式: 賣方在前)
        if not seller_ban and unique_unmatched:
            seller_ban = unique_unmatched.pop(0)
        if not buyer_ban and unique_unmatched:
            buyer_ban = unique_unmatched.pop(0)

        return buyer_ban, seller_ban
