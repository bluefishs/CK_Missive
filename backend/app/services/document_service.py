"""
公文服務層 - 業務邏輯處理 (已修復回應結構)
"""
import logging
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, extract, func, select
from sqlalchemy.exc import IntegrityError

from app.extended.models import OfficialDocument as Document, ContractProject, GovernmentAgency
from app.schemas.document import DocumentFilter, DocumentImportResult, DocumentSearchRequest
from app.services.document_calendar_integrator import DocumentCalendarIntegrator
from app.core.cache_manager import cache_dropdown_data, cache_statistics

logger = logging.getLogger(__name__)

class DocumentService:
    """公文服務類別，已包含所有公文相關的業務邏輯"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.calendar_integrator = DocumentCalendarIntegrator()

    async def _get_or_create_agency_id(self, agency_name: Optional[str]) -> Optional[int]:
        """
        智慧機關名稱匹配：
        1. 先精確匹配 agency_name
        2. 再匹配 agency_short_name（支援簡稱對應）
        3. 最後做模糊匹配（包含關係）
        4. 都沒找到才新增
        """
        if not agency_name or not agency_name.strip(): return None
        agency_name = agency_name.strip()

        # 1. 精確匹配 agency_name
        result = await self.db.execute(select(GovernmentAgency).where(GovernmentAgency.agency_name == agency_name))
        db_agency = result.scalar_one_or_none()
        if db_agency:
            return db_agency.id

        # 2. 匹配 agency_short_name（支援簡稱對應）
        result = await self.db.execute(select(GovernmentAgency).where(GovernmentAgency.agency_short_name == agency_name))
        db_agency = result.scalar_one_or_none()
        if db_agency:
            logger.info(f"機關簡稱匹配成功: '{agency_name}' -> '{db_agency.agency_name}'")
            return db_agency.id

        # 3. 模糊匹配：檢查是否為現有機關的子字串或包含現有機關
        result = await self.db.execute(
            select(GovernmentAgency).where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{agency_name}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{agency_name}%")
                )
            ).limit(1)
        )
        db_agency = result.scalar_one_or_none()
        if db_agency:
            logger.info(f"機關模糊匹配成功: '{agency_name}' -> '{db_agency.agency_name}'")
            return db_agency.id

        # 4. 都沒找到，新增機關
        new_agency = GovernmentAgency(agency_name=agency_name)
        self.db.add(new_agency)
        await self.db.flush()
        await self.db.refresh(new_agency)
        logger.info(f"新增機關: '{agency_name}'")
        return new_agency.id

    async def _get_or_create_project_id(self, project_name: Optional[str]) -> Optional[int]:
        if not project_name or not project_name.strip(): return None
        project_name = project_name.strip()
        result = await self.db.execute(select(ContractProject).where(ContractProject.project_name == project_name))
        db_project = result.scalar_one_or_none()
        if db_project: return db_project.id
        new_project = ContractProject(project_name=project_name, year=datetime.now().year, status="進行中")
        self.db.add(new_project)
        await self.db.flush()
        await self.db.refresh(new_project)
        return new_project.id

    def _apply_filters(self, query, filters: DocumentFilter):
        if filters.doc_type: query = query.where(Document.doc_type == filters.doc_type)
        if filters.year: query = query.where(extract('year', Document.doc_date) == filters.year)
        if filters.keyword:
            query = query.where(or_(
                Document.subject.ilike(f"%{filters.keyword}%"),
                Document.doc_number.ilike(f"%{filters.keyword}%"
            )))
        return query

    async def get_documents(self, skip: int = 0, limit: int = 100, filters: Optional[DocumentFilter] = None) -> Dict[str, Any]:
        try:
            query = select(Document)
            if filters: query = self._apply_filters(query, filters)
            count_query = select(func.count()).select_from(query.subquery())
            total = (await self.db.execute(count_query)).scalar_one()
            result = await self.db.execute(query.order_by(Document.id.desc()).offset(skip).limit(limit))
            documents = result.scalars().all()
            # --- MODIFIED: Changed 'documents' to 'items' to match frontend expectation ---
            return {"items": documents, "total": total, "page": (skip // limit) + 1, "limit": limit, "total_pages": (total + limit - 1) // limit}
        except Exception as e:
            logger.error(f"get_documents 失敗: {e}", exc_info=True)
            return {"items": [], "total": 0, "page": 1, "limit": limit, "total_pages": 0}

    async def create_document(self, doc_data: Dict[str, Any], current_user_id: int) -> Optional[Document]:
        try:
            sender_agency_id = await self._get_or_create_agency_id(doc_data.get('sender'))
            receiver_agency_id = await self._get_or_create_agency_id(doc_data.get('receiver'))
            project_id = await self._get_or_create_project_id(doc_data.get('contract_case'))
            doc_payload = {k: v for k, v in doc_data.items() if hasattr(Document, k)}
            doc_payload.update({
                'sender_agency_id': sender_agency_id,
                'receiver_agency_id': receiver_agency_id,
                'contract_project_id': project_id
            })
            new_document = Document(**doc_payload)
            self.db.add(new_document)
            await self.db.commit()
            await self.db.refresh(new_document)
            if new_document.receive_date:
                await self.calendar_integrator.convert_document_to_events(db=self.db, document=new_document, creator_id=current_user_id)
            return new_document
        except Exception as e:
            await self.db.rollback()
            logger.error(f"建立公文時發生未預期錯誤: {e}", exc_info=True)
            return None

    async def get_document_by_id(self, document_id: int) -> Optional[Document]:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalars().first()

    # ... (其他函式保持不變) ...
