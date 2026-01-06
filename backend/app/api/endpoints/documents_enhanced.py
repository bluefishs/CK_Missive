"""
增強版公文管理 API 端點 - POST-only 資安機制，統一回應格式
"""
import io
import csv
import logging
from typing import Optional, List
from datetime import date as date_type
from fastapi import APIRouter, Query, Depends, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, or_, and_, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def parse_date_string(date_str: Optional[str]) -> Optional[date_type]:
    """將日期字串轉換為 Python date 物件"""
    if not date_str:
        return None
    try:
        # 支援 YYYY-MM-DD 格式
        parts = date_str.split('-')
        if len(parts) == 3:
            return date_type(int(parts[0]), int(parts[1]), int(parts[2]))
        return None
    except (ValueError, IndexError):
        logger.warning(f"無法解析日期字串: {date_str}")
        return None

from app.db.database import get_async_db
from app.extended.models import OfficialDocument, ContractProject, GovernmentAgency
from app.services.document_service import DocumentService
from app.schemas.document import (
    DocumentFilter, DocumentListQuery, DocumentListResponse, DocumentResponse, StaffInfo
)
from app.extended.models import User, project_user_assignment
from app.schemas.common import (
    PaginationMeta,
    DeleteResponse,
    SuccessResponse,
    SortOrder,
)
from app.core.exceptions import NotFoundException
from app.core.audit_logger import DocumentUpdateGuard, log_document_change

router = APIRouter()


# ============================================================================
# 查詢參數 Schema（下拉選項用）
# ============================================================================

class DropdownQuery(BaseModel):
    """下拉選項查詢參數"""
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    limit: int = Field(default=100, ge=1, le=1000, description="限制筆數")


class AgencyDropdownQuery(DropdownQuery):
    """機關下拉選項查詢參數"""
    agency_type: Optional[str] = Field(None, description="機關類型")


