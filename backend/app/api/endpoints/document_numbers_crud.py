#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
發文字號管理 API - CRUD 端點

包含端點：
- POST /document-numbers/create - 建立新發文字號
- POST /document-numbers/update/{id} - 更新發文字號
- POST /document-numbers/delete/{id} - 刪除發文字號 (軟刪除)

拆分自 document_numbers.py

⚠️ 此模組已棄用 (DEPRECATED) — 將於 v4.0.0 移除

@version 1.0.0
@date 2026-03-30
"""

import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response
from sqlalchemy import select

from app.core.rate_limiter import limiter
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import OfficialDocument, ContractProject, User
from app.core.config import settings
from app.core.dependencies import require_auth

from app.schemas.document_number import (
    DocumentNumberItem,
    NextNumberRequest,
    DocumentNumberCreateRequest,
    DocumentNumberUpdateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_DOC_PREFIX = getattr(settings, 'DOC_NUMBER_PREFIX', '乾坤測字第')


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
        # 取得下一個字號 — 匯入查詢邏輯避免循環依賴
        from app.api.endpoints.document_numbers import get_next_document_number
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
        logger.error(f"建立發文字號失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="建立發文字號失敗，請稍後再試")


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
        logger.error(f"更新發文字號失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新發文字號失敗，請稍後再試")


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
        logger.error(f"刪除發文字號失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="刪除發文字號失敗，請稍後再試")
