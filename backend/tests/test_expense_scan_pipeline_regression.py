# -*- coding: utf-8 -*-
"""Regression — 核銷掃描管線（2026-07-31 owner 三項回報）

1. 收據影像看不到 → `service.create()` 沒有 `receipt_image_path` 參數，
   端點卻以 kwarg 傳入 → TypeError → auto_create 全數 500
   （07-30 只改了字串值，沒驗證這個呼叫本身會拋例外）
2. QR 金額與紙本不符（DC-09761665：QR 957 / 紙本 940）
"""
import inspect
import pytest
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


class TestOutboundNotificationGuard:
    """守護「安全網」本身 —— 它保護的是 owner 的 LINE 月配額（200 則）

    2026-07-31：跑測試把兩則真實告警推到 owner 手機。加了 autouse 安全網後，
    這個守護確保它不會在未來被無聲移除或 patch 錯層。
    """

    def test_guard_fixture_exists_and_is_autouse(self):
        src = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
        assert "_block_outbound_notifications" in src
        i = src.index("_block_outbound_notifications")
        assert "autouse=True" in src[max(0, i - 200):i]

    def test_guard_blanks_credentials_rather_than_patching_methods(self):
        """抽憑證，不替換方法 —— 替換方法會打斷『正在測那個方法』的測試

        同日兩次踩到：v1 換掉 push_message、v2 換掉 _call_line_api，
        都打斷了原本就安全的測試。v3 改為抽掉 token。
        """
        import re as _re
        raw = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
        # 必須先剝註解：conftest 的沿革註解裡就寫著 push_message / _call_line_api
        #（同日第三次踩到「比對命中自己的說明文字」）
        src = _re.sub(r'"""[\s\S]*?"""', "", raw)
        src = _re.sub(r"(?m)^\s*#.*$", "", src)
        i = src.index("blanked = {")
        block = src[i:i + 600]
        assert "LINE_CHANNEL_ACCESS_TOKEN" in block
        assert "TELEGRAM_BOT_TOKEN" in block
        assert "patch(\"app.services.integration" not in src, "不得替換 LINE/Telegram 服務方法"

    def test_outbound_credentials_are_absent_at_runtime(self):
        """實際驗證：測試執行期沒有任何對外憑證（而非只看原始碼）"""
        import os
        for k in ("LINE_CHANNEL_ACCESS_TOKEN", "TELEGRAM_BOT_TOKEN"):
            assert not os.getenv(k), f"{k} 在測試環境仍有值 → 可能真的送出訊息"

    @pytest.mark.asyncio
    async def test_line_service_is_disabled_by_default_in_tests(self):
        """預設建立的 LineBotService 應為 disabled → push 直接回 False"""
        from app.services.integration.line_bot import LineBotService
        svc = LineBotService()
        assert svc.enabled is False
        assert await svc.push_message("U_test", "should not send") is False
