"""
桃園派工關聯管理服務

提供統一的關聯管理功能，減少 API 端點中的重複邏輯

@version 2.0.0
@date 2026-01-21
@updated 2026-03-23 — 遷移至 Repository 層 (B1)
"""

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repository import DocumentRepository
from app.repositories.taoyuan.dispatch_doc_link_repository import (
    DispatchDocLinkRepository,
)
from app.repositories.taoyuan.dispatch_project_link_repository import (
    DispatchProjectLinkRepository,
)

logger = logging.getLogger(__name__)


class TaoyuanLinkService:
    """桃園派工關聯管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._doc_repo = DispatchDocLinkRepository(db)
        self._project_repo = DispatchProjectLinkRepository(db)
        self._document_repo = DocumentRepository(db)

    # =========================================================================
    # 派工-公文關聯
    # =========================================================================

    async def get_dispatch_document_links(
        self, dispatch_id: int
    ) -> List[Dict[str, Any]]:
        """取得派工單的公文關聯列表"""
        links = await self._doc_repo.get_documents_for_dispatch(dispatch_id)
        return [
            {
                'link_id': link.id,
                'link_type': link.link_type,
                'document_id': link.document_id,
                'doc_number': link.document.doc_number if link.document else None,
                'subject': link.document.subject if link.document else None,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ]

    async def link_dispatch_to_document(
        self,
        dispatch_id: int,
        document_id: int,
        link_type: str = 'agency_incoming'
    ) -> Optional[int]:
        """將派工單關聯到公文

        Returns:
            link_id: 關聯記錄 ID，若已存在則返回 None
        """
        link = await self._doc_repo.link_dispatch_to_document(
            dispatch_id, document_id, link_type
        )
        return link.id if link else None

    async def unlink_dispatch_from_document(
        self, dispatch_id: int, link_id: int
    ) -> bool:
        """移除派工單與公文的關聯"""
        return await self._doc_repo.unlink_dispatch_from_document(link_id)

    # =========================================================================
    # 派工-工程關聯
    # =========================================================================

    async def get_dispatch_project_links(
        self, dispatch_id: int
    ) -> List[Dict[str, Any]]:
        """取得派工單的工程關聯列表"""
        links = await self._project_repo.get_projects_for_dispatch(dispatch_id)
        return [
            {
                'link_id': link.id,
                'project_id': link.taoyuan_project_id,
                'project_name': link.project.project_name if link.project else None,
                'district': link.project.district if link.project else None,
                'review_year': link.project.review_year if link.project else None,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ]

    async def link_dispatch_to_project(
        self, dispatch_id: int, project_id: int
    ) -> Optional[int]:
        """將派工單關聯到工程"""
        link = await self._project_repo.link_dispatch_to_project(
            dispatch_id, project_id
        )
        return link.id if link else None

    async def unlink_dispatch_from_project(
        self, dispatch_id: int, link_id: int
    ) -> bool:
        """移除派工單與工程的關聯"""
        return await self._project_repo.unlink_dispatch_from_project(link_id)

    # =========================================================================
    # 公文-派工關聯 (以公文為主體)
    # =========================================================================

    async def get_document_dispatch_links(
        self, document_id: int
    ) -> List[Dict[str, Any]]:
        """取得公文關聯的派工單列表"""
        links = await self._doc_repo.get_dispatches_for_document(document_id)

        dispatch_orders = []
        for link in links:
            if link.dispatch_order:
                order = link.dispatch_order
                # 取得關聯的機關/乾坤函文文號
                agency_doc_number = None
                company_doc_number = None
                if order.agency_doc_id:
                    agency_doc = await self._document_repo.get_by_id(order.agency_doc_id)
                    agency_doc_number = agency_doc.doc_number if agency_doc else None
                if order.company_doc_id:
                    company_doc = await self._document_repo.get_by_id(order.company_doc_id)
                    company_doc_number = company_doc.doc_number if company_doc else None

                dispatch_orders.append({
                    'link_id': link.id,
                    'link_type': link.link_type,
                    'dispatch_order_id': order.id,
                    'dispatch_no': order.dispatch_no,
                    'project_name': order.project_name,
                    'work_type': order.work_type,
                    'sub_case_name': order.sub_case_name,
                    'deadline': order.deadline,
                    'case_handler': order.case_handler,
                    'survey_unit': order.survey_unit,
                    'contact_note': order.contact_note,
                    'cloud_folder': order.cloud_folder,
                    'project_folder': order.project_folder,
                    'agency_doc_number': agency_doc_number,
                    'company_doc_number': company_doc_number,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                })

        return dispatch_orders

    async def link_document_to_dispatch(
        self,
        document_id: int,
        dispatch_id: int,
        link_type: str = 'agency_incoming'
    ) -> Optional[int]:
        """將公文關聯到派工單 (以公文為主體)"""
        return await self.link_dispatch_to_document(dispatch_id, document_id, link_type)

    async def unlink_document_from_dispatch(
        self, document_id: int, link_id: int
    ) -> bool:
        """移除公文與派工單的關聯"""
        return await self._doc_repo.unlink_dispatch_from_document(link_id)

    # =========================================================================
    # 公文-工程直接關聯
    # =========================================================================

    async def get_document_project_links(
        self, document_id: int
    ) -> List[Dict[str, Any]]:
        """取得公文直接關聯的工程列表"""
        links = await self._project_repo.get_projects_for_document(document_id)
        return [
            {
                'link_id': link.id,
                'link_type': link.link_type,
                'notes': link.notes,
                'project_id': link.taoyuan_project_id,
                'project_name': link.project.project_name if link.project else None,
                'district': link.project.district if link.project else None,
                'review_year': link.project.review_year if link.project else None,
                'case_type': link.project.case_type if link.project else None,
                'sub_case_name': link.project.sub_case_name if link.project else None,
                'case_handler': link.project.case_handler if link.project else None,
                'survey_unit': link.project.survey_unit if link.project else None,
                'start_point': link.project.start_point if link.project else None,
                'end_point': link.project.end_point if link.project else None,
                'road_length': float(link.project.road_length) if link.project and link.project.road_length else None,
                'current_width': float(link.project.current_width) if link.project and link.project.current_width else None,
                'planned_width': float(link.project.planned_width) if link.project and link.project.planned_width else None,
                'review_result': link.project.review_result if link.project else None,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ]

    async def link_document_to_project(
        self,
        document_id: int,
        project_id: int,
        link_type: str = 'agency_incoming',
        notes: Optional[str] = None
    ) -> Optional[int]:
        """將公文直接關聯到工程"""
        link = await self._project_repo.link_document_to_project(
            document_id, project_id, link_type, notes
        )
        return link.id if link else None

    async def unlink_document_from_project(
        self, document_id: int, link_id: int
    ) -> bool:
        """移除公文與工程的直接關聯"""
        return await self._project_repo.unlink_document_from_project(link_id)

    # =========================================================================
    # 工程-派工關聯 (以工程為主體)
    # =========================================================================

    async def get_project_dispatch_links(
        self, project_id: int
    ) -> List[Dict[str, Any]]:
        """取得工程關聯的派工單列表"""
        links = await self._project_repo.get_dispatches_for_project(project_id)
        return [
            {
                'link_id': link.id,
                'dispatch_order_id': link.dispatch_order_id,
                'dispatch_no': link.dispatch_order.dispatch_no if link.dispatch_order else None,
                'project_name': link.dispatch_order.project_name if link.dispatch_order else None,
                'work_type': link.dispatch_order.work_type if link.dispatch_order else None,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ]

    async def link_project_to_dispatch(
        self, project_id: int, dispatch_id: int
    ) -> Optional[int]:
        """將工程關聯到派工單"""
        return await self.link_dispatch_to_project(dispatch_id, project_id)

    async def unlink_project_from_dispatch(
        self, project_id: int, link_id: int
    ) -> bool:
        """移除工程與派工單的關聯"""
        return await self._project_repo.unlink_dispatch_from_project(link_id)

    # =========================================================================
    # 批次操作
    # =========================================================================

    async def batch_get_document_dispatch_links(
        self, document_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """批次取得多筆公文的派工關聯"""
        links_map = await self._doc_repo.batch_get_dispatch_links_for_documents(
            document_ids
        )

        grouped: Dict[int, List[Dict[str, Any]]] = {}
        for doc_id, links in links_map.items():
            grouped[doc_id] = []
            for link in links:
                if link.dispatch_order:
                    grouped[doc_id].append({
                        'link_id': link.id,
                        'link_type': link.link_type,
                        'dispatch_order_id': link.dispatch_order.id,
                        'dispatch_no': link.dispatch_order.dispatch_no,
                        'project_name': link.dispatch_order.project_name,
                        'work_type': link.dispatch_order.work_type,
                    })

        return grouped

    async def batch_get_document_project_links(
        self, document_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """批次取得多筆公文的工程關聯"""
        links_map = await self._project_repo.batch_get_project_links_for_documents(
            document_ids
        )

        grouped: Dict[int, List[Dict[str, Any]]] = {}
        for doc_id, links in links_map.items():
            grouped[doc_id] = []
            for link in links:
                if link.project:
                    grouped[doc_id].append({
                        'link_id': link.id,
                        'link_type': link.link_type,
                        'notes': link.notes,
                        'project_id': link.taoyuan_project_id,
                        'project_name': link.project.project_name,
                        'district': link.project.district,
                        'review_year': link.project.review_year,
                    })

        return grouped
