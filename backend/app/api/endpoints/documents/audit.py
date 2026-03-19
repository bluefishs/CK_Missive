"""
公文審計日誌 API 端點

包含：審計日誌查詢、公文變更歷史

@version 4.0.0
@date 2026-02-21
"""
from fastapi import APIRouter, Body, HTTPException, Request
from starlette.responses import Response
from sqlalchemy import text, select, func, and_, literal_column, column as sa_column

from app.core.rate_limiter import limiter
from app.core.dependencies import require_admin

from .common import (
    logger, Depends, AsyncSession, get_async_db, User,
    AuditLogQuery, AuditLogItem, AuditLogResponse, PaginationMeta,
)

router = APIRouter()

# 白名單驗證 — 防禦性設計（audit_logs 無 ORM 模型，使用 raw SQL）
ALLOWED_TABLES = frozenset({
    "official_documents", "documents", "contract_projects",
    "government_agencies", "partner_vendors", "users",
    "document_attachments", "document_calendar_events",
    "site_navigation_items", "site_configurations",
    "taoyuan_projects", "taoyuan_dispatch_orders",
    "taoyuan_dispatch_project_links", "taoyuan_dispatch_work_records",
    "project_vendor_association", "project_user_assignment",
    "project_agency_contacts", "staff_certifications",
})

ALLOWED_ACTIONS = frozenset({
    "CREATE", "UPDATE", "DELETE", "VIEW",
    "create", "update", "delete", "view",
    "LOGIN", "LOGOUT", "login", "logout",
})


# ============================================================================
# 審計日誌查詢 API
# ============================================================================

@router.post(
    "/audit-logs",
    response_model=AuditLogResponse,
    summary="查詢審計日誌"
)
@limiter.limit("30/minute")
async def get_audit_logs(
    request: Request,
    response: Response,
    query: AuditLogQuery = Body(default=AuditLogQuery()),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """
    查詢審計日誌

    支援依公文 ID、操作類型、使用者、日期範圍等條件篩選
    """
    try:
        # 白名單驗證
        if query.table_name and query.table_name not in ALLOWED_TABLES:
            raise HTTPException(status_code=400, detail=f"無效的表格名稱: {query.table_name}")
        if query.action and query.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail=f"無效的操作類型: {query.action}")

        # 構建查詢條件 — 使用 SQLAlchemy Core 表達式，避免 f-string SQL
        audit_logs = text("audit_logs")
        conditions = []

        if query.document_id:
            conditions.append(sa_column('record_id') == query.document_id)
        if query.table_name:
            conditions.append(sa_column('table_name') == query.table_name)
        if query.action:
            conditions.append(sa_column('action') == query.action)
        if query.user_id:
            conditions.append(sa_column('user_id') == query.user_id)
        if query.is_critical is not None:
            conditions.append(sa_column('is_critical') == query.is_critical)
        if query.date_from:
            conditions.append(sa_column('created_at') >= query.date_from)
        if query.date_to:
            conditions.append(sa_column('created_at') <= query.date_to + " 23:59:59")

        where_expr = and_(*conditions) if conditions else True

        # 計算總筆數 — 使用 SQLAlchemy Core（無 f-string 拼接）
        count_stmt = select(func.count()).select_from(text("audit_logs")).where(where_expr)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 查詢資料（分頁）
        offset = (query.page - 1) * query.limit
        data_stmt = (
            select(
                sa_column('id'),
                sa_column('table_name'),
                sa_column('record_id'),
                sa_column('action'),
                sa_column('changes'),
                sa_column('user_id'),
                sa_column('user_name'),
                sa_column('source'),
                sa_column('is_critical'),
                func.to_char(sa_column('created_at'), 'YYYY-MM-DD HH24:MI:SS').label('created_at'),
            )
            .select_from(text("audit_logs"))
            .where(where_expr)
            .order_by(sa_column('created_at').desc())
            .limit(query.limit)
            .offset(offset)
        )

        result = await db.execute(data_stmt)
        rows = result.fetchall()

        items = [
            AuditLogItem(
                id=row.id,
                table_name=row.table_name,
                record_id=row.record_id,
                action=row.action,
                changes=row.changes,
                user_id=row.user_id,
                user_name=row.user_name,
                source=row.source,
                is_critical=row.is_critical or False,
                created_at=row.created_at
            )
            for row in rows
        ]

        total_pages = (total + query.limit - 1) // query.limit

        return AuditLogResponse(
            success=True,
            items=items,
            pagination=PaginationMeta(
                total=total,
                page=query.page,
                limit=query.limit,
                total_pages=total_pages,
                has_next=query.page < total_pages,
                has_prev=query.page > 1
            )
        )
    except Exception as e:
        logger.error(f"查詢審計日誌失敗: {e}", exc_info=True)
        return AuditLogResponse(
            success=False,
            items=[],
            pagination=PaginationMeta(
                total=0, page=1, limit=query.limit,
                total_pages=0, has_next=False, has_prev=False
            )
        )


@router.post(
    "/{document_id}/audit-history",
    response_model=AuditLogResponse,
    summary="查詢公文變更歷史"
)
@limiter.limit("30/minute")
async def get_document_audit_history(
    request: Request,
    response: Response,
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """查詢特定公文的變更歷史記錄"""
    query = AuditLogQuery(document_id=document_id, table_name="documents", limit=50)
    return await get_audit_logs(
        request=request, response=response, query=query,
        db=db, current_user=current_user,
    )
