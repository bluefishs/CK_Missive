"""
統計查詢助手

從 query_helper.py 拆分 (v1.1.0)
提供統一的統計查詢功能：計數、分組、日期範圍、平均值、趨勢。
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar('ModelType')


class StatisticsHelper:
    """
    統計助手

    提供統一的統計查詢功能，減少各服務中的重複統計代碼。

    Usage:
        stats = await StatisticsHelper.get_basic_stats(db, MyModel)
        group_stats = await StatisticsHelper.get_grouped_stats(
            db, MyModel, 'status', MyModel.id
        )
    """

    @staticmethod
    async def get_basic_stats(
        db: AsyncSession,
        model: Type[ModelType],
        count_field: Any = None
    ) -> Dict[str, int]:
        """取得基本統計資料（總數）"""
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        query = select(func.count(count_field))
        result = await db.execute(query)
        total = result.scalar_one()

        return {"total": total}

    @staticmethod
    async def get_grouped_stats(
        db: AsyncSession,
        model: Type[ModelType],
        group_field_name: str,
        count_field: Any = None,
        filter_condition: Any = None
    ) -> Dict[str, int]:
        """取得分組統計資料"""
        if not hasattr(model, group_field_name):
            return {}

        group_field = getattr(model, group_field_name)
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        query = select(
            group_field,
            func.count(count_field).label('count')
        ).group_by(group_field)

        if filter_condition is not None:
            query = query.where(filter_condition)

        result = await db.execute(query)
        rows = result.all()

        return {str(row[0]) if row[0] else 'null': row[1] for row in rows}

    @staticmethod
    async def get_date_range_stats(
        db: AsyncSession,
        model: Type[ModelType],
        date_field_name: str,
        count_field: Any = None,
        filter_condition: Any = None
    ) -> Dict[str, Any]:
        """取得日期範圍統計"""
        if not hasattr(model, date_field_name):
            return {"min_date": None, "max_date": None, "total": 0}

        date_field = getattr(model, date_field_name)
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        query = select(
            func.min(date_field).label('min_date'),
            func.max(date_field).label('max_date'),
            func.count(count_field).label('total')
        )

        if filter_condition is not None:
            query = query.where(filter_condition)

        result = await db.execute(query)
        row = result.one()

        return {
            "min_date": row.min_date,
            "max_date": row.max_date,
            "total": row.total
        }

    @staticmethod
    async def get_average_stats(
        db: AsyncSession,
        model: Type[ModelType],
        numeric_field_name: str,
        filter_condition: Any = None,
        exclude_null: bool = True
    ) -> Dict[str, Any]:
        """取得數值欄位的平均值統計"""
        if not hasattr(model, numeric_field_name):
            return {"average": None, "min": None, "max": None, "count": 0}

        numeric_field = getattr(model, numeric_field_name)

        query = select(
            func.avg(numeric_field).label('average'),
            func.min(numeric_field).label('min'),
            func.max(numeric_field).label('max'),
            func.count(numeric_field).label('count')
        )

        if exclude_null:
            query = query.where(numeric_field.isnot(None))

        if filter_condition is not None:
            query = query.where(filter_condition)

        result = await db.execute(query)
        row = result.one()

        return {
            "average": round(float(row.average), 2) if row.average else None,
            "min": float(row.min) if row.min else None,
            "max": float(row.max) if row.max else None,
            "count": row.count
        }

    @staticmethod
    async def get_trend_stats(
        db: AsyncSession,
        model: Type[ModelType],
        date_field_name: str,
        group_by: str = 'month',
        count_field: Any = None,
        filter_condition: Any = None,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """取得時間趨勢統計"""
        if not hasattr(model, date_field_name):
            return []

        date_field = getattr(model, date_field_name)
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        if group_by == 'day':
            period_expr = func.to_char(date_field, 'YYYY-MM-DD')
        elif group_by == 'week':
            period_expr = func.to_char(date_field, 'IYYY-IW')
        elif group_by == 'year':
            period_expr = func.to_char(date_field, 'YYYY')
        else:
            period_expr = func.to_char(date_field, 'YYYY-MM')

        query = select(
            period_expr.label('period'),
            func.count(count_field).label('count')
        ).where(
            date_field.isnot(None)
        ).group_by(
            period_expr
        ).order_by(
            desc(period_expr)
        ).limit(limit)

        if filter_condition is not None:
            query = query.where(filter_condition)

        result = await db.execute(query)
        rows = result.all()

        return [{"period": row.period, "count": row.count} for row in reversed(rows)]
