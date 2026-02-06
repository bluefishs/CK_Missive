"""
公文統計與下拉選單 API 端點

包含：下拉選項、統計資料、發文字號、趨勢分析、效率統計

@version 5.0.0
@date 2026-02-07
"""
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import Optional

from fastapi import APIRouter, Body, Request
from sqlalchemy import select, func, extract, and_, case
from starlette.responses import Response

from .common import (
    logger, Depends, AsyncSession, get_async_db,
    OfficialDocument,
    DocumentListQuery,
    DropdownQuery, AgencyDropdownQuery,
    User, require_auth,
    DocumentStatisticsService, get_statistics_service,
)
from app.core.dependencies import optional_auth
from app.core.rate_limiter import limiter
from app.extended.models import DocumentCalendarEvent
from app.schemas.document_number import NextNumberRequest, NextNumberResponse

router = APIRouter()


# ============================================================================
# 下拉選項 API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/contract-projects-dropdown",
    summary="取得承攬案件下拉選項"
)
async def get_contract_projects_dropdown(
    query: DropdownQuery = Body(default=DropdownQuery()),
    service: DocumentStatisticsService = Depends(get_statistics_service)
):
    """取得承攬案件下拉選項 - 從 contract_projects 表查詢"""
    try:
        options = await service.get_contract_projects_dropdown(
            search=query.search,
            limit=query.limit
        )
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
    service: DocumentStatisticsService = Depends(get_statistics_service)
):
    """
    取得政府機關下拉選項

    優化版：從 government_agencies 表取得標準化機關名稱，
    與 http://localhost:3000/agencies 頁面顯示一致。
    """
    try:
        options = await service.get_agencies_dropdown(
            search=query.search,
            limit=query.limit
        )
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
    service: DocumentStatisticsService = Depends(get_statistics_service)
):
    """取得文檔年度選項"""
    try:
        year_list = await service.get_document_years()
        return {
            "success": True,
            "years": year_list,
            "total": len(year_list)
        }
    except Exception as e:
        logger.error(f"取得年度選項失敗: {e}", exc_info=True)
        return {"success": False, "years": [], "total": 0}


# ============================================================================
# 統計 API
# ============================================================================

@router.post(
    "/statistics",
    summary="取得公文統計資料"
)
async def get_documents_statistics(
    service: DocumentStatisticsService = Depends(get_statistics_service)
):
    """取得公文統計資料 (收發文分類基於 category 欄位)"""
    try:
        return await service.get_overall_statistics()
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
            "current_year_count": 0,
            "current_year_send_count": 0,
            "delivery_method_stats": {
                "electronic": 0,
                "paper": 0,
                "both": 0
            }
        }


@router.post(
    "/filtered-statistics",
    summary="取得篩選後的公文統計資料"
)
@limiter.limit("30/minute")
async def get_filtered_statistics(
    request: Request,
    response: Response,
    query: DocumentListQuery = Body(default=DocumentListQuery()),
    service: DocumentStatisticsService = Depends(get_statistics_service)
):
    """
    根據篩選條件取得動態統計資料

    回傳基於當前篩選條件的：
    - total: 符合條件的總數
    - send_count: 符合條件的發文數
    - receive_count: 符合條件的收文數

    用於前端 Tab 標籤的動態數字顯示
    """
    try:
        return await service.get_filtered_statistics(
            doc_number=query.doc_number,
            keyword=query.keyword,
            doc_type=query.doc_type,
            year=query.year,
            sender=query.sender,
            receiver=query.receiver,
            delivery_method=query.delivery_method,
            doc_date_from=query.doc_date_from,
            doc_date_to=query.doc_date_to,
            contract_case=query.contract_case,
        )
    except Exception as e:
        logger.error(f"取得篩選統計失敗: {e}", exc_info=True)
        return {
            "success": False,
            "total": 0,
            "send_count": 0,
            "receive_count": 0,
            "filters_applied": False,
            "error": str(e)
        }


# ============================================================================
# 趨勢與效率分析 API
# ============================================================================

@router.post(
    "/trends",
    summary="取得公文收發趨勢（過去 12 個月）"
)
async def get_document_trends(
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(optional_auth()),
):
    """
    取得過去 12 個月每月收文/發文數量趨勢

    使用 category 欄位區分收文/發文，按 doc_date 的年月分組統計。

    回傳格式:
        {
          "success": true,
          "trends": [
            { "month": "2025-03", "received": 45, "sent": 23 },
            ...
          ]
        }
    """
    try:
        today = date.today()
        # 計算 12 個月前的第一天
        twelve_months_ago = (today - relativedelta(months=11)).replace(day=1)

        # 使用 extract + GROUP BY 統計每月收發文數量
        year_col = extract('year', OfficialDocument.doc_date)
        month_col = extract('month', OfficialDocument.doc_date)

        query = (
            select(
                year_col.label('year'),
                month_col.label('month'),
                func.sum(
                    case(
                        (OfficialDocument.category == '收文', 1),
                        else_=0
                    )
                ).label('received'),
                func.sum(
                    case(
                        (OfficialDocument.category == '發文', 1),
                        else_=0
                    )
                ).label('sent'),
            )
            .where(
                and_(
                    OfficialDocument.doc_date.isnot(None),
                    OfficialDocument.doc_date >= twelve_months_ago,
                )
            )
            .group_by(year_col, month_col)
            .order_by(year_col.asc(), month_col.asc())
        )

        result = await db.execute(query)
        rows = result.all()

        # 建立完整的 12 個月資料（即使某月無資料也填入 0）
        month_map = {}
        for row in rows:
            key = f"{int(row.year)}-{int(row.month):02d}"
            month_map[key] = {
                "month": key,
                "received": int(row.received or 0),
                "sent": int(row.sent or 0),
            }

        trends = []
        cursor = twelve_months_ago
        while cursor <= today:
            key = f"{cursor.year}-{cursor.month:02d}"
            if key in month_map:
                trends.append(month_map[key])
            else:
                trends.append({
                    "month": key,
                    "received": 0,
                    "sent": 0,
                })
            cursor = cursor + relativedelta(months=1)

        return {
            "success": True,
            "trends": trends,
        }
    except Exception as e:
        logger.error(f"取得公文趨勢失敗: {e}", exc_info=True)
        return {
            "success": False,
            "trends": [],
            "error": str(e),
        }


