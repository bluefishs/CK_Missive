"""
機關匹配服務

從 AgencyService 拆分，負責智慧機關匹配、批次關聯、建議、修復等功能。

版本: 1.0.0
更新日期: 2026-03-10
"""
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, literal

from app.repositories import AgencyRepository
from app.extended.models import GovernmentAgency, OfficialDocument

logger = logging.getLogger(__name__)


class AgencyMatchingService:
    """
    機關匹配服務

    負責智慧機關匹配、批次公文關聯、機關建議、名稱修復等。

    Example:
        service = AgencyMatchingService(db)
        matched = await service.match_agency("桃園市政府")
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = AgencyRepository(db)
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 文字解析
    # =========================================================================

    def _parse_agency_text(self, text: str) -> List[Tuple[Optional[str], str]]:
        """
        解析機關文字，提取機關代碼和名稱

        支援格式：
        - "機關名稱" -> [(None, "機關名稱")]
        - "代碼 (機關名稱)" -> [("代碼", "機關名稱")]
        - "代碼 機關名稱" -> [("代碼", "機關名稱")]
        - "代碼1 (名稱1) | 代碼2 (名稱2)" -> 多個機關
        """
        if not text or not text.strip():
            return []

        results = []
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
                if not name.startswith('(') and not name.startswith('（'):
                    results.append((code.strip(), name.strip()))
                    continue

            # 模式3: 純機關名稱（無代碼）
            clean_name = re.sub(r'[\(（].+?[\)）]', '', part).strip()
            if clean_name:
                results.append((None, clean_name))

        return results

    # =========================================================================
    # 智慧匹配
    # =========================================================================

    async def match_agency(self, text: str) -> Optional[GovernmentAgency]:
        """
        智慧匹配機關 - 從文字中尋找對應的機關

        匹配優先順序：
        1. 完全匹配機關代碼
        2. 完全匹配機關名稱
        3. 完全匹配機關簡稱
        4. 部分匹配機關名稱（名稱包含在文字中）
        """
        if not text or not text.strip():
            return None

        parsed = self._parse_agency_text(text)
        if not parsed:
            return None

        code, name = parsed[0]

        # 1. 優先以機關代碼匹配
        if code:
            agency = await self.repository.find_one_by(agency_code=code)
            if agency:
                return agency

        # 2. 完全匹配機關名稱
        agency = await self.repository.find_one_by(agency_name=name)
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

        # 4. 部分匹配 - DB 端比對
        result = await self.db.execute(
            select(GovernmentAgency).where(
                GovernmentAgency.agency_name.isnot(None),
                or_(
                    func.strpos(literal(text), GovernmentAgency.agency_name) > 0,
                    func.strpos(literal(text), GovernmentAgency.agency_short_name) > 0,
                ),
            )
            .order_by(func.length(GovernmentAgency.agency_name).desc())
            .limit(1)
        )
        agency = result.scalar_one_or_none()
        if agency:
            return agency

        return None

    async def match_agencies_for_document(
        self,
        sender: Optional[str],
        receiver: Optional[str],
    ) -> Dict[str, Optional[int]]:
        """
        為公文匹配發文機關和受文機關

        Returns:
            {"sender_agency_id": int|None, "receiver_agency_id": int|None}
        """
        result: Dict[str, Optional[int]] = {
            "sender_agency_id": None,
            "receiver_agency_id": None,
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

    # =========================================================================
    # 批次關聯
    # =========================================================================

    async def batch_associate_agencies(
        self,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        批次為所有公文關聯機關

        Args:
            overwrite: 是否覆蓋現有關聯

        Returns:
            處理結果統計
        """
        stats: Dict[str, Any] = {
            "total_documents": 0,
            "sender_updated": 0,
            "receiver_updated": 0,
            "sender_matched": 0,
            "receiver_matched": 0,
            "errors": [],
        }

        try:
            base_query = select(OfficialDocument)
            if not overwrite:
                base_query = base_query.where(
                    or_(
                        OfficialDocument.sender_agency_id.is_(None),
                        OfficialDocument.receiver_agency_id.is_(None),
                    )
                )

            count_query = select(func.count(OfficialDocument.id))
            if not overwrite:
                count_query = count_query.where(
                    or_(
                        OfficialDocument.sender_agency_id.is_(None),
                        OfficialDocument.receiver_agency_id.is_(None),
                    )
                )
            stats["total_documents"] = (await self.db.execute(count_query)).scalar() or 0

            batch_size = 100
            offset = 0

            while True:
                result = await self.db.execute(
                    base_query.order_by(OfficialDocument.id)
                    .offset(offset).limit(batch_size)
                )
                documents = result.scalars().all()
                if not documents:
                    break

                for doc in documents:
                    try:
                        updates = {}

                        if doc.sender and (overwrite or doc.sender_agency_id is None):
                            agency = await self.match_agency(doc.sender)
                            if agency:
                                stats["sender_matched"] += 1
                                if doc.sender_agency_id != agency.id:
                                    updates["sender_agency_id"] = agency.id
                                    stats["sender_updated"] += 1

                        if doc.receiver and (overwrite or doc.receiver_agency_id is None):
                            agency = await self.match_agency(doc.receiver)
                            if agency:
                                stats["receiver_matched"] += 1
                                if doc.receiver_agency_id != agency.id:
                                    updates["receiver_agency_id"] = agency.id
                                    stats["receiver_updated"] += 1

                        if updates:
                            await self.db.execute(
                                update(OfficialDocument)
                                .where(OfficialDocument.id == doc.id)
                                .values(**updates)
                            )

                    except Exception as e:
                        logger.warning(f"文件 {doc.id} 機關關聯失敗: {e}")
                        stats["errors"].append(f"文件 {doc.id}: 關聯處理失敗")

                await self.db.commit()
                offset += batch_size

            logger.info(f"批次機關關聯完成: {stats}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"批次機關關聯失敗: {e}", exc_info=True)
            stats["errors"].append("系統錯誤，請稍後再試")

        return stats

    async def get_unassociated_summary(self) -> Dict[str, Any]:
        """取得未關聯機關的公文統計"""
        total = (await self.db.execute(
            select(func.count(OfficialDocument.id))
        )).scalar() or 0

        no_sender = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.is_(None),
                OfficialDocument.sender.isnot(None),
                OfficialDocument.sender != '',
            )
        )).scalar() or 0

        no_receiver = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.receiver_agency_id.is_(None),
                OfficialDocument.receiver.isnot(None),
                OfficialDocument.receiver != '',
            )
        )).scalar() or 0

        has_sender = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.isnot(None)
            )
        )).scalar() or 0

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
                "receiver": round(has_receiver / total * 100, 1) if total > 0 else 0,
            },
        }

    async def suggest_agency(
        self,
        text: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """根據文字建議可能的機關"""
        if not text or len(text) < 2:
            return []

        result = await self.db.execute(
            select(GovernmentAgency).where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{text}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{text}%"),
                    GovernmentAgency.agency_code.ilike(f"%{text}%"),
                )
            ).limit(limit)
        )
        agencies = result.scalars().all()

        return [
            {
                "id": a.id,
                "agency_name": a.agency_name,
                "agency_code": a.agency_code,
                "agency_short_name": a.agency_short_name,
            }
            for a in agencies
        ]

    # =========================================================================
    # 資料修復
    # =========================================================================

    async def fix_parsed_names(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        修復機關名稱/代碼解析錯誤

        解析格式如：
        - "A01020100G (內政部國土管理署城鄉發展分署)" → 代碼 + 名稱
        - "EB50819619 乾坤測繪科技有限公司" → 代碼 + 名稱

        重複名稱會合併記錄（刪除錯誤記錄、更新關聯）。
        """
        from app.services.strategies.agency_matcher import parse_agency_string

        agencies = await self.repository.get_all_agencies()
        name_to_id = {a.agency_name: a.id for a in agencies}

        fixed_details = []
        merged_count = 0
        updated_count = 0

        for agency in agencies:
            original_name = agency.agency_name
            original_code = agency.agency_code

            parsed_code, parsed_name = parse_agency_string(original_name)

            if not (parsed_code and parsed_name != original_name and not original_code):
                continue

            existing_id = name_to_id.get(parsed_name)

            if existing_id and existing_id != agency.id:
                detail = {
                    "id": agency.id,
                    "action": "merge",
                    "original_name": original_name,
                    "original_code": original_code,
                    "new_name": parsed_name,
                    "new_code": parsed_code,
                    "merge_to_id": existing_id,
                    "message": f"合併至已存在的機關 ID={existing_id}",
                }
                fixed_details.append(detail)
                if not dry_run:
                    await self.repository.reassign_document_agency(agency.id, existing_id)
                    await self.db.delete(agency)
                    merged_count += 1
            else:
                detail = {
                    "id": agency.id,
                    "action": "update",
                    "original_name": original_name,
                    "original_code": original_code,
                    "new_name": parsed_name,
                    "new_code": parsed_code,
                }
                fixed_details.append(detail)
                if not dry_run:
                    agency.agency_name = parsed_name
                    agency.agency_code = parsed_code
                    updated_count += 1

        if not dry_run and fixed_details:
            await self.db.commit()

        return {
            "fixed_count": len(fixed_details),
            "merged": merged_count,
            "updated": updated_count,
            "details": fixed_details,
            "dry_run": dry_run,
        }
