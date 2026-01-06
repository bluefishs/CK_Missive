"""
公文服務層 - 業務邏輯處理 (已修復回應結構)
"""
import logging
import time
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
                Document.doc_number.ilike(f"%{filters.keyword}%")
            ))
        # 收發文分類篩選
        if hasattr(filters, 'category') and filters.category:
            query = query.where(Document.category == filters.category)
        # 承攬案件篩選
        if hasattr(filters, 'contract_case') and filters.contract_case:
            query = query.outerjoin(ContractProject, Document.contract_project_id == ContractProject.id)
            query = query.where(or_(
                ContractProject.project_name.ilike(f"%{filters.contract_case}%"),
                ContractProject.project_code.ilike(f"%{filters.contract_case}%")
            ))
        return query

    async def get_documents(self, skip: int = 0, limit: int = 100, filters: Optional[DocumentFilter] = None) -> Dict[str, Any]:
        try:
            query = select(Document)
            if filters: query = self._apply_filters(query, filters)
            count_query = select(func.count()).select_from(query.subquery())
            total = (await self.db.execute(count_query)).scalar_one()
            # 預設按公文日期降冪排序（最新日期在最上方），日期相同時按 id 降冪
            result = await self.db.execute(query.order_by(Document.doc_date.desc().nullslast(), Document.id.desc()).offset(skip).limit(limit))
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

    async def _get_next_auto_serial(self, doc_type: str) -> str:
        """產生下一個流水號 (R0001=收文, S0001=發文)"""
        prefix = 'R' if doc_type == '收文' else 'S'
        # 查詢當前最大流水號
        result = await self.db.execute(
            select(func.max(Document.auto_serial)).where(
                Document.auto_serial.like(f'{prefix}%')
            )
        )
        max_serial = result.scalar_one_or_none()
        if max_serial:
            try:
                num = int(max_serial[1:]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'{prefix}{num:04d}'

    async def import_documents_from_processed_data(self, processed_documents: List[Dict[str, Any]]) -> DocumentImportResult:
        """
        從已處理的文件資料列表匯入資料庫
        - 支援去重（根據公文字號）
        - 自動關聯機關和案件
        - 自動產生流水號 (auto_serial)
        - 回傳詳細的匯入結果
        """
        start_time = time.time()
        total_rows = len(processed_documents)
        success_count = 0
        error_count = 0
        skipped_count = 0
        errors: List[str] = []

        for idx, doc_data in enumerate(processed_documents):
            try:
                doc_number = doc_data.get('doc_number', '').strip()

                # 檢查是否已存在（去重）
                if doc_number:
                    existing = await self.db.execute(
                        select(Document).where(Document.doc_number == doc_number)
                    )
                    if existing.scalar_one_or_none():
                        logger.debug(f"跳過重複公文: {doc_number}")
                        skipped_count += 1
                        continue

                # 準備匯入資料
                sender_agency_id = await self._get_or_create_agency_id(doc_data.get('sender'))
                receiver_agency_id = await self._get_or_create_agency_id(doc_data.get('receiver'))
                project_id = await self._get_or_create_project_id(doc_data.get('contract_case'))

                # 取得文件類型並產生流水號
                doc_type = doc_data.get('doc_type', '收文')
                auto_serial = await self._get_next_auto_serial(doc_type)

                # 映射欄位到資料庫模型 (注意：OfficialDocument 模型沒有 notes 欄位)
                doc_payload = {
                    'auto_serial': auto_serial,
                    'doc_number': doc_number,
                    'doc_type': doc_type,
                    'category': doc_type,  # category 與 doc_type 相同
                    'subject': doc_data.get('subject', ''),
                    'sender': doc_data.get('sender', ''),
                    'receiver': doc_data.get('receiver', ''),
                    'sender_agency_id': sender_agency_id,
                    'receiver_agency_id': receiver_agency_id,
                    'contract_project_id': project_id,
                    'status': doc_data.get('status', '待處理'),
                }

                # 處理日期欄位
                if doc_data.get('doc_date'):
                    try:
                        doc_payload['doc_date'] = datetime.strptime(doc_data['doc_date'], '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        doc_payload['doc_date'] = None

                if doc_data.get('receive_date'):
                    try:
                        # 嘗試多種日期格式
                        receive_str = doc_data['receive_date']
                        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y/%m/%d %H:%M:%S']:
                            try:
                                doc_payload['receive_date'] = datetime.strptime(receive_str, fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            doc_payload['receive_date'] = None
                    except (ValueError, TypeError):
                        doc_payload['receive_date'] = None

                # 建立文件
                new_document = Document(**doc_payload)
                self.db.add(new_document)
                await self.db.flush()
                success_count += 1
                logger.debug(f"成功匯入公文: {doc_number}")

            except IntegrityError as e:
                await self.db.rollback()
                skipped_count += 1
                error_msg = f"公文違反約束 (IntegrityError): doc_number='{doc_data.get('doc_number')}', error={str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
            except Exception as e:
                error_count += 1
                error_msg = f"第 {idx + 1} 筆匯入失敗: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

        # 提交所有變更
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"提交匯入變更失敗: {e}", exc_info=True)
            raise

        processing_time = time.time() - start_time
        return DocumentImportResult(
            total_rows=total_rows,
            success_count=success_count,
            error_count=error_count,
            skipped_count=skipped_count,
            errors=errors if errors else [],
            processing_time=processing_time
        )
