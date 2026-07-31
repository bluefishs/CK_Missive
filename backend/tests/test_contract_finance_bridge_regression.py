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
        """產號失敗不得阻斷建案本身 —— 案件比橋樑重要"""
        src = _read("app/services/contract/core.py")
        i = src.index('if not project_data.get("case_code")')
        seg = src[i:i + 900]
        assert "try:" in seg and "except Exception" in seg
        assert "logger.warning" in seg
        assert "raise" not in _strip_comments(seg), "產號失敗不得 raise"

    def test_uses_pm_module_code_for_consistency(self):
        """case_code 語意即「建案案號」，應用 PM 產號器（避免第三套命名體系）"""
        src = _strip_comments(_read("app/services/contract/core.py"))
        i = src.index("generate_case_code")
        assert '"pm"' in src[i:i + 200]


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
