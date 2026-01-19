"""
公文統計與下拉選單 API 端點

包含：下拉選項、統計資料、發文字號

@version 3.1.0
@date 2026-01-19
"""
from datetime import datetime
from fastapi import APIRouter, Body
from sqlalchemy import select, text, or_

from .common import (
    logger, Depends, AsyncSession, get_async_db,
    ContractProject, DocumentFilter,
    DocumentService, DocumentListQuery,
    DropdownQuery, AgencyDropdownQuery,
    User, require_auth,
)
from app.schemas.document_number import NextNumberRequest, NextNumberResponse
from app.core.config import settings

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
    """
    取得政府機關下拉選項

    優化版：從 government_agencies 表取得標準化機關名稱，
    與 http://localhost:3000/agencies 頁面顯示一致。
    """
    try:
        # 從 government_agencies 表取得標準化機關名稱
        sql_query = """
        SELECT id, agency_name, agency_code, agency_short_name
        FROM government_agencies
        WHERE agency_name IS NOT NULL AND agency_name != ''
        """

        params = {}
        if query.search:
            sql_query += " AND (agency_name ILIKE :search OR agency_short_name ILIKE :search)"
            params["search"] = f"%{query.search}%"

        sql_query += " ORDER BY agency_name LIMIT :limit"
        params["limit"] = query.limit

        result = await db.execute(text(sql_query), params)
        agencies = result.fetchall()

        options = []
        for row in agencies:
            options.append({
                "value": row.agency_name,  # 使用標準化名稱作為值
                "label": row.agency_name,  # 顯示標準化名稱
                "id": row.id,
                "agency_code": row.agency_code or "",
                "agency_short_name": row.agency_short_name or ""
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


# ============================================================================
# 統計 API
# ============================================================================

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

        # 發文形式統計 (僅統計發文類別)
        electronic_query = "SELECT COUNT(*) as count FROM documents WHERE category = '發文' AND delivery_method = '電子交換'"
        paper_query = "SELECT COUNT(*) as count FROM documents WHERE category = '發文' AND delivery_method = '紙本郵寄'"
        both_query = "SELECT COUNT(*) as count FROM documents WHERE category = '發文' AND delivery_method = '電子+紙本'"

        # 本年度發文數
        current_year_send_query = "SELECT COUNT(*) as count FROM documents WHERE category = '發文' AND EXTRACT(YEAR FROM doc_date) = EXTRACT(YEAR FROM CURRENT_DATE)"

        total_result = await db.execute(text(total_query))
        send_result = await db.execute(text(send_query))
        receive_result = await db.execute(text(receive_query))
        current_year_result = await db.execute(text(current_year_query))

        # 發文形式統計
        electronic_result = await db.execute(text(electronic_query))
        paper_result = await db.execute(text(paper_query))
        both_result = await db.execute(text(both_query))
        current_year_send_result = await db.execute(text(current_year_send_query))

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
            "current_year_count": current_year_result.scalar() or 0,
            "current_year_send_count": current_year_send_result.scalar() or 0,
            "delivery_method_stats": {
                "electronic": electronic_result.scalar() or 0,
                "paper": paper_result.scalar() or 0,
                "both": both_result.scalar() or 0
            }
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
async def get_filtered_statistics(
    query: DocumentListQuery = Body(default=DocumentListQuery()),
    db: AsyncSession = Depends(get_async_db)
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
        # 構建基本 WHERE 條件（不含 category）
        conditions = []
        params = {}

        # 公文字號專用篩選（僅搜尋 doc_number 欄位）
        if query.doc_number:
            conditions.append("doc_number ILIKE :doc_number")
            params["doc_number"] = f"%{query.doc_number}%"

        # 關鍵字搜尋（主旨、說明、備註 - 不含 doc_number）
        if query.keyword:
            conditions.append("""
                (subject ILIKE :keyword
                 OR content ILIKE :keyword OR notes ILIKE :keyword)
            """)
            params["keyword"] = f"%{query.keyword}%"

        if query.doc_type:
            conditions.append("doc_type = :doc_type")
            params["doc_type"] = query.doc_type

        if query.year:
            conditions.append("EXTRACT(YEAR FROM doc_date) = :year")
            params["year"] = query.year

        if query.sender:
            conditions.append("sender ILIKE :sender")
            params["sender"] = f"%{query.sender}%"

        if query.receiver:
            conditions.append("receiver ILIKE :receiver")
            params["receiver"] = f"%{query.receiver}%"

        if query.delivery_method:
            conditions.append("delivery_method = :delivery_method")
            params["delivery_method"] = query.delivery_method

        if query.doc_date_from:
            conditions.append("doc_date >= :doc_date_from")
            params["doc_date_from"] = query.doc_date_from

        if query.doc_date_to:
            conditions.append("doc_date <= :doc_date_to")
            params["doc_date_to"] = query.doc_date_to

        if query.contract_case:
            # 需要 JOIN contract_projects 表
            conditions.append("""
                contract_project_id IN (
                    SELECT id FROM contract_projects
                    WHERE project_name ILIKE :contract_case OR project_code ILIKE :contract_case
                )
            """)
            params["contract_case"] = f"%{query.contract_case}%"

        # 組合 WHERE 子句
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 總數查詢
        total_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause}"
        total_result = await db.execute(text(total_query), params)
        total = total_result.scalar() or 0

        # 發文數查詢
        send_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause} AND category = '發文'"
        send_result = await db.execute(text(send_query), params)
        send_count = send_result.scalar() or 0

        # 收文數查詢
        receive_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause} AND category = '收文'"
        receive_result = await db.execute(text(receive_query), params)
        receive_count = receive_result.scalar() or 0

        logger.info(f"篩選統計: total={total}, send={send_count}, receive={receive_count}, filters={params}")

        return {
            "success": True,
            "total": total,
            "send_count": send_count,
            "receive_count": receive_count,
            "filters_applied": bool(conditions)
        }

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
# 向後相容：保留已棄用端點
# ============================================================================

