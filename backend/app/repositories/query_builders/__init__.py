"""
Query Builder 模組

提供流暢介面 (Fluent Interface) 的查詢建構器。

使用方式:
    from app.repositories.query_builders import DocumentQueryBuilder

    documents = await (
        DocumentQueryBuilder(db)
        .with_status("待處理")
        .with_date_range(start_date, end_date)
        .with_keyword("桃園")
        .execute()
    )

版本: 1.0.0
建立日期: 2026-02-06
"""

from .document_query_builder import DocumentQueryBuilder

__all__ = ['DocumentQueryBuilder']
