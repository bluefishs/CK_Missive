"""
DispatchLinkRepository - 派工-公文-工程三方關聯資料存取層 (組合包裝)

透過組合模式整合 DispatchDocLinkRepository 和 DispatchProjectLinkRepository，
維持向後相容的統一介面。

拆分結構:
- dispatch_doc_link_repository.py: 派工-公文關聯 CRUD + 同步 + 批次查詢
- dispatch_project_link_repository.py: 派工-工程 / 公文-工程關聯 CRUD + 清理 + 批次查詢
- dispatch_link_repository.py: 本檔案，組合包裝層

@version 2.0.0
@date 2026-02-25
"""

import logging
from typing import Optional, List, Dict, Any, Set

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDocumentProjectLink,
    CanonicalEntity,
    EntityAlias,
    TaoyuanDispatchEntityLink,
)

from .dispatch_doc_link_repository import DispatchDocLinkRepository
from .dispatch_project_link_repository import DispatchProjectLinkRepository

logger = logging.getLogger(__name__)


class DispatchLinkRepository:
    """
    派工-公文-工程三方關聯資料存取層（組合包裝）

    維持向後相容的統一介面，內部委派給：
    - DispatchDocLinkRepository: 派工-公文關聯
    - DispatchProjectLinkRepository: 派工-工程 / 公文-工程關聯

    建議新程式碼直接使用拆分後的子 Repository。
    """

    def __init__(self, db: AsyncSession):
        """
        初始化 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
        self._doc_repo = DispatchDocLinkRepository(db)
        self._project_repo = DispatchProjectLinkRepository(db)

    # =========================================================================
    # 派工-公文關聯 (Dispatch-Document) — 委派給 DispatchDocLinkRepository
    # =========================================================================

    async def link_dispatch_to_document(
        self,
        dispatch_id: int,
        document_id: int,
        link_type: str = "agency_incoming",
        auto_commit: bool = True,
        confidence: Optional[str] = None,
    ) -> Optional[TaoyuanDispatchDocumentLink]:
        return await self._doc_repo.link_dispatch_to_document(
            dispatch_id, document_id, link_type, auto_commit, confidence
        )

    async def unlink_dispatch_from_document(
        self, link_id: int, auto_commit: bool = True
    ) -> bool:
        return await self._doc_repo.unlink_dispatch_from_document(link_id, auto_commit)

    async def get_documents_for_dispatch(
        self, dispatch_id: int
    ) -> List[TaoyuanDispatchDocumentLink]:
        return await self._doc_repo.get_documents_for_dispatch(dispatch_id)

    async def get_dispatches_for_document(
        self, document_id: int
    ) -> List[TaoyuanDispatchDocumentLink]:
        return await self._doc_repo.get_dispatches_for_document(document_id)

    async def find_dispatch_document_link(
        self,
        dispatch_id: int,
        document_id: int,
        link_type: Optional[str] = None,
    ) -> Optional[TaoyuanDispatchDocumentLink]:
        return await self._doc_repo.find_dispatch_document_link(
            dispatch_id, document_id, link_type
        )

    async def sync_document_links(
        self,
        dispatch_id: int,
        agency_doc_id: Optional[int] = None,
        company_doc_id: Optional[int] = None,
        auto_commit: bool = False,
    ) -> Dict[str, Any]:
        return await self._doc_repo.sync_document_links(
            dispatch_id, agency_doc_id, company_doc_id, auto_commit
        )

    # =========================================================================
    # 派工-工程關聯 (Dispatch-Project) — 委派給 DispatchProjectLinkRepository
    # =========================================================================

    async def link_dispatch_to_project(
        self,
        dispatch_id: int,
        project_id: int,
        auto_commit: bool = True,
    ) -> Optional[TaoyuanDispatchProjectLink]:
        return await self._project_repo.link_dispatch_to_project(
            dispatch_id, project_id, auto_commit
        )

    async def unlink_dispatch_from_project(
        self, link_id: int, auto_commit: bool = True
    ) -> bool:
        return await self._project_repo.unlink_dispatch_from_project(
            link_id, auto_commit
        )

    async def get_projects_for_dispatch(
        self, dispatch_id: int
    ) -> List[TaoyuanDispatchProjectLink]:
        return await self._project_repo.get_projects_for_dispatch(dispatch_id)

    async def get_dispatches_for_project(
        self, project_id: int
    ) -> List[TaoyuanDispatchProjectLink]:
        return await self._project_repo.get_dispatches_for_project(project_id)

    async def replace_dispatch_project_links(
        self,
        dispatch_id: int,
        project_ids: List[int],
        auto_commit: bool = True,
    ) -> List[TaoyuanDispatchProjectLink]:
        return await self._project_repo.replace_dispatch_project_links(
            dispatch_id, project_ids, auto_commit
        )

    # =========================================================================
    # 公文-工程關聯 (Document-Project) — 委派給 DispatchProjectLinkRepository
    # =========================================================================

    async def link_document_to_project(
        self,
        document_id: int,
        project_id: int,
        link_type: Optional[str] = None,
        notes: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Optional[TaoyuanDocumentProjectLink]:
        return await self._project_repo.link_document_to_project(
            document_id, project_id, link_type, notes, auto_commit
        )

    async def unlink_document_from_project(
        self, link_id: int, auto_commit: bool = True
    ) -> bool:
        return await self._project_repo.unlink_document_from_project(
            link_id, auto_commit
        )

    async def get_projects_for_document(
        self, document_id: int
    ) -> List[TaoyuanDocumentProjectLink]:
        return await self._project_repo.get_projects_for_document(document_id)

    async def get_documents_for_project(
        self, project_id: int
    ) -> List[TaoyuanDocumentProjectLink]:
        return await self._project_repo.get_documents_for_project(project_id)

    # =========================================================================
    # 孤立記錄清理 — 委派給 DispatchProjectLinkRepository
    # =========================================================================

    async def cleanup_auto_synced_document_project_links(
        self, dispatch_no: str, auto_commit: bool = False
    ) -> int:
        return await self._project_repo.cleanup_auto_synced_document_project_links(
            dispatch_no, auto_commit
        )

    async def cleanup_reverse_document_project_links(
        self,
        dispatch_order_id: int,
        project_id: int,
        dispatch_no: str,
        auto_commit: bool = False,
    ) -> int:
        return await self._project_repo.cleanup_reverse_document_project_links(
            dispatch_order_id, project_id, dispatch_no, auto_commit
        )

    # =========================================================================
    # 批次查詢 — 委派給對應子 Repository
    # =========================================================================

    async def batch_get_dispatch_links_for_documents(
        self, document_ids: List[int]
    ) -> Dict[int, List[TaoyuanDispatchDocumentLink]]:
        return await self._doc_repo.batch_get_dispatch_links_for_documents(
            document_ids
        )

    async def batch_get_project_links_for_documents(
        self, document_ids: List[int]
    ) -> Dict[int, List[TaoyuanDocumentProjectLink]]:
        return await self._project_repo.batch_get_project_links_for_documents(
            document_ids
        )

    async def batch_get_dispatch_links_for_projects(
        self, project_ids: List[int]
    ) -> Dict[int, List[TaoyuanDispatchProjectLink]]:
        return await self._project_repo.batch_get_dispatch_links_for_projects(
            project_ids
        )

    # =========================================================================
    # 統計 — 委派給對應子 Repository
    # =========================================================================

    async def get_doc_id_and_types_for_dispatch(
        self, dispatch_id: int
    ) -> List[Any]:
        return await self._doc_repo.get_doc_id_and_types_for_dispatch(dispatch_id)

    async def get_project_ids_for_dispatch(self, dispatch_id: int) -> List[int]:
        return await self._project_repo.get_project_ids_for_dispatch(dispatch_id)

    async def count_documents_for_dispatch(self, dispatch_id: int) -> int:
        return await self._doc_repo.count_documents_for_dispatch(dispatch_id)

    async def count_projects_for_dispatch(self, dispatch_id: int) -> int:
        return await self._project_repo.count_projects_for_dispatch(dispatch_id)

    async def count_projects_for_document(self, document_id: int) -> int:
        return await self._project_repo.count_projects_for_document(document_id)

    # =========================================================================
    # 派工-實體關聯 (Dispatch-Entity)
    # =========================================================================

    async def find_matching_entity_ids(
        self,
        keywords: List[str],
    ) -> Set[int]:
        """
        根據關鍵詞搜尋匹配的正規化實體 ID

        搜尋策略:
        1. CanonicalEntity.canonical_name 精確匹配
        2. EntityAlias.alias_name 精確匹配
        3. CanonicalEntity.canonical_name ILIKE 模糊匹配 (限 location/project 類型, 關鍵詞 >= 2 字元)

        Args:
            keywords: 核心識別關鍵詞列表

        Returns:
            匹配的 CanonicalEntity ID 集合
        """
        matched: Set[int] = set()

        for keyword in keywords:
            # 精確匹配 canonical_name
            result = await self.db.execute(
                select(CanonicalEntity.id).where(
                    CanonicalEntity.canonical_name == keyword
                )
            )
            for row in result.all():
                matched.add(row[0])

            # 精確匹配 alias_name
            result = await self.db.execute(
                select(EntityAlias.canonical_entity_id).where(
                    EntityAlias.alias_name == keyword
                )
            )
            for row in result.all():
                matched.add(row[0])

            # 模糊匹配 (限 location/project)
            if len(keyword) >= 2:
                result = await self.db.execute(
                    select(CanonicalEntity.id).where(
                        CanonicalEntity.canonical_name.ilike(f"%{keyword}%"),
                        CanonicalEntity.entity_type.in_(['location', 'project']),
                    )
                )
                for row in result.all():
                    matched.add(row[0])

        return matched

    async def replace_auto_entity_links(
        self,
        dispatch_id: int,
        entity_ids: Set[int],
    ) -> int:
        """
        替換派工單的自動實體關聯 (source='auto')

        先刪除現有 auto 來源的關聯，再建立新關聯。

        Args:
            dispatch_id: 派工單 ID
            entity_ids: 要關聯的 CanonicalEntity ID 集合

        Returns:
            新建的關聯數量
        """
        # 刪除現有 auto 來源的關聯
        await self.db.execute(
            delete(TaoyuanDispatchEntityLink).where(
                TaoyuanDispatchEntityLink.dispatch_order_id == dispatch_id,
                TaoyuanDispatchEntityLink.source == 'auto',
            )
        )

        # 建立新關聯
        for entity_id in entity_ids:
            link = TaoyuanDispatchEntityLink(
                dispatch_order_id=dispatch_id,
                canonical_entity_id=entity_id,
                source='auto',
                confidence=1.0,
            )
            self.db.add(link)

        return len(entity_ids)