@router.post("/document-years", summary="取得年度選項（已棄用）", deprecated=True)
async def get_document_years_legacy(db: AsyncSession = Depends(get_async_db)):
    """已棄用，請改用 POST /documents-enhanced/years"""
    return await get_document_years(db)


# ============================================================================
# 發文字號 API
# ============================================================================

# 發文字號前綴 (可從設定檔讀取)
DEFAULT_DOC_PREFIX = getattr(settings, 'DOC_NUMBER_PREFIX', '乾坤測字第')


@router.post("/next-send-number", response_model=NextNumberResponse)
async def get_next_send_number(
    request: NextNumberRequest = NextNumberRequest(),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    取得下一個可用的發文字號 (POST-only)

    文號格式：{前綴}{民國年3位}{流水號7位}號
    範例：乾坤測字第1150000001號 (民國115年第1號)

    新年度自動重置流水號從 0000001 開始
    """
    try:
        prefix = request.prefix or DEFAULT_DOC_PREFIX
        current_year = request.year or datetime.now().year
        roc_year = current_year - 1911

        # 查詢該民國年度的最大流水號
        year_pattern = f"{prefix}{roc_year}%"

        # 使用原生 SQL 查詢，提取流水號
        prefix_len = len(prefix)
        year_len = len(str(roc_year))

        raw_query = text(f"""
            SELECT MAX(
                CAST(
                    SUBSTRING(doc_number, {prefix_len + year_len + 1}, 7)
                    AS INTEGER
                )
            ) as max_seq
            FROM documents
            WHERE doc_number LIKE :pattern
            AND (category = '發文' OR doc_type = '發文')
        """)

        max_seq_result = await db.execute(
            raw_query,
            {"pattern": year_pattern}
        )
        row = max_seq_result.fetchone()
        max_sequence = row[0] if row and row[0] else 0

        next_sequence = max_sequence + 1

        # 生成完整文號：前綴 + 民國年(3位) + 流水號(7位) + 號
        full_number = f"{prefix}{roc_year}{next_sequence:07d}號"

        return NextNumberResponse(
            full_number=full_number,
            year=current_year,
            roc_year=roc_year,
            sequence_number=next_sequence,
            previous_max=max_sequence,
            prefix=prefix
        )

    except Exception as e:
        # 查詢失敗時返回預設值 (新年度第1號)
        logger.error(f"取得下一個字號失敗: {e}")
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
