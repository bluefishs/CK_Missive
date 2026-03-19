"""
PM Query Service — 專案管理 Agent 工具查詢服務

提供 Agent 用的專案管理查詢能力：
- search_projects: 搜尋承攬案件
- get_project_detail: 取得案件詳情（含工程/派工/金額）
- get_project_progress: 取得案件進度與里程碑
- get_overdue_milestones: 查詢所有逾期里程碑

Version: 1.1.0
Created: 2026-03-15
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PMQueryService:
    """專案管理查詢服務 — 供 Agent 工具使用"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_projects(
        self,
        keywords: Optional[List[str]] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        client_agency: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """搜尋承攬案件"""
        from app.extended.models.core import ContractProject

        query = select(ContractProject)

        if keywords:
            keyword_filters = []
            for kw in keywords:
                keyword_filters.append(
                    ContractProject.project_name.ilike(f"%{kw}%")
                )
            query = query.where(or_(*keyword_filters))

        if status:
            query = query.where(ContractProject.status == status)

        if year:
            query = query.where(ContractProject.year == year)

        if client_agency:
            query = query.where(
                ContractProject.client_agency.ilike(f"%{client_agency}%")
            )

        query = query.order_by(ContractProject.updated_at.desc()).limit(min(limit, 20))

        result = await self.db.execute(query)
        projects = result.scalars().all()

        items = []
        for p in projects:
            items.append({
                "id": p.id,
                "project_name": p.project_name,
                "project_code": p.project_code,
                "year": p.year,
                "status": p.status,
                "client_agency": p.client_agency,
                "category": p.category,
                "contract_amount": p.contract_amount,
                "progress": p.progress,
                "start_date": str(p.start_date) if p.start_date else None,
                "end_date": str(p.end_date) if p.end_date else None,
            })

        return {"projects": items, "count": len(items)}

    async def get_project_detail(self, project_id: int) -> Dict[str, Any]:
        """取得案件詳情（含關聯工程/派工/金額）"""
        from app.extended.models.core import ContractProject
        from app.extended.models.taoyuan import (
            TaoyuanDispatchOrder,
            TaoyuanProject,
        )

        # 基本資訊
        result = await self.db.execute(
            select(ContractProject).where(ContractProject.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": f"找不到案件 ID={project_id}", "count": 0}

        detail: Dict[str, Any] = {
            "id": project.id,
            "project_name": project.project_name,
            "project_code": project.project_code,
            "year": project.year,
            "status": project.status,
            "client_agency": project.client_agency,
            "category": project.category,
            "case_nature": project.case_nature,
            "contract_amount": project.contract_amount,
            "winning_amount": project.winning_amount,
            "progress": project.progress,
            "start_date": str(project.start_date) if project.start_date else None,
            "end_date": str(project.end_date) if project.end_date else None,
            "location": project.location,
            "contact_person": project.contact_person,
            "notes": project.notes,
        }

        # 關聯工程數
        eng_count = await self.db.execute(
            select(func.count(TaoyuanProject.id)).where(
                TaoyuanProject.contract_project_id == project_id
            )
        )
        detail["engineering_count"] = eng_count.scalar() or 0

        # 關聯派工數
        disp_count = await self.db.execute(
            select(func.count(TaoyuanDispatchOrder.id)).where(
                TaoyuanDispatchOrder.contract_project_id == project_id
            )
        )
        detail["dispatch_count"] = disp_count.scalar() or 0

        return {"project": detail, "count": 1}

    async def get_project_progress(self, project_id: int) -> Dict[str, Any]:
        """取得案件進度與里程碑概要"""
        from app.extended.models.core import ContractProject
        from app.extended.models.taoyuan import (
            TaoyuanDispatchOrder,
            TaoyuanProject,
        )

        result = await self.db.execute(
            select(ContractProject).where(ContractProject.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": f"找不到案件 ID={project_id}", "count": 0}

        # 派工單統計（依批次）
        batch_result = await self.db.execute(
            select(
                TaoyuanDispatchOrder.batch_no,
                TaoyuanDispatchOrder.batch_label,
                func.count(TaoyuanDispatchOrder.id).label("count"),
            )
            .where(TaoyuanDispatchOrder.contract_project_id == project_id)
            .group_by(TaoyuanDispatchOrder.batch_no, TaoyuanDispatchOrder.batch_label)
            .order_by(TaoyuanDispatchOrder.batch_no)
        )
        batches = [
            {"batch_no": r.batch_no, "batch_label": r.batch_label, "count": r.count}
            for r in batch_result.all()
        ]

        # 工程進度摘要
        eng_result = await self.db.execute(
            select(
                TaoyuanProject.project_name,
                TaoyuanProject.building_survey_status,
                TaoyuanProject.land_agreement_status,
                TaoyuanProject.acceptance_status,
            )
            .where(TaoyuanProject.contract_project_id == project_id)
            .limit(20)
        )
        engineering = [
            {
                "project_name": r.project_name,
                "survey_status": r.building_survey_status,
                "land_status": r.land_agreement_status,
                "acceptance": r.acceptance_status,
            }
            for r in eng_result.all()
        ]

        today = date.today()
        is_overdue = project.end_date and project.end_date < today
        days_remaining = (
            (project.end_date - today).days if project.end_date and not is_overdue else None
        )

        return {
            "progress": {
                "project_name": project.project_name,
                "overall_progress": project.progress,
                "status": project.status,
                "is_overdue": is_overdue,
                "days_remaining": days_remaining,
                "end_date": str(project.end_date) if project.end_date else None,
                "dispatch_batches": batches,
                "engineering_summary": engineering,
            },
            "count": 1,
        }

    async def get_overdue_milestones(self, limit: int = 20) -> Dict[str, Any]:
        """查詢所有逾期里程碑（已過期但未完成）"""
        from app.extended.models.pm import PMCase, PMMilestone

        today = date.today()

        query = (
            select(
                PMMilestone.id,
                PMMilestone.milestone_name,
                PMMilestone.milestone_type,
                PMMilestone.planned_date,
                PMMilestone.status,
                PMMilestone.notes,
                PMCase.case_code,
                PMCase.case_name,
            )
            .join(PMCase, PMMilestone.pm_case_id == PMCase.id)
            .where(
                PMMilestone.status.in_(["pending", "in_progress"]),
                PMMilestone.planned_date < today,
            )
            .order_by(PMMilestone.planned_date.asc())
            .limit(min(limit, 50))
        )
        result = await self.db.execute(query)
        rows = result.all()

        items = [
            {
                "milestone_id": row.id,
                "milestone_name": row.milestone_name,
                "milestone_type": row.milestone_type,
                "planned_date": str(row.planned_date),
                "status": row.status,
                "case_code": row.case_code,
                "case_name": row.case_name,
                "overdue_days": (today - row.planned_date).days,
                "notes": row.notes,
            }
            for row in rows
        ]

        return {"milestones": items, "count": len(items)}
