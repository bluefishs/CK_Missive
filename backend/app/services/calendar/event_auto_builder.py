# -*- coding: utf-8 -*-
"""
行事曆事件自動建立器

提供公文匯入時自動建立行事曆事件的功能。
根據公文類型、主旨關鍵字自動判定事件類型。
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.extended.models import OfficialDocument, DocumentCalendarEvent

logger = logging.getLogger(__name__)


class CalendarEventAutoBuilder:
    """公文事件自動建立器"""

    # 公文類型對應事件類型
    DOC_TYPE_EVENT_MAP: Dict[str, str] = {
        '開會通知單': 'meeting',
        '會勘通知單': 'meeting',
    }

    # 主旨關鍵字對應事件類型
    KEYWORD_EVENT_MAP: Dict[str, str] = {
        '截止': 'deadline',
        '期限': 'deadline',
        '審查': 'review',
        '審核': 'review',
        '會議': 'meeting',
        '會勘': 'meeting',
        '開會': 'meeting',
    }

    # 類別預設事件類型
    CATEGORY_DEFAULT_MAP: Dict[str, str] = {
        '收文': 'reminder',
        '發文': 'reference',
    }

    # 事件類型對應優先級
    EVENT_TYPE_PRIORITY_MAP: Dict[str, str] = {
        'deadline': 'high',
        'meeting': 'high',
        'review': 'normal',
        'reminder': 'normal',
        'reference': 'low',
    }

    # 事件類型對應標題前綴
    EVENT_TYPE_PREFIX_MAP: Dict[str, str] = {
        'deadline': '[截止]',
        'meeting': '[會議]',
        'review': '[審查]',
        'reminder': '[提醒]',
        'reference': '[參考]',
    }

    def __init__(self, db: AsyncSession):
        """
        初始化事件建立器

        Args:
            db: 資料庫連線
        """
        self.db = db
        self._created_count = 0
        self._skipped_count = 0

    @property
    def created_count(self) -> int:
        """已建立事件數"""
        return self._created_count

    @property
    def skipped_count(self) -> int:
        """跳過事件數"""
        return self._skipped_count

    def reset_counters(self):
        """重置計數器"""
        self._created_count = 0
        self._skipped_count = 0

    async def auto_create_event(
        self,
        document: OfficialDocument,
        skip_if_exists: bool = True,
        created_by: Optional[int] = None
    ) -> Optional[DocumentCalendarEvent]:
        """
        自動為公文建立行事曆事件

        Args:
            document: 公文物件
            skip_if_exists: 已有事件時是否跳過
            created_by: 建立者 ID

        Returns:
            建立的事件或 None
        """
        if not document or not document.id:
            return None

        # 檢查是否已存在
        if skip_if_exists:
            existing = await self._check_existing_event(document.id)
            if existing:
                self._skipped_count += 1
                logger.debug(f"公文 {document.id} 已有事件，跳過")
                return None

        # 決定事件類型
        event_type = self._determine_event_type(document)

        # 決定事件日期
        event_date = self._determine_event_date(document)
        if not event_date:
            self._skipped_count += 1
            logger.debug(f"公文 {document.id} 無有效日期，跳過")
            return None

        # 建立事件
        event = DocumentCalendarEvent(
            document_id=document.id,
            title=self._build_title(document, event_type),
            description=self._build_description(document),
            start_date=event_date,
            end_date=event_date + timedelta(hours=1),
            all_day=True,
            event_type=event_type,
            priority=self.EVENT_TYPE_PRIORITY_MAP.get(event_type, 'normal'),
            created_by=created_by,
        )

        self.db.add(event)
        self._created_count += 1
        logger.info(f"為公文 {document.id} 建立事件: {event.title}")

        return event

    async def batch_create_events(
        self,
        documents: List[OfficialDocument],
        skip_if_exists: bool = True,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        批次建立事件

        Args:
            documents: 公文列表
            skip_if_exists: 已有事件時是否跳過
            created_by: 建立者 ID

        Returns:
            批次結果統計
        """
        self.reset_counters()

        for document in documents:
            await self.auto_create_event(
                document=document,
                skip_if_exists=skip_if_exists,
                created_by=created_by
            )

        return {
            'total': len(documents),
            'created': self._created_count,
            'skipped': self._skipped_count,
        }

    async def create_event_for_new_document(
        self,
        document: OfficialDocument,
        created_by: Optional[int] = None
    ) -> Optional[DocumentCalendarEvent]:
        """
        為新建立的公文建立事件 (不檢查重複)

        Args:
            document: 公文物件
            created_by: 建立者 ID

        Returns:
            建立的事件或 None
        """
        return await self.auto_create_event(
            document=document,
            skip_if_exists=False,
            created_by=created_by
        )

    async def _check_existing_event(self, document_id: int) -> bool:
        """檢查公文是否已有事件"""
        query = select(DocumentCalendarEvent.id).where(
            DocumentCalendarEvent.document_id == document_id
        ).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    def _determine_event_type(self, document: OfficialDocument) -> str:
        """
        決定事件類型

        優先順序:
        1. 公文類型對應
        2. 主旨關鍵字
        3. 類別預設值
        """
        # 1. 公文類型優先
        if document.doc_type and document.doc_type in self.DOC_TYPE_EVENT_MAP:
            return self.DOC_TYPE_EVENT_MAP[document.doc_type]

        # 2. 主旨關鍵字
        if document.subject:
            for keyword, event_type in self.KEYWORD_EVENT_MAP.items():
                if keyword in document.subject:
                    return event_type

        # 3. 類別預設
        if document.category:
            return self.CATEGORY_DEFAULT_MAP.get(document.category, 'reminder')

        return 'reminder'

    def _determine_event_date(self, document: OfficialDocument) -> Optional[datetime]:
        """
        決定事件日期

        優先順序:
        1. 收文日期 (receive_date)
        2. 公文日期 (doc_date)
        3. 發文日期 (send_date)
        4. 建立時間 (created_at)
        """
        if document.receive_date:
            return datetime.combine(document.receive_date, datetime.min.time())
        if document.doc_date:
            return datetime.combine(document.doc_date, datetime.min.time())
        if document.send_date:
            return datetime.combine(document.send_date, datetime.min.time())
        if document.created_at:
            return document.created_at

        return None

    def _build_title(self, document: OfficialDocument, event_type: str) -> str:
        """建立事件標題"""
        prefix = self.EVENT_TYPE_PREFIX_MAP.get(event_type, '')
        subject = document.subject or '無主旨'

        # 限制標題長度
        max_subject_len = 100
        if len(subject) > max_subject_len:
            subject = subject[:max_subject_len] + '...'

        return f"{prefix} {subject}".strip()

    def _build_description(self, document: OfficialDocument) -> str:
        """建立事件描述"""
        parts = []

        if document.doc_number:
            parts.append(f"公文字號: {document.doc_number}")
        if document.category:
            parts.append(f"類別: {document.category}")
        if document.doc_type:
            parts.append(f"公文類型: {document.doc_type}")

        return '\n'.join(parts) if parts else ''


# 便利函數
async def create_event_for_document(
    db: AsyncSession,
    document: OfficialDocument,
    created_by: Optional[int] = None
) -> Optional[DocumentCalendarEvent]:
    """
    為單一公文建立行事曆事件

    Args:
        db: 資料庫連線
        document: 公文物件
        created_by: 建立者 ID

    Returns:
        建立的事件或 None
    """
    builder = CalendarEventAutoBuilder(db)
    return await builder.auto_create_event(document, created_by=created_by)
