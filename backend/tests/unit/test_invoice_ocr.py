"""發票 OCR 辨識服務 — 單元測試

測試範圍:
- 發票號碼提取
- 日期解析 (民國/西元)
- 金額提取
- 統編提取 (買方/賣方)
- 信心度計算
- OCR 不可用時的降級處理
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.services.invoice_ocr_service import InvoiceOCRService, InvoiceOCRResult


class TestInvoiceOCRParsing:
    """OCR 文字解析邏輯測試 (不依賴 Tesseract)"""

    @pytest.fixture
    def service(self):
        return InvoiceOCRService()

    def test_extract_inv_num(self, service):
        """從文字中提取發票號碼"""
        result = service._parse_text("電子發票 AB12345678 開立日期")
        assert result.inv_num == "AB12345678"

    def test_extract_inv_num_none(self, service):
        """無發票號碼時回傳 None"""
        result = service._parse_text("一般文字沒有發票")
        assert result.inv_num is None
        assert "未偵測到發票號碼" in result.warnings

    def test_extract_roc_date(self, service):
        """民國日期解析"""
        result = service._parse_text("日期 115年03月21日")
        assert result.date == date(2026, 3, 21)

    def test_extract_roc_date_slash(self, service):
        """民國日期斜線格式"""
        result = service._parse_text("日期 115/03/21")
        assert result.date == date(2026, 3, 21)

    def test_extract_ce_date(self, service):
        """西元日期解析"""
        result = service._parse_text("2026/03/21 電子發票")
        assert result.date == date(2026, 3, 21)

    def test_extract_ce_date_dash(self, service):
        """西元日期 dash 格式"""
        result = service._parse_text("開立日 2026-03-21")
        assert result.date == date(2026, 3, 21)

    def test_extract_date_none(self, service):
        """無日期時回傳 None"""
        result = service._parse_text("發票 AB12345678 金額 100")
        assert result.date is None
        assert "未偵測到發票日期" in result.warnings

    def test_extract_amount_with_label(self, service):
        """帶標籤的金額"""
        result = service._parse_text("合計 1,050")
        assert result.amount == Decimal("1050")

    def test_extract_amount_nt_dollar(self, service):
        """NT$ 前綴金額"""
        result = service._parse_text("NT$2,500")
        assert result.amount == Decimal("2500")

    def test_extract_amount_total_label(self, service):
        """總額標籤"""
        result = service._parse_text("總額 500")
        assert result.amount == Decimal("500")

    def test_extract_amount_none(self, service):
        """無金額時回傳 None"""
        result = service._parse_text("一般文字")
        assert result.amount is None
        assert "未偵測到金額" in result.warnings

    def test_extract_tax(self, service):
        """提取稅額"""
        result = service._parse_text("稅額 50 合計 1,050")
        assert result.tax_amount == Decimal("50")

    def test_extract_tax_none(self, service):
        """無稅額時回傳 None"""
        result = service._parse_text("合計 1,050")
        assert result.tax_amount is None

    def test_extract_bans_with_context(self, service):
        """根據上下文區分買賣方統編"""
        text = "買方 12345678 賣方 87654321 合計 100"
        result = service._parse_text(text)
        assert result.buyer_ban == "12345678"
        assert result.seller_ban == "87654321"

    def test_extract_bans_positional(self, service):
        """無上下文時按順序分配 (賣方在前)"""
        text = "統編 11112222 33334444 合計 100"
        result = service._parse_text(text)
        assert result.seller_ban == "11112222"
        assert result.buyer_ban == "33334444"

    def test_bans_exclude_inv_num_digits(self, service):
        """排除發票號碼尾碼"""
        text = "AB12345678 統編 87654321 合計 100"
        result = service._parse_text(text)
        # 12345678 是發票號碼尾段，不應作為統編
        assert result.seller_ban == "87654321"
        assert result.buyer_ban is None

    def test_confidence_all_fields(self, service):
        """全欄位辨識時信心度 = 1.0"""
        text = "AB12345678 115年03月21日 買方 12345678 賣方 87654321 合計 1,050"
        result = service._parse_text(text)
        assert result.confidence == 1.0

    def test_confidence_partial(self, service):
        """部分欄位辨識時信心度 < 1.0"""
        result = service._parse_text("AB12345678 合計 500")
        assert 0 < result.confidence < 1.0

    def test_confidence_zero(self, service):
        """無欄位辨識時信心度 = 0"""
        result = service._parse_text("普通文字內容")
        assert result.confidence == 0.0

    def test_raw_text_truncated(self, service):
        """raw_text 限制在 2000 字內"""
        long_text = "AB12345678 " * 300
        result = service._parse_text(long_text)
        assert len(result.raw_text) <= 2000

    def test_full_invoice_text(self, service):
        """完整發票文字解析"""
        text = """
        電子發票證明聯
        AB12345678
        115年03月21日
        買方 12345678
        賣方/營業人 87654321
        品名 文具
        數量 2
        單價 50
        合計 100
        稅額 5
        總計 105
        """
        result = service._parse_text(text)
        assert result.inv_num == "AB12345678"
        assert result.date == date(2026, 3, 21)
        assert result.buyer_ban == "12345678"
        assert result.seller_ban == "87654321"
        assert result.tax_amount == Decimal("5")
        assert result.amount is not None


class TestInvoiceOCRImage:
    """OCR 影像辨識測試 (mock Tesseract)"""

    @pytest.fixture
    def service(self):
        return InvoiceOCRService()

    @patch('app.services.invoice_ocr_service._is_ocr_available', return_value=False)
    def test_ocr_unavailable(self, mock_avail, service):
        """OCR 不可用時回傳警告"""
        result = service.parse_image("/fake/path.jpg")
        assert "Tesseract OCR 未安裝" in result.warnings[0]

    @patch('app.services.invoice_ocr_service._is_ocr_available', return_value=True)
    @patch('app.services.invoice_ocr_service.InvoiceOCRService._extract_text')
    def test_parse_image_success(self, mock_extract, mock_avail, service):
        """成功解析影像"""
        mock_extract.return_value = "AB12345678 115年03月21日 合計 500"
        result = service.parse_image("/fake/invoice.jpg")
        assert result.inv_num == "AB12345678"
        assert result.amount == Decimal("500")

    @patch('app.services.invoice_ocr_service._is_ocr_available', return_value=True)
    @patch('app.services.invoice_ocr_service.InvoiceOCRService._extract_text')
    def test_parse_image_empty_text(self, mock_extract, mock_avail, service):
        """空白影像"""
        mock_extract.return_value = ""
        result = service.parse_image("/fake/blank.jpg")
        assert "影像辨識未提取到任何文字" in result.warnings
