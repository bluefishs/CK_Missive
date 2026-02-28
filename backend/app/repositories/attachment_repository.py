"""
AttachmentRepository - 附件資料存取

繼承 BaseRepository，提供 DocumentAttachment 特定查詢方法。

版本: 1.0.0
建立日期: 2026-02-28
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base_repository import BaseRepository
from app.extended.models import DocumentAttachment


class AttachmentRepository(BaseRepository[DocumentAttachment]):
    """附件 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, DocumentAttachment)

    async def get_by_document_id(self, document_id: int) -> List[DocumentAttachment]:
        result = await self.db.execute(
            select(DocumentAttachment)
            .where(DocumentAttachment.document_id == document_id)
            .order_by(DocumentAttachment.created_at.desc())
        )
        return list(result.scalars().all())
