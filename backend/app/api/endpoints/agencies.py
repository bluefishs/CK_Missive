"""
機關單位管理 API 端點 - POST-only 資安機制，統一回應格式

v3.0 - 2026-02-06
- 重構: AgencyService 升級為工廠模式，移除端點中的 db 參數傳遞
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_async_db
from app.core.dependencies import require_auth, require_admin, require_permission, get_service
from app.extended.models import User
from app.schemas.agency import (
    Agency, AgencyCreate, AgencyUpdate, AgencyWithStats,
    AgenciesResponse, AgencyStatistics,
    AgencyListQuery, AgencyListResponse,
    AgencySuggestRequest, AgencySuggestResponse,
    AssociationSummary, BatchAssociateRequest, BatchAssociateResponse,
    FixAgenciesRequest, FixAgenciesResponse
)
from app.schemas.common import PaginationMeta, SortOrder
from app.services.agency_service import AgencyService

logger = logging.getLogger(__name__)

router = APIRouter()

# 注意：AgencyListQuery, AgencyListResponse 等型別已統一定義於 app/schemas/agency.py


# ============================================================================
# 機關列表 API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/list",
    response_model=AgencyListResponse,
    summary="查詢機關列表",
    description="使用統一分頁格式查詢機關列表（POST-only 資安機制）"
)
async def list_agencies(
    query: AgencyListQuery = Body(default=AgencyListQuery()),
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """
    查詢機關列表（POST-only 資安機制）

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
        skip = (query.page - 1) * query.limit

        if query.include_stats:
            result = await agency_service.get_agencies_with_stats(
                skip=skip, limit=query.limit, search=query.search,
                category=query.category
            )
            items = result["agencies"]
            total = result["total"]
        else:
            items = await agency_service.get_list(
                skip=skip, limit=query.limit
            )
            total = len(items)

        return AgencyListResponse(
            success=True,
            items=items,
            pagination=PaginationMeta.create(
                total=total,
                page=query.page,
                limit=query.limit
            )
        )
    except Exception as e:
        logger.error(f"查詢機關列表失敗: {e}", exc_info=True)
        return AgencyListResponse(
            success=False,
            items=[],
            pagination=PaginationMeta.create(total=0, page=1, limit=query.limit)
        )


@router.post(
    "/{agency_id}/detail",
    response_model=Agency,
    summary="取得機關詳情"
)
async def get_agency_detail(
    agency_id: int,
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """取得單一機關詳情"""
    agency = await agency_service.get_by_id(agency_id)
    if agency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到指定的機關單位"
        )
    return agency


@router.post(
    "",
    response_model=Agency,
    status_code=status.HTTP_201_CREATED,
    summary="建立機關"
)
async def create_agency(
    agency: AgencyCreate = Body(...),
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_permission("agencies:create"))
):
    """
    建立新機關單位

    🔒 權限要求：agencies:create
    """
    try:
        return await agency_service.create(agency)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post(
    "/{agency_id}/update",
    response_model=Agency,
    summary="更新機關"
)
async def update_agency(
    agency_id: int,
    agency: AgencyUpdate = Body(...),
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_permission("agencies:edit"))
):
    """
    更新機關單位資料

    🔒 權限要求：agencies:edit
    """
    updated = await agency_service.update(agency_id, agency)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到要更新的機關單位"
        )
    return updated


