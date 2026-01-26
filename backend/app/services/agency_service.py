"""
機關服務層 - 繼承 BaseService 實現標準 CRUD

使用泛型基類減少重複代碼，提供統一的資料庫操作介面。
包含智慧機關匹配功能，支援自動關聯公文與機關。

v2.1.0 (2026-01-22): 重構使用 BaseService 新方法
- get_agencies_with_search → 使用 get_list_with_search
- get_total_with_search → 使用 get_count_with_search
- get_agency_statistics → 使用 @with_stats_error_handling
"""
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, update

from app.services.base_service import BaseService, with_stats_error_handling
from app.services.base import DeleteCheckHelper, StatisticsHelper
from app.extended.models import GovernmentAgency, OfficialDocument
from app.schemas.agency import AgencyCreate, AgencyUpdate

logger = logging.getLogger(__name__)


class AgencyService(BaseService[GovernmentAgency, AgencyCreate, AgencyUpdate]):
    """
    機關服務 - 繼承 BaseService

    提供機關相關的 CRUD 操作和業務邏輯。
    """

    # 類別層級設定
    SEARCH_FIELDS = ['agency_name', 'agency_short_name']
    DEFAULT_SORT_FIELD = 'agency_name'

    def __init__(self) -> None:
        """初始化機關服務"""
        super().__init__(GovernmentAgency, "機關")

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
        db: AsyncSession,
        data: AgencyCreate
    ) -> GovernmentAgency:
        """
        建立機關 - 加入名稱重複檢查

        Args:
            db: 資料庫 session
            data: 建立資料

        Returns:
            新建的機關

        Raises:
            ValueError: 機關名稱已存在
        """
        # 檢查機關名稱是否重複
        existing = await self.get_by_field(db, "agency_name", data.agency_name)
        if existing:
            raise ValueError(f"機關名稱已存在: {data.agency_name}")

        return await super().create(db, data)

    async def delete(
        self,
        db: AsyncSession,
        agency_id: int
    ) -> bool:
        """
        刪除機關 - 檢查是否有關聯公文

        Args:
            db: 資料庫 session
            agency_id: 機關 ID

        Returns:
            是否刪除成功

        Raises:
            ValueError: 機關仍有關聯公文
        """
        # 使用 DeleteCheckHelper 檢查關聯公文
        can_delete, usage_count = await DeleteCheckHelper.check_multiple_usages(
            db, OfficialDocument,
            [('sender_agency_id', agency_id), ('receiver_agency_id', agency_id)]
        )

        if not can_delete:
            raise ValueError(f"無法刪除，尚有 {usage_count} 筆公文與此機關關聯")

        return await super().delete(db, agency_id)

    # =========================================================================
    # 擴充方法 - 業務特定功能
    # =========================================================================

    async def get_agency_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[GovernmentAgency]:
        """
        依名稱取得機關

        Args:
            db: 資料庫 session
            name: 機關名稱

        Returns:
            機關或 None
        """
        return await self.get_by_field(db, "agency_name", name)

    async def get_agencies_with_search(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得機關列表（含搜尋）- 使用 BaseService.get_list_with_search

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字

        Returns:
            機關列表（字典格式）
        """
        return await self.get_list_with_search(
            db, skip, limit, search,
            search_fields=self.SEARCH_FIELDS,
            sort_by=self.DEFAULT_SORT_FIELD,
            to_dict_func=self._to_dict
        )

    async def get_total_with_search(
        self,
        db: AsyncSession,
        search: Optional[str] = None
    ) -> int:
        """
        取得機關總數（含搜尋條件）- 使用 BaseService.get_count_with_search

        Args:
            db: 資料庫 session
            search: 搜尋關鍵字

        Returns:
            符合條件的機關總數
        """
        return await self.get_count_with_search(db, search, self.SEARCH_FIELDS)

    async def get_agencies_with_stats(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        取得機關列表含統計資料

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字

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

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        # 取得分頁資料
        agencies_result = await db.execute(
            query.order_by(
                desc(func.coalesce(GovernmentAgency.updated_at, GovernmentAgency.created_at))
            ).offset(skip).limit(limit)
        )
        agencies = agencies_result.scalars().all()

        # 計算各機關統計
        agencies_with_stats = [
            await self._calculate_agency_stats(db, agency)
            for agency in agencies
        ]

        return {
            "agencies": agencies_with_stats,
            "total": total,
            "returned": len(agencies_with_stats)
        }

    async def _calculate_agency_stats(
        self,
        db: AsyncSession,
        agency: GovernmentAgency
    ) -> Dict[str, Any]:
        """
        計算單一機關的統計資料

        Args:
            db: 資料庫 session
            agency: 機關實體

        Returns:
            含統計資料的機關字典
        """
        # 發送/接收公文數
        sent_count = (await db.execute(
            select(func.count()).where(OfficialDocument.sender_agency_id == agency.id)
        )).scalar() or 0

        received_count = (await db.execute(
            select(func.count()).where(OfficialDocument.receiver_agency_id == agency.id)
        )).scalar() or 0

        # 最後活動日期
        last_activity = (await db.execute(
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

    @with_stats_error_handling(
        default_return={"total_agencies": 0, "categories": []},
        operation_name="統計資料"
    )
    async def get_agency_statistics(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        取得機關統計資料 - 使用 @with_stats_error_handling 裝飾器

        Args:
            db: 資料庫 session

        Returns:
            統計資料字典
        """
        # 使用 StatisticsHelper 取得基本統計
        basic_stats = await StatisticsHelper.get_basic_stats(db, GovernmentAgency)
        total_agencies = basic_stats.get("total", 0)

        # 使用 StatisticsHelper 取得分組統計
        grouped_stats = await StatisticsHelper.get_grouped_stats(
            db, GovernmentAgency, 'agency_type'
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
        db: AsyncSession,
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
            db: 資料庫 session
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
            agency = await self.get_by_field(db, "agency_code", code)
            if agency:
                return agency

        # 2. 完全匹配機關名稱
        agency = await self.get_by_field(db, "agency_name", name)
        if agency:
            return agency

        # 3. 完全匹配機關簡稱
        result = await db.execute(
            select(GovernmentAgency).where(
                GovernmentAgency.agency_short_name == name
            )
        )
        agency = result.scalar_one_or_none()
        if agency:
            return agency

        # 4. 部分匹配 - 機關名稱包含在搜尋文字中
        result = await db.execute(
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
        db: AsyncSession,
        sender: Optional[str],
        receiver: Optional[str]
    ) -> Dict[str, Optional[int]]:
        """
        為公文匹配發文機關和受文機關

        Args:
            db: 資料庫 session
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
            agency = await self.match_agency(db, sender)
            if agency:
                result["sender_agency_id"] = agency.id

        if receiver:
            agency = await self.match_agency(db, receiver)
            if agency:
                result["receiver_agency_id"] = agency.id

        return result

    async def batch_associate_agencies(
        self,
        db: AsyncSession,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        批次為所有公文關聯機關

        Args:
            db: 資料庫 session
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

            result = await db.execute(query)
            documents = result.scalars().all()
            stats["total_documents"] = len(documents)

            for doc in documents:
                try:
                    updates = {}

                    # 處理發文機關
                    if doc.sender and (overwrite or doc.sender_agency_id is None):
                        agency = await self.match_agency(db, doc.sender)
                        if agency:
                            stats["sender_matched"] += 1
                            if doc.sender_agency_id != agency.id:
                                updates["sender_agency_id"] = agency.id
                                stats["sender_updated"] += 1

                    # 處理受文機關
                    if doc.receiver and (overwrite or doc.receiver_agency_id is None):
                        agency = await self.match_agency(db, doc.receiver)
                        if agency:
                            stats["receiver_matched"] += 1
                            if doc.receiver_agency_id != agency.id:
                                updates["receiver_agency_id"] = agency.id
                                stats["receiver_updated"] += 1

                    # 更新公文
                    if updates:
                        await db.execute(
                            update(OfficialDocument)
                            .where(OfficialDocument.id == doc.id)
                            .values(**updates)
                        )

                except Exception as e:
                    stats["errors"].append(f"文件 {doc.id}: {str(e)}")

            await db.commit()
            logger.info(f"批次機關關聯完成: {stats}")

        except Exception as e:
            await db.rollback()
            logger.error(f"批次機關關聯失敗: {e}", exc_info=True)
            stats["errors"].append(f"系統錯誤: {str(e)}")

        return stats

    async def get_unassociated_summary(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        取得未關聯機關的公文統計

        Returns:
            未關聯統計
        """
        # 總公文數
        total = (await db.execute(
            select(func.count(OfficialDocument.id))
        )).scalar() or 0

        # 無發文機關關聯數
        no_sender = (await db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.is_(None),
                OfficialDocument.sender.isnot(None),
                OfficialDocument.sender != ''
            )
        )).scalar() or 0

        # 無受文機關關聯數
        no_receiver = (await db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.receiver_agency_id.is_(None),
                OfficialDocument.receiver.isnot(None),
                OfficialDocument.receiver != ''
            )
        )).scalar() or 0

        # 已關聯發文機關
        has_sender = (await db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.isnot(None)
            )
        )).scalar() or 0

        # 已關聯受文機關
        has_receiver = (await db.execute(
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
        db: AsyncSession,
        text: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根據文字建議可能的機關

        Args:
            db: 資料庫 session
            text: 搜尋文字
            limit: 回傳數量限制

        Returns:
            建議的機關列表
        """
        if not text or len(text) < 2:
            return []

        # 模糊搜尋
        result = await db.execute(
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
    # 向後相容方法 (逐步淘汰)
    # =========================================================================

    async def get_agency(self, db: AsyncSession, agency_id: int) -> Optional[GovernmentAgency]:
        """
        @deprecated v2.0 (2026-01-20) 使用 get_by_id 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.get_by_id(db, agency_id)

    async def get_agencies(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[GovernmentAgency]:
        """
        @deprecated v2.0 (2026-01-20) 使用 get_list 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.get_list(db, skip=skip, limit=limit)

    async def create_agency(self, db: AsyncSession, agency: AgencyCreate) -> GovernmentAgency:
        """
        @deprecated v2.0 (2026-01-20) 使用 create 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.create(db, agency)

    async def update_agency(self, db: AsyncSession, agency_id: int, agency_update: AgencyUpdate) -> Optional[GovernmentAgency]:
        """
        @deprecated v2.0 (2026-01-20) 使用 update 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.update(db, agency_id, agency_update)

    async def delete_agency(self, db: AsyncSession, agency_id: int) -> bool:
        """
        @deprecated v2.0 (2026-01-20) 使用 delete 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.delete(db, agency_id)