# ============================================================================
# 公文列表 API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/list",
    response_model=DocumentListResponse,
    summary="查詢公文列表",
    description="使用統一分頁格式查詢公文列表（POST-only 資安機制）"
)
async def list_documents(
    query: DocumentListQuery = Body(default=DocumentListQuery()),
    db: AsyncSession = Depends(get_async_db)
):
    """
    查詢公文列表（POST-only 資安機制）

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
        logger.info(f"公文查詢請求: keyword={query.keyword}, contract_case={query.contract_case}")

        service = DocumentService(db)

        # 構建篩選條件
        filters = DocumentFilter(
            keyword=query.keyword,
            doc_type=query.doc_type,
            year=query.year,
            status=query.status,
            sender=query.sender,
            receiver=query.receiver,
            date_from=query.doc_date_from,
            date_to=query.doc_date_to,
            sort_by=query.sort_by,
            sort_order=query.sort_order.value if query.sort_order else "desc"
        )

        # 手動加入承攬案件篩選
        if query.contract_case:
            setattr(filters, 'contract_case', query.contract_case)

        # 加入收發文分類篩選 (前端用 send/receive，資料庫用 發文/收文)
        if query.category:
            category_mapping = {'send': '發文', 'receive': '收文'}
            db_category = category_mapping.get(query.category, query.category)
            setattr(filters, 'category', db_category)

        # 計算 skip
        skip = (query.page - 1) * query.limit

        result = await service.get_documents(
            skip=skip,
            limit=query.limit,
            filters=filters
        )

        # 轉換為統一回應格式
        items = result.get("items", [])
        total = result.get("total", 0)

        # 收集所有 project_id 以批次查詢
        project_ids = list(set(doc.contract_project_id for doc in items if doc.contract_project_id))

        # 批次查詢承攬案件資訊
        project_map = {}
        staff_map = {}
        if project_ids:
            # 查詢案件名稱
            project_query = select(ContractProject.id, ContractProject.project_name).where(
                ContractProject.id.in_(project_ids)
            )
            project_result = await db.execute(project_query)
            for row in project_result:
                project_map[row.id] = row.project_name

            # 查詢業務同仁
            staff_query = select(
                project_user_assignment.c.project_id,
                project_user_assignment.c.role,
                User.id.label('user_id'),
                User.full_name
            ).select_from(
                project_user_assignment.join(User, project_user_assignment.c.user_id == User.id)
            ).where(project_user_assignment.c.project_id.in_(project_ids))

            staff_result = await db.execute(staff_query)
            for row in staff_result:
                if row.project_id not in staff_map:
                    staff_map[row.project_id] = []
                staff_map[row.project_id].append(StaffInfo(
                    user_id=row.user_id,
                    name=row.full_name or '未知',
                    role=row.role or 'member'
                ))

        # 轉換為 DocumentResponse
        response_items = []
        for doc in items:
            try:
                doc_dict = {
                    **doc.__dict__,
                    'contract_project_name': project_map.get(doc.contract_project_id) if doc.contract_project_id else None,
                    'assigned_staff': staff_map.get(doc.contract_project_id, []) if doc.contract_project_id else []
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
# 下拉選項 API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/contract-projects-dropdown",
    summary="取得承攬案件下拉選項"
)
async def get_contract_projects_dropdown(
    query: DropdownQuery = Body(default=DropdownQuery()),
    db: AsyncSession = Depends(get_async_db)
):
    """取得承攬案件下拉選項 - 從 contract_projects 表查詢"""
    try:
        db_query = select(
            ContractProject.id,
            ContractProject.project_name,
            ContractProject.year,
            ContractProject.category
        )

        if query.search:
            db_query = db_query.where(
                or_(
                    ContractProject.project_name.ilike(f"%{query.search}%"),
                    ContractProject.project_code.ilike(f"%{query.search}%"),
                    ContractProject.client_agency.ilike(f"%{query.search}%")
                )
            )

        db_query = db_query.order_by(
            ContractProject.year.desc(),
            ContractProject.project_name.asc()
        ).limit(query.limit)

        result = await db.execute(db_query)
        projects = result.all()

        options = []
        for project in projects:
            options.append({
                "value": project.project_name,
                "label": f"{project.project_name} ({project.year}年)",
                "id": project.id,
                "year": project.year,
                "category": project.category
            })

        return {
            "success": True,
            "options": options,
            "total": len(options)
        }

    except Exception as e:
        logger.error(f"取得承攬案件選項失敗: {e}", exc_info=True)
        return {"success": False, "options": [], "total": 0, "error": str(e)}


@router.post(
    "/agencies-dropdown",
    summary="取得政府機關下拉選項"
)
async def get_agencies_dropdown(
    query: AgencyDropdownQuery = Body(default=AgencyDropdownQuery()),
    db: AsyncSession = Depends(get_async_db)
):
    """取得政府機關下拉選項"""
    try:
        # 直接查詢機關名稱
        sql_query = """
        SELECT DISTINCT agency as name
        FROM (
            SELECT sender as agency FROM documents WHERE sender IS NOT NULL AND sender != ''
            UNION
            SELECT receiver as agency FROM documents WHERE receiver IS NOT NULL AND receiver != ''
        ) combined_agencies
        WHERE agency IS NOT NULL AND agency != ''
        """

        params = {}
        if query.search:
            sql_query += " AND agency ILIKE :search"
            params["search"] = f"%{query.search}%"

        sql_query += " ORDER BY agency LIMIT :limit"
        params["limit"] = query.limit

        result = await db.execute(text(sql_query), params)
        raw_agencies = result.fetchall()

        # 簡化處理：直接返回機關名稱
        unique_agencies = set()
        for row in raw_agencies:
            agency_name = row.name.strip() if row.name else ""
            if agency_name:
                unique_agencies.add(agency_name)

        options = []
        for idx, agency_name in enumerate(sorted(unique_agencies)):
            options.append({
                "value": agency_name,
                "label": agency_name,
                "id": idx + 1,
                "agency_code": "",
                "agency_type": "未分類"
            })

        return {
            "success": True,
            "options": options,
            "total": len(options)
        }

    except Exception as e:
        logger.error(f"取得政府機關選項失敗: {e}", exc_info=True)
        return {"success": False, "options": [], "total": 0, "error": str(e)}


@router.post(
    "/years",
    summary="取得文檔年度選項"
)
async def get_document_years(
    db: AsyncSession = Depends(get_async_db)
):
    """取得文檔年度選項"""
    try:
        sql_query = """
        SELECT DISTINCT EXTRACT(YEAR FROM doc_date) as year
        FROM documents
        WHERE doc_date IS NOT NULL
        ORDER BY year DESC
        """

        result = await db.execute(text(sql_query))
        years = result.fetchall()

        year_list = [int(row.year) for row in years if row.year]

        return {
            "success": True,
            "years": year_list,
            "total": len(year_list)
        }

    except Exception as e:
        logger.error(f"取得年度選項失敗: {e}", exc_info=True)
        return {"success": False, "years": [], "total": 0}


@router.post(
    "/statistics",
    summary="取得公文統計資料"
)
async def get_documents_statistics(
    db: AsyncSession = Depends(get_async_db)
):
    """取得公文統計資料 (收發文分類基於 category 欄位)"""
    try:
        total_query = "SELECT COUNT(*) as count FROM documents"
        send_query = "SELECT COUNT(*) as count FROM documents WHERE category = '發文'"
        receive_query = "SELECT COUNT(*) as count FROM documents WHERE category = '收文'"
        current_year_query = "SELECT COUNT(*) as count FROM documents WHERE EXTRACT(YEAR FROM doc_date) = EXTRACT(YEAR FROM CURRENT_DATE)"

        total_result = await db.execute(text(total_query))
        send_result = await db.execute(text(send_query))
        receive_result = await db.execute(text(receive_query))
        current_year_result = await db.execute(text(current_year_query))

        total = total_result.scalar() or 0
        send = send_result.scalar() or 0
        receive = receive_result.scalar() or 0

        return {
            "success": True,
            "total": total,
            "total_documents": total,
            "send": send,
            "send_count": send,
            "receive": receive,
            "receive_count": receive,
            "current_year_count": current_year_result.scalar() or 0
        }
    except Exception as e:
        logger.error(f"取得統計資料失敗: {e}", exc_info=True)
        return {
            "success": False,
            "total": 0,
            "total_documents": 0,
            "send": 0,
            "send_count": 0,
            "receive": 0,
            "receive_count": 0,
            "current_year_count": 0
        }


# ============================================================================
# 公文 CRUD API（POST-only 資安機制）
# ============================================================================

class DocumentCreateRequest(BaseModel):
    """公文建立請求"""
    doc_number: str = Field(..., description="公文編號")
    doc_type: str = Field(..., description="公文類型")
    subject: str = Field(..., description="主旨")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date: Optional[str] = Field(None, description="公文日期")
    receive_date: Optional[str] = Field(None, description="收文日期")
    send_date: Optional[str] = Field(None, description="發文日期")
    status: Optional[str] = Field(None, description="狀態")
    category: Optional[str] = Field(None, description="收發文類別")
    contract_case: Optional[str] = Field(None, description="承攬案件名稱")
    contract_project_id: Optional[int] = Field(None, description="承攬案件 ID")
    doc_word: Optional[str] = Field(None, description="發文字")
    doc_class: Optional[str] = Field(None, description="文別")
    assignee: Optional[str] = Field(None, description="承辦人")
    notes: Optional[str] = Field(None, description="備註")
    priority_level: Optional[str] = Field(None, description="優先級")
    content: Optional[str] = Field(None, description="內容")


class DocumentUpdateRequest(BaseModel):
    """公文更新請求"""
    doc_number: Optional[str] = Field(None, description="公文編號")
    doc_type: Optional[str] = Field(None, description="公文類型")
    subject: Optional[str] = Field(None, description="主旨")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date: Optional[str] = Field(None, description="公文日期")
    receive_date: Optional[str] = Field(None, description="收文日期")
    send_date: Optional[str] = Field(None, description="發文日期")
    status: Optional[str] = Field(None, description="狀態")
    category: Optional[str] = Field(None, description="收發文類別")
    contract_case: Optional[str] = Field(None, description="承攬案件名稱")
    contract_project_id: Optional[int] = Field(None, description="承攬案件 ID")
    doc_word: Optional[str] = Field(None, description="發文字")
    doc_class: Optional[str] = Field(None, description="文別")
    assignee: Optional[str] = Field(None, description="承辦人")
    notes: Optional[str] = Field(None, description="備註")
    priority_level: Optional[str] = Field(None, description="優先級")
    content: Optional[str] = Field(None, description="內容")


@router.post(
    "/{document_id}/detail",
    response_model=DocumentResponse,
    summary="取得公文詳情"
)
async def get_document_detail(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """取得單一公文詳情（POST-only 資安機制）"""
    try:
        query = select(OfficialDocument).where(OfficialDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException(f"找不到公文 ID: {document_id}")

        return DocumentResponse.model_validate(document)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"取得公文詳情失敗: {e}", exc_info=True)
        raise


@router.post(
    "",
    response_model=DocumentResponse,
    summary="建立公文"
)
async def create_document(
    data: DocumentCreateRequest = Body(...),
    db: AsyncSession = Depends(get_async_db)
):
    """建立新公文（POST-only 資安機制）"""
    try:
        create_data = data.model_dump(exclude_unset=True)

        # 日期欄位需要特別處理：字串轉換為 date 物件
        date_fields = ['doc_date', 'receive_date', 'send_date']
        for field in date_fields:
            if field in create_data and isinstance(create_data[field], str):
                create_data[field] = parse_date_string(create_data[field])

        document = OfficialDocument(**create_data)
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return DocumentResponse.model_validate(document)
    except Exception as e:
        await db.rollback()
        logger.error(f"建立公文失敗: {e}", exc_info=True)
        raise


@router.post(
    "/{document_id}/update",
    response_model=DocumentResponse,
    summary="更新公文"
)
async def update_document(
    document_id: int,
    data: DocumentUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_async_db)
):
    """更新公文（POST-only 資安機制，含審計日誌）"""
    try:
        query = select(OfficialDocument).where(OfficialDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException(f"找不到公文 ID: {document_id}")

        # 初始化審計保護器，記錄原始資料
        guard = DocumentUpdateGuard(db, document_id)
        original_data = {
            col.name: getattr(document, col.name)
            for col in document.__table__.columns
        }

        update_data = data.model_dump(exclude_unset=True)

        # 日期欄位需要特別處理：字串轉換為 date 物件
        date_fields = ['doc_date', 'receive_date', 'send_date']
        processed_data = {}

        for key, value in update_data.items():
            if value is not None:
                # 處理日期欄位
                if key in date_fields:
                    parsed_date = parse_date_string(value) if isinstance(value, str) else value
                    setattr(document, key, parsed_date)
                    processed_data[key] = parsed_date
                else:
                    setattr(document, key, value)
                    processed_data[key] = value

        # 記錄審計日誌（變更前後比對）
        changes = {}
        for key, new_value in processed_data.items():
            old_value = original_data.get(key)
            if old_value != new_value:
                changes[key] = {"old": str(old_value), "new": str(new_value)}

        if changes:
            await log_document_change(
                db=db,
                document_id=document_id,
                action="UPDATE",
                changes=changes,
                source="API"
            )
            logger.info(f"公文 {document_id} 更新: {list(changes.keys())}")

        await db.commit()
        await db.refresh(document)
        return DocumentResponse.model_validate(document)
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新公文失敗: {e}", exc_info=True)
        raise


@router.post(
    "/{document_id}/delete",
    response_model=DeleteResponse,
    summary="刪除公文"
)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """刪除公文（POST-only 資安機制）"""
    try:
        query = select(OfficialDocument).where(OfficialDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException(f"找不到公文 ID: {document_id}")

        await db.delete(document)
        await db.commit()

        return DeleteResponse(
            success=True,
            message="公文已刪除",
            deleted_id=document_id
        )
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"刪除公文失敗: {e}", exc_info=True)
        raise


# ============================================================================
# 向後相容：保留 GET 端點（已棄用，將在未來版本移除）
# ============================================================================

@router.get(
    "/integrated-search",
    summary="整合式公文搜尋（已棄用，請改用 POST /list）",
    deprecated=True
)
async def integrated_document_search_legacy(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(50, ge=1, le=1000, description="取得筆數"),
    keyword: Optional[str] = Query(None, description="關鍵字搜尋"),
    doc_type: Optional[str] = Query(None, description="公文類型"),
    year: Optional[int] = Query(None, description="年度"),
    status: Optional[str] = Query(None, description="狀態"),
    contract_case: Optional[str] = Query(None, description="承攬案件"),
    sender: Optional[str] = Query(None, description="發文單位"),
    receiver: Optional[str] = Query(None, description="受文單位"),
    doc_date_from: Optional[str] = Query(None, description="公文日期起"),
    doc_date_to: Optional[str] = Query(None, description="公文日期迄"),
    sort_by: Optional[str] = Query("updated_at", description="排序欄位"),
    sort_order: Optional[str] = Query("desc", description="排序順序"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    整合式公文搜尋（已棄用）

    請改用 POST /documents-enhanced/list 端點
    """
    try:
        service = DocumentService(db)

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


