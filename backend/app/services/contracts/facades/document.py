# -*- coding: utf-8 -*-
"""DocumentFacade - Document context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

解 step 29 揭發：
  - ai -> document (3 imports)
  - 其他 context 對 document 散查

統一封 official document CRUD / dispatch link / chunk / entity 操作。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession


class DocumentFacade:
    """Document bounded context 對外唯一入口

    使用範例：
        facade = DocumentFacade(db)
        doc = await facade.get_by_id(123)
        results = await facade.search("query")
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Public API ===

    async def get_by_id(
        self,
        doc_id: int,
        with_attachments: bool = False,
    ) -> Optional[dict]:
        """取得單一 document"""
        try:
            from app.repositories.document_repository import DocumentRepository
            repo = DocumentRepository(self._db)
            return await repo.get_with_optional_relations(
                doc_id, with_attachments=with_attachments,
            )
        except (ImportError, AttributeError):
            return None

    async def search(
        self,
        query: str,
        *,
        user_id: Optional[int] = None,
        doc_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """搜尋 documents（支援關鍵字 + RLS）"""
        try:
            from app.repositories.document_repository import DocumentRepository
            repo = DocumentRepository(self._db)
            docs, _ = await repo.filter_documents(
                keyword=query, doc_type=doc_type, user_id=user_id, limit=limit,
            )
            return docs
        except (ImportError, AttributeError):
            return []

    async def get_recent_for_user(
        self,
        user_id: int,
        days: int = 7,
    ) -> List[dict]:
        """近 N 天 documents（給 calendar / notification 用）"""
        try:
            from app.repositories.document_repository import DocumentRepository
            repo = DocumentRepository(self._db)
            return await repo.get_recent_for_user(user_id, days=days)
        except (ImportError, AttributeError):
            return []

    async def get_statistics(
        self,
        *,
        year: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> dict:
        """document 統計（給 ai / dashboard 用）"""
        try:
            from app.repositories.document_stats_repository import (
                DocumentStatsRepository,
            )
            repo = DocumentStatsRepository(self._db)
            return await repo.get_statistics(year=year, user_id=user_id)
        except (ImportError, AttributeError):
            return {"total": 0, "incoming": 0, "outgoing": 0}

    async def get_linked_dispatches(
        self,
        doc_id: int,
    ) -> List[dict]:
        """取得關聯 dispatch 單"""
        try:
            from app.repositories.taoyuan.dispatch_doc_link_repository import (
                DispatchDocLinkRepository,
            )
            repo = DispatchDocLinkRepository(self._db)
            return await repo.list_by_document(doc_id)
        except (ImportError, AttributeError):
            return []


__all__ = ["DocumentFacade"]
