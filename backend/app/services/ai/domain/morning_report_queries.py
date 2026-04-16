# -*- coding: utf-8 -*-
"""Morning Report Queries — 晨報資料查詢層

從 morning_report_service.py 拆分的查詢職責標記。
目前查詢方法仍留在 MorningReportService（與 db session 緊耦合），
此模組提供 MorningReportQueries 作為未來遷移的目標類別。

Phase 1 (current): 標記拆分邊界，queries 仍在 service
Phase 2 (future): 將 _get_* 方法逐步遷移至此

Version: 1.0.0
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MorningReportQueries:
    """晨報資料查詢層 — 所有 DB 查詢的目標存放處。

    Phase 1: 僅作為實例化標記；實際查詢仍在 MorningReportService。
    Phase 2: 逐步將 _get_dispatch_deadlines 等方法遷入。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
