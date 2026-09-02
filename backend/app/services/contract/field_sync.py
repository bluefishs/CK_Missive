"""
案件欄位三方同步服務

pm_cases ↔ contract_projects ↔ erp_quotations
以 case_code 或 project_code 為關聯 KEY，
任一方更新核心欄位時自動同步其餘兩方。

同步欄位: category, case_nature, client_name, contract_amount

Version: 1.0.0
Created: 2026-03-30
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 同步欄位清單
SYNC_FIELDS = ["category", "case_nature", "client_name", "contract_amount", "status"]


class CaseFieldSyncService:
    """案件欄位三方同步"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_from_pm(self, pm_case_id: int, changed_fields: Dict[str, Any]) -> Dict[str, bool]:
        """PM Case 更新後，同步到 ContractProject + ERPQuotation"""
        from app.extended.models.pm import PMCase
        from app.extended.models.core import ContractProject
        from app.extended.models.erp import ERPQuotation

        synced = {"contract_project": False, "erp_quotation": False}

        # 取得 PM Case
        result = await self.db.execute(select(PMCase).where(PMCase.id == pm_case_id))
        pm = result.scalar_one_or_none()
        if not pm or not pm.case_code:
            return synced

        # 2026-09-02：status 只允許承攬案→PM 案單向同步。PM 案的 status 是邀標階段語意
        # （planning/contracted/closed），承攬案的是執行階段語意（執行中/已結案），
        # 反向映射沒有意義；而 SYNC_FIELDS 是雙向共用的，同日為了修「結案不同步」
        # 加了 status 進去，這裡要明確擋掉，否則 PM 案改 status 會把英文值寫進承攬案。
        sync_data = {k: v for k, v in changed_fields.items() if k in SYNC_FIELDS and k != "status" and v is not None}
        if not sync_data:
            return synced

        # 同步到 ContractProject (via case_code or project_code)
        cp_result = await self.db.execute(
            select(ContractProject).where(
                (ContractProject.case_code == pm.case_code) |
                (ContractProject.project_code == pm.project_code)
            )
        )
        cp = cp_result.scalar_one_or_none()
        if cp:
            cp_update = {}
            if "category" in sync_data:
                cp_update["category"] = sync_data["category"]
            if "case_nature" in sync_data:
                cp_update["case_nature"] = sync_data["case_nature"]
            if "client_name" in sync_data:
                cp_update["client_agency"] = sync_data["client_name"]
            if "contract_amount" in sync_data:
                cp_update["contract_amount"] = float(sync_data["contract_amount"]) if sync_data["contract_amount"] else None
            if cp_update:
                for k, v in cp_update.items():
                    setattr(cp, k, v)
                synced["contract_project"] = True
                logger.info(f"[SYNC] PM→CP: pm_case={pm_case_id} → contract_project={cp.id} fields={list(cp_update.keys())}")

        # 同步到 ERPQuotation (via case_code)
        erp_result = await self.db.execute(
            select(ERPQuotation).where(ERPQuotation.case_code == pm.case_code)
        )
        erp = erp_result.scalar_one_or_none()
        if erp:
            erp_update = {}
            if "client_name" in sync_data:
                erp_update["client_name"] = sync_data["client_name"]
            if "contract_amount" in sync_data:
                erp_update["total_price"] = float(sync_data["contract_amount"]) if sync_data["contract_amount"] else None
            if erp_update:
                for k, v in erp_update.items():
                    setattr(erp, k, v)
                synced["erp_quotation"] = True
                logger.info(f"[SYNC] PM→ERP: pm_case={pm_case_id} → erp_quotation={erp.id} fields={list(erp_update.keys())}")

        return synced

    async def sync_from_contract(self, contract_project_id: int, changed_fields: Dict[str, Any]) -> Dict[str, bool]:
        """ContractProject 更新後，同步到 PMCase + ERPQuotation"""
        from app.extended.models.core import ContractProject
        from app.extended.models.pm import PMCase
        from app.extended.models.erp import ERPQuotation

        synced = {"pm_case": False, "erp_quotation": False}

        result = await self.db.execute(select(ContractProject).where(ContractProject.id == contract_project_id))
        cp = result.scalar_one_or_none()
        if not cp:
            return synced

        sync_data = {k: v for k, v in changed_fields.items() if k in SYNC_FIELDS + ["client_agency"] and v is not None}
        if not sync_data:
            return synced

        # 同步到 PM Case
        if cp.case_code:
            pm_result = await self.db.execute(select(PMCase).where(PMCase.case_code == cp.case_code))
            pm = pm_result.scalar_one_or_none()
            if pm:
                pm_update = {}
                if "category" in sync_data:
                    pm_update["category"] = sync_data["category"]
                if "case_nature" in sync_data:
                    pm_update["case_nature"] = sync_data["case_nature"]
                if "client_agency" in sync_data:
                    pm_update["client_name"] = sync_data["client_agency"]
                if "contract_amount" in sync_data:
                    pm_update["contract_amount"] = sync_data["contract_amount"]
                # 2026-09-02：承攬案結案時 PM 案不跟著結——實測 48 筆承攬案「已結案」而
                # PM 案仍 contracted，於是 /pm/cases 篩「已結案」看不到那 12 件未收款的案子
                #（owner：「已結案未收齊 12 件但 /pm/cases 僅顯示 1 筆」）。
                # 承攬案是主檔，它的狀態要映射到 PM 案；存量 48 筆已同日回填。
                if "status" in sync_data:
                    mapped = {"已結案": "closed", "執行中": "contracted"}.get(sync_data["status"])
                    if mapped:
                        pm_update["status"] = mapped
                if pm_update:
                    for k, v in pm_update.items():
                        setattr(pm, k, v)
                    synced["pm_case"] = True
                    logger.info(f"[SYNC] CP→PM: contract_project={contract_project_id} → pm_case={pm.id}")

        # 同步到 ERP
        if cp.case_code:
            erp_result = await self.db.execute(select(ERPQuotation).where(ERPQuotation.case_code == cp.case_code))
            erp = erp_result.scalar_one_or_none()
            if erp:
                if "case_nature" in sync_data:
                    # ERP 沒有 case_nature，只同步金額/客戶
                    pass
                if "client_agency" in sync_data:
                    erp.client_name = sync_data["client_agency"]
                    synced["erp_quotation"] = True
                if "contract_amount" in sync_data:
                    erp.total_price = float(sync_data["contract_amount"]) if sync_data["contract_amount"] else None
                    synced["erp_quotation"] = True

        return synced
