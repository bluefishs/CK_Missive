# -*- coding: utf-8 -*-
"""AgencyFacade - Agency (委託機關) context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class AgencyFacade:
    """Agency bounded context 對外唯一入口"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, agency_id: int) -> Optional[dict]:
        try:
            from app.repositories.agency_repository import AgencyRepository
            repo = AgencyRepository(self._db)
            return await repo.get_by_id(agency_id)
        except (ImportError, AttributeError):
            return None

    async def match_by_name(self, name: str) -> Optional[dict]:
        """模糊比對機關名稱（給文件 ingest 用）"""
        try:
            from app.repositories.agency_repository import AgencyRepository
            repo = AgencyRepository(self._db)
            return await repo.match_agency(name)
        except (ImportError, AttributeError):
            return None

    async def list_active(self, limit: int = 100) -> List[dict]:
        try:
            from app.repositories.agency_repository import AgencyRepository
            repo = AgencyRepository(self._db)
            return await repo.list_active(limit=limit)
        except (ImportError, AttributeError):
            return []

    async def get_contact(self, agency_id: int) -> Optional[dict]:
        try:
            from app.repositories.contact_repository import ContactRepository
            repo = ContactRepository(self._db)
            return await repo.get_primary_contact_for_agency(agency_id)
        except (ImportError, AttributeError):
            return None


__all__ = ["AgencyFacade"]