@router.post(
    "/{agency_id}/delete",
    summary="刪除機關"
)
async def delete_agency(
    agency_id: int,
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_permission("agencies:delete"))
):
    """
    刪除機關單位

    🔒 權限要求：agencies:delete
    """
    try:
        success = await agency_service.delete(agency_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到要刪除的機關單位"
            )
        return {
            "success": True,
            "message": "機關單位已刪除",
            "deleted_id": agency_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post(
    "/statistics",
    response_model=AgencyStatistics,
    summary="取得機關統計資料"
)
async def get_agency_statistics(
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """取得機關統計資料"""
    return await agency_service.get_agency_statistics()


# ============================================================================
# 向後相容：保留 GET 端點（已棄用，將在未來版本移除）
# ============================================================================

@router.post(
    "",
    response_model=AgenciesResponse,
    summary="[相容] 取得機關列表 (預計 2026-07 移除)",
    deprecated=True
)
async def list_agencies_legacy(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_stats: bool = True,
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """
    [相容性端點] 取得機關列表

    ⚠️ **預計廢止日期**: 2026-07
    此端點為向後相容保留，請改用 POST /agencies/list
    """
    if include_stats:
        return await agency_service.get_agencies_with_stats(
            skip=skip, limit=limit, search=search
        )
    else:
        agencies = await agency_service.get_list(skip=skip, limit=limit)
        return AgenciesResponse(agencies=agencies, total=len(agencies), returned=len(agencies))


@router.post(
    "/statistics",
    response_model=AgencyStatistics,
    summary="[相容] 取得統計資料 (預計 2026-07 移除)",
    deprecated=True
)
async def get_statistics_legacy(
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """
    ⚠️ **預計廢止日期**: 2026-07
    此端點為向後相容保留，請改用 POST /agencies/statistics
    """
    return await agency_service.get_agency_statistics()


# ============================================================================
# 資料修復 API
# ============================================================================
# 注意：FixAgenciesRequest, FixAgenciesResponse 已統一定義於 app/schemas/agency.py


@router.post(
    "/fix-parsed-names",
    response_model=FixAgenciesResponse,
    summary="修復機關名稱/代碼解析錯誤"
)
async def fix_agency_parsed_names(
    request: FixAgenciesRequest = Body(default=FixAgenciesRequest()),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """
    修復機關名稱/代碼解析錯誤

    修復格式如：
    - "A01020100G (內政部國土管理署城鄉發展分署)" -> 代碼: A01020100G, 名稱: 內政部國土管理署城鄉發展分署
    - "EB50819619 乾坤測繪科技有限公司" -> 代碼: EB50819619, 名稱: 乾坤測繪科技有限公司

    當解析出的名稱已存在時，會合併記錄（刪除錯誤記錄，更新關聯）

    Args:
        request: 請求參數，包含 dry_run 設定
    """
    from sqlalchemy import select, update
    from app.extended.models import GovernmentAgency, OfficialDocument
    from app.services.strategies.agency_matcher import parse_agency_string

    dry_run = request.dry_run

    try:
        # 查詢所有機關
        result = await db.execute(select(GovernmentAgency))
        agencies = result.scalars().all()

        # 建立名稱 -> ID 映射（用於檢查重複）
        name_to_id = {a.agency_name: a.id for a in agencies}

        fixed_details = []
        merged_count = 0
        updated_count = 0

        for agency in agencies:
            original_name = agency.agency_name
            original_code = agency.agency_code

            # 解析名稱
            parsed_code, parsed_name = parse_agency_string(original_name)

            # 檢查是否需要修復（名稱包含代碼格式，且代碼欄位為空）
            if not (parsed_code and parsed_name != original_name and not original_code):
                continue

            # 檢查解析出的名稱是否已存在
            existing_id = name_to_id.get(parsed_name)

            if existing_id and existing_id != agency.id:
                # 情況 A: 重複 - 需要合併記錄
                detail = {
                    "id": agency.id,
                    "action": "merge",
                    "original_name": original_name,
                    "original_code": original_code,
                    "new_name": parsed_name,
                    "new_code": parsed_code,
                    "merge_to_id": existing_id,
                    "message": f"合併至已存在的機關 ID={existing_id}"
                }
                fixed_details.append(detail)

                if not dry_run:
                    # 更新關聯的公文（sender_agency_id, receiver_agency_id）
                    await db.execute(
                        update(OfficialDocument)
                        .where(OfficialDocument.sender_agency_id == agency.id)
                        .values(sender_agency_id=existing_id)
                    )
                    await db.execute(
                        update(OfficialDocument)
                        .where(OfficialDocument.receiver_agency_id == agency.id)
                        .values(receiver_agency_id=existing_id)
                    )
                    # 刪除重複的錯誤記錄
                    await db.delete(agency)
                    merged_count += 1
            else:
                # 情況 B: 不重複 - 直接更新
                detail = {
                    "id": agency.id,
                    "action": "update",
                    "original_name": original_name,
                    "original_code": original_code,
                    "new_name": parsed_name,
                    "new_code": parsed_code
                }
                fixed_details.append(detail)

                if not dry_run:
                    agency.agency_name = parsed_name
                    agency.agency_code = parsed_code
                    updated_count += 1

        if not dry_run and fixed_details:
            await db.commit()

        message_parts = []
        if dry_run:
            message_parts.append("乾跑模式：")
        message_parts.append(f"找到 {len(fixed_details)} 筆需要修復的機關資料")
        if fixed_details:
            if dry_run:
                merge_planned = sum(1 for d in fixed_details if d.get("action") == "merge")
                update_planned = sum(1 for d in fixed_details if d.get("action") == "update")
                message_parts.append(f"（{update_planned} 筆更新，{merge_planned} 筆合併）")
            else:
                message_parts.append(f"，已修復（{updated_count} 筆更新，{merged_count} 筆合併）")

        return FixAgenciesResponse(
            success=True,
            message="".join(message_parts),
            fixed_count=len(fixed_details),
            details=fixed_details
        )

    except Exception as e:
        logger.error(f"修復機關資料失敗: {e}", exc_info=True)
        await db.rollback()
        return FixAgenciesResponse(
            success=False,
            message=f"修復失敗: {str(e)}",
            fixed_count=0,
            details=[]
        )


# ============================================================================
# 智慧機關關聯 API
# ============================================================================

# 注意：AssociationSummary, BatchAssociateRequest, BatchAssociateResponse,
#       AgencySuggestRequest, AgencySuggestResponse 已統一定義於 app/schemas/agency.py


@router.post(
    "/association-summary",
    response_model=AssociationSummary,
    summary="取得機關關聯統計"
)
async def get_association_summary(
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """
    取得公文與機關關聯的統計資料

    回傳包含：
    - 已關聯/未關聯發文機關數量
    - 已關聯/未關聯受文機關數量
    - 關聯率百分比
    """
    return await agency_service.get_unassociated_summary()


@router.post(
    "/batch-associate",
    response_model=BatchAssociateResponse,
    summary="批次智慧關聯機關"
)
async def batch_associate_agencies(
    request: BatchAssociateRequest = Body(default=BatchAssociateRequest()),
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_admin())
):
    """
    批次為所有公文自動關聯機關

    智慧匹配規則：
    1. 優先匹配機關代碼
    2. 完全匹配機關名稱
    3. 完全匹配機關簡稱
    4. 部分匹配（機關名稱包含在文字中）

    Args:
        request: 包含 overwrite 參數（是否覆蓋現有關聯）
    """
    try:
        stats = await agency_service.batch_associate_agencies(
            overwrite=request.overwrite
        )

        message_parts = []
        if stats["sender_updated"] > 0 or stats["receiver_updated"] > 0:
            message_parts.append(
                f"成功關聯：發文機關 {stats['sender_updated']} 筆、"
                f"受文機關 {stats['receiver_updated']} 筆"
            )
        else:
            message_parts.append("沒有新的機關可供關聯")

        if stats["errors"]:
            message_parts.append(f"（{len(stats['errors'])} 個錯誤）")

        return BatchAssociateResponse(
            success=len(stats["errors"]) == 0,
            message="".join(message_parts),
            total_documents=stats["total_documents"],
            sender_updated=stats["sender_updated"],
            receiver_updated=stats["receiver_updated"],
            sender_matched=stats["sender_matched"],
            receiver_matched=stats["receiver_matched"],
            errors=stats["errors"][:10]  # 只回傳前 10 個錯誤
        )
    except Exception as e:
        logger.error(f"批次關聯機關失敗: {e}", exc_info=True)
        return BatchAssociateResponse(
            success=False,
            message=f"關聯失敗: {str(e)}",
            errors=[str(e)]
        )


@router.post(
    "/suggest",
    response_model=AgencySuggestResponse,
    summary="智慧建議機關"
)
async def suggest_agencies(
    request: AgencySuggestRequest = Body(...),
    agency_service: AgencyService = Depends(get_service(AgencyService)),
    current_user: User = Depends(require_auth())
):
    """
    根據輸入文字智慧建議可能的機關

    用於表單自動完成，支援模糊搜尋機關名稱、簡稱、代碼
    """
    try:
        suggestions = await agency_service.suggest_agency(
            text=request.text, limit=request.limit
        )
        return AgencySuggestResponse(success=True, suggestions=suggestions)
    except Exception as e:
        logger.error(f"機關建議失敗: {e}", exc_info=True)
        return AgencySuggestResponse(success=False, suggestions=[])
