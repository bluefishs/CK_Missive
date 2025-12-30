"""
增強版公文管理 API 端點 - 支援多表整合查詢 (已優化機關名稱標準化)
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, or_, and_
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.db.database import get_async_db
from app.extended.models import OfficialDocument, ContractProject, GovernmentAgency
from app.services.document_service import DocumentService
from app.schemas.document import DocumentFilter

router = APIRouter()

@router.get("/contract-projects-dropdown")
async def get_contract_projects_dropdown(
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    limit: int = Query(100, ge=1, le=1000, description="限制筆數"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得承攬案件下拉選項 - 從 contract_projects 表查詢
    """
    try:
        query = select(ContractProject.id, ContractProject.project_name, ContractProject.year, ContractProject.category)

        if search:
            query = query.where(
                or_(
                    ContractProject.project_name.ilike(f"%{search}%"),
                    ContractProject.project_code.ilike(f"%{search}%"),
                    ContractProject.client_agency.ilike(f"%{search}%")
                )
            )

        query = query.order_by(ContractProject.year.desc(), ContractProject.project_name.asc()).limit(limit)
        result = await db.execute(query)
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
            "options": options,
            "total": len(options)
        }

    except Exception as e:
        logger.error(f"取得承攬案件選項失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取得承攬案件選項失敗: {str(e)}")

@router.get("/agencies-dropdown")
async def get_agencies_dropdown(
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    agency_type: Optional[str] = Query(None, description="機關類型"),
    limit: int = Query(100, ge=1, le=1000, description="限制筆數"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得政府機關下拉選項 - 使用標準化機關名稱，不包含統計數據
    專為公文管理篩選設計，確保機關名稱統一標準化顯示
    """
    try:
        # 直接查詢機關名稱，不包含統計數據
        query = """
        SELECT DISTINCT agency as name
        FROM (
            SELECT sender as agency FROM documents WHERE sender IS NOT NULL AND sender != ''
            UNION
            SELECT receiver as agency FROM documents WHERE receiver IS NOT NULL AND receiver != ''
        ) combined_agencies
        WHERE agency IS NOT NULL AND agency != ''
        """

        # 添加搜尋條件
        params = {}
        if search:
            query += " AND agency ILIKE :search"
            params["search"] = f"%{search}%"

        query += " ORDER BY agency LIMIT :limit"
        params["limit"] = limit

        result = await db.execute(text(query), params)
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
            "options": options,
            "total": len(options)
        }

    except Exception as e:
        logger.error(f"取得政府機關選項失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取得政府機關選項失敗: {str(e)}")

@router.get("/integrated-search")
async def integrated_document_search(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(50, ge=1, le=1000, description="取得筆數"),
    # 基本篩選
    keyword: Optional[str] = Query(None, description="關鍵字搜尋"),
    doc_type: Optional[str] = Query(None, description="公文類型"),
    year: Optional[int] = Query(None, description="年度"),
    status: Optional[str] = Query(None, description="狀態"),
    # 進階篩選
    contract_case: Optional[str] = Query(None, description="承攬案件"),
    sender: Optional[str] = Query(None, description="發文單位"),
    receiver: Optional[str] = Query(None, description="受文單位"),
    doc_date_from: Optional[str] = Query(None, description="公文日期起"),
    doc_date_to: Optional[str] = Query(None, description="公文日期迄"),
    # 排序
    sort_by: Optional[str] = Query("updated_at", description="排序欄位"),
    sort_order: Optional[str] = Query("desc", description="排序順序"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    整合式公文搜尋 - 支援多表JOIN查詢
    """
    try:
        logger.info(f"整合搜尋請求: keyword={keyword}, contract_case={contract_case}, sender={sender}")

        service = DocumentService(db)

        # 構建篩選條件
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

        # 手動加入承攬案件篩選
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
        raise HTTPException(status_code=500, detail=f"整合搜尋失敗: {str(e)}")

@router.get("/document-years")
async def get_document_years(
    db: AsyncSession = Depends(get_async_db)
):
    """取得文檔年度選項"""
    try:
        query = """
        SELECT DISTINCT EXTRACT(YEAR FROM doc_date) as year
        FROM documents
        WHERE doc_date IS NOT NULL
        ORDER BY year DESC
        """

        result = await db.execute(text(query))
        years = result.fetchall()

        # 轉換為字串列表
        year_list = [str(int(row.year)) for row in years if row.year]

        return {
            "years": year_list,
            "total": len(year_list)
        }

    except Exception as e:
        logger.error(f"取得年度選項失敗: {e}", exc_info=True)
        return {
            "years": [],
            "total": 0
        }

@router.get("/statistics")
async def get_documents_statistics(
    db: AsyncSession = Depends(get_async_db)
):
    """取得公文統計資料"""
    try:
        # 基本統計查詢
        total_query = "SELECT COUNT(*) as count FROM documents"
        send_query = "SELECT COUNT(*) as count FROM documents WHERE doc_type = '發文'"
        receive_query = "SELECT COUNT(*) as count FROM documents WHERE doc_type = '收文'"
        current_year_query = "SELECT COUNT(*) as count FROM documents WHERE EXTRACT(YEAR FROM doc_date) = EXTRACT(YEAR FROM CURRENT_DATE)"

        total_result = await db.execute(text(total_query))
        send_result = await db.execute(text(send_query))
        receive_result = await db.execute(text(receive_query))
        current_year_result = await db.execute(text(current_year_query))

        return {
            "total_documents": total_result.scalar() or 0,
            "send_count": send_result.scalar() or 0,
            "receive_count": receive_result.scalar() or 0,
            "current_year_count": current_year_result.scalar() or 0
        }
    except Exception as e:
        logger.error(f"取得統計資料失敗: {e}", exc_info=True)
        return {
            "total_documents": 0,
            "send_count": 0,
            "receive_count": 0,
            "current_year_count": 0
        }