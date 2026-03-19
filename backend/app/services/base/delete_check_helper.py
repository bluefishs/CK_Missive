"""
刪除前關聯檢查助手

從 query_helper.py 拆分 (v1.1.0)
提供統一的刪除前關聯檢查功能，防止破壞資料完整性。
"""

from typing import Any, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar('ModelType')


class DeleteCheckHelper:
    """
    刪除檢查助手

    Usage:
        can_delete, count = await DeleteCheckHelper.check_usage(
            db, OfficialDocument, 'sender_agency_id', agency_id
        )
        if not can_delete:
            raise ResourceInUseException(f"機關", f"仍有 {count} 筆公文關聯")
    """

    @staticmethod
    async def check_usage(
        db: AsyncSession,
        related_model: Type[ModelType],
        foreign_key_field: str,
        entity_id: int
    ) -> Tuple[bool, int]:
        """檢查實體是否被其他資料使用"""
        if not hasattr(related_model, foreign_key_field):
            return True, 0

        fk_field = getattr(related_model, foreign_key_field)
        id_field = related_model.id if hasattr(related_model, 'id') else None

        if id_field is None:
            return True, 0

        query = select(func.count(id_field)).where(fk_field == entity_id)
        result = await db.execute(query)
        count = result.scalar_one()

        return count == 0, count

    @staticmethod
    async def check_multiple_usages(
        db: AsyncSession,
        related_model: Type[ModelType],
        checks: List[Tuple[str, int]]
    ) -> Tuple[bool, int]:
        """檢查多個外鍵欄位的使用情況（OR 邏輯）"""
        conditions = []
        for field_name, entity_id in checks:
            if hasattr(related_model, field_name):
                field = getattr(related_model, field_name)
                conditions.append(field == entity_id)

        if not conditions:
            return True, 0

        id_field = related_model.id if hasattr(related_model, 'id') else None
        if id_field is None:
            return True, 0

        query = select(func.count(id_field)).where(or_(*conditions))
        result = await db.execute(query)
        count = result.scalar_one()

        return count == 0, count

    @staticmethod
    async def check_association_usage(
        db: AsyncSession,
        association_table: Any,
        foreign_key_column: str,
        entity_id: int,
        count_column: Optional[str] = None
    ) -> Tuple[bool, int]:
        """檢查多對多關聯表中的使用情況"""
        if not hasattr(association_table, 'c'):
            return True, 0

        fk_col = getattr(association_table.c, foreign_key_column, None)
        if fk_col is None:
            return True, 0

        if count_column:
            count_col = getattr(association_table.c, count_column, None)
        else:
            count_col = fk_col

        if count_col is None:
            return True, 0

        query = select(func.count(count_col)).where(fk_col == entity_id)
        result = await db.execute(query)
        count = result.scalar_one()

        return count == 0, count
