"""
機關服務層 - CRUD + 搜尋

工廠模式，db session 在建構函數注入。
統計功能已拆分至 AgencyStatisticsService。
匹配功能已拆分至 AgencyMatchingService。

版本: 4.0.0
更新日期: 2026-03-10
變更: 拆分為 3 服務 (CRUD / Statistics / Matching)

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
from sqlalchemy import select, func, or_

from app.repositories import AgencyRepository
from app.services.base import DeleteCheckHelper
from app.extended.models import GovernmentAgency, OfficialDocument
from app.schemas.agency import AgencyCreate, AgencyUpdate

logger = logging.getLogger(__name__)


class AgencyService:
    """
    機關服務 - CRUD + 搜尋

    統計功能: AgencyStatisticsService
    匹配功能: AgencyMatchingService
    """

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
        query = select(self.model).order_by(self.model.agency_name)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: AgencyCreate) -> GovernmentAgency:
        """
        建立機關 - 加入名稱重複檢查

        Raises:
            ValueError: 機關名稱已存在
        """
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

        return agency

    async def update(self, agency_id: int, data: AgencyUpdate) -> Optional[GovernmentAgency]:
        """更新機關"""
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(agency_id, update_data)

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
        return await self.repository.delete(agency_id)

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
        """取得機關列表（含搜尋）"""
        query = select(self.model)

        if search:
            search_pattern = f"%{search}%"
            conditions = [
                getattr(self.model, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(self.model, field)
            ]
            if conditions:
                query = query.where(or_(*conditions))

        sort_column = getattr(self.model, self.DEFAULT_SORT_FIELD, self.model.id)
        query = query.order_by(sort_column.asc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()
        return [self._to_dict(item) for item in items]

    async def get_total_with_search(self, search: Optional[str] = None) -> int:
        """取得機關總數（含搜尋條件）"""
        subquery = select(self.model.id)

        if search:
            search_pattern = f"%{search}%"
            conditions = [
                getattr(self.model, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(self.model, field)
            ]
            if conditions:
                subquery = subquery.where(or_(*conditions))

        query = select(func.count()).select_from(subquery.subquery())
        result = await self.db.execute(query)
        return result.scalar() or 0

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
