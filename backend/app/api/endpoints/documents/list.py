"""
公文列表與搜尋 API 端點

包含：列表查詢、優化搜尋、搜尋建議、專案關聯公文查詢

@version 3.1.0
@date 2026-02-04
"""
import asyncio
from fastapi import APIRouter, Query, Body, Request
from starlette.responses import Response
from sqlalchemy import select, func
from app.core.rate_limiter import limiter

from .common import (
    logger, Depends, AsyncSession, get_async_db,
    OfficialDocument, ContractProject, GovernmentAgency, DocumentAttachment,
    User, project_user_assignment,
    DocumentService, DocumentFilter, DocumentListQuery, DocumentListResponse,
    DocumentResponse, StaffInfo, PaginationMeta,
    ProjectDocumentsQuery, OptimizedSearchRequest, SearchSuggestionRequest,
    require_auth, get_document_service,
)

router = APIRouter()


# ============================================================================
# 公文列表 API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/list",
    response_model=DocumentListResponse,
    summary="查詢公文列表",
    description="使用統一分頁格式查詢公文列表（POST-only 資安機制，含行級別權限過濾）"
)
@limiter.limit("30/minute")
async def list_documents(
    request: Request,
    response: Response,
    query: DocumentListQuery = Body(default=DocumentListQuery()),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(require_auth())
):
    """
    查詢公文列表（POST-only 資安機制）

    🔒 權限規則：
    - 需要登入認證
    - superuser/admin: 可查看所有公文
    - 一般使用者: 只能查看關聯專案的公文，或無專案關聯的公文

    回應格式：
    ```json
    {
        "success": true,
        "items": [...],
        "pagination": {
            "total": 100,
            "page": 1,
            "limit": 20,
            "total_pages": 5,
            "has_next": true,
            "has_prev": false
        }
    }
    ```
    """
    try:
        # 詳細記錄所有查詢參數
        logger.info(f"[API] 公文查詢請求: keyword={query.keyword}, doc_number={query.doc_number}, "
                   f"doc_type={query.doc_type}, year={query.year}, "
                   f"sender={query.sender}, receiver={query.receiver}, "
                   f"delivery_method={query.delivery_method}, "
                   f"doc_date_from={query.doc_date_from}, doc_date_to={query.doc_date_to}, "
                   f"contract_case={query.contract_case}, category={query.category}")

        # 構建篩選條件
        filters = DocumentFilter(
            keyword=query.keyword,
            doc_number=query.doc_number,  # 公文字號專用篩選
            doc_type=query.doc_type,
            year=query.year,
            status=query.status,
            sender=query.sender,
            receiver=query.receiver,
            date_from=query.doc_date_from,
            date_to=query.doc_date_to,
            delivery_method=query.delivery_method,
            contract_case=query.contract_case,  # 直接設定，不用 setattr
            sort_by=query.sort_by,
            sort_order=query.sort_order.value if query.sort_order else "desc"
        )

        # 加入收發文分類篩選 (前端用 send/receive，資料庫用 發文/收文)
        if query.category:
            category_mapping = {'send': '發文', 'receive': '收文'}
            db_category = category_mapping.get(query.category, query.category)
            setattr(filters, 'category', db_category)

        # 計算 skip
        skip = (query.page - 1) * query.limit

        # 傳遞 current_user 進行行級別權限過濾
        result = await service.get_documents(
            skip=skip,
            limit=query.limit,
            filters=filters,
            current_user=current_user
        )

        # 轉換為統一回應格式
        items = result.get("items", [])
        total = result.get("total", 0)

        # 取得 db session (從 service)
        db = service.db

        # 收集所有 ID 以批次查詢
        project_ids = list(set(doc.contract_project_id for doc in items if doc.contract_project_id))
        doc_ids = [doc.id for doc in items]
        agency_ids = set()
        for doc in items:
            if doc.sender_agency_id:
                agency_ids.add(doc.sender_agency_id)
            if doc.receiver_agency_id:
                agency_ids.add(doc.receiver_agency_id)

        # 準備查詢
        project_map = {}
        staff_map = {}
        attachment_count_map = {}
        agency_map = {}

        # 批次查詢關聯資料（循序執行，AsyncSession 不支援 gather 並行）
        async def fetch_projects():
            if not project_ids:
                return []
            query = select(ContractProject.id, ContractProject.project_name).where(
                ContractProject.id.in_(project_ids)
            )
            return (await db.execute(query)).all()

        async def fetch_staff():
            if not project_ids:
                return []
            query = select(
                project_user_assignment.c.project_id,
                project_user_assignment.c.role,
                User.id.label('user_id'),
                User.full_name
            ).select_from(
                project_user_assignment.join(User, project_user_assignment.c.user_id == User.id)
            ).where(project_user_assignment.c.project_id.in_(project_ids))
            return (await db.execute(query)).all()

        async def fetch_attachments():
            if not doc_ids:
                return []
            query = select(
                DocumentAttachment.document_id,
                func.count(DocumentAttachment.id).label('count')
            ).where(
                DocumentAttachment.document_id.in_(doc_ids)
            ).group_by(DocumentAttachment.document_id)
            return (await db.execute(query)).all()

        async def fetch_agencies():
            if not agency_ids:
                return []
            query = select(
                GovernmentAgency.id,
                GovernmentAgency.agency_name
            ).where(GovernmentAgency.id.in_(agency_ids))
            return (await db.execute(query)).all()

        # 循序執行關聯查詢（AsyncSession 不支援同 session gather 並行）
        try:
            project_rows = await fetch_projects()
            staff_rows = await fetch_staff()
            attachment_rows = await fetch_attachments()
            agency_rows = await fetch_agencies()
        except Exception as e:
            logger.warning(f"關聯查詢失敗，回退至基本資料: {e}")
            project_rows, staff_rows, attachment_rows, agency_rows = [], [], [], []

        # 處理查詢結果
        for row in project_rows:
            project_map[row.id] = row.project_name

        for row in staff_rows:
            if row.project_id not in staff_map:
                staff_map[row.project_id] = []
            staff_map[row.project_id].append(StaffInfo(
                user_id=row.user_id,
                name=row.full_name or '未知',
                role=row.role or 'member'
            ))

        for row in attachment_rows:
            attachment_count_map[row.document_id] = row.count

        for row in agency_rows:
            agency_map[row.id] = row.agency_name

        # 轉換為 DocumentResponse
        response_items = []
        for doc in items:
            try:
                doc_dict = {
                    **doc.__dict__,
                    'contract_project_name': project_map.get(doc.contract_project_id) if doc.contract_project_id else None,
                    'assigned_staff': staff_map.get(doc.contract_project_id, []) if doc.contract_project_id else [],
                    'attachment_count': attachment_count_map.get(doc.id, 0),
                    # 機關名稱虛擬欄位
                    'sender_agency_name': agency_map.get(doc.sender_agency_id) if doc.sender_agency_id else None,
                    'receiver_agency_name': agency_map.get(doc.receiver_agency_id) if doc.receiver_agency_id else None,
                }
                # 移除 SQLAlchemy 內部屬性
                doc_dict.pop('_sa_instance_state', None)
                response_items.append(DocumentResponse.model_validate(doc_dict))
            except Exception as e:
                logger.warning(f"轉換公文資料失敗: {e}")
                continue

        return DocumentListResponse(
            items=response_items,
            pagination=PaginationMeta.create(
                total=total,
                page=query.page,
                limit=query.limit
            )
        )

    except Exception as e:
        logger.error(f"公文查詢失敗: {e}", exc_info=True)
        return DocumentListResponse(
            items=[],
            pagination=PaginationMeta.create(total=0, page=1, limit=query.limit)
        )


