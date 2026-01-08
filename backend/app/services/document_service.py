"""
公文服務層 - 業務邏輯處理 (已重構)

職責：
- 公文 CRUD 操作
- 公文查詢與篩選
- 公文匯入（委派給策略類別）

已拆分模組：
- AgencyMatcher: 機關名稱匹配 (app.services.strategies)
- ProjectMatcher: 案件名稱匹配 (app.services.strategies)
- DocumentCalendarIntegrator: 日曆整合
"""
import logging
import time
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, extract, func, select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import selectinload, joinedload

from app.extended.models import OfficialDocument as Document, ContractProject, GovernmentAgency
from app.schemas.document import DocumentFilter, DocumentImportResult, DocumentSearchRequest
from app.services.document_calendar_integrator import DocumentCalendarIntegrator
from app.services.strategies.agency_matcher import AgencyMatcher, ProjectMatcher
from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder
from app.core.cache_manager import cache_dropdown_data, cache_statistics

logger = logging.getLogger(__name__)


class DocumentService:
    """
    公文服務類別

    提供公文相關的業務邏輯，包括：
    - CRUD 操作
    - 查詢與篩選
    - 匯入匯出

    使用策略模式處理：
    - 機關名稱匹配 (AgencyMatcher)
    - 案件名稱匹配 (ProjectMatcher)
    """

    def __init__(self, db: AsyncSession, auto_create_events: bool = True):
        self.db = db
        self.calendar_integrator = DocumentCalendarIntegrator()
        # 初始化策略類別
        self._agency_matcher = AgencyMatcher(db)
        self._project_matcher = ProjectMatcher(db)
        # 行事曆事件自動建立器
        self._auto_create_events = auto_create_events
        self._event_builder = CalendarEventAutoBuilder(db) if auto_create_events else None

    async def _get_or_create_agency_id(self, agency_name: Optional[str]) -> Optional[int]:
        """
        智慧機關名稱匹配 (委派給 AgencyMatcher)

        匹配策略：
        1. 精確匹配 agency_name
        2. 精確匹配 agency_short_name
        3. 模糊匹配
        4. 自動新增

        Args:
            agency_name: 機關名稱

        Returns:
            機關 ID
        """
        return await self._agency_matcher.match_or_create(agency_name)

    async def _get_or_create_project_id(self, project_name: Optional[str]) -> Optional[int]:
        """
        智慧案件名稱匹配 (委派給 ProjectMatcher)

        Args:
            project_name: 案件名稱

        Returns:
            案件 ID
        """
        return await self._project_matcher.match_or_create(project_name)

    def _parse_date_string(self, date_str: str) -> date:
        """
        解析日期字串為 date 物件

        支援格式：YYYY-MM-DD, YYYY/MM/DD

        Args:
            date_str: 日期字串

        Returns:
            date 物件或 None
        """
        if not date_str:
            return None
        try:
            normalized = date_str.replace('/', '-')
            return datetime.strptime(normalized, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"[篩選] 無效的日期格式: {date_str}")
            return None

    def _extract_agency_names(self, agency_value: str) -> list:
        """
        從下拉選項值中提取機關名稱

        支援格式：
        - 純名稱: "桃園市政府"
        - 代碼+名稱: "380110000G (桃園市政府工務局)"
        - 多機關: "376480000A (南投縣政府) | A01020100G (內政部國土管理署城鄉發展分署)"
        - 換行格式: "380110000G\\n(桃園市政府工務局)"

        Args:
            agency_value: 下拉選項值

        Returns:
            提取出的機關名稱列表
        """
        import re

        if not agency_value:
            return []

        names = []

        # 先按 | 分割多個機關
        parts = agency_value.split('|')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 處理換行格式: "380110000G\n(桃園市政府工務局)"
            part = part.replace('\n', ' ').replace('\r', ' ')

            # 嘗試提取括號內的名稱: "380110000G (桃園市政府工務局)" -> "桃園市政府工務局"
            match = re.search(r'\(([^)]+)\)', part)
            if match:
                names.append(match.group(1).strip())
            else:
                # 嘗試移除代碼前綴: "380110000G 桃園市政府工務局" -> "桃園市政府工務局"
                # 代碼格式通常是 字母+數字 組合
                cleaned = re.sub(r'^[A-Z0-9]+\s*', '', part, flags=re.IGNORECASE)
                if cleaned:
                    names.append(cleaned.strip())
                else:
                    # 如果全都被移除了，就用原值（可能本身就是純名稱）
                    names.append(part)

        return names

    def _apply_filters(self, query, filters: DocumentFilter):
        """
        套用篩選條件到查詢

        使用 DocumentFilter 的輔助方法取得有效值，
        支援多種參數命名慣例 (如 date_from 和 doc_date_from)

        Args:
            query: SQLAlchemy 查詢物件
            filters: 篩選條件

        Returns:
            套用篩選後的查詢物件
        """
        # 取得有效的篩選值 (使用 DocumentFilter 的輔助方法)
        effective_keyword = filters.get_effective_keyword() if hasattr(filters, 'get_effective_keyword') else (filters.keyword or getattr(filters, 'search', None))
        effective_date_from = filters.get_effective_date_from() if hasattr(filters, 'get_effective_date_from') else (filters.date_from or getattr(filters, 'doc_date_from', None))
        effective_date_to = filters.get_effective_date_to() if hasattr(filters, 'get_effective_date_to') else (filters.date_to or getattr(filters, 'doc_date_to', None))

        # 調試日誌
        logger.info(f"[篩選] 有效條件: keyword={effective_keyword}, doc_type={filters.doc_type}, "
                   f"year={filters.year}, sender={filters.sender}, receiver={filters.receiver}, "
                   f"delivery_method={filters.delivery_method}, "
                   f"date_from={effective_date_from}, date_to={effective_date_to}, "
                   f"contract_case={filters.contract_case}, category={filters.category}")

        # 公文類型篩選
        if filters.doc_type:
            query = query.where(Document.doc_type == filters.doc_type)

        # 年度篩選
        if filters.year:
            query = query.where(extract('year', Document.doc_date) == filters.year)

        # 關鍵字搜尋（主旨、文號、說明、備註）
        if effective_keyword:
            kw = f"%{effective_keyword}%"
            query = query.where(or_(
                Document.subject.ilike(kw),
                Document.doc_number.ilike(kw),
                Document.content.ilike(kw),
                Document.notes.ilike(kw)
            ))

        # 收發文分類篩選
        if filters.category:
            logger.debug(f"[篩選] 套用 category: {filters.category}")
            query = query.where(Document.category == filters.category)

        # 發文形式篩選 (驗證有效值)
        if filters.delivery_method:
            valid_methods = ['電子交換', '紙本郵寄']
            if filters.delivery_method in valid_methods:
                logger.debug(f"[篩選] 套用 delivery_method: {filters.delivery_method}")
                query = query.where(Document.delivery_method == filters.delivery_method)
            else:
                logger.warning(f"[篩選] 無效的 delivery_method: {filters.delivery_method}")

        # 發文單位篩選 (智能名稱提取 + 模糊匹配)
        if filters.sender:
            sender_names = self._extract_agency_names(filters.sender)
            logger.debug(f"[篩選] 套用 sender: {filters.sender} -> 提取名稱: {sender_names}")
            if sender_names:
                # 使用 OR 邏輯匹配任一名稱
                sender_conditions = [Document.sender.ilike(f"%{name}%") for name in sender_names]
                query = query.where(or_(*sender_conditions))

        # 受文單位篩選 (智能名稱提取 + 模糊匹配)
        if filters.receiver:
            receiver_names = self._extract_agency_names(filters.receiver)
            logger.debug(f"[篩選] 套用 receiver: {filters.receiver} -> 提取名稱: {receiver_names}")
            if receiver_names:
                # 使用 OR 邏輯匹配任一名稱
                receiver_conditions = [Document.receiver.ilike(f"%{name}%") for name in receiver_names]
                query = query.where(or_(*receiver_conditions))

        # 公文日期範圍篩選
        if effective_date_from:
            date_from_val = self._parse_date_string(effective_date_from) if isinstance(effective_date_from, str) else effective_date_from
            if date_from_val:
                logger.debug(f"[篩選] 套用 date_from: {date_from_val}")
                query = query.where(Document.doc_date >= date_from_val)

        if effective_date_to:
            date_to_val = self._parse_date_string(effective_date_to) if isinstance(effective_date_to, str) else effective_date_to
            if date_to_val:
                logger.debug(f"[篩選] 套用 date_to: {date_to_val}")
                query = query.where(Document.doc_date <= date_to_val)

        # 承攬案件篩選 (案件名稱或編號模糊匹配)
        if filters.contract_case:
            logger.debug(f"[篩選] 套用 contract_case: {filters.contract_case}")
            query = query.outerjoin(ContractProject, Document.contract_project_id == ContractProject.id)
            query = query.where(or_(
                ContractProject.project_name.ilike(f"%{filters.contract_case}%"),
                ContractProject.project_code.ilike(f"%{filters.contract_case}%")
            ))

        # 承辦人篩選
        if hasattr(filters, 'assignee') and filters.assignee:
            logger.debug(f"[篩選] 套用 assignee: {filters.assignee}")
            query = query.where(Document.assignee.ilike(f"%{filters.assignee}%"))

        return query

    async def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[DocumentFilter] = None,
        include_relations: bool = True
    ) -> Dict[str, Any]:
        """
        取得公文列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數
            filters: 篩選條件
            include_relations: 是否預載入關聯資料 (N+1 優化)

        Returns:
            分頁結果字典
        """
        try:
            query = select(Document)

            # N+1 查詢優化：預載入關聯資料
            if include_relations:
                query = query.options(
                    selectinload(Document.contract_project),
                    selectinload(Document.sender_agency),
                    selectinload(Document.receiver_agency),
                )

            if filters:
                query = self._apply_filters(query, filters)

            # 計算總數
            count_query = select(func.count()).select_from(query.subquery())
            total = (await self.db.execute(count_query)).scalar_one()

            # 預設按公文日期降冪排序（最新日期在最上方），日期相同時按 id 降冪
            result = await self.db.execute(
                query.order_by(
                    Document.doc_date.desc().nullslast(),
                    Document.id.desc()
                ).offset(skip).limit(limit)
            )
            documents = result.scalars().all()

            return {
                "items": documents,
                "total": total,
                "page": (skip // limit) + 1 if limit > 0 else 1,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit if limit > 0 else 0
            }
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

    async def get_document_by_id(
        self,
        document_id: int,
        include_relations: bool = True
    ) -> Optional[Document]:
        """
        根據 ID 取得公文

        Args:
            document_id: 公文 ID
            include_relations: 是否預載入關聯資料

        Returns:
            公文物件
        """
        query = select(Document).where(Document.id == document_id)

        # N+1 優化：預載入關聯資料
        if include_relations:
            query = query.options(
                selectinload(Document.contract_project),
                selectinload(Document.sender_agency),
                selectinload(Document.receiver_agency),
                selectinload(Document.attachments),
            )

        result = await self.db.execute(query)
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

        此方法為 CSV 匯入流程的核心，負責：
        1. 去重檢查 - 根據公文字號 (doc_number) 跳過已存在的記錄
        2. 機關關聯 - 使用 AgencyMatcher 智慧匹配/建立發文單位和受文單位
        3. 案件關聯 - 使用 ProjectMatcher 智慧匹配/建立承攬案件
        4. 流水號產生 - 根據文件類型自動產生序號 (R0001/S0001)

        機關匹配流程（AgencyMatcher.match_or_create）：
        - 支援解析 "代碼 (名稱)" 或 "代碼 名稱" 格式
        - 匹配順序：精確名稱 > 解析後名稱 > 代碼 > 簡稱 > 模糊匹配 > 自動建立
        - 詳見 app/services/strategies/agency_matcher.py

        Args:
            processed_documents: 已由 DocumentCSVProcessor 處理的文件字典列表

        Returns:
            DocumentImportResult: 匯入結果，包含成功/失敗/跳過數量及錯誤訊息

        維護說明：
        - 若需修改機關匹配邏輯，請修改 AgencyMatcher
        - 若需修改案件匹配邏輯，請修改 ProjectMatcher
        - 若需修復已匯入的錯誤機關資料，使用 POST /api/agencies/fix-parsed-names
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

                # 自動建立行事曆事件
                if self._auto_create_events and self._event_builder:
                    await self._event_builder.auto_create_event(new_document, skip_if_exists=False)

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