@router.post(
    "/efficiency",
    summary="取得公文處理效率統計"
)
async def get_document_efficiency(
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(optional_auth()),
):
    """
    取得公文各狀態分布和逾期統計

    狀態分布：按 status 欄位分組統計數量。
    逾期判斷：status 不是「已結案」且關聯行事曆事件的 end_date 早於今天
    （行事曆事件狀態非 completed）。

    回傳格式:
        {
          "success": true,
          "status_distribution": [
            { "status": "待處理", "count": 120 },
            ...
          ],
          "overdue_count": 8,
          "overdue_rate": 0.016,
          "total": 745
        }
    """
    try:
        # 1. 狀態分布查詢
        status_query = (
            select(
                OfficialDocument.status,
                func.count(OfficialDocument.id).label('count'),
            )
            .where(OfficialDocument.status.isnot(None))
            .group_by(OfficialDocument.status)
            .order_by(func.count(OfficialDocument.id).desc())
        )
        status_result = await db.execute(status_query)
        status_rows = status_result.all()

        status_distribution = [
            {"status": row.status, "count": int(row.count)}
            for row in status_rows
        ]

        # 2. 總數查詢
        total_query = select(func.count(OfficialDocument.id))
        total = (await db.execute(total_query)).scalar() or 0

        # 3. 逾期統計：公文未結案且有已過期的行事曆事件
        now = datetime.now()
        overdue_query = (
            select(func.count(func.distinct(OfficialDocument.id)))
            .join(
                DocumentCalendarEvent,
                DocumentCalendarEvent.document_id == OfficialDocument.id,
            )
            .where(
                and_(
                    OfficialDocument.status != '已結案',
                    DocumentCalendarEvent.end_date.isnot(None),
                    DocumentCalendarEvent.end_date < now,
                    DocumentCalendarEvent.status != 'completed',
                )
            )
        )
        overdue_count = (await db.execute(overdue_query)).scalar() or 0

        # 4. 計算逾期率
        overdue_rate = round(overdue_count / total, 3) if total > 0 else 0.0

        return {
            "success": True,
            "status_distribution": status_distribution,
            "overdue_count": overdue_count,
            "overdue_rate": overdue_rate,
            "total": total,
        }
    except Exception as e:
        logger.error(f"取得公文效率統計失敗: {e}", exc_info=True)
        return {
            "success": False,
            "status_distribution": [],
            "overdue_count": 0,
            "overdue_rate": 0.0,
            "total": 0,
            "error": str(e),
        }


# ============================================================================
# 向後相容：保留已棄用端點
# ============================================================================

@router.post("/document-years", summary="取得年度選項（已棄用，預計 2026-07 移除）", deprecated=True)
async def get_document_years_legacy(
    service: DocumentStatisticsService = Depends(get_statistics_service)
):
    """
    ⚠️ **預計廢止日期**: 2026-07
    已棄用，請改用 POST /documents-enhanced/years
    """
    return await get_document_years(service)


# ============================================================================
# 發文字號 API
# ============================================================================

@router.post("/next-send-number", response_model=NextNumberResponse)
async def get_next_send_number(
    request: NextNumberRequest = NextNumberRequest(),
    service: DocumentStatisticsService = Depends(get_statistics_service),
    current_user: User = Depends(require_auth())
):
    """
    取得下一個可用的發文字號 (POST-only)

    文號格式：{前綴}{民國年3位}{流水號7位}號
    範例：乾坤測字第1150000001號 (民國115年第1號)

    新年度自動重置流水號從 0000001 開始
    """
    try:
        result = await service.get_next_send_number(
            prefix=request.prefix,
            year=request.year
        )
        return NextNumberResponse(
            full_number=result['full_number'],
            year=result['year'],
            roc_year=result['roc_year'],
            sequence_number=result['sequence_number'],
            previous_max=result['previous_max'],
            prefix=result['prefix']
        )
    except Exception as e:
        # 查詢失敗時返回預設值 (新年度第1號)
        logger.error(f"取得下一個字號失敗: {e}")
        from datetime import datetime
        from app.core.config import settings

        DEFAULT_DOC_PREFIX = getattr(settings, 'DOC_NUMBER_PREFIX', '乾坤測字第')
        fallback_year = request.year or datetime.now().year
        roc_year = fallback_year - 1911
        prefix = request.prefix or DEFAULT_DOC_PREFIX

        return NextNumberResponse(
            full_number=f"{prefix}{roc_year}0000001號",
            year=fallback_year,
            roc_year=roc_year,
            sequence_number=1,
            previous_max=0,
            prefix=prefix
        )
