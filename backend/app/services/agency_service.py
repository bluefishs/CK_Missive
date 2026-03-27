"""
機關服務層 - CRUD + 搜尋

工廠模式，db session 在建構函數注入。
統計功能已拆分至 AgencyStatisticsService。
匹配功能已拆分至 AgencyMatchingService。

版本: 4.1.0
更新日期: 2026-03-23
變更: 遷移至 Repository 層 (A7) — 消除直接 db.execute()

使用方式:
    from app.core.dependencies import get_service
    from app.services.agency_service import AgencyService

    @router.get("/agencies")
    async def list_agencies(
        service: AgencyService = Depends(get_service(AgencyService))
    ):
        return await service.get_list()
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import AgencyRepository
from app.services.base import DeleteCheckHelper
from app.extended.models import GovernmentAgency, OfficialDocument
from app.schemas.agency import AgencyCreate, AgencyUpdate
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class AgencyService(AuditableServiceMixin):
    """
    機關服務 - CRUD + 搜尋

    統計功能: AgencyStatisticsService
    匹配功能: AgencyMatchingService
    """

    AUDIT_TABLE = "government_agencies"
    SEARCH_FIELDS = ['agency_name', 'agency_short_name']
    DEFAULT_SORT_FIELD = 'agency_name'

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = AgencyRepository(db)
        self.model = GovernmentAgency
        self.entity_name = "機關"
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 基礎 CRUD
    # =========================================================================

    async def get_by_id(self, agency_id: int) -> Optional[GovernmentAgency]:
        """根據 ID 取得機關"""
        return await self.repository.get_by_id(agency_id)

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[GovernmentAgency]:
        """根據欄位值取得單筆機關"""
        kwargs = {field_name: field_value}
        return await self.repository.find_one_by(**kwargs)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentAgency]:
        """取得機關列表"""
        agencies, _ = await self.repository.filter_agencies(
            skip=skip, limit=limit
        )
        return agencies

    async def create(self, data: AgencyCreate) -> GovernmentAgency:
        """
        建立機關 - 加入名稱正規化 + 重複檢查

        Raises:
            ValueError: 機關名稱已存在或無效
        """
        # 正規化名稱（去除協力廠商後綴、統編前綴等）
        from app.services.receiver_normalizer import normalize_unit
        normalized = normalize_unit(data.agency_name)
        if normalized.primary != data.agency_name:
            data.agency_name = normalized.primary

        # 攔截自家公司名稱（不應出現在機關表）
        _SELF_KEYWORDS = ("乾坤測繪", "乾坤科技")
        if any(kw in data.agency_name for kw in _SELF_KEYWORDS):
            raise ValueError(f"自家公司不應建為機關: {data.agency_name}")

        existing = await self.get_by_field("agency_name", data.agency_name)
        if existing:
            raise ValueError(f"機關名稱已存在: {data.agency_name}")
        agency = await self.repository.create(data.model_dump())

        # 回溯連結：將已存在的同名 CanonicalEntity 連結到新建機關
        try:
            from app.services.ai.canonical_entity_service import CanonicalEntityService
            entity_svc = CanonicalEntityService(self.db)
            await entity_svc.link_existing_entities(
                record_name=agency.agency_name,
                entity_type="org",
                record_id=agency.id,
                field="linked_agency_id",
            )
        except Exception as e:
            logger.warning(f"Agency 回溯連結 NER 實體失敗: {e}")

        await self.audit_create(agency.id, data.model_dump())

        return agency

    async def update(self, agency_id: int, data: AgencyUpdate) -> Optional[GovernmentAgency]:
        """更新機關"""
        update_data = data.model_dump(exclude_unset=True)
        result = await self.repository.update(agency_id, update_data)
        if result:
            await self.audit_update(agency_id, update_data)
        return result

    async def delete(self, agency_id: int) -> bool:
        """
        刪除機關 - 檢查是否有關聯公文

        Raises:
            ValueError: 機關仍有關聯公文
        """
        can_delete, usage_count = await DeleteCheckHelper.check_multiple_usages(
            self.db, OfficialDocument,
            [('sender_agency_id', agency_id), ('receiver_agency_id', agency_id)]
        )
        if not can_delete:
            raise ValueError(f"無法刪除，尚有 {usage_count} 筆公文與此機關關聯")
        result = await self.repository.delete(agency_id)
        if result:
            await self.audit_delete(agency_id)
        return result

    # =========================================================================
    # 搜尋
    # =========================================================================

    async def get_agency_by_name(self, name: str) -> Optional[GovernmentAgency]:
        """依名稱取得機關"""
        return await self.get_by_field("agency_name", name)

    async def get_agencies_with_search(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """取得機關列表（含搜尋）— 委派至 AgencyRepository"""
        agencies, _ = await self.repository.filter_agencies(
            search=search, skip=skip, limit=limit
        )
        return [self._to_dict(item) for item in agencies]

    async def get_total_with_search(self, search: Optional[str] = None) -> int:
        """取得機關總數（含搜尋條件）— 委派至 AgencyRepository"""
        _, total = await self.repository.filter_agencies(
            search=search, skip=0, limit=1
        )
        return total

    # =========================================================================
    # 工具方法
    # =========================================================================

    async def exists(self, agency_id: int) -> bool:
        """檢查機關是否存在"""
        return await self.repository.exists(agency_id)

    async def get_by_code(self, agency_code: str) -> Optional[GovernmentAgency]:
        """根據機關代碼取得機關"""
        return await self.repository.find_one_by(agency_code=agency_code)

    def _to_dict(self, agency: GovernmentAgency) -> Dict[str, Any]:
        """將機關實體轉換為字典"""
        return {
            "id": agency.id,
            "agency_name": agency.agency_name,
            "agency_short_name": agency.agency_short_name,
            "agency_code": agency.agency_code,
            "agency_type": agency.agency_type,
            "contact_person": agency.contact_person,
            "phone": agency.phone,
            "email": agency.email,
            "address": agency.address,
            "notes": agency.notes,
            "created_at": agency.created_at,
            "updated_at": agency.updated_at,
        }
