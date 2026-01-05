#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
發文字號管理API端點
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, desc, extract
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import OfficialDocument
from pydantic import BaseModel

router = APIRouter()

class DocumentNumberResponse(BaseModel):
    id: int
    doc_prefix: str
    year: int
    sequence_number: int
    full_number: str
    subject: str
    contract_case: str
    receiver: str
    doc_date: str
    status: str

class DocumentNumberListResponse(BaseModel):
    items: List[DocumentNumberResponse]
    total: int
    page: int
    per_page: int

class YearlyStats(BaseModel):
    year: int
    count: int

class YearRange(BaseModel):
    min_year: Optional[int] = None
    max_year: Optional[int] = None

class DocumentNumberStats(BaseModel):
    total_count: int
    draft_count: int
    sent_count: int
    max_sequence: int
    year_range: YearRange
    yearly_stats: List[YearlyStats]

class NextNumberResponse(BaseModel):
    next_number: str
    year: int
    sequence: int

@router.get("", response_model=DocumentNumberListResponse)
async def get_document_numbers(
    page: int = Query(1, ge=1, description="頁數"),
    per_page: int = Query(20, ge=1, le=100, description="每頁筆數"),
    year: Optional[int] = Query(None, description="年度篩選"),
    status: Optional[str] = Query(None, description="狀態篩選"),
    keyword: Optional[str] = Query(None, description="關鍵字搜尋"),
    db: AsyncSession = Depends(get_async_db)
):
    """取得發文字號列表"""
    
    try:
        # 基本查詢
        query = select(OfficialDocument)
        
        # 篩選條件
        if year:
            query = query.where(extract('year', OfficialDocument.doc_date) == year)
        
        if status:
            query = query.where(OfficialDocument.status == status)
            
        if keyword:
            query = query.where(
                OfficialDocument.subject.contains(keyword) |
                OfficialDocument.doc_number.contains(keyword) |
                OfficialDocument.receiver.contains(keyword)
            )
        
        # 總數
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分頁
        offset = (page - 1) * per_page
        query = query.options(selectinload(OfficialDocument.contract_project))
        query = query.offset(offset).limit(per_page)
        query = query.order_by(desc(OfficialDocument.doc_date))
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # 轉換為回應格式
        items = []
        for doc in documents:
            # 從文號中提取前綴和序號
            doc_number = doc.doc_number or ""
            doc_prefix = ""
            sequence_number = 0
            year_num = doc.doc_date.year if doc.doc_date else 2024
            
            # 簡單的文號解析
            if doc_number:
                parts = doc_number.split('字第')
                if len(parts) >= 2:
                    doc_prefix = parts[0] + '字第'
                    number_part = parts[1].replace('號', '')
                    try:
                        sequence_number = int(number_part)
                    except:
                        sequence_number = 0
            
            # 取得關聯的案件名稱
            contract_case_name = ""
            if doc.contract_project:
                contract_case_name = doc.contract_project.project_name or ""

            items.append(DocumentNumberResponse(
                id=doc.id,
                doc_prefix=doc_prefix,
                year=year_num,
                sequence_number=sequence_number,
                full_number=doc_number,
                subject=doc.subject or "",
                contract_case=contract_case_name,
                receiver=doc.receiver or "",
                doc_date=str(doc.doc_date) if doc.doc_date else "",
                status=doc.status or "draft"
            ))
        
        return DocumentNumberListResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢發文字號失敗: {str(e)}")

@router.get("/stats", response_model=DocumentNumberStats)
async def get_document_numbers_stats(
    db: AsyncSession = Depends(get_async_db)
):
    """取得發文字號統計資料"""
    
    try:
        # 總數
        total_query = select(func.count()).select_from(OfficialDocument)
        total_result = await db.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # 已發送總數
        sent_query = select(func.count()).select_from(
            select(OfficialDocument).where(
                OfficialDocument.status == 'sent'
            ).subquery()
        )
        sent_result = await db.execute(sent_query)
        sent_count = sent_result.scalar() or 0
        
        # 草稿總數
        draft_query = select(func.count()).select_from(
            select(OfficialDocument).where(
                OfficialDocument.status == 'draft'
            ).subquery()
        )
        draft_result = await db.execute(draft_query)
        draft_count = draft_result.scalar() or 0
        
        # 年度範圍
        year_range_query = select(
            func.min(extract('year', OfficialDocument.doc_date)),
            func.max(extract('year', OfficialDocument.doc_date))
        ).where(OfficialDocument.doc_date.isnot(None))
        year_range_result = await db.execute(year_range_query)
        min_year, max_year = year_range_result.first() or (None, None)
        
        # 年度統計
        yearly_stats_query = select(
            extract('year', OfficialDocument.doc_date).label('year'),
            func.count().label('count')
        ).where(
            OfficialDocument.doc_date.isnot(None)
        ).group_by(
            extract('year', OfficialDocument.doc_date)
        ).order_by(
            desc('year')
        )
        yearly_stats_result = await db.execute(yearly_stats_query)
        yearly_data = yearly_stats_result.all()
        
        yearly_stats = [
            YearlyStats(year=int(row.year), count=row.count) 
            for row in yearly_data
        ]
        
        # 最大序號 (簡化處理)
        max_sequence = 0
        if yearly_data:
            max_sequence = max(row.count for row in yearly_data)
        
        return DocumentNumberStats(
            total_count=total_count,
            draft_count=draft_count,
            sent_count=sent_count,
            max_sequence=max_sequence,
            year_range=YearRange(
                min_year=int(min_year) if min_year else None,
                max_year=int(max_year) if max_year else None
            ),
            yearly_stats=yearly_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資料失敗: {str(e)}")

@router.get("/next-number", response_model=NextNumberResponse)
async def get_next_document_number(
    prefix: Optional[str] = Query("南投縣建設字第", description="文號前綴"),
    year: Optional[int] = Query(None, description="指定年度 (預設為當前年度)"),
    db: AsyncSession = Depends(get_async_db)
):
    """取得下一個可用的發文字號"""

    try:
        current_year = year or datetime.now().year
        
        # 查詢當年度最大序號
        query = select(func.max(
            func.cast(
                func.regexp_replace(
                    func.regexp_replace(OfficialDocument.doc_number, r'.*字第', ''),
                    r'號.*', ''
                ), 
                'INTEGER'
            )
        )).where(
            extract('year', OfficialDocument.doc_date) == current_year
        ).where(
            OfficialDocument.doc_number.like(f'{prefix}%')
        )
        
        result = await db.execute(query)
        max_sequence = result.scalar() or 0
        
        next_sequence = max_sequence + 1
        next_number = f"{prefix}{next_sequence:010d}號"
        
        return NextNumberResponse(
            next_number=next_number,
            year=current_year,
            sequence=next_sequence
        )
        
    except Exception:
        # 如果查詢失敗，返回默認的下一個號碼
        fallback_year = year or datetime.now().year
        next_sequence = 1
        next_number = f"{prefix}{next_sequence:010d}號"

        return NextNumberResponse(
            next_number=next_number,
            year=fallback_year,
            sequence=next_sequence
        )