#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
發文字號管理 API 端點

⚠️ 此模組已棄用 (DEPRECATED)
================================

此模組將在未來版本中移除。請改用 documents_enhanced 端點。

遷移指南：
=========

舊端點 → 新端點
- POST /document-numbers/query      → POST /documents-enhanced/list (category='發文')
- POST /document-numbers/stats      → POST /documents-enhanced/statistics (category='send')
- POST /document-numbers/next-number → POST /documents-enhanced/next-send-number
- POST /document-numbers/create     → POST /documents-enhanced/create (doc_type='發文')
- POST /document-numbers/update/{id} → POST /documents-enhanced/{id}/update
- POST /document-numbers/delete/{id} → POST /documents-enhanced/{id}/delete

前端已完成遷移：
- DocumentNumbersPage 使用 documentsApi（documents-enhanced 端點）
- NextSendNumber 使用 DOCUMENTS_ENDPOINTS.NEXT_SEND_NUMBER

此模組保留目的：
- 向後相容性（過渡期）
- 將於 v4.0.0 正式移除

@version 2.1.0 (DEPRECATED)
@date 2026-01-19
"""

from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response
from sqlalchemy import func, select, desc, extract, or_

from app.core.rate_limiter import limiter
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import OfficialDocument, ContractProject, User
from app.core.config import settings
from app.core.dependencies import require_auth

# 統一從 schemas 匯入型別定義
from app.schemas.document_number import (
    DocumentNumberItem,
    DocumentNumberListResponse,
    DocumentNumberQueryRequest,
    YearlyStats,
    YearRange,
    DocumentNumberStats,
    NextNumberRequest,
    NextNumberResponse,
    DocumentNumberCreateRequest,
    DocumentNumberUpdateRequest,
)

router = APIRouter()


# =============================================================================
# 設定常量
# =============================================================================

# 發文字號前綴 (可從設定檔讀取)
DEFAULT_DOC_PREFIX = getattr(settings, 'DOC_NUMBER_PREFIX', '乾坤測字第')


# =============================================================================
# API 端點 (POST-only)
# =============================================================================

@router.post("/query", response_model=DocumentNumberListResponse)
@limiter.limit("60/minute")
async def query_document_numbers(
    http_request: Request,
    response: Response,
    request: DocumentNumberQueryRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    查詢發文字號列表 (POST-only 資安機制)

    - 支援分頁、篩選、排序
    - 關鍵字搜尋：主旨、文號、受文單位
    """
    try:
        query = select(OfficialDocument).where(
            OfficialDocument.doc_type == '發文'
        )

        # 年度篩選
        if request.year:
            query = query.where(
                extract('year', OfficialDocument.doc_date) == request.year
            )

        # 狀態篩選
        if request.status:
            query = query.where(OfficialDocument.status == request.status)

        # 關鍵字搜尋
        if request.keyword:
            keyword = f"%{request.keyword}%"
            query = query.where(
                or_(
                    OfficialDocument.subject.ilike(keyword),
                    OfficialDocument.doc_number.ilike(keyword),
                    OfficialDocument.receiver.ilike(keyword)
                )
            )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 排序
        order_column = getattr(OfficialDocument, request.sort_by, OfficialDocument.doc_date)
        if request.sort_order == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # 分頁
        offset = (request.page - 1) * request.limit
        query = query.options(selectinload(OfficialDocument.contract_project))
        query = query.offset(offset).limit(request.limit)

        result = await db.execute(query)
        documents = result.scalars().all()

        # 轉換回應格式
        items = []
        for doc in documents:
            doc_number = doc.doc_number or ""
            doc_prefix = ""
            sequence_number = 0
            year_num = doc.doc_date.year if doc.doc_date else datetime.now().year

            # 解析文號
            if doc_number:
                parts = doc_number.split('字第')
                if len(parts) >= 2:
                    doc_prefix = parts[0] + '字第'
                    number_part = parts[1].replace('號', '')
                    try:
                        sequence_number = int(number_part)
                    except ValueError:
                        sequence_number = 0

            contract_case_name = ""
            contract_case_id = None
            if doc.contract_project:
                contract_case_name = doc.contract_project.project_name or ""
                contract_case_id = doc.contract_project.id

            items.append(DocumentNumberItem(
                id=doc.id,
                doc_prefix=doc_prefix,
                year=year_num,
                sequence_number=sequence_number,
                full_number=doc_number,
                subject=doc.subject or "",
                contract_case=contract_case_name,
                contract_case_id=contract_case_id,
                receiver=doc.receiver or "",
                doc_date=str(doc.doc_date) if doc.doc_date else None,
                status=doc.status or "draft",
                created_at=str(doc.created_at) if doc.created_at else None
            ))

        total_pages = (total + request.limit - 1) // request.limit if request.limit > 0 else 0

        return DocumentNumberListResponse(
            items=items,
            total=total,
            page=request.page,
            limit=request.limit,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢發文字號失敗: {str(e)}")


@router.post("/stats", response_model=DocumentNumberStats)
@limiter.limit("60/minute")
async def get_document_numbers_stats(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得發文字號統計資料 (POST-only)"""
    try:
        base_filter = OfficialDocument.doc_type == '發文'

        # 總數
        total_result = await db.execute(
            select(func.count()).where(base_filter)
        )
        total_count = total_result.scalar() or 0

        # 各狀態數量
        sent_result = await db.execute(
            select(func.count()).where(
                base_filter,
                OfficialDocument.status == 'sent'
            )
        )
        sent_count = sent_result.scalar() or 0

        draft_result = await db.execute(
            select(func.count()).where(
                base_filter,
                OfficialDocument.status == 'draft'
            )
        )
        draft_count = draft_result.scalar() or 0

        archived_result = await db.execute(
            select(func.count()).where(
                base_filter,
                OfficialDocument.status == 'archived'
            )
        )
        archived_count = archived_result.scalar() or 0

        # 年度範圍
        year_range_result = await db.execute(
            select(
                func.min(extract('year', OfficialDocument.doc_date)),
                func.max(extract('year', OfficialDocument.doc_date))
            ).where(
                base_filter,
                OfficialDocument.doc_date.isnot(None)
            )
        )
        min_year, max_year = year_range_result.first() or (None, None)

        # 年度統計
        yearly_stats_result = await db.execute(
            select(
                extract('year', OfficialDocument.doc_date).label('year'),
                func.count().label('count')
            ).where(
                base_filter,
                OfficialDocument.doc_date.isnot(None)
            ).group_by(
                extract('year', OfficialDocument.doc_date)
            ).order_by(desc('year'))
        )
        yearly_data = yearly_stats_result.all()

        yearly_stats = [
            YearlyStats(year=int(row.year), count=row.count)
            for row in yearly_data
        ]

        # 最大序號
        max_sequence = max(row.count for row in yearly_data) if yearly_data else 0

        return DocumentNumberStats(
            total_count=total_count,
            draft_count=draft_count,
            sent_count=sent_count,
            archived_count=archived_count,
            max_sequence=max_sequence,
            year_range=YearRange(
                min_year=int(min_year) if min_year else None,
                max_year=int(max_year) if max_year else None
            ),
            yearly_stats=yearly_stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資料失敗: {str(e)}")


@router.post("/next-number", response_model=NextNumberResponse)
@limiter.limit("60/minute")
async def get_next_document_number(
    http_request: Request,
    response: Response,
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
        # 文號格式：乾坤測字第1150000002號
        # 前綴 + 民國年(3位) + 流水號(7位) + 號
        # 使用精確匹配：乾坤測字第115% (民國115年)
        year_pattern = f"{prefix}{roc_year}%"

        # 使用原生 SQL 查詢，提取流水號
        # 從文號中提取民國年後的7位數字作為流水號
        from sqlalchemy import text
        prefix_len = len(prefix)  # 乾坤測字第 = 5個字
        year_len = len(str(roc_year))  # 115 = 3位

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
        import logging
        logging.error(f"取得下一個字號失敗: {e}")
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


@router.post("/create", response_model=DocumentNumberItem)
@limiter.limit("30/minute")
async def create_document_number(
    http_request: Request,
    response: Response,
    request: DocumentNumberCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """建立新發文字號 (POST-only)"""
    try:
        # 取得下一個字號
        next_num = await get_next_document_number(http_request, response, NextNumberRequest(), db)

        # 處理日期
        doc_date = None
        if request.doc_date:
            try:
                doc_date = datetime.strptime(request.doc_date, '%Y-%m-%d').date()
            except ValueError:
                doc_date = date.today()
        else:
            doc_date = date.today()

        # 建立公文記錄
        new_doc = OfficialDocument(
            doc_number=next_num.full_number,
            doc_type='發文',
            category='發文',
            subject=request.subject,
            receiver=request.receiver,
            contract_project_id=request.contract_case_id,
            doc_date=doc_date,
            status=request.status,
        )

        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        # 載入關聯
        if new_doc.contract_project_id:
            await db.execute(
                select(ContractProject).where(
                    ContractProject.id == new_doc.contract_project_id
                )
            )

        contract_case_name = ""
        if new_doc.contract_project:
            contract_case_name = new_doc.contract_project.project_name or ""

        return DocumentNumberItem(
            id=new_doc.id,
            doc_prefix=DEFAULT_DOC_PREFIX,
            year=doc_date.year if doc_date else datetime.now().year,
            sequence_number=next_num.sequence_number,
            full_number=new_doc.doc_number or "",
            subject=new_doc.subject or "",
            contract_case=contract_case_name,
            contract_case_id=new_doc.contract_project_id,
            receiver=new_doc.receiver or "",
            doc_date=str(doc_date) if doc_date else None,
            status=new_doc.status or "draft",
            created_at=str(new_doc.created_at) if new_doc.created_at else None
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"建立發文字號失敗: {str(e)}")


@router.post("/update/{document_id}", response_model=DocumentNumberItem)
@limiter.limit("30/minute")
async def update_document_number(
    document_id: int,
    http_request: Request,
    response: Response,
    request: DocumentNumberUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """更新發文字號 (POST-only)"""
    try:
        # 查詢現有記錄
        result = await db.execute(
            select(OfficialDocument)
            .options(selectinload(OfficialDocument.contract_project))
            .where(OfficialDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="發文字號不存在")

        # 更新欄位
        if request.subject is not None:
            doc.subject = request.subject
        if request.receiver is not None:
            doc.receiver = request.receiver
        if request.contract_case_id is not None:
            doc.contract_project_id = request.contract_case_id
        if request.doc_date is not None:
            try:
                doc.doc_date = datetime.strptime(request.doc_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        if request.status is not None:
            doc.status = request.status

        await db.commit()
        await db.refresh(doc)

        # 解析文號
        doc_number = doc.doc_number or ""
        sequence_number = 0
        if doc_number:
            parts = doc_number.split('字第')
            if len(parts) >= 2:
                number_part = parts[1].replace('號', '')
                try:
                    sequence_number = int(number_part)
                except ValueError:
                    pass

        contract_case_name = ""
        if doc.contract_project:
            contract_case_name = doc.contract_project.project_name or ""

        return DocumentNumberItem(
            id=doc.id,
            doc_prefix=DEFAULT_DOC_PREFIX,
            year=doc.doc_date.year if doc.doc_date else datetime.now().year,
            sequence_number=sequence_number,
            full_number=doc_number,
            subject=doc.subject or "",
            contract_case=contract_case_name,
            contract_case_id=doc.contract_project_id,
            receiver=doc.receiver or "",
            doc_date=str(doc.doc_date) if doc.doc_date else None,
            status=doc.status or "draft",
            created_at=str(doc.created_at) if doc.created_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新發文字號失敗: {str(e)}")


@router.post("/delete/{document_id}")
@limiter.limit("30/minute")
async def delete_document_number(
    document_id: int,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """刪除發文字號 (POST-only，軟刪除)"""
    try:
        result = await db.execute(
            select(OfficialDocument).where(OfficialDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="發文字號不存在")

        # 軟刪除：將狀態改為 archived
        doc.status = 'archived'
        await db.commit()

        return {"success": True, "message": "發文字號已歸檔"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"刪除發文字號失敗: {str(e)}")


# =============================================================================
# 向後相容的 GET 端點 (將逐步棄用)
# =============================================================================

@router.post("", response_model=DocumentNumberListResponse, deprecated=True,
              summary="[相容] 取得發文字號列表 (預計 2026-07 移除)")
@limiter.limit("60/minute")
async def get_document_numbers_legacy(
    request: Request,
    response: Response,
    page: int = 1,
    per_page: int = 20,
    year: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    [已棄用] 取得發文字號列表

    ⚠️ **預計廢止日期**: 2026-07
    請改用 POST /document-numbers/query
    """
    query_request = DocumentNumberQueryRequest(
        page=page,
        limit=per_page,
        year=year,
        status=status,
        keyword=keyword
    )
    return await query_document_numbers(request, response, query_request, db)


@router.post("/stats", response_model=DocumentNumberStats, deprecated=True,
              summary="[相容] 取得統計資料 (預計 2026-07 移除)")
@limiter.limit("60/minute")
async def get_stats_legacy(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    [已棄用] 取得統計資料

    ⚠️ **預計廢止日期**: 2026-07
    請改用 POST /document-numbers/stats
    """
    return await get_document_numbers_stats(request, response, db)


@router.post("/next-number", response_model=NextNumberResponse, deprecated=True,
              summary="[相容] 取得下一個字號 (預計 2026-07 移除)")
@limiter.limit("60/minute")
async def get_next_number_legacy(
    request: Request,
    response: Response,
    prefix: Optional[str] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    [已棄用] 取得下一個字號

    ⚠️ **預計廢止日期**: 2026-07
    請改用 POST /document-numbers/next-number
    """
    next_request = NextNumberRequest(prefix=prefix, year=year)
    return await get_next_document_number(request, response, next_request, db)