# ============================================================================
# 優化搜尋 API
# ============================================================================

@router.post(
    "/search/optimized",
    summary="優化全文搜尋",
    description="使用智能關鍵字處理和結果排名的優化搜尋"
)
async def optimized_search(
    request: OptimizedSearchRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    優化全文搜尋

    特點：
    - 智能關鍵字分詞處理
    - 支援公文字號格式識別
    - 多欄位權重搜尋
    - 搜尋結果快取
    """
    from app.services.search_optimizer import SearchOptimizer

    try:
        optimizer = SearchOptimizer(db)

        # 構建篩選條件
        filters = {}
        if request.category:
            category_mapping = {'send': '發文', 'receive': '收文'}
            filters['category'] = category_mapping.get(request.category, request.category)
        if request.delivery_method:
            filters['delivery_method'] = request.delivery_method
        if request.year:
            filters['year'] = request.year

        # 執行優化搜尋
        skip = (request.page - 1) * request.limit
        result = await optimizer.search_with_ranking(
            keyword=request.keyword,
            filters=filters,
            skip=skip,
            limit=request.limit
        )

        # 轉換結果格式
        items = []
        for doc in result.get("items", []):
            items.append({
                "id": doc.id,
                "doc_number": doc.doc_number,
                "doc_type": doc.doc_type,
                "subject": doc.subject,
                "sender": doc.sender,
                "receiver": doc.receiver,
                "doc_date": str(doc.doc_date) if doc.doc_date else None,
                "category": doc.category,
                "delivery_method": doc.delivery_method,
                "status": doc.status,
            })

        total = result.get("total", 0)

        return {
            "success": True,
            "items": items,
            "pagination": {
                "total": total,
                "page": request.page,
                "limit": request.limit,
                "total_pages": (total + request.limit - 1) // request.limit if request.limit > 0 else 0,
                "has_next": request.page * request.limit < total,
                "has_prev": request.page > 1
            },
            "search_info": {
                "tokens": result.get("tokens", []),
                "normalized_keyword": result.get("normalized_keyword", request.keyword)
            }
        }

    except Exception as e:
        logger.error(f"優化搜尋失敗: {e}", exc_info=True)
        return {
            "success": False,
            "items": [],
            "pagination": {"total": 0, "page": 1, "limit": request.limit},
            "error": str(e)
        }


@router.post(
    "/search/suggestions",
    summary="取得搜尋建議",
    description="根據輸入前綴提供自動完成建議"
)
async def get_search_suggestions(
    request: SearchSuggestionRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得搜尋建議（自動完成）

    根據用戶輸入提供：
    - 主旨匹配建議
    - 文號匹配建議
    """
    from app.services.search_optimizer import SearchOptimizer

    try:
        optimizer = SearchOptimizer(db)
        suggestions = await optimizer.get_search_suggestions(
            prefix=request.prefix,
            limit=request.limit
        )

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions)
        }

    except Exception as e:
        logger.error(f"取得搜尋建議失敗: {e}", exc_info=True)
        return {
            "success": False,
            "suggestions": [],
            "error": str(e)
        }


