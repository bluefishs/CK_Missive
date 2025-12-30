"""
Service layer for Contract Project operations
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError

from app.extended.models import ContractProject, project_vendor_association
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)

class ProjectService:
    """承攬案件相關的資料庫操作服務"""

    async def get_project(self, db: AsyncSession, project_id: int) -> Optional[ContractProject]:
        result = await db.execute(select(ContractProject).where(ContractProject.id == project_id))
        return result.scalar_one_or_none()

    async def get_projects(self, db: AsyncSession, query_params) -> Dict[str, Any]:
        query = select(ContractProject)
        if query_params.search:
            query = query.where(ContractProject.project_name.ilike(f"%{query_params.search}%"))
        if query_params.year: query = query.where(ContractProject.year == query_params.year)
        if query_params.category: query = query.where(ContractProject.category == query_params.category)
        if query_params.status: query = query.where(ContractProject.status == query_params.status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        result = await db.execute(
            query.order_by(ContractProject.id.desc()).offset(query_params.skip).limit(query_params.limit)
        )
        projects = result.scalars().all()
        return {"projects": projects, "total": total}

    async def create_project(self, db: AsyncSession, project: ProjectCreate) -> ContractProject:
        if project.project_code:
            existing = (await db.execute(select(ContractProject).where(ContractProject.project_code == project.project_code))).scalar_one_or_none()
            if existing:
                raise ValueError(f"專案編號 {project.project_code} 已存在")
        
        db_project = ContractProject(**project.model_dump())
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)
        return db_project

    async def update_project(self, db: AsyncSession, project_id: int, project_update: ProjectUpdate) -> Optional[ContractProject]:
        db_project = await self.get_project(db, project_id)
        if not db_project:
            return None
        
        update_data = project_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_project, key, value)
        
        await db.commit()
        await db.refresh(db_project)
        return db_project

    async def delete_project(self, db: AsyncSession, project_id: int) -> bool:
        db_project = await self.get_project(db, project_id)
        if not db_project:
            return False
        
        # 注意：此處應先處理關聯的公文，但為簡化，暫時直接刪除。
        # 在正式系統中，應先檢查 documents.contract_project_id 是否有引用。
        # 我們在 models.py 中設定了級聯刪除，所以關聯的 calendar_events 等會被處理。
        
        await db.delete(db_project)
        await db.commit()
        return True

    async def get_project_statistics(self, db: AsyncSession) -> dict:
        """取得專案統計資料"""
        try:
            # 總專案數
            total_result = await db.execute(select(func.count(ContractProject.id)))
            total_projects = total_result.scalar() or 0

            # 按狀態分組統計
            status_result = await db.execute(
                select(ContractProject.status, func.count(ContractProject.id))
                .group_by(ContractProject.status)
                .order_by(ContractProject.status)
            )
            status_stats = [
                {"status": row[0] or "未設定", "count": row[1]}
                for row in status_result.fetchall()
            ]

            # 按年度分組統計
            year_result = await db.execute(
                select(ContractProject.year, func.count(ContractProject.id))
                .group_by(ContractProject.year)
                .order_by(ContractProject.year.desc())
            )
            year_stats = [
                {"year": row[0], "count": row[1]}
                for row in year_result.fetchall()
            ]

            # 平均合約金額
            amount_result = await db.execute(
                select(func.avg(ContractProject.contract_amount)).where(ContractProject.contract_amount.isnot(None))
            )
            avg_amount = amount_result.scalar()
            avg_amount = round(float(avg_amount), 2) if avg_amount else 0.0

            return {
                "total_projects": total_projects,
                "status_breakdown": status_stats,
                "year_breakdown": year_stats,
                "average_contract_amount": avg_amount
            }
        except Exception as e:
            logger.error(f"取得專案統計資料失敗: {e}", exc_info=True)
            return {
                "total_projects": 0,
                "status_breakdown": [],
                "year_breakdown": [],
                "average_contract_amount": 0.0
            }
