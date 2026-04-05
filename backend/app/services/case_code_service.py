"""統一案號編碼服務

參照公文系統專案編碼機制 CK{年度}_{類別}_{性質}_{流水號}，擴充為跨模組統一案號。

編碼格式: CK{年度4碼}_{模組2碼}_{類別2碼}_{流水號3碼}

模組代碼:
  PM = 專案管理 (Project Management)
  FN = 財務管理 (Finance/ERP)
  DP = 派工管理 (Dispatch)
  GN = 一般委辦 (General，相容既有 contract_projects)

類別代碼 (依模組):
  PM: 01=委辦招標, 02=承攬報價
  FN: 01=報價單, 02=變更單, 03=追加減, 99=其他
  DP: 01=地上物, 02=土地查估, 03=計畫書, 04=測量, 99=其他
  GN: 01=委辦招標, 02=承攬報價

範例:
  CK2025_PM_01_001 → 2025年 PM 測量案第1號
  CK2025_FN_01_001 → 2025年 ERP 報價單第1號
  CK2025_DP_02_001 → 2025年 派工 土地查估第1號

Version: 1.1.0
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pm.case_repository import PMCaseRepository
from app.repositories.erp.quotation_repository import ERPQuotationRepository
from app.repositories import ProjectRepository, DocumentRepository

logger = logging.getLogger(__name__)

# ============================================================================
# 模組與類別常數定義 (SSOT)
# ============================================================================

MODULE_CODES = {
    "pm": "PM",
    "erp": "FN",
    "dispatch": "DP",
    "general": "GN",
}

PM_CATEGORY_CODES = {
    "01": "委辦招標",
    "02": "承攬報價",
}

ERP_CATEGORY_CODES = {
    "01": "報價單",
    "02": "變更單",
    "03": "追加減",
    "99": "其他",
}

DISPATCH_CATEGORY_CODES = {
    "01": "地上物查估",
    "02": "土地查估",
    "03": "計畫書",
    "04": "測量作業",
    "99": "其他",
}

GENERAL_CATEGORY_CODES = {
    "01": "委辦招標",
    "02": "承攬報價",
}

MODULE_CATEGORIES = {
    "PM": PM_CATEGORY_CODES,
    "FN": ERP_CATEGORY_CODES,
    "DP": DISPATCH_CATEGORY_CODES,
    "GN": GENERAL_CATEGORY_CODES,
}


class CaseCodeService:
    """統一案號編碼服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pm_repo = PMCaseRepository(db)
        self.erp_repo = ERPQuotationRepository(db)
        self.project_repo = ProjectRepository(db)
        self.doc_repo = DocumentRepository(db)

    async def generate_case_code(
        self,
        module: str,
        year: int,
        category: str = "01",
    ) -> str:
        """
        自動產生統一案號

        Args:
            module: 模組代碼 ('pm', 'erp', 'dispatch', 'general')
            year: 年度 (民國年或西元年，自動處理)
            category: 類別代碼 ('01', '02', ...)

        Returns:
            案號字串，例如 CK2025_PM_01_001
        """
        mod_code = MODULE_CODES.get(module.lower())
        if not mod_code:
            raise ValueError(f"未知模組: {module}，可用: {list(MODULE_CODES.keys())}")

        cat_code = category[:2].zfill(2) if category else "01"
        year_str = str(year) if year > 1911 else str(year + 1911)

        prefix = f"CK{year_str}_{mod_code}_{cat_code}_"

        # 查詢所有同 prefix 的案號 (跨 PM + ERP 表)
        next_serial = await self._find_next_serial(prefix)

        return f"{prefix}{str(next_serial).zfill(3)}"

    async def _find_next_serial(self, prefix: str) -> int:
        """在 PM/ERP 表中查找最大流水號"""
        max_serial = 0

        # 查 PM
        pm_max = await self.pm_repo.get_max_case_code_by_prefix(prefix)
        if pm_max:
            try:
                serial = int(pm_max.split("_")[-1])
                max_serial = max(max_serial, serial)
            except (IndexError, ValueError):
                pass

        # 查 ERP
        erp_max = await self.erp_repo.get_max_case_code_by_prefix(prefix)
        if erp_max:
            try:
                serial = int(erp_max.split("_")[-1])
                max_serial = max(max_serial, serial)
            except (IndexError, ValueError):
                pass

        return max_serial + 1

    async def validate_case_code(self, case_code: str) -> bool:
        """驗證案號格式是否合規"""
        parts = case_code.split("_")
        if len(parts) != 4:
            return False
        if not parts[0].startswith("CK") or not parts[0][2:].isdigit():
            return False
        if parts[1] not in MODULE_CODES.values():
            return False
        if not parts[2].isdigit() or len(parts[2]) != 2:
            return False
        if not parts[3].isdigit() or len(parts[3]) != 3:
            return False
        return True

    async def check_duplicate(self, case_code: str) -> bool:
        """檢查案號是否已存在 (跨 PM + ERP)"""
        if await self.pm_repo.exists_by_case_code(case_code):
            return True
        return await self.erp_repo.exists_by_case_code(case_code)

    @staticmethod
    def parse_case_code(case_code: str) -> Optional[dict]:
        """解析案號結構"""
        parts = case_code.split("_")
        if len(parts) != 4:
            return None
        try:
            year = int(parts[0][2:])
            module = parts[1]
            category = parts[2]
            serial = int(parts[3])
            # 查模組標籤
            mod_name = {v: k for k, v in MODULE_CODES.items()}.get(module, "unknown")
            # 查類別標籤
            cat_labels = MODULE_CATEGORIES.get(module, {})
            cat_name = cat_labels.get(category, "未定義")
            return {
                "year": year,
                "module": module,
                "module_name": mod_name,
                "category": category,
                "category_name": cat_name,
                "serial": serial,
                "formatted": case_code,
            }
        except (ValueError, IndexError):
            return None

    async def generate_project_code(
        self, year: int, category: str = "01", case_nature: str = "01",
    ) -> str:
        """產生成案專案編號 (project_code)

        格式: {年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}
        範例: 2026_01_01_001

        類別: 01委辦招標(政府機關), 02承攬報價
        性質: 01地面測量, 02LiDAR掃描, 03UAV空拍, 04航空測量,
              05安全檢測, 06建物保存, 07建築線測量, 08透地雷達,
              09資訊系統, 10技師簽證, 11其他類別
        """
        year_str = str(year) if year > 1911 else str(year + 1911)
        cat_code = category[:2].zfill(2) if category else "01"
        nat_code = case_nature[:2].zfill(2) if case_nature else "01"
        prefix = f"CK{year_str}_{cat_code}_{nat_code}_"

        # 查最大流水號 (同時查有/無 CK 前綴，相容舊資料)
        max_code = await self.project_repo.get_max_project_code_by_prefix(prefix)
        old_prefix = f"{year_str}_{cat_code}_{nat_code}_"
        old_max = await self.project_repo.get_max_project_code_by_prefix(old_prefix)

        next_serial = 1
        for code in (max_code, old_max):
            if code:
                try:
                    serial = int(code.split("_")[-1])
                    next_serial = max(next_serial, serial + 1)
                except (IndexError, ValueError):
                    pass

        return f"{prefix}{str(next_serial).zfill(3)}"

    async def promote_to_project(self, case_code: str) -> dict:
        """成案觸發：從 PM Case 自動建立 ContractProject + 連結 ERP Quotation

        1. 查找 PM Case
        2. 產生 project_code
        3. 建立 ContractProject (繼承基本欄位 + case_code)
        4. 更新 PM Case 的 project_code + status
        5. 更新 ERP Quotation 的 project_code (如存在)

        Returns:
            {'project_code': str, 'contract_project_id': int, 'erp_linked': bool}
        """
        # 1. 查找 PM Case + 狀態檢查
        pm_case = await self.pm_repo.get_by_case_code(case_code)
        if not pm_case:
            raise ValueError(f"找不到案號 {case_code}")
        if pm_case.project_code:
            raise ValueError(f"案號 {case_code} 已成案，project_code={pm_case.project_code}")
        # 僅「已承攬」狀態允許成案 (planning/closed 不可)
        blocked_statuses = ("planning", "closed")
        if pm_case.status in blocked_statuses:
            raise ValueError(f"案號 {case_code} 狀態為 {pm_case.status}，僅已承攬案件可成案")

        # 2. 產生 project_code (含作業性質)
        project_code = await self.generate_project_code(
            year=pm_case.year or 114,
            category=pm_case.category or "01",
            case_nature=getattr(pm_case, 'case_nature', None) or "01",
        )

        # 3. 建立 ContractProject (透過 Repository)
        contract_project = await self.project_repo.create({
            "project_name": pm_case.case_name,
            "project_code": project_code,
            "case_code": case_code,
            "year": pm_case.year,
            "category": pm_case.category,
            "case_nature": getattr(pm_case, 'case_nature', None),
            "client_agency": pm_case.client_name,
            "contract_amount": float(pm_case.contract_amount) if pm_case.contract_amount else None,
            "start_date": pm_case.start_date,
            "end_date": pm_case.end_date,
            "status": "執行中",
            "location": getattr(pm_case, 'location', None),
            "description": pm_case.description,
            "notes": pm_case.notes,
        }, auto_commit=False)

        # 4. 更新 PM Case
        pm_case.project_code = project_code
        pm_case.status = "in_progress"

        # 5. 連結 / 自動建立 ERP Quotation
        erp_linked = False
        erp_quotation = await self.erp_repo.get_by_case_code(case_code)
        if erp_quotation:
            # 已有 → 更新 project_code
            erp_quotation.project_code = project_code
            erp_linked = True
        else:
            # 成案時自動建立 ERP Quotation (確保專案財務紀錄存在)
            from app.extended.models.erp import ERPQuotation
            new_erp = ERPQuotation(
                case_code=case_code,
                case_name=pm_case.case_name,
                project_code=project_code,
                year=pm_case.year,
                total_price=pm_case.contract_amount,
                status="confirmed",
            )
            self.db.add(new_erp)
            erp_linked = True
            logger.info(f"自動建立 ERP Quotation: case_code={case_code}")

        await self.db.commit()

        logger.info(
            f"成案完成: case_code={case_code} → project_code={project_code}, "
            f"contract_project_id={contract_project.id}, erp_linked={erp_linked}"
        )

        return {
            "project_code": project_code,
            "contract_project_id": contract_project.id,
            "erp_linked": erp_linked,
        }

    async def cross_module_lookup(self, case_code: str) -> dict:
        """跨模組查詢案號 — 回傳該案號在 PM/ERP 各自的記錄"""
        result: dict = {"case_code": case_code, "pm": None, "erp": None}

        # PM
        result["pm"] = await self.pm_repo.get_lookup_by_case_code(case_code)

        # ERP
        result["erp"] = await self.erp_repo.get_lookup_by_case_code(case_code)

        return result

    async def find_linked_documents(self, case_code: str, limit: int = 20) -> list:
        """透過 case_code 查找相關公文

        搜尋策略 (優先使用 case_code 欄位，回退 project_code):
        1. ContractProject.case_code 精確匹配
        2. ContractProject.project_code 精確匹配 (向後相容)
        3. OfficialDocument.contract_project_id 指向該 project
        """
        # 優先用 case_code 欄位查找
        project_ids = await self.project_repo.get_ids_by_case_code(case_code)

        # 回退：用 project_code 查找 (向後相容)
        if not project_ids:
            project_ids = await self.project_repo.get_ids_by_project_code(case_code)

        if not project_ids:
            return []

        return await self.doc_repo.get_by_project_ids(project_ids, limit=limit)

    # =========================================================================
    # Asset Code 自動生成 (ADR-0013 Phase 1)
    # =========================================================================

    ASSET_CATEGORY_CODES = {
        "equipment": "EQ",   # 設備
        "vehicle": "VH",     # 車輛
        "instrument": "IN",  # 儀器
        "furniture": "FN",   # 家具
        "other": "OT",       # 其他
    }

    async def generate_asset_code(
        self,
        year: int,
        category: str = "equipment",
    ) -> str:
        """自動產生資產編號

        格式: AT_{yyyy}_{CC}_{NNN}
        範例: AT_2026_EQ_001

        Args:
            year: 年度 (西元年)
            category: 資產類別 (equipment/vehicle/instrument/furniture/other)
        """
        year_str = str(year) if year > 1911 else str(year + 1911)
        cat_code = self.ASSET_CATEGORY_CODES.get(category, "OT")
        prefix = f"AT_{year_str}_{cat_code}_"

        from sqlalchemy import select, func
        from app.extended.models.asset import Asset

        result = await self.db.execute(
            select(func.max(Asset.asset_code))
            .where(Asset.asset_code.like(f"{prefix}%"))
        )
        max_code = result.scalar()

        next_serial = 1
        if max_code:
            try:
                next_serial = int(max_code.split("_")[-1]) + 1
            except (IndexError, ValueError):
                pass

        return f"{prefix}{str(next_serial).zfill(3)}"

    @staticmethod
    def get_module_categories(module: str) -> dict:
        """取得模組可用類別"""
        mod_code = MODULE_CODES.get(module.lower(), module.upper())
        return MODULE_CATEGORIES.get(mod_code, {})
