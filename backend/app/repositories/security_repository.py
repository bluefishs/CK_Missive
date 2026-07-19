"""SecurityRepository — 資安管理中心資料存取（DDD 標準化，2026-07-20）

標準化收斂：原 endpoints/security.py 端點內直接 select()/group_by SecurityIssue/
SecurityScan，繞過 repository 層（治理端點標準化盲區）。抽出本 repository 封裝所有
SecurityIssue/SecurityScan 查詢，端點/service 改委派。行為保真。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.security import SecurityIssue, SecurityScan


class SecurityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── SecurityIssue 聚合（OWASP 儀表板）──────────────────────────
    async def owasp_category_stats(self) -> List[Any]:
        """依 OWASP 類別統計 total + open_count。"""
        q = await self.db.execute(
            select(
                SecurityIssue.owasp_category,
                func.count().label("count"),
                func.sum(case((SecurityIssue.status == "open", 1), else_=0)).label("open_count"),
            )
            .where(SecurityIssue.owasp_category.isnot(None))
            .group_by(SecurityIssue.owasp_category)
        )
        return q.all()

    async def open_severity_distribution(self) -> Dict[str, int]:
        q = await self.db.execute(
            select(SecurityIssue.severity, func.count())
            .where(SecurityIssue.status == "open")
            .group_by(SecurityIssue.severity)
        )
        return {row[0]: row[1] for row in q.all()}

    async def status_distribution(self) -> Dict[str, int]:
        q = await self.db.execute(
            select(SecurityIssue.status, func.count()).group_by(SecurityIssue.status)
        )
        return dict(q.all())

    async def count_total_issues(self) -> int:
        return (await self.db.execute(select(func.count()).select_from(SecurityIssue))).scalar() or 0

    async def count_open_issues(self) -> int:
        return (await self.db.execute(
            select(func.count()).select_from(SecurityIssue).where(SecurityIssue.status == "open")
        )).scalar() or 0

    async def last_scan(self) -> Optional[SecurityScan]:
        q = await self.db.execute(
            select(SecurityScan).order_by(SecurityScan.created_at.desc()).limit(1)
        )
        return q.scalar_one_or_none()

    # ── SecurityIssue CRUD ─────────────────────────────────────────
    async def list_issues(
        self, project_name: Optional[str], status: Optional[str],
        severity: Optional[str], page: int, limit: int,
    ) -> tuple[List[SecurityIssue], int]:
        stmt = select(SecurityIssue)
        if project_name:
            stmt = stmt.where(SecurityIssue.project_name == project_name)
        if status:
            stmt = stmt.where(SecurityIssue.status == status)
        if severity:
            stmt = stmt.where(SecurityIssue.severity == severity)
        total = (await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar() or 0
        stmt = stmt.order_by(SecurityIssue.created_at.desc()).offset((page - 1) * limit).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()
        return rows, total

    async def create_issue(self, data: Dict[str, Any]) -> SecurityIssue:
        issue = SecurityIssue(**data)
        self.db.add(issue)
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def update_issue(self, issue_id: int, updates: Dict[str, Any]) -> Optional[SecurityIssue]:
        issue = await self.db.get(SecurityIssue, issue_id)
        if not issue:
            return None
        if updates.get("status") == "resolved":
            updates["resolved_at"] = datetime.now()
        for k, v in updates.items():
            setattr(issue, k, v)
        await self.db.commit()
        return issue

    async def recent_issues(self, statuses: List[str], limit: int) -> List[SecurityIssue]:
        q = await self.db.execute(
            select(SecurityIssue)
            .where(SecurityIssue.status.in_(statuses))
            .order_by(SecurityIssue.updated_at.desc())
            .limit(limit)
        )
        return list(q.scalars().all())

    # ── SecurityScan ───────────────────────────────────────────────
    async def list_scans(
        self, project_name: Optional[str], page: int, limit: int,
    ) -> List[SecurityScan]:
        stmt = select(SecurityScan).order_by(SecurityScan.created_at.desc())
        if project_name:
            stmt = stmt.where(SecurityScan.project_name == project_name)
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def recent_scans(self, limit: int) -> List[SecurityScan]:
        q = await self.db.execute(
            select(SecurityScan).order_by(SecurityScan.created_at.desc()).limit(limit)
        )
        return list(q.scalars().all())

    async def create_scan(self, **kwargs: Any) -> SecurityScan:
        scan = SecurityScan(**kwargs)
        self.db.add(scan)
        await self.db.commit()
        await self.db.refresh(scan)
        return scan
