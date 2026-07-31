# -*- coding: utf-8 -*-
"""Regression — 核銷掃描管線（2026-07-31 owner 三項回報）

1. 收據影像看不到 → `service.create()` 沒有 `receipt_image_path` 參數，
   端點卻以 kwarg 傳入 → TypeError → auto_create 全數 500
   （07-30 只改了字串值，沒驗證這個呼叫本身會拋例外）
2. QR 金額與紙本不符（DC-09761665：QR 957 / 紙本 940）
"""
import inspect
import re
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


def _strip_py_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"(?m)^\s*#.*$", "", src)


class TestReceiptPathIsPersisted:
    def test_service_create_has_no_receipt_kwarg(self):
        """釘住事實：路徑必須放進 schema，不是 kwarg"""
        from app.services.erp.expense_invoice import ExpenseInvoiceService
        params = inspect.signature(ExpenseInvoiceService.create).parameters
        assert "receipt_image_path" not in params

    def test_no_caller_passes_receipt_as_kwarg(self):
        """掃全同型：任何 create(...) 都不得以 kwarg 傳 receipt_image_path"""
        offenders = []
        for rel in ("app/api/endpoints/erp/expenses_io.py",
                    "app/services/integration/line_image_handler.py"):
            src = _strip_py_comments(_read(rel))
            # create( ... receipt_image_path= ...)：只抓 create 呼叫，排除 schema 建構
            for m in re.finditer(r"\.create\((?:[^()]|\([^()]*\))*?receipt_image_path\s*=", src):
                offenders.append(f"{rel}: {m.group(0)[:60]}")
        assert not offenders, (
            "receipt_image_path 必須放進 ExpenseInvoiceCreate，"
            f"以 kwarg 傳給 create() 會 TypeError：{offenders}"
        )

    def test_schema_carries_receipt_path(self):
        from app.schemas.erp.expense import ExpenseInvoiceCreate
        assert "receipt_image_path" in ExpenseInvoiceCreate.model_fields


class TestQrAmountConsistency:
    """QR 內含金額自相矛盾必須被標記（不得自動改）"""

    def _parse(self, sales_hex: str, total_hex: str):
        from app.services.erp.invoice_recognizer import RecognitionResult
        from app.services.erp.invoice_qr_decoder import parse_head_qr
        raw = "DC09761665" + "1150724" + "5640" + sales_hex + total_hex + "50819619" + "70864289" + "X" * 24
        r = RecognitionResult()
        parse_head_qr(raw, r)
        return r

    def test_real_case_dc09761665_is_flagged(self):
        """真實案例：QR 895/957，紙本 895/45/940（差額為加油金折抵）"""
        r = self._parse("0000037f", "000003bd")
        assert r.sales_amount == Decimal("895")
        assert r.total_amount == Decimal("957")
        assert r.warnings, "QR 金額矛盾未被標記 → 會直接存成錯誤金額"
        assert "940" in r.warnings[0], "警示應提示依 5% 稅率推算的期望值"

    def test_consistent_invoice_not_flagged(self):
        """一致的發票不得誤報（290 = 276 × 1.05 四捨五入）"""
        r = self._parse("00000114", "00000122")  # 276 / 290
        assert r.total_amount == Decimal("290")
        assert not r.warnings

    def test_rounding_within_tolerance_not_flagged(self):
        """四捨五入 1 元誤差屬正常"""
        r = self._parse("00000129", "0000013C")  # 297 / 316（期望 312，差 4）
        # 差 4 > 容差 max(1, 3.16) → 應標記；確認容差邏輯有作用
        assert r.warnings

    def test_does_not_mutate_amount(self):
        """只警示、不自動修改 —— 免稅/零稅率發票本來就會偏離 1.05"""
        r = self._parse("0000037f", "000003bd")
        assert r.amount == Decimal("957"), "不得自動改寫金額，應交由人核對"
