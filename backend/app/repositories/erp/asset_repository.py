"""ERP 資產管理 Repository"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.asset import Asset, AssetLog
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AssetRepository(BaseRepository[Asset]):
    """資產資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Asset)

    async def list_assets(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        case_code: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Asset], int]:
        """篩選資產列表 + 總數"""
        query = select(Asset)

        if category:
            query = query.where(Asset.category == category)
        if status:
            query = query.where(Asset.status == status)
        if case_code:
            query = query.where(Asset.case_code == case_code)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(
                or_(
                    Asset.name.ilike(pattern),
                    Asset.asset_code.ilike(pattern),
                    Asset.brand.ilike(pattern),
                    Asset.model.ilike(pattern),
                    Asset.serial_number.ilike(pattern),
                    Asset.custodian.ilike(pattern),
                    Asset.location.ilike(pattern),
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginated results
        query = query.order_by(Asset.id.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_asset(self, asset_id: int) -> Optional[Asset]:
        """取得單一資產"""
        return await self.get_by_id(asset_id)

    async def create_asset(self, data: Dict[str, Any]) -> Asset:
        """建立資產"""
        asset = Asset(**data)
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)
        return asset

    async def update_asset(self, asset_id: int, data: Dict[str, Any]) -> Optional[Asset]:
        """更新資產"""
        asset = await self.get_by_id(asset_id)
        if not asset:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(asset, key, value)
        await self.db.flush()
        await self.db.refresh(asset)
        return asset

    async def delete_asset(self, asset_id: int) -> bool:
        """刪除資產"""
        asset = await self.get_by_id(asset_id)
        if not asset:
            return False
        await self.db.delete(asset)
        await self.db.flush()
        return True

    async def get_asset_stats(self) -> Dict[str, Any]:
        """取得資產統計"""
        # Status counts
        status_query = (
            select(Asset.status, func.count(Asset.id))
            .group_by(Asset.status)
        )
        result = await self.db.execute(status_query)
        status_counts = {row[0]: row[1] for row in result.all()}

        # Category counts with total value
        category_query = (
            select(
                Asset.category,
                func.count(Asset.id).label("count"),
                func.coalesce(func.sum(Asset.current_value), 0).label("value"),
            )
            .group_by(Asset.category)
        )
        result = await self.db.execute(category_query)
        by_category = {}
        for row in result.all():
            by_category[row.category] = {
                "count": row.count,
                "value": str(Decimal(str(row.value))),
            }

        # Total value
        total_value_query = select(
            func.coalesce(func.sum(Asset.current_value), 0)
        )
        total_value = await self.db.scalar(total_value_query) or 0

        total_count = sum(status_counts.values())

        return {
            "total_count": total_count,
            "in_use": status_counts.get("in_use", 0),
            "maintenance": status_counts.get("maintenance", 0),
            "idle": status_counts.get("idle", 0),
            "disposed": status_counts.get("disposed", 0),
            "total_value": Decimal(str(total_value)),
            "by_category": by_category,
        }

    async def get_asset_with_invoice(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """Get asset with linked expense invoice details"""
        from app.extended.models.invoice import ExpenseInvoice

        asset = await self.get_asset(asset_id)
        if not asset:
            return None

        result: Dict[str, Any] = {
            "asset": asset,
            "invoice": None,
            "case_quotation": None,
        }

        # Get linked invoice
        if asset.expense_invoice_id:
            inv = (await self.db.execute(
                select(ExpenseInvoice).where(ExpenseInvoice.id == asset.expense_invoice_id)
            )).scalars().first()
            if inv:
                result["invoice"] = {
                    "id": inv.id,
                    "inv_num": inv.inv_num,
                    "date": str(inv.date) if inv.date else None,
                    "amount": str(inv.amount) if inv.amount else "0",
                    "seller_ban": inv.seller_ban,
                    "category": inv.category,
                    "status": inv.status,
                    "source": inv.source,
                }

        # Get case quotation if case_code exists
        if asset.case_code:
            from app.extended.models.erp import ERPQuotation
            quot = (await self.db.execute(
                select(ERPQuotation).where(ERPQuotation.case_code == asset.case_code)
            )).scalars().first()
            if quot:
                result["case_quotation"] = {
                    "id": quot.id,
                    "case_code": quot.case_code,
                    "case_name": quot.case_name,
                    "total_price": str(quot.total_price) if quot.total_price else "0",
                    "status": quot.status,
                }

        return result

    async def get_assets_by_invoice(self, expense_invoice_id: int) -> List[Asset]:
        """取得關聯到指定發票的所有資產"""
        query = (
            select(Asset)
            .where(Asset.expense_invoice_id == expense_invoice_id)
            .order_by(Asset.id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_code(self, asset_code: str) -> Optional[Asset]:
        """根據資產編號查詢"""
        query = select(Asset).where(Asset.asset_code == asset_code)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def check_code_exists(self, asset_code: str) -> bool:
        """檢查資產編號是否已存在"""
        query = select(func.count()).where(Asset.asset_code == asset_code)
        count = await self.db.scalar(query) or 0
        return count > 0


class AssetLogRepository(BaseRepository[AssetLog]):
    """資產行為紀錄資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, AssetLog)

    async def list_asset_logs(
        self,
        asset_id: int,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AssetLog], int]:
        """取得資產行為紀錄列表"""
        query = select(AssetLog).where(AssetLog.asset_id == asset_id)

        if action:
            query = query.where(AssetLog.action == action)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginated results
        query = query.order_by(AssetLog.action_date.desc(), AssetLog.id.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create_asset_log(self, data: Dict[str, Any]) -> AssetLog:
        """建立行為紀錄"""
        log = AssetLog(**data)
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log
