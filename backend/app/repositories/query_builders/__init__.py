"""
Query Builder 模組

提供流暢介面 (Fluent Interface) 的查詢建構器。

使用方式:
    from app.repositories.query_builders import (
        DocumentQueryBuilder,
        ProjectQueryBuilder,
        AgencyQueryBuilder,
    )

    # 公文查詢
    documents = await (
        DocumentQueryBuilder(db)
        .with_status("待處理")
        .with_date_range(start_date, end_date)
        .with_keyword("桃園")
        .execute()
    )

    # 專案查詢
    projects = await (
        ProjectQueryBuilder(db)
        .with_status("進行中")
        .with_year(2026)
        .with_user_access(user_id)
        .execute()
    )

    # 機關查詢
    agencies = await (
        AgencyQueryBuilder(db)
        .with_type("市政府")
        .with_has_documents()
        .execute()
    )

版本: 1.1.0
建立日期: 2026-02-06
更新: 2026-02-06 - 新增 ProjectQueryBuilder, AgencyQueryBuilder
"""

from .document_query_builder import DocumentQueryBuilder
from .project_query_builder import ProjectQueryBuilder
from .agency_query_builder import AgencyQueryBuilder

__all__ = [
    'DocumentQueryBuilder',
    'ProjectQueryBuilder',
    'AgencyQueryBuilder',
]
