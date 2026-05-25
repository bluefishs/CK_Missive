# -*- coding: utf-8 -*-
"""ContractFacade - Contract project context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

解 step 29 揭發：
  - erp -> contract (4 imports) — ERP 模組大量查 contract project
  - document -> contract (1)
  - 其他散 imports

統一封 contract_project / case_code / staff / agency_contact 操作。
"""
from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class ContractFacade:
    """Contract project bounded context 對外唯一入口

    案件(case_code 邀標/報價階段) + 承攬專案(project_code 成案後) 跨域查詢。

    使用範例：
        facade = ContractFacade(db)
        project = await facade.get_by_case_code("CK2026_01_03_001")
        staff = await facade.list_staff(project_id=42)
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Public API ===

    async def get_by_case_code(
        self,
        case_code: str,
    ) -> Optional[dict]:
        """以 case_code 取得 contract project

        取代 erp/billing_service.py 直 import contract/case_code.py
        """
        try:
            from app.services.contract.case_code import resolve_case_code
            return await resolve_case_code(self._db, case_code)
        except (ImportError, AttributeError):
            return None

    async def get_by_project_code(
        self,
        project_code: str,
    ) -> Optional[dict]:
        """以 project_code 取得 contract project"""
        try:
            from app.repositories.project_repository import ProjectRepository
            repo = ProjectRepository(self._db)
            return await repo.get_by_project_code(project_code)
        except (ImportError, AttributeError):
            return None

    async def list_staff(
        self,
        project_id: int,
    ) -> List[dict]:
        """列承辦人員（跨域查詢）"""
        try:
            from app.services.contract.staff_service import ContractStaffService
            svc = ContractStaffService(self._db)
            return await svc.list_for_project(project_id)
        except (ImportError, AttributeError):
            return []

    async def get_agency_contact(
        self,
        project_id: int,
    ) -> Optional[dict]:
        """取得專案對應機關聯絡人（給 calendar/notification 用）"""
        try:
            from app.services.contract.agency_contact_service import (
                AgencyContactService,
            )
            svc = AgencyContactService(self._db)
            return await svc.get_primary_for_project(project_id)
        except (ImportError, AttributeError):
            return None

    async def list_vendors(
        self,
        project_id: int,
    ) -> List[dict]:
        """列承攬廠商（跨域查詢）"""
        try:
            from app.services.contract.field_sync_service import list_project_vendors
            return await list_project_vendors(self._db, project_id)
        except (ImportError, AttributeError):
            return []


__all__ = ["ContractFacade"]
