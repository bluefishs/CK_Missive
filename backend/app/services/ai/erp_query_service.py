"""
ERP Query Service — 企業資源 Agent 工具查詢服務

提供 Agent 用的 ERP 查詢能力：
- search_vendors: 搜尋協力廠商
- get_vendor_detail: 取得廠商詳情（含關聯案件）
- get_contract_summary: 取得合約金額統計
- get_unpaid_billings: 查詢未收款/逾期請款

Version: 1.1.0
Created: 2026-03-15
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ERPQueryService:
    """企業資源查詢服務 — 供 Agent 工具使用"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_vendors(
        self,
        keywords: Optional[List[str]] = None,
        business_type: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """搜尋協力廠商"""
        from app.extended.models.core import PartnerVendor

        query = select(PartnerVendor)

        if keywords:
            keyword_filters = []
            for kw in keywords:
                keyword_filters.append(PartnerVendor.vendor_name.ilike(f"%{kw}%"))
            query = query.where(or_(*keyword_filters))

        if business_type:
            query = query.where(
                PartnerVendor.business_type.ilike(f"%{business_type}%")
            )

        query = query.order_by(PartnerVendor.updated_at.desc()).limit(min(limit, 20))

        result = await self.db.execute(query)
        vendors = result.scalars().all()

        items = []
        for v in vendors:
            items.append({
                "id": v.id,
                "vendor_name": v.vendor_name,
                "vendor_code": v.vendor_code,
                "contact_person": v.contact_person,
                "phone": v.phone,
                "business_type": v.business_type,
                "rating": v.rating,
            })

        return {"vendors": items, "count": len(items)}

    async def get_vendor_detail(self, vendor_id: int) -> Dict[str, Any]:
        """取得廠商詳情"""
        from app.extended.models.core import PartnerVendor

        result = await self.db.execute(
            select(PartnerVendor).where(PartnerVendor.id == vendor_id)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            return {"error": f"找不到廠商 ID={vendor_id}", "count": 0}

        detail = {
            "id": vendor.id,
            "vendor_name": vendor.vendor_name,
            "vendor_code": vendor.vendor_code,
            "contact_person": vendor.contact_person,
            "phone": vendor.phone,
            "email": vendor.email,
            "address": vendor.address,
            "business_type": vendor.business_type,
            "rating": vendor.rating,
        }

        return {"vendor": detail, "count": 1}

    async def get_contract_summary(
        self,
        year: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """取得合約金額統計概要"""
        from app.extended.models.core import ContractProject

        base_query = select(ContractProject)

        if year:
            base_query = base_query.where(ContractProject.year == year)
        if status:
            base_query = base_query.where(ContractProject.status == status)

        # 總金額統計
        stats_query = select(
            func.count(ContractProject.id).label("total_projects"),
            func.sum(ContractProject.contract_amount).label("total_contract_amount"),
            func.sum(ContractProject.winning_amount).label("total_winning_amount"),
            func.avg(ContractProject.progress).label("avg_progress"),
        )
        if year:
            stats_query = stats_query.where(ContractProject.year == year)
        if status:
            stats_query = stats_query.where(ContractProject.status == status)

        result = await self.db.execute(stats_query)
        row = result.one()

        # 依狀態分佈
        status_query = select(
            ContractProject.status,
            func.count(ContractProject.id).label("count"),
            func.sum(ContractProject.contract_amount).label("amount"),
        ).group_by(ContractProject.status)

        if year:
            status_query = status_query.where(ContractProject.year == year)

        status_result = await self.db.execute(status_query)
        status_dist = [
            {
                "status": r.status or "未設定",
                "count": r.count,
                "amount": float(r.amount) if r.amount else 0,
            }
            for r in status_result.all()
        ]

        # 依年度分佈
        year_query = (
            select(
                ContractProject.year,
                func.count(ContractProject.id).label("count"),
                func.sum(ContractProject.contract_amount).label("amount"),
            )
            .where(ContractProject.year.isnot(None))
            .group_by(ContractProject.year)
            .order_by(ContractProject.year.desc())
            .limit(10)
        )
        year_result = await self.db.execute(year_query)
        year_dist = [
            {
                "year": r.year,
                "count": r.count,
                "amount": float(r.amount) if r.amount else 0,
            }
            for r in year_result.all()
        ]

        return {
            "summary": {
                "total_projects": row.total_projects or 0,
                "total_contract_amount": float(row.total_contract_amount) if row.total_contract_amount else 0,
                "total_winning_amount": float(row.total_winning_amount) if row.total_winning_amount else 0,
                "avg_progress": round(float(row.avg_progress), 1) if row.avg_progress else 0,
                "status_distribution": status_dist,
                "year_distribution": year_dist,
            },
            "count": 1,
        }

    async def get_unpaid_billings(self, limit: int = 20) -> Dict[str, Any]:
        """查詢未收款/逾期請款"""
        from datetime import date

        from app.extended.models.erp import ERPBilling, ERPQuotation

        today = date.today()

        query = (
            select(
                ERPBilling.id,
                ERPBilling.billing_period,
                ERPBilling.billing_date,
                ERPBilling.billing_amount,
                ERPBilling.payment_status,
                ERPBilling.payment_date,
                ERPBilling.payment_amount,
                ERPBilling.notes,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .where(ERPBilling.payment_status.in_(["pending", "partial", "overdue"]))
            .order_by(ERPBilling.billing_date.asc())
            .limit(min(limit, 50))
        )
        result = await self.db.execute(query)
        rows = result.all()

        items = [
            {
                "billing_id": row.id,
                "billing_period": row.billing_period,
                "billing_date": str(row.billing_date) if row.billing_date else None,
                "billing_amount": str(row.billing_amount) if row.billing_amount else "0",
                "payment_amount": str(row.payment_amount) if row.payment_amount else "0",
                "outstanding": str(
                    (row.billing_amount or 0) - (row.payment_amount or 0)
                ),
                "payment_status": row.payment_status,
                "payment_date": str(row.payment_date) if row.payment_date else None,
                "case_code": row.case_code,
                "case_name": row.case_name,
                "is_overdue": row.payment_status == "overdue",
                "notes": row.notes,
            }
            for row in rows
        ]

        return {"billings": items, "count": len(items)}
