"""統一案號編碼服務

參照公文系統專案編碼機制 CK{年度}_{類別}_{性質}_{流水號}，擴充為跨模組統一案號。

編碼格式: CK{年度4碼}_{模組2碼}_{類別2碼}_{流水號3碼}

模組代碼:
  PM = 專案管理 (Project Management)
  FN = 財務管理 (Finance/ERP)
  DP = 派工管理 (Dispatch)
  GN = 一般委辦 (General，相容既有 contract_projects)

類別代碼 (依模組):
  PM: 01=測量案, 02=資訊案, 03=規劃案, 04=監造案, 05=複合案, 99=其他
  FN: 01=報價單, 02=變更單, 03=追加減, 99=其他
  DP: 01=地上物, 02=土地查估, 03=計畫書, 04=測量, 99=其他
  GN: 01=委辦案件, 02=協力計畫, 03=小額採購, 04=其他類別

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
    "01": "測量案",
    "02": "資訊案",
    "03": "規劃案",
    "04": "監造案",
    "05": "複合案",
    "99": "其他",
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
    "01": "委辦案件",
    "02": "協力計畫",
    "03": "小額採購",
    "04": "其他類別",
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

        搜尋策略:
        1. ContractProject.project_code 精確匹配 case_code
        2. OfficialDocument.contract_project_id 指向該 project
        """
        # 先找 ContractProject IDs
        project_ids = await self.project_repo.get_ids_by_project_code(case_code)

        if not project_ids:
            return []

        # 再找關聯公文
        return await self.doc_repo.get_by_project_ids(project_ids, limit=limit)

    @staticmethod
    def get_module_categories(module: str) -> dict:
        """取得模組可用類別"""
        mod_code = MODULE_CODES.get(module.lower(), module.upper())
        return MODULE_CATEGORIES.get(mod_code, {})
