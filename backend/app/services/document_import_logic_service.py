"""
公文匯入邏輯服務

從 DocumentService 拆分，負責 CSV 匯入流程的核心邏輯。

@version 1.0.0
@date 2026-03-18
"""
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extended.models import OfficialDocument as Document
from app.schemas.document import DocumentImportResult
from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder
from app.scripts.normalize_unicode import normalize_text

logger = logging.getLogger(__name__)


class DocumentImportLogicService:
    """公文匯入邏輯服務

    負責 CSV 匯入流程的核心邏輯，包括：
    1. 去重檢查 - 根據公文字號 (doc_number) 跳過已存在的記錄
    2. 機關關聯 - 使用 AgencyMatcher 智慧匹配/建立發文單位和受文單位
    3. 案件關聯 - 使用 ProjectMatcher 智慧匹配/建立承攬案件
    4. 流水號產生 - 根據文件類型自動產生序號 (R0001/S0001)
    """

    def __init__(self, db: AsyncSession, auto_create_events: bool = True):
        self.db = db
        self._auto_create_events = auto_create_events
        self._event_builder = CalendarEventAutoBuilder(db) if auto_create_events else None

    async def import_documents_from_processed_data(
        self,
        processed_documents: List[Dict[str, Any]],
        get_or_create_agency_id,
        get_or_create_project_id,
        get_next_auto_serial,
    ) -> DocumentImportResult:
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
            get_or_create_agency_id: 機關匹配回調函數
            get_or_create_project_id: 案件匹配回調函數
            get_next_auto_serial: 流水號產生回調函數

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

        # 日期解析函數（迴圈外定義，避免重複建立）
        _date_formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y/%m/%d %H:%M:%S']

        def _parse_import_date(value) -> Optional[date]:
            if value is None:
                return None
            # pandas NaT (Not a Time)
            try:
                import pandas as pd
                if pd.isna(value):
                    return None
            except (ImportError, TypeError, ValueError):
                pass
            # Already a date/datetime object (pandas Timestamp inherits datetime)
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            # String parsing fallback
            str_value = str(value).strip()
            if not str_value:
                return None
            for fmt in _date_formats:
                try:
                    return datetime.strptime(str_value, fmt).date()
                except (ValueError, TypeError):
                    continue
            return None

        # 需要 Unicode 正規化的欄位
        _normalize_keys = [
            'doc_number', 'subject', 'sender', 'receiver',
            'contract_case', 'notes', 'content', 'ck_note', 'assignee',
        ]

        for idx, doc_data in enumerate(processed_documents):
            try:
                # Unicode 正規化：清理康熙部首等異常字元
                for key in _normalize_keys:
                    if key in doc_data and doc_data[key]:
                        doc_data[key] = normalize_text(str(doc_data[key]))

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
                sender_agency_id = await get_or_create_agency_id(doc_data.get('sender'))
                receiver_agency_id = await get_or_create_agency_id(doc_data.get('receiver'))
                project_id = await get_or_create_project_id(doc_data.get('contract_case'))

                # 取得文件類型並產生流水號
                doc_type = doc_data.get('doc_type', '收文')
                auto_serial = await get_next_auto_serial(doc_type)

                # 映射欄位到資料庫模型
                doc_payload = {
                    'auto_serial': auto_serial,
                    'doc_number': doc_number,
                    'doc_type': doc_type,
                    'category': doc_data.get('category') or doc_type,
                    'subject': doc_data.get('subject', ''),
                    'sender': doc_data.get('sender', ''),
                    'receiver': doc_data.get('receiver', ''),
                    'sender_agency_id': sender_agency_id,
                    'receiver_agency_id': receiver_agency_id,
                    'contract_project_id': project_id,
                    'status': doc_data.get('status', '待處理'),
                    'delivery_method': doc_data.get('delivery_method') or doc_data.get('dispatch_type'),
                    'notes': doc_data.get('notes'),
                    'content': doc_data.get('content'),
                    'ck_note': doc_data.get('ck_note'),
                    'assignee': doc_data.get('assignee'),
                }

                # 處理日期欄位（統一多格式解析）
                if doc_data.get('doc_date') is not None:
                    doc_payload['doc_date'] = _parse_import_date(doc_data['doc_date'])

                if doc_data.get('receive_date') is not None:
                    doc_payload['receive_date'] = _parse_import_date(doc_data['receive_date'])

                if doc_data.get('send_date') is not None:
                    doc_payload['send_date'] = _parse_import_date(doc_data['send_date'])

                # 自動補齊：發文類缺 send_date 時用 doc_date；收文類缺 receive_date 時用 doc_date
                parsed_doc_date = doc_payload.get('doc_date')
                if parsed_doc_date:
                    if doc_type == '發文' and not doc_payload.get('send_date'):
                        doc_payload['send_date'] = parsed_doc_date
                    elif doc_type == '收文' and not doc_payload.get('receive_date'):
                        doc_payload['receive_date'] = parsed_doc_date

                # 清除 None 值（避免覆蓋模型預設值）
                doc_payload = {k: v for k, v in doc_payload.items() if v is not None}

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
                logger.warning(f"公文違反約束 (IntegrityError): doc_number='{doc_data.get('doc_number')}': {e}")
                errors.append(f"公文 '{doc_data.get('doc_number')}' 違反唯一性約束，已跳過")
            except Exception as e:
                error_count += 1
                logger.error(f"第 {idx + 1} 筆匯入失敗: {e}", exc_info=True)
                errors.append(f"第 {idx + 1} 筆匯入失敗")

        # 提交所有變更
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"提交匯入變更失敗: {e}", exc_info=True)
            raise

        # 通知 NER 排程器有新公文（事件驅動，立即處理）
        if success_count > 0:
            from app.services.ai.document.extraction_scheduler import notify_new_documents
            notify_new_documents(success_count)

        processing_time = time.time() - start_time
        return DocumentImportResult(
            total_rows=total_rows,
            success_count=success_count,
            error_count=error_count,
            skipped_count=skipped_count,
            errors=errors if errors else [],
            processing_time=processing_time
        )