@router.get("/document-years", summary="取得年度選項（已棄用）", deprecated=True)
async def get_document_years_legacy(db: AsyncSession = Depends(get_async_db)):
    """已棄用，請改用 POST /documents-enhanced/years"""
    return await get_document_years(db)


# ============================================================================
# 專案關聯公文 API（自動關聯機制）
# ============================================================================

class ProjectDocumentsQuery(BaseModel):
    """專案關聯公文查詢參數"""
    project_id: int = Field(..., description="專案 ID")
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=50, ge=1, le=100, description="每頁筆數")


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

        # 查詢專案名稱（所有文件共用同一個專案）
        project_name = None
        if query.project_id:
            project_query = select(ContractProject.project_name).where(
                ContractProject.id == query.project_id
            )
            project_result = await db.execute(project_query)
            project_name = project_result.scalar()

        # 查詢專案承辦同仁（使用 project_user_assignment 關聯表）
        assigned_staff = []
        if query.project_id:
            # 從關聯表查詢專案成員，並 JOIN users 表獲取姓名
            staff_query = (
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
            staff_result = await db.execute(staff_query)
            staff_rows = staff_result.all()
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
# 公文匯出 API
# ============================================================================

class DocumentExportQuery(BaseModel):
    """公文匯出查詢參數"""
    document_ids: Optional[List[int]] = Field(None, description="指定匯出的公文ID列表，若為空則匯出全部")
    category: Optional[str] = Field(None, description="類別篩選 (收文/發文)")
    year: Optional[int] = Field(None, description="年度篩選")
    format: str = Field(default="csv", description="匯出格式 (csv)")


@router.post("/export", summary="匯出公文資料")
async def export_documents(
    query: DocumentExportQuery = Body(...),
    db: AsyncSession = Depends(get_async_db)
):
    """
    匯出公文資料為 CSV 格式

    支援功能:
    - 依指定 ID 列表匯出
    - 依類別/年度篩選後匯出
    - 若未指定條件則匯出全部
    """
    try:
        # 構建查詢
        doc_query = select(OfficialDocument).options(
            selectinload(OfficialDocument.contract_project)
        )

        # 篩選條件
        conditions = []
        if query.document_ids:
            conditions.append(OfficialDocument.id.in_(query.document_ids))
        if query.category:
            conditions.append(OfficialDocument.category == query.category)
        if query.year:
            conditions.append(func.extract('year', OfficialDocument.doc_date) == query.year)

        if conditions:
            doc_query = doc_query.where(and_(*conditions))

        doc_query = doc_query.order_by(OfficialDocument.doc_date.desc())

        result = await db.execute(doc_query)
        documents = result.scalars().all()

        # 產生 CSV
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # 寫入標題列
        headers = [
            '序號', '公文文號', '主旨', '類別', '發文/收文日期',
            '發文單位', '受文單位', '承攬案件', '狀態', '備註'
        ]
        writer.writerow(headers)

        # 寫入資料列
        for idx, doc in enumerate(documents, start=1):
            contract_case_name = ""
            if doc.contract_project:
                contract_case_name = doc.contract_project.project_name or ""

            row = [
                doc.auto_serial or idx,
                doc.doc_number or "",
                doc.subject or "",
                doc.category or "",
                str(doc.doc_date) if doc.doc_date else "",
                doc.sender or "",
                doc.receiver or "",
                contract_case_name,
                doc.status or "",
                doc.notes or ""
            ]
            writer.writerow(row)

        # 重置游標位置
        output.seek(0)

        # 回傳 CSV 檔案
        from datetime import datetime
        filename = f"documents_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter(['\ufeff' + output.getvalue()]),  # BOM for Excel UTF-8
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"匯出公文失敗: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"匯出公文失敗: {str(e)}")
