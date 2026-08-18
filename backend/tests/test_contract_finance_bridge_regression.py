# -*- coding: utf-8 -*-
"""Regression — 方案 B：承攬案件建立即產生財務橋樑（2026-07-31）

背景：`case_code` 是承攬案件通往財務/核銷的唯一橋樑（報價、費用核銷、核銷 QR 都靠它）。
直接建立的承攬案件不走「建案→成案」，case_code 恆為 NULL → 財務紀錄永遠空。
過去每次事後補 fallback，成因沒解決；B 方案在建立當下就補上。
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"(?m)^\s*#.*$", "", src)


class TestCaseCodeAutoGeneration:
    def test_create_generates_case_code_when_absent(self):
        src = _strip_comments(_read("app/services/contract/core.py"))
        m = re.search(r"async def create\(self, data: ProjectCreate\)[\s\S]*?return db_project", src)
        assert m, "找不到 ProjectService.create"
        body = m.group(0)
        assert 'if not project_data.get("case_code")' in body, "建立時未補 case_code"
        assert "generate_case_code" in body

    def test_case_code_generation_is_fail_soft(self):
        """產號失敗不得阻斷建案本身 —— 案件比橋樑重要

        ⚠️ 2026-08-18：原本取 `src[i:i+900]` 固定字元窗，而 08-18 在那段
        加了一段較長的註解（說明為何由 PM 改為 GN），`try:` 就被擠出窗外
        → 測試失敗，**但程式碼行為完全沒變**。

        固定字元窗會讓「寫了註解」與「刪掉 try」產生同一個結果。
        改為先去註解再取窗：斷言的對象是程式碼，註解長度不該影響它。
        """
        src = _strip_comments(_read("app/services/contract/core.py"))
        i = src.index('if not project_data.get("case_code")')
        seg = src[i:i + 900]
        assert "try:" in seg and "except Exception" in seg
        assert "logger.warning" in seg
        assert "raise" not in seg, "產號失敗不得 raise"

    def test_manual_creation_does_not_forge_pm_case_code(self):
        """手動建承攬案件**不得**產出 PM 式案號（2026-08-18 反轉原規則）。

        原測試斷言必須是 `"pm"`，理由寫「避免第三套命名體系」。
        那個前提本來就不成立 —— `FN`（ERP 產號器）早就在用，
        模組代碼本來就有多個，那是同一套體系裡的欄位不是另一套體系。

        真正的問題是：`ProjectService.create` 產 PM 式案號卻**不建立
        pm_cases 列**，於是 `CK2026_PM_01_008` 是一個長得像 PM 案件、
        指向的地方卻不存在的案號。實測 3 筆這樣的資料（全部執行中、
        全部有報價），而 2026 的 pm_cases 只到 `_007`。

        改用 `general`（GN）＝案號誠實表達「不是從 PM 建案來的」。
        跨模組唯一性不受影響 —— case_code 的職責是唯一鍵，不是宣告來源。
        """
        src = _strip_comments(_read("app/services/contract/core.py"))
        i = src.index("generate_case_code")
        seg = src[i:i + 200]
        assert '"pm"' not in seg, (
            "手動建立承攬案件不得用 PM 產號器 —— 它不建立 pm_cases 列，"
            "產出的案號會指向不存在的 PM 案件"
        )
        assert '"general"' in seg


class TestFinanceContainer:
    def test_container_creation_is_idempotent(self):
        """既有報價則跳過 —— 讓補跑既有案件也安全"""
        src = _read("app/services/contract/core.py")
        assert "_ensure_finance_container" in src
        i = src.index("async def _ensure_finance_container")
        body = src[i:i + 1800]
        assert "if existing:" in body and "return" in body

    def test_container_matches_both_keys(self):
        """比對 case_code 與 project_code 兩把鑰匙（既有資料兩者不一定同值）"""
        src = _read("app/services/contract/core.py")
        i = src.index("async def _ensure_finance_container")
        body = src[i:i + 1800]
        assert "ERPQuotation.case_code" in body
        assert "ERPQuotation.project_code" in body

    def test_container_leaves_amount_blank(self):
        """金額屬業務決策，不得自動填 —— 只帶預算上限"""
        src = _read("app/services/contract/core.py")
        i = src.index("async def _ensure_finance_container")
        body = src[i:i + 1800]
        assert "budget_limit=" in body
        assert "total_price=" not in body, "不得自動填總價"
        assert 'status="draft"' in body

    def test_container_failure_does_not_block_project(self):
        src = _read("app/services/contract/core.py")
        i = src.index("_ensure_finance_container(db_project)")
        seg = src[max(0, i - 300):i + 400]
        assert "try:" in seg and "except Exception" in seg
        assert "logger.warning" in seg
