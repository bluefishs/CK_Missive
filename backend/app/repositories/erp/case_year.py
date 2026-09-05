# -*- coding: utf-8 -*-
"""案件類統計的年度口徑（2026-09-05 owner 裁示）：年度＝案號年 `CK{年}`，不是 `erp_quotations.year`。

為什麼：`erp_quotations.year` 是報價單「建立那年」——舊案在 2026 補建的錨點報價單 year=2026，
14/277 張成案報價單與案號年不同（桃園 CK2023_01_01_001 的報價單 year=2026）⇒ 用報價單年篩 2026
會把 2023、2025 的案列進來。專案帳款頁（quotation_repository）早已用案號年；委託單位帳款、廠商帳款、
帳齡此前用報價單年，同一個 2026 三頁三種答案。這裡只留一個實作，誰要篩年度都從這裡拿條件。
非 CK 制案號（極少數舊資料）退回 `year` 欄位。權威：FIELD_SEMANTICS「年度篩選的口徑」。
"""
from __future__ import annotations

from sqlalchemy import or_

from app.extended.models.erp import ERPQuotation


def quotation_case_year_condition(year: int):
    """回 SQLAlchemy 條件：報價單所屬案件的年度＝year。"""
    return or_(
        ERPQuotation.case_code.like(f"CK{int(year)}_%"),
        # 案號不是 CK 制的舊資料才看 year 欄
        (~ERPQuotation.case_code.like("CK%")) & (ERPQuotation.year == int(year)),
    )
