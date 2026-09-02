# -*- coding: utf-8 -*-
"""Regression（2026-09-02 晚）——三表同步白名單含 case_name；quote_kind 推導單一來源。

背景：owner 的「完整案名」109 筆要三表各改一次，因為 `case_name` 不在 `SYNC_FIELDS`；
同日 owner 問「為何報價單有 01 委辦招標」——同一張表裝三種東西而沒有欄位標明。
"""
import re
from pathlib import Path

import pytest

from app.services.contract.field_sync import CONTRACT_SYNC_FIELDS, SYNC_FIELDS
from app.services.erp.quote_kind import BACKFILL_SQL, category_of, infer_quote_kind

BACKEND = Path(__file__).resolve().parents[1]


class TestSyncWhitelist:
    def test_case_name_in_whitelist(self):
        assert "case_name" in SYNC_FIELDS
        assert "project_name" in CONTRACT_SYNC_FIELDS and "client_agency" in CONTRACT_SYNC_FIELDS

    def test_contract_crud_uses_single_source(self):
        src = (BACKEND / "app/api/endpoints/projects/crud.py").read_text(encoding="utf-8")
        src = re.sub(r"(?m)^\s*#.*$", "", src)
        assert "CONTRACT_SYNC_FIELDS" in src
        assert not re.search(r"sync_fields\s*=\s*\[", src), "端點不得自抄一份欄位清單"

    def test_pm_cases_endpoint_uses_single_source(self):
        """PM 更新端點不得 inline 一份 `if k in ("category", ...)` —— 09-02 晚 probe：PM 改案名不同步"""
        src = (BACKEND / "app/api/endpoints/pm/cases.py").read_text(encoding="utf-8")
        src = re.sub(r"(?m)^\s*#.*$", "", src)
        inline = [m.group(0) for m in re.finditer(r'\bk in \(([^)]*)\)', src) if '"category"' in m.group(0)]
        assert not inline, f"pm/cases.py 有 inline 同步清單：{inline}"
        assert "SYNC_FIELDS" in src

    def test_erp_quotation_sync_targets_exist(self):
        """sync 寫到 ERPQuotation 的欄位必須真的存在 —— setattr 不存在的欄位是靜默不落地"""
        from app.extended.models.erp import ERPQuotation
        cols = {c.name for c in ERPQuotation.__table__.columns}
        fs = (BACKEND / "app/services/contract/field_sync.py").read_text(encoding="utf-8")
        fs = re.sub(r"(?m)^\s*#.*$", "", fs)  # 註解裡描述反例的那一行不算（判準範圍不得含描述它的文字）
        targets = set(re.findall(r'erp_update\["([a-z_]+)"\]', fs)) | set(re.findall(r"\berp\.([a-z_]+)\s*=", fs))
        missing = sorted(t for t in targets if t not in cols)
        assert not missing, f"field_sync 寫 ERPQuotation 不存在的欄位：{missing}"


KNOWN = [
    ("CK2026_PM_02_001", "02", "contract"),
    ("CK2026_GN_02_001", "02", "contract"),
    ("CK2025_02_01_001", "02", "contract"),
    ("CK2026_PM_01_005", "01", "tender"),
    ("CK2026_GN_01_001", "01", "tender"),
    ("CK2025_01_03_001", "01", "tender"),
    ("CK2026_FN_01_001", "01", "tender"),
    ("CK2025_03_01_002", "03", None),
    ("B115-C017b-0", None, None),
    ("", None, None),
]


class TestQuoteKind:
    @pytest.mark.parametrize("code,cat,kind", KNOWN)
    def test_python_rule(self, code, cat, kind):
        assert category_of(code) == cat
        assert infer_quote_kind(code) == kind

    def test_auto_created_is_anchor(self):
        assert infer_quote_kind("CK2026_PM_02_001", auto_created=True) == "finance_anchor"

    def test_backfill_sql_matches_migration(self):
        """migration 不 import 應用層，所以 SQL 存了兩份 —— 兩份必須逐字相同"""
        mig = next((BACKEND / "alembic/versions").glob("20260902a001_*.py")).read_text(encoding="utf-8")
        m = re.search(r'_BACKFILL = """([\s\S]*?)"""', mig)
        # 檔案文字裡是 `\d`（原始碼的兩個反斜線），BACKFILL_SQL 是求值後的 `\d` —— 只還原反斜線，
        # 不用 unicode_escape（它會把中文字打壞）
        assert m and m.group(1).replace("\\\\", "\\").strip() == BACKFILL_SQL.strip()

    def test_sql_rule_agrees_with_python(self):
        """把 SQL 的 CASE 用 Python 的 re 重跑一次，8 組已知案號兩邊答案要一致"""
        tender = re.compile(r"^CK\d{4}_(PM|GN|FN|DP)_01_|^CK\d{4}_01_\d{2}_")
        contract = re.compile(r"^CK\d{4}_(PM|GN|FN|DP)_02_|^CK\d{4}_02_\d{2}_")
        assert "_(PM|GN|FN|DP)_01_" in BACKFILL_SQL and "_(PM|GN|FN|DP)_02_" in BACKFILL_SQL
        for code, _cat, kind in KNOWN:
            sql_kind = "tender" if tender.search(code) else ("contract" if contract.search(code) else None)
            assert sql_kind == infer_quote_kind(code), code

    def test_three_write_paths_set_kind(self):
        """三條建立路徑各自帶明確值；漏一條就是下一批「未分類」"""
        cc = (BACKEND / "app/services/tender/case_creation.py").read_text(encoding="utf-8")
        assert 'quote_kind=("tender"' in cc
        pc = (BACKEND / "app/services/contract/case_code.py").read_text(encoding="utf-8")
        assert 'quote_kind="finance_anchor"' in pc
        qs = (BACKEND / "app/services/erp/quotation_service.py").read_text(encoding="utf-8")
        assert "infer_quote_kind" in qs

    def test_response_schema_exposes_kind(self):
        from app.schemas.erp.quotation import ERPQuotationResponse
        assert "quote_kind" in ERPQuotationResponse.model_fields
