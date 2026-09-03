# -*- coding: utf-8 -*-
"""匯入「已成立」的新 PM 案必須走正式 promote，不可只寫 status=contracted（2026-09-04 金流複查）。

09-03 那次匯入留下 16 筆 PM 案標已承攬而沒有承攬案：承攬列表看不到、報價單沒 project_code、
損益摘要當未成案、掛著的請款在成案口徑裡消失 —— 每張表單獨看都「正常」。
三支測試不打 DB：db 是 AsyncMock，promote 被替換掉，只驗「有沒有叫、叫幾次、擋住有沒有記下來」。
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.erp.quotation_legacy_import import QuotationLegacyImportService


def _svc():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.flush = AsyncMock()
    db.add = MagicMock()
    svc = QuotationLegacyImportService(db)
    svc.code_service = MagicMock()
    svc.code_service.promote_to_project = AsyncMock(return_value={"project_code": "CK2026_02_999"})
    return svc


def _row(legacy, established, name="測試案"):
    return {"legacy_no": legacy, "case_name": name, "year": 2026, "client_name": None,
            "total_price": 1000, "established": established, "quoted_date": date(2026, 1, 1), "location": None}


@pytest.mark.asyncio
async def test_established_new_case_is_promoted():
    svc = _svc()
    n = await svc._ensure_pm_cases([_row("B115-T001-0", True), _row("B115-T002-0", False, "未成立")],
                                   code_of={"B115-T001-0": "CK2026_PM_02_901", "B115-T002-0": "CK2026_PM_02_902"})
    assert n == 2
    svc.code_service.promote_to_project.assert_awaited_once_with("CK2026_PM_02_901")
    assert svc.promoted_count == 1 and svc.promote_failures == []


@pytest.mark.asyncio
async def test_promote_blocked_is_recorded_not_swallowed():
    svc = _svc()
    svc.code_service.promote_to_project = AsyncMock(side_effect=ValueError("同名承攬案件已存在：CK2026_02_001"))
    await svc._ensure_pm_cases([_row("B115-T003-0", True)], code_of={"B115-T003-0": "CK2026_PM_02_903"})
    assert svc.promoted_count == 0
    assert svc.promote_failures and svc.promote_failures[0]["case_code"] == "CK2026_PM_02_903"
    assert "同名" in svc.promote_failures[0]["reason"]


@pytest.mark.asyncio
async def test_dry_run_reports_but_never_promotes():
    svc = _svc()
    n = await svc._ensure_pm_cases([_row("B115-T004-0", True)], dry_run=True, code_of={"B115-T004-0": None})
    assert n == 1 and svc.will_promote == 1
    svc.code_service.promote_to_project.assert_not_awaited()
    svc.db.add.assert_not_called()
