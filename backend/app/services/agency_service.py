"""
機關服務層 - 工廠模式

使用工廠模式，db session 在建構函數注入。

版本: 3.0.0
更新日期: 2026-02-06
變更: 從 BaseService 繼承模式升級為工廠模式

使用方式:
    # 依賴注入（推薦）
    from app.core.dependencies import get_service

    @router.get("/agencies")
    async def list_agencies(
        service: AgencyService = Depends(get_service(AgencyService))
    ):
        return await service.get_agencies_with_stats()

    # 手動建立
    async def some_function(db: AsyncSession):
        service = AgencyService(db)
        stats = await service.get_agency_statistics()
"""
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, update

from app.repositories import AgencyRepository
from app.services.base import DeleteCheckHelper, StatisticsHelper
from app.extended.models import GovernmentAgency, OfficialDocument
from app.schemas.agency import AgencyCreate, AgencyUpdate

logger = logging.getLogger(__name__)


class AgencyService:
    """
    機關服務 - 工廠模式

    所有方法不再需要傳入 db 參數，db session 在建構時注入。

    Example:
        service = AgencyService(db)

        # 列表查詢
        agencies = await service.get_agencies_with_search(search="桃園")

        # 建立
        agency = await service.create(AgencyCreate(agency_name="新機關"))

        # 智慧匹配
        matched = await service.match_agency("桃園市政府")
    """

    # 類別層級設定
    SEARCH_FIELDS = ['agency_name', 'agency_short_name']
    DEFAULT_SORT_FIELD = 'agency_name'

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化機關服務

        Args:
            db: AsyncSession 資料庫連線
        """
        self.db = db
        self.repository = AgencyRepository(db)
        self.model = GovernmentAgency
        self.entity_name = "機關"
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 基礎 CRUD 方法
    # =========================================================================

    async def get_by_id(self, agency_id: int) -> Optional[GovernmentAgency]:
        """
        根據 ID 取得機關

        Args:
            agency_id: 機關 ID

        Returns:
            機關物件或 None
        """
        return await self.repository.get_by_id(agency_id)

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[GovernmentAgency]:
        """
        根據欄位值取得單筆機關

        Args:
            field_name: 欄位名稱
            field_value: 欄位值

        Returns:
            機關物件，若不存在則返回 None
        """
        kwargs = {field_name: field_value}
        return await self.repository.find_one_by(**kwargs)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentAgency]:
        """
        取得機關列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數

        Returns:
            機關列表
        """
        query = select(self.model).order_by(self.model.agency_name)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        agency_id: int,
        data: AgencyUpdate,
    ) -> Optional[GovernmentAgency]:
        """
        更新機關

        Args:
            agency_id: 機關 ID
            data: 更新資料

        Returns:
            更新後的機關，或 None（如不存在）
        """
        if hasattr(data, 'model_dump'):
            update_data = data.model_dump(exclude_unset=True)
        else:
            update_data = data.dict(exclude_unset=True)

        return await self.repository.update(agency_id, update_data)

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
            "updated_at": agency.updated_at
        }

    # =========================================================================
    # 覆寫方法 - 加入業務邏輯
    # =========================================================================

    async def create(
        self,
        data: AgencyCreate
    ) -> GovernmentAgency:
        """
        建立機關 - 加入名稱重複檢查

        Args:
            data: 建立資料

        Returns:
            新建的機關

        Raises:
            ValueError: 機關名稱已存在
        """
        # 檢查機關名稱是否重複
        existing = await self.get_by_field("agency_name", data.agency_name)
        if existing:
            raise ValueError(f"機關名稱已存在: {data.agency_name}")

        # 將 Pydantic schema 轉為 dict 後傳入 repository
        if hasattr(data, 'model_dump'):
            entity_data = data.model_dump()
        else:
            entity_data = data.dict()

        return await self.repository.create(entity_data)

    async def delete(
        self,
        agency_id: int
    ) -> bool:
        """
        刪除機關 - 檢查是否有關聯公文

        Args:
            agency_id: 機關 ID

        Returns:
            是否刪除成功

        Raises:
            ValueError: 機關仍有關聯公文
        """
        # 使用 DeleteCheckHelper 檢查關聯公文
        can_delete, usage_count = await DeleteCheckHelper.check_multiple_usages(
            self.db, OfficialDocument,
            [('sender_agency_id', agency_id), ('receiver_agency_id', agency_id)]
        )

        if not can_delete:
            raise ValueError(f"無法刪除，尚有 {usage_count} 筆公文與此機關關聯")

        return await self.repository.delete(agency_id)

    # =========================================================================
    # 擴充方法 - 業務特定功能
    # =========================================================================

    async def get_agency_by_name(
        self,
        name: str
    ) -> Optional[GovernmentAgency]:
        """
        依名稱取得機關

        Args:
            name: 機關名稱

        Returns:
            機關或 None
        """
        return await self.get_by_field("agency_name", name)

    async def get_agencies_with_search(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得機關列表（含搜尋）

        Args:
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字

        Returns:
            機關列表（字典格式）
        """
        query = select(self.model)

        # 應用搜尋條件
        if search:
            search_pattern = f"%{search}%"
            conditions = [
                getattr(self.model, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(self.model, field)
            ]
            if conditions:
                query = query.where(or_(*conditions))

        # 排序與分頁
        sort_column = getattr(self.model, self.DEFAULT_SORT_FIELD, self.model.id)
        query = query.order_by(sort_column.asc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return [self._to_dict(item) for item in items]

    async def get_total_with_search(
        self,
        search: Optional[str] = None
    ) -> int:
        """
        取得機關總數（含搜尋條件）

        Args:
            search: 搜尋關鍵字

        Returns:
            符合條件的機關總數
        """
        subquery = select(self.model.id)

        # 應用搜尋條件
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

    async def get_agencies_with_stats(
        self,
        db: Optional[AsyncSession] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        取得機關列表含統計資料

        Args:
            db: (向後相容，已忽略) 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字
            category: 機關分類篩選 (政府機關/民間企業/其他單位)

        Returns:
            含統計資料的機關列表
        """
        query = select(GovernmentAgency)

        if search:
            query = query.where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{search}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{search}%")
                )
            )

        # 分類篩選（基於 agency_type 欄位）
        if category:
            if category == '政府機關':
                query = query.where(GovernmentAgency.agency_type == '政府機關')
            elif category == '民間企業':
                query = query.where(GovernmentAgency.agency_type == '民間企業')
            elif category == '其他單位':
                # 其他單位包含：其他機關、社會團體、教育機構、空值等
                query = query.where(
                    or_(
                        GovernmentAgency.agency_type.is_(None),
                        GovernmentAgency.agency_type == '',
                        GovernmentAgency.agency_type == '其他單位',
                        GovernmentAgency.agency_type == '其他機關',
                        GovernmentAgency.agency_type == '社會團體',
                        GovernmentAgency.agency_type == '教育機構',
                    )
                )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # 取得分頁資料
        agencies_result = await self.db.execute(
            query.order_by(
                desc(func.coalesce(GovernmentAgency.updated_at, GovernmentAgency.created_at))
            ).offset(skip).limit(limit)
        )
        agencies = agencies_result.scalars().all()

        # 計算各機關統計
        agencies_with_stats = [
            await self._calculate_agency_stats(agency)
            for agency in agencies
        ]

        return {
            "agencies": agencies_with_stats,
            "total": total,
            "returned": len(agencies_with_stats)
        }

    async def _calculate_agency_stats(
        self,
        agency: GovernmentAgency
    ) -> Dict[str, Any]:
        """
        計算單一機關的統計資料

        Args:
            agency: 機關實體

        Returns:
            含統計資料的機關字典
        """
        # 發送/接收公文數
        sent_count = (await self.db.execute(
            select(func.count()).where(OfficialDocument.sender_agency_id == agency.id)
        )).scalar() or 0

        received_count = (await self.db.execute(
            select(func.count()).where(OfficialDocument.receiver_agency_id == agency.id)
        )).scalar() or 0

        # 最後活動日期
        last_activity = (await self.db.execute(
            select(func.max(OfficialDocument.doc_date)).where(
                or_(
                    OfficialDocument.sender_agency_id == agency.id,
                    OfficialDocument.receiver_agency_id == agency.id
                )
            )
        )).scalar_one_or_none()

        # 標準化分類
        normalized_category = self._normalize_category(agency.agency_type)

        return {
            "id": agency.id,
            "agency_name": agency.agency_name,
            "agency_short_name": agency.agency_short_name,
            "agency_code": agency.agency_code,
            "agency_type": agency.agency_type,
            "category": normalized_category,
            "contact_person": agency.contact_person,
            "phone": agency.phone,
            "email": agency.email,
            "address": agency.address,
            "document_count": sent_count + received_count,
            "sent_count": sent_count,
            "received_count": received_count,
            "last_activity": last_activity,
            "created_at": agency.created_at,
            "updated_at": agency.updated_at
        }

    async def get_agency_statistics(
        self,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        取得機關統計資料

        Args:
            db: (向後相容，已忽略) 資料庫 session

        Returns:
            統計資料字典
        """
        try:
            # 使用 StatisticsHelper 取得基本統計
            basic_stats = await StatisticsHelper.get_basic_stats(self.db, GovernmentAgency)
            total_agencies = basic_stats.get("total", 0)

            # 使用 StatisticsHelper 取得分組統計
            grouped_stats = await StatisticsHelper.get_grouped_stats(
                self.db, GovernmentAgency, 'agency_type'
            )

            # 套用分類標準化邏輯
            category_counts: Dict[str, int] = {}
            for agency_type, count in grouped_stats.items():
                # 'null' 代表空值
                original_type = None if agency_type == 'null' else agency_type
                category = self._normalize_category(original_type)
                category_counts[category] = category_counts.get(category, 0) + count

            # 依照指定順序排序
            category_order = ['政府機關', '民間企業', '其他單位']
            categories = []
            for cat in category_order:
                cnt = category_counts.get(cat, 0)
                if cnt > 0:
                    categories.append({
                        'category': cat,
                        'count': cnt,
                        'percentage': round((cnt / total_agencies * 100), 1) if total_agencies > 0 else 0
                    })

            return {
                "total_agencies": total_agencies,
                "categories": categories
            }
        except Exception as e:
            self.logger.error(f"取得機關統計資料失敗: {e}", exc_info=True)
            return {"total_agencies": 0, "categories": []}

    def _normalize_category(self, agency_type: Optional[str]) -> str:
        """
        將機關類型標準化為三大分類

        Args:
            agency_type: 原始機關類型

        Returns:
            標準化分類：政府機關、民間企業、其他單位
        """
        if not agency_type:
            return '其他單位'
        if agency_type == '政府機關':
            return '政府機關'
        if agency_type == '民間企業':
            return '民間企業'
        return '其他單位'

    def _categorize_agency(self, agency_name: str) -> str:
        """
        根據機關名稱推斷分類（備用方法）

        Args:
            agency_name: 機關名稱

        Returns:
            推斷的分類
        """
        name = (agency_name or "").lower()
        if any(k in name for k in ['政府', '市政', '縣政', '部', '局', '署', '處']):
            return '政府機關'
        if any(k in name for k in ['公司', '企業', '集團']):
            return '民間企業'
        return '其他單位'

    # =========================================================================
    # 智慧機關匹配功能
    # =========================================================================

    def _parse_agency_text(self, text: str) -> List[Tuple[Optional[str], str]]:
        """
        解析機關文字，提取機關代碼和名稱

        支援格式：
        - "機關名稱" -> [(None, "機關名稱")]
        - "代碼 (機關名稱)" -> [("代碼", "機關名稱")]
        - "代碼 機關名稱" -> [("代碼", "機關名稱")]
        - "代碼1 (名稱1) | 代碼2 (名稱2)" -> 多個機關

        Args:
            text: 原始機關文字

        Returns:
            (機關代碼, 機關名稱) 的列表
        """
        if not text or not text.strip():
            return []

        results = []
        # 處理多個受文者（以 | 分隔）
        parts = text.split("|")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 模式1: "代碼 (機關名稱)" 或 "代碼\n(機關名稱)"
            match = re.match(r'^([A-Z0-9]+)\s*[\n\(（](.+?)[\)）]?\s*$', part, re.IGNORECASE)
            if match:
                code, name = match.groups()
                results.append((code.strip(), name.strip().rstrip('）)')))
                continue

            # 模式2: "代碼 機關名稱" (代碼為英數字混合)
            match = re.match(r'^([A-Z0-9]{6,})\s+(.+)$', part, re.IGNORECASE)
            if match:
                code, name = match.groups()
                # 排除括號開頭的情況
                if not name.startswith('(') and not name.startswith('（'):
                    results.append((code.strip(), name.strip()))
                    continue

            # 模式3: 純機關名稱（無代碼）
            # 移除可能的括號說明文字
            clean_name = re.sub(r'[\(（].+?[\)）]', '', part).strip()
            if clean_name:
                results.append((None, clean_name))

        return results

    async def match_agency(
        self,
        text: str
    ) -> Optional[GovernmentAgency]:
        """
        智慧匹配機關 - 從文字中尋找對應的機關

        匹配優先順序：
        1. 完全匹配機關代碼
        2. 完全匹配機關名稱
        3. 完全匹配機關簡稱
        4. 部分匹配機關名稱（名稱包含在文字中）

        Args:
            text: 發文/受文機關文字

        Returns:
            匹配的機關或 None
        """
        if not text or not text.strip():
            return None

        # 解析文字取得可能的機關資訊（只取第一個）
        parsed = self._parse_agency_text(text)
        if not parsed:
            return None

        code, name = parsed[0]

        # 1. 優先以機關代碼匹配
        if code:
            agency = await self.get_by_field("agency_code", code)
            if agency:
                return agency

        # 2. 完全匹配機關名稱
        agency = await self.get_by_field("agency_name", name)
        if agency:
            return agency

        # 3. 完全匹配機關簡稱
        result = await self.db.execute(
            select(GovernmentAgency).where(
                GovernmentAgency.agency_short_name == name
            )
        )
        agency = result.scalar_one_or_none()
        if agency:
            return agency

        # 4. 部分匹配 - 機關名稱包含在搜尋文字中
        result = await self.db.execute(
            select(GovernmentAgency).where(
                GovernmentAgency.agency_name.isnot(None)
            )
        )
        agencies = result.scalars().all()

        for agency in agencies:
            # 檢查機關名稱是否完整出現在文字中
            if agency.agency_name and agency.agency_name in text:
                return agency
            # 檢查簡稱是否出現
            if agency.agency_short_name and agency.agency_short_name in text:
                return agency

        return None

    async def match_agencies_for_document(
        self,
        sender: Optional[str],
        receiver: Optional[str]
    ) -> Dict[str, Optional[int]]:
        """
        為公文匹配發文機關和受文機關

        Args:
            sender: 發文機關文字
            receiver: 受文機關文字

        Returns:
            {"sender_agency_id": int|None, "receiver_agency_id": int|None}
        """
        result = {
            "sender_agency_id": None,
            "receiver_agency_id": None
        }

        if sender:
            agency = await self.match_agency(sender)
            if agency:
                result["sender_agency_id"] = agency.id

        if receiver:
            agency = await self.match_agency(receiver)
            if agency:
                result["receiver_agency_id"] = agency.id

        return result

    async def batch_associate_agencies(
        self,
        db: Optional[AsyncSession] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        批次為所有公文關聯機關

        Args:
            db: (向後相容，已忽略) 資料庫 session
            overwrite: 是否覆蓋現有關聯

        Returns:
            處理結果統計
        """
        stats = {
            "total_documents": 0,
            "sender_updated": 0,
            "receiver_updated": 0,
            "sender_matched": 0,
            "receiver_matched": 0,
            "errors": []
        }

        try:
            # 取得需要處理的公文
            query = select(OfficialDocument)
            if not overwrite:
                # 只處理尚未關聯的
                query = query.where(
                    or_(
                        OfficialDocument.sender_agency_id.is_(None),
                        OfficialDocument.receiver_agency_id.is_(None)
                    )
                )

            result = await self.db.execute(query)
            documents = result.scalars().all()
            stats["total_documents"] = len(documents)

            for doc in documents:
                try:
                    updates = {}

                    # 處理發文機關
                    if doc.sender and (overwrite or doc.sender_agency_id is None):
                        agency = await self.match_agency(doc.sender)
                        if agency:
                            stats["sender_matched"] += 1
                            if doc.sender_agency_id != agency.id:
                                updates["sender_agency_id"] = agency.id
                                stats["sender_updated"] += 1

                    # 處理受文機關
                    if doc.receiver and (overwrite or doc.receiver_agency_id is None):
                        agency = await self.match_agency(doc.receiver)
                        if agency:
                            stats["receiver_matched"] += 1
                            if doc.receiver_agency_id != agency.id:
                                updates["receiver_agency_id"] = agency.id
                                stats["receiver_updated"] += 1

                    # 更新公文
                    if updates:
                        await self.db.execute(
                            update(OfficialDocument)
                            .where(OfficialDocument.id == doc.id)
                            .values(**updates)
                        )

                except Exception as e:
                    stats["errors"].append(f"文件 {doc.id}: {str(e)}")

            await self.db.commit()
            logger.info(f"批次機關關聯完成: {stats}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"批次機關關聯失敗: {e}", exc_info=True)
            stats["errors"].append(f"系統錯誤: {str(e)}")

        return stats

    async def get_unassociated_summary(
        self,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        取得未關聯機關的公文統計

        Args:
            db: (向後相容，已忽略) 資料庫 session

        Returns:
            未關聯統計
        """
        # 總公文數
        total = (await self.db.execute(
            select(func.count(OfficialDocument.id))
        )).scalar() or 0

        # 無發文機關關聯數
        no_sender = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.is_(None),
                OfficialDocument.sender.isnot(None),
                OfficialDocument.sender != ''
            )
        )).scalar() or 0

        # 無受文機關關聯數
        no_receiver = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.receiver_agency_id.is_(None),
                OfficialDocument.receiver.isnot(None),
                OfficialDocument.receiver != ''
            )
        )).scalar() or 0

        # 已關聯發文機關
        has_sender = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.isnot(None)
            )
        )).scalar() or 0

        # 已關聯受文機關
        has_receiver = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.receiver_agency_id.isnot(None)
            )
        )).scalar() or 0

        return {
            "total_documents": total,
            "sender_associated": has_sender,
            "sender_unassociated": no_sender,
            "receiver_associated": has_receiver,
            "receiver_unassociated": no_receiver,
            "association_rate": {
                "sender": round(has_sender / total * 100, 1) if total > 0 else 0,
                "receiver": round(has_receiver / total * 100, 1) if total > 0 else 0
            }
        }

    async def suggest_agency(
        self,
        db: Optional[AsyncSession] = None,
        text: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根據文字建議可能的機關

        Args:
            db: (向後相容，已忽略) 資料庫 session
            text: 搜尋文字
            limit: 回傳數量限制

        Returns:
            建議的機關列表
        """
        if not text or len(text) < 2:
            return []

        # 模糊搜尋
        result = await self.db.execute(
            select(GovernmentAgency).where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{text}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{text}%"),
                    GovernmentAgency.agency_code.ilike(f"%{text}%")
                )
            ).limit(limit)
        )
        agencies = result.scalars().all()

        return [
            {
                "id": a.id,
                "agency_name": a.agency_name,
                "agency_code": a.agency_code,
                "agency_short_name": a.agency_short_name
            }
            for a in agencies
        ]

    # =========================================================================
    # 工具方法
    # =========================================================================

    async def exists(self, agency_id: int) -> bool:
        """檢查機關是否存在"""
        return await self.repository.exists(agency_id)

    async def get_by_code(self, agency_code: str) -> Optional[GovernmentAgency]:
        """根據機關代碼取得機關"""
        return await self.repository.find_one_by(agency_code=agency_code)

    # =========================================================================
    # 向後相容方法 (保留至 v4.0)
    #
    # 這些方法保留舊的 db 參數簽名，但內部使用 self.db。
    # 傳入的 db 參數會被忽略。
    # =========================================================================

    async def get_agency(self, db: AsyncSession, agency_id: int) -> Optional[GovernmentAgency]:
        """
        @deprecated v3.0 (2026-02-06) 使用 get_by_id 代替
        移除計畫: v4.0 (2026-06-01)
        """
        return await self.get_by_id(agency_id)

    async def get_agencies(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[GovernmentAgency]:
        """
        @deprecated v3.0 (2026-02-06) 使用 get_list 代替
        移除計畫: v4.0 (2026-06-01)
        """
        return await self.get_list(skip=skip, limit=limit)

    async def create_agency(self, db: AsyncSession, agency: AgencyCreate) -> GovernmentAgency:
        """
        @deprecated v3.0 (2026-02-06) 使用 create 代替
        移除計畫: v4.0 (2026-06-01)
        """
        return await self.create(agency)

    async def update_agency(self, db: AsyncSession, agency_id: int, agency_update: AgencyUpdate) -> Optional[GovernmentAgency]:
        """
        @deprecated v3.0 (2026-02-06) 使用 update 代替
        移除計畫: v4.0 (2026-06-01)
        """
        return await self.update(agency_id, agency_update)

    async def delete_agency(self, db: AsyncSession, agency_id: int) -> bool:
        """
        @deprecated v3.0 (2026-02-06) 使用 delete 代替
        移除計畫: v4.0 (2026-06-01)
        """
        return await self.delete(agency_id)

