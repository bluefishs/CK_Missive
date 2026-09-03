# -*- coding: utf-8 -*-
"""Regression（2026-09-03）——成案即應收：自動第一期的三個掛點與規則。

owner：「有報價費用應收總額就自動新增第一期費用數據，以利建構後續通報與稽催機制，非常重要」。
沒有第一期，夜間吹哨者的 billing_overdue 對那個案子永遠不會響——09-03 量到 90 張 3,109 萬。
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _src(rel: str) -> str:
    s = (BACKEND / rel).read_text(encoding="utf-8")
    s = re.sub(r'"""[\s\S]*?"""', "", s)
    return re.sub(r"(?m)^\s*#.*$", "", s)


class TestEnsureFirstPeriod:
    def test_method_exists_and_uses_create(self):
        """走 create()（有合約上限守衛、同日同額查重、billing_code、帳本同步），不直接 INSERT"""
        s = _src("app/services/erp/billing_service.py")
        m = re.search(r"async def ensure_first_period\([\s\S]*?\n    async def ", s)
        assert m, "ensure_first_period 不存在"
        body = m.group(0)
        assert "await self.create(" in body
        assert '"一次請領"' in body and "pending" in body
        assert "return None" in body and "except Exception" in body, "失敗必須只 log 不 raise"

    def test_guards(self):
        s = _src("app/services/erp/billing_service.py")
        body = re.search(r"async def ensure_first_period\([\s\S]*?\n    async def ", s).group(0)
        assert "total_price" in body and "<= 0" in body, "無總額不建"
        assert "project_code" in body, "未成案不建"
        assert "erp_quotation_id == quotation_id" in body, "已有請款不建"

    def test_three_hooks(self):
        """成案／新建報價單／更新報價單三條路都要掛，漏一條就是下一批 90 張"""
        assert "ensure_first_period(" in _src("app/services/contract/case_code.py")
        qs = _src("app/services/erp/quotation_service.py")
        assert qs.count("ensure_first_period(") >= 2, "quotation_service 的 create 與 update 都要掛"
        assert '"total_price" in changes' in qs

    def test_weekly_103_registered(self):
        sh = (BACKEND.parent / "scripts/checks/run_fitness_weekly.sh").read_text(encoding="utf-8")
        assert 'run_step "103"' in sh and "first_billing_presence_audit.py" in sh
