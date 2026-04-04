"""
統一發票辨識器單元測試

測試 QR Head/Detail 解析邏輯（不依賴影像/pyzbar/OCR）。
"""
import pytest
from datetime import date
from decimal import Decimal

from app.services.invoice_recognizer import (
    RecognitionResult,
    _parse_head_qr,
    _parse_detail_qr,
    InvoiceItem,
)


class TestParseHeadQR:
    """QR Head 解析 (財政部 77 字元規範)"""

    # 範例 QR Head: AB12345678 11506150001 00001388 0000017A 00000000 12345678 ...驗證碼...
    # inv_num=AB12345678, 民國115年06月15日, 隨機碼=0001
    # 銷售額=0x00001388=5000, 總額=0x0000017A=... wait, let me construct a proper one
    # 銷售額 hex 00001388 = 5000, 總額 hex 00001482 = 5250 (含稅)
    SAMPLE_QR = "AB123456781150615000100001388000014820000000012345678ABCDEFGHIJKLMNOPQRSTUVWX"

    def test_parse_inv_num(self):
        """發票號碼正確解析"""
        result = RecognitionResult()
        _parse_head_qr(self.SAMPLE_QR, result)
        assert result.inv_num == "AB12345678"

    def test_parse_date_roc_to_ad(self):
        """民國年正確轉為西元"""
        result = RecognitionResult()
        _parse_head_qr(self.SAMPLE_QR, result)
        assert result.date == date(2026, 6, 15)  # 民國115 + 1911

    def test_parse_random_code(self):
        """隨機碼正確解析"""
        result = RecognitionResult()
        _parse_head_qr(self.SAMPLE_QR, result)
        assert result.random_code == "0001"

    def test_parse_amounts_hex(self):
        """銷售額與總額 hex 解碼正確"""
        result = RecognitionResult()
        _parse_head_qr(self.SAMPLE_QR, result)
        assert result.sales_amount == Decimal("5000")  # 0x00001388
        assert result.total_amount == Decimal("5250")   # 0x00001482
        assert result.amount == result.total_amount
        assert result.tax_amount == Decimal("250")

    def test_parse_buyer_ban_zero_is_none(self):
        """買方統編 00000000 應為 None"""
        result = RecognitionResult()
        _parse_head_qr(self.SAMPLE_QR, result)
        assert result.buyer_ban is None

    def test_parse_seller_ban(self):
        """賣方統編正確解析"""
        result = RecognitionResult()
        _parse_head_qr(self.SAMPLE_QR, result)
        assert result.seller_ban == "12345678"

    def test_parse_with_buyer_ban(self):
        """有買方統編時不應為 None"""
        qr = "CD987654321150615000100001388000014828765432112345678ABCDEFGHIJKLMNOPQRSTUVWX"
        result = RecognitionResult()
        _parse_head_qr(qr, result)
        assert result.buyer_ban == "87654321"
        assert result.seller_ban == "12345678"

    def test_parse_zero_tax(self):
        """免稅發票 (銷售額 = 總額)"""
        # 銷售額 = 總額 = 0x00002710 = 10000
        qr = "EF123456781150101999900002710000027100000000099887766ABCDEFGHIJKLMNOPQRSTUVWX"
        result = RecognitionResult()
        _parse_head_qr(qr, result)
        assert result.sales_amount == Decimal("10000")
        assert result.total_amount == Decimal("10000")
        assert result.tax_amount == Decimal("0")


class TestParseDetailQR:
    """QR Detail 解析 (品項明細)"""

    def test_basic_items(self):
        """基本品項解析 (3 個一組)"""
        raw = "**:咖啡:1:50:三明治:2:35"
        items = _parse_detail_qr(raw)
        assert len(items) == 2
        assert items[0].name == "咖啡"
        assert items[0].qty == 1.0
        assert items[0].unit_price == 50.0
        assert items[0].amount == 50.0
        assert items[1].name == "三明治"
        assert items[1].qty == 2.0
        assert items[1].amount == 70.0

    def test_empty_string(self):
        """空字串回傳空列表"""
        items = _parse_detail_qr("")
        assert items == []

    def test_only_prefix(self):
        """只有 ** 前綴"""
        items = _parse_detail_qr("**")
        assert items == []

    def test_single_item(self):
        """單一品項"""
        items = _parse_detail_qr("**:影印紙:3:150")
        assert len(items) == 1
        assert items[0].name == "影印紙"
        assert items[0].amount == 450.0

    def test_incomplete_group_skipped(self):
        """不完整的組應被跳過"""
        raw = "**:完整品:1:100:殘缺品:2"
        items = _parse_detail_qr(raw)
        assert len(items) == 1
        assert items[0].name == "完整品"

    def test_base64_encoded(self):
        """Base64 編碼的 Detail QR"""
        import base64
        plain = "**:紙杯:10:5"
        encoded = base64.b64encode(plain.encode("utf-8")).decode()
        items = _parse_detail_qr(encoded)
        assert len(items) == 1
        assert items[0].name == "紙杯"


class TestRecognitionResultToDict:
    """RecognitionResult.to_dict() 序列化"""

    def test_empty_result(self):
        """空結果應有基本結構"""
        r = RecognitionResult()
        d = r.to_dict()
        assert d["success"] is False
        assert d["method"] == ""
        assert d["items"] == []

    def test_full_result(self):
        """完整結果包含所有欄位"""
        r = RecognitionResult(
            success=True, method="qr",
            inv_num="AB12345678", date=date(2026, 1, 1),
            amount=Decimal("1000"), confidence=0.95,
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["inv_num"] == "AB12345678"
        assert d["confidence"] == 0.95
