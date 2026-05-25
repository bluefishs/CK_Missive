# -*- coding: utf-8 -*-
"""VendorFacade - Vendor (廠商) context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class VendorFacade:
    """Vendor bounded context 對外唯一入口"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, vendor_id: int) -> Optional[dict]:
        try:
            from app.repositories.vendor_repository import VendorRepository
            repo = VendorRepository(self._db)
            return await repo.get_by_id(vendor_id)
        except (ImportError, AttributeError):
            return None

    async def list_by_type(
        self,
        vendor_type: str = "subcontractor",
        limit: int = 100,
    ) -> List[dict]:
        """按 vendor_type 列廠商 (subcontractor / client)"""
        try:
            from app.repositories.vendor_repository import VendorRepository
            repo = VendorRepository(self._db)
            return await repo.list_by_type(vendor_type=vendor_type, limit=limit)
        except (ImportError, AttributeError):
            return []

    async def list_for_project(self, project_id: int) -> List[dict]:
        """列特定專案的承攬廠商"""
        try:
            from app.repositories.vendor_repository import VendorRepository
            repo = VendorRepository(self._db)
            return await repo.list_for_project(project_id)
        except (ImportError, AttributeError):
            return []

    async def match_by_name(self, name: str) -> Optional[dict]:
        """模糊比對廠商名稱"""
        try:
            from app.repositories.vendor_repository import VendorRepository
            repo = VendorRepository(self._db)
            return await repo.match_by_name(name)
        except (ImportError, AttributeError):
            return None


__all__ = ["VendorFacade"]