@router.post(
    "/search/popular",
    summary="取得熱門搜尋詞",
    description="取得最近的熱門搜尋關鍵詞"
)
async def get_popular_searches(
    limit: int = Query(default=10, ge=1, le=20, description="數量上限"),
    db: AsyncSession = Depends(get_async_db)
):
    """取得熱門搜尋詞"""
    from app.services.search_optimizer import SearchOptimizer

    try:
        optimizer = SearchOptimizer(db)
        popular = await optimizer.get_popular_searches(limit=limit)

        return {
            "success": True,
            "popular_searches": popular,
            "count": len(popular)
        }

    except Exception as e:
        logger.error(f"取得熱門搜尋失敗: {e}", exc_info=True)
        return {
            "success": False,
            "popular_searches": [],
            "error": str(e)
        }


# ============================================================================
# 專案關聯公文 API（自動關聯機制）
# ============================================================================

@router.post(
    "/by-project",
    response_model=DocumentListResponse,
    summary="查詢專案關聯公文",
    description="根據 project_id 自動查詢該專案的所有關聯公文"
)
async def get_documents_by_project(
    query: ProjectDocumentsQuery = Body(...),
    db: AsyncSession = Depends(get_async_db)
):
    """
    根據專案 ID 查詢關聯公文（自動關聯機制）

    關聯邏輯：
    依據 documents.contract_project_id = project_id 查詢

    回傳該專案的所有公文紀錄
    """
    try:
        # 構建查詢條件：依 contract_project_id 匹配
        doc_query = select(OfficialDocument).where(
            OfficialDocument.contract_project_id == query.project_id
        ).order_by(
            OfficialDocument.doc_date.desc(),
            OfficialDocument.id.desc()
        )

        # 計算總數
        count_query = select(func.count()).select_from(doc_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分頁
        skip = (query.page - 1) * query.limit
        doc_query = doc_query.offset(skip).limit(query.limit)

        result = await db.execute(doc_query)
        documents = result.scalars().all()

        # 並行查詢專案名稱和承辦同仁 (v3.1.0 優化)
        project_name = None
        assigned_staff = []

        if query.project_id:
            async def fetch_project_name():
                pq = select(ContractProject.project_name).where(
                    ContractProject.id == query.project_id
                )
                result = await db.execute(pq)
                return result.scalar()

            async def fetch_project_staff():
                sq = (
                    select(
                        project_user_assignment.c.user_id,
                        project_user_assignment.c.role,
                        User.full_name,
                        User.username
                    )
                    .join(User, User.id == project_user_assignment.c.user_id)
                    .where(
                        project_user_assignment.c.project_id == query.project_id,
                        project_user_assignment.c.status == 'active'
                    )
                )
                result = await db.execute(sq)
                return result.all()

            # 循序執行（AsyncSession 不支援同 session gather 並行）
            project_name = await fetch_project_name()
            staff_rows = await fetch_project_staff()

            assigned_staff = [
                StaffInfo(
                    user_id=row.user_id,
                    name=row.full_name or row.username or f"User {row.user_id}",
                    role=row.role or "member"
                )
                for row in staff_rows
            ]

        # 轉換為回應格式（包含專案關聯資訊）
        response_items = []
        for doc in documents:
            try:
                doc_dict = {
                    **{k: v for k, v in doc.__dict__.items() if not k.startswith('_')},
                    'contract_project_name': project_name,
                    'assigned_staff': assigned_staff
                }
                response_items.append(DocumentResponse.model_validate(doc_dict))
            except Exception as e:
                logger.warning(f"轉換公文資料失敗: {e}")
                continue

        return DocumentListResponse(
            items=response_items,
            pagination=PaginationMeta.create(
                total=total,
                page=query.page,
                limit=query.limit
            )
        )

    except Exception as e:
        logger.error(f"查詢專案關聯公文失敗: {e}", exc_info=True)
        return DocumentListResponse(
            items=[],
            pagination=PaginationMeta.create(total=0, page=1, limit=query.limit)
        )


# ============================================================================
# 向後相容：保留已棄用端點
# ============================================================================

@router.post(
    "/integrated-search",
    summary="整合式公文搜尋（已棄用，預計 2026-07 移除）",
    deprecated=True
)
async def integrated_document_search_legacy(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(50, ge=1, le=1000, description="取得筆數"),
    keyword: str | None = Query(None, description="關鍵字搜尋"),
    doc_type: str | None = Query(None, description="公文類型"),
    year: int | None = Query(None, description="年度"),
    status: str | None = Query(None, description="狀態"),
    contract_case: str | None = Query(None, description="承攬案件"),
    sender: str | None = Query(None, description="發文單位"),
    receiver: str | None = Query(None, description="受文單位"),
    doc_date_from: str | None = Query(None, description="公文日期起"),
    doc_date_to: str | None = Query(None, description="公文日期迄"),
    sort_by: str | None = Query("updated_at", description="排序欄位"),
    sort_order: str | None = Query("desc", description="排序順序"),
    service: DocumentService = Depends(get_document_service)
):
    """
    整合式公文搜尋（已棄用）

    ⚠️ **預計廢止日期**: 2026-07
    請改用 POST /documents-enhanced/list 端點
    """
    try:
        filters = DocumentFilter(
            keyword=keyword,
            doc_type=doc_type,
            year=year,
            status=status,
            sender=sender,
            receiver=receiver,
            date_from=doc_date_from,
            date_to=doc_date_to,
            sort_by=sort_by,
            sort_order=sort_order
        )

        if contract_case:
            setattr(filters, 'contract_case', contract_case)

        result = await service.get_documents(
            skip=skip,
            limit=limit,
            filters=filters
        )

        return result

    except Exception as e:
        logger.error(f"整合搜尋失敗: {e}", exc_info=True)
        return {"items": [], "total": 0, "page": 1, "limit": limit, "total_pages": 0}
