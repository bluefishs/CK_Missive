# -*- coding: utf-8 -*-
"""匯入服務 step 6 — 案件身分改由 code_of 決定（2026-08-28 A32 之後）

鎖定的語意：A32 把存量 pm_cases 全轉為 CK 建案案號之後，匯入若仍用
`_derive_case_code(legacy_no)`（＝報價單編號原文）去比對 pm_cases，
既有案子永遠「找不到」⇒ 每次匯入都重複建案（08-20 那 36 組分身的同型）。

修法：呼叫端傳 `code_of`（legacy_no → case_code）：
  · 既有報價單 → 它現在的 CK case_code ⇒ 案子找得到、不重建
  · 新業務 → dry-run 為 None（計為必建、不耗流水號）；寫入前必須先產號
"""
import pytest

from app.extended.models.pm import PMCase
from app.services.erp.quotation_legacy_import import QuotationLegacyImportService

ROW = {
    "legacy_no": "B114-T999-0",
    "case_name": "回歸測試－匯入案件身分",
    "client_name": None,
    "year": 2025,
    "quoted_date": None,
    "total_price": None,
    "established": True,
    "location": None,
}


@pytest.mark.asyncio
async def test_existing_case_under_ck_code_is_found_not_duplicated(db_session):
    # 既有案子：A32 轉換後的形態 —— case_code 是 CK 碼，舊編號不在 pm_cases 上
    db_session.add(PMCase(
        case_code="CK2025_PM_02_901", case_name=ROW["case_name"],
        year=2025, category="02", status="contracted",
    ))
    await db_session.flush()

    svc = QuotationLegacyImportService.__new__(QuotationLegacyImportService)
    svc.db = db_session

    # 修法後：code_of 指到 CK 碼 ⇒ 找得到 ⇒ 不補建
    n = await svc._ensure_pm_cases(
        [dict(ROW)], dry_run=True,
        code_of={ROW["legacy_no"]: "CK2025_PM_02_901"},
    )
    assert n == 0, "既有案子（CK 碼）必須被找到 —— 補建數應為 0"

    # 反證（舊行為）：用 legacy 原文比對 ⇒ 找不到 ⇒ 會再建一件
    n_old = await svc._ensure_pm_cases([dict(ROW)], dry_run=True, code_of=None)
    # 2026-08-31 起 `_ensure_pm_cases` 對 CK 制案號也做「同名即分身」比對（08-20 那 26 件分身的修法），
    # 所以即使 legacy 原文對不到 CK 碼，同名的既有案也會被認出、不再補建 ⇒ 舊行為的危害已由第二道守門擋住。
    # 這裡改記新契約：兩條路都不得補建。若這裡變回 1，代表同名比對被拿掉了。
    assert n_old == 0, "同名既有案（CK 碼）也必須被認出 —— 08-31 起由同名比對兜底，補建數應為 0"


@pytest.mark.asyncio
async def test_new_business_counts_in_dry_run_and_blocks_write_without_code(db_session):
    svc = QuotationLegacyImportService.__new__(QuotationLegacyImportService)
    svc.db = db_session

    # dry-run：新業務（code None）計為必建，不需要先耗流水號
    n = await svc._ensure_pm_cases(
        [dict(ROW)], dry_run=True, code_of={ROW["legacy_no"]: None},
    )
    assert n == 1

    # 寫入模式：漏產號必須出聲，不得靜靜少建
    with pytest.raises(ValueError, match="沒有建案案號"):
        await svc._ensure_pm_cases(
            [dict(ROW)], dry_run=False, code_of={ROW["legacy_no"]: None},
        )
