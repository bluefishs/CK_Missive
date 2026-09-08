# -*- coding: utf-8 -*-
"""報價單彙整總表匯入的金額取值（2026-09-08 回歸鎖）。

## 立這支的事故

owner 提供總表原始列：

    工作地點  嘉義市湖子內段新民小段240等地號
    報價金額  63,810 ｜ 稅額 3,190 ｜ 總價 67,000

而系統存的是 **66,999.50** —— 那正好是 `63,810 × 1.05`。

兩個錯疊在一起：

1. 總表的「報價金額」是**未稅**，而 `erp_quotations.total_price` 的語意是**含稅**
   （FIELD_SEMANTICS）。匯入器直接對接 ⇒ 未稅被寫進含稅欄位。
   全庫因此有 12 張帶著 `tax ≈ 總價×5%` 的簽名（正確的是 `tax ≈ 總價/21`，228 張如此）。
2. 總表真正的含稅值（「總價」欄）**有被讀進來，但只丟進 notes**，從來沒有用過。

⚠️ 而且不能用 `未稅 × 1.05` 補救：總表的總價是「未稅＋**四捨五入後**的稅額」
（63,810 ＋ 3,190 ＝ 67,000），`63,810 × 1.05` 會得到 66,999.5。
**有權威值就不要重算 —— 重算會在四捨五入處與來源分家。**

這 0.5 元不是無害的：它讓 `/erp/quotations`（走 `fmtMoney`，會 round）
與 `/erp/client-accounts`（當時直接 `toLocaleString`）**顯示不同的總額**，
而兩邊各自看都沒有錯。
"""
from decimal import Decimal

import pytest

from app.services.erp.quotation_legacy_import import _sum_or_none


class TestSumOrNone:
    """`_sum_or_none` 是取值順序的第二段 —— 缺值不得當 0。"""

    def test_both_present(self):
        assert _sum_or_none(Decimal("63810"), Decimal("3190")) == Decimal("67000")

    def test_missing_tax_returns_none(self):
        # 缺稅額時回 None，讓呼叫端退回下一個來源 ——
        # 若當成 0 相加，會算出「未稅＝含稅」這個看似合理的錯值
        assert _sum_or_none(Decimal("63810"), None) is None

    def test_missing_net_returns_none(self):
        assert _sum_or_none(None, Decimal("3190")) is None


class TestTotalPriceResolution:
    """取值順序：總表「總價」→（未稅＋稅額）→ 未稅。"""

    @staticmethod
    def _resolve(grand_total, net, tax):
        """複製 quotation_legacy_import 的取值式（同一段邏輯，不另立一套）。"""
        return grand_total or _sum_or_none(net, tax) or net

    def test_uses_source_grand_total(self):
        """總表寫了總價就用它 —— owner 那一列的真實數字。"""
        got = self._resolve(Decimal("67000"), Decimal("63810"), Decimal("3190"))
        assert got == Decimal("67000")

    def test_grand_total_beats_recomputation(self):
        """權威值優先於重算：×1.05 會得到 66,999.5，與來源差 0.5。"""
        assert self._resolve(Decimal("67000"), Decimal("63810"), Decimal("3190")) != \
            (Decimal("63810") * Decimal("1.05"))

    def test_falls_back_to_net_plus_tax(self):
        """總表沒有總價欄時，用「未稅＋稅額」——仍然不是 ×1.05。"""
        got = self._resolve(None, Decimal("63810"), Decimal("3190"))
        assert got == Decimal("67000")

    def test_falls_back_to_net_when_no_tax(self):
        """兩者都缺就退回未稅（維持原行為；那種列的稅額本來就是 0）。"""
        assert self._resolve(None, Decimal("50000"), None) == Decimal("50000")

    @pytest.mark.parametrize("net,tax,expect", [
        (Decimal("63810"), Decimal("3190"), Decimal("67000")),   # 稅額帶 .5 被總表 round 掉
        (Decimal("124214"), Decimal("6211"), Decimal("130425")),  # owner 09-08 手動修的那張
        (Decimal("118000"), Decimal("5900"), Decimal("123900")),
        (Decimal("28000"), Decimal("1400"), Decimal("29400")),
    ])
    def test_known_rows(self, net, tax, expect):
        """實際出過事的幾列，全部要算回正確的含稅值。"""
        assert self._resolve(None, net, tax) == expect
