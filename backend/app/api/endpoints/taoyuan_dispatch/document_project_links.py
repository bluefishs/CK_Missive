"""
桃園派工系統 - 公文-工程關聯 API

直接關聯（不經過派工單）

包含端點：
- /document/{document_id}/project-links - 查詢公文關聯的工程
- /document/{document_id}/link-project - 將公文關聯到工程
- /document/{document_id}/unlink-project/{link_id} - 移除公文與工程的關聯
- /documents/batch-project-links - 批次查詢多筆公文的工程關聯
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .common import (
    get_async_db, require_auth,
    TaoyuanProject, TaoyuanDocumentProjectLink, Document
)

router = APIRouter()


@router.post("/document/{document_id}/project-links", summary="查詢公文關聯的工程")
async def get_document_project_links(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    以公文為主體，查詢該公文直接關聯的所有工程
    用於「工程關聯」Tab 顯示已關聯的工程
    """
    result = await db.execute(
        select(TaoyuanDocumentProjectLink)
        .options(selectinload(TaoyuanDocumentProjectLink.project))
        .where(TaoyuanDocumentProjectLink.document_id == document_id)
    )
    links = result.scalars().all()

    projects = []
    for link in links:
        if link.project:
            proj = link.project
            projects.append({
                'link_id': link.id,
                'link_type': link.link_type,
                'notes': link.notes,
                'project_id': proj.id,
                'project_name': proj.project_name,
                'district': proj.district,
                'review_year': proj.review_year,
                'case_type': proj.case_type,
                'sub_case_name': proj.sub_case_name,
                'case_handler': proj.case_handler,
                'survey_unit': proj.survey_unit,
                'start_point': proj.start_point,
                'end_point': proj.end_point,
                'road_length': float(proj.road_length) if proj.road_length else None,
                'current_width': float(proj.current_width) if proj.current_width else None,
                'planned_width': float(proj.planned_width) if proj.planned_width else None,
                'review_result': proj.review_result,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            })

    return {
        "success": True,
        "document_id": document_id,
        "projects": projects,
        "total": len(projects)
    }


@router.post("/document/{document_id}/link-project", summary="將公文關聯到工程")
async def link_project_to_document(
    document_id: int,
    project_id: int,
    link_type: str = 'agency_incoming',
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    以公文為主體，將公文直接關聯到指定的工程（不經過派工單）

    link_type:
    - agency_incoming: 機關來函
    - company_outgoing: 乾坤發文
    """
    # 檢查公文是否存在
    doc = await db.execute(select(Document).where(Document.id == document_id))
    if not doc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="公文不存在")

    # 檢查工程是否存在
    proj = await db.execute(select(TaoyuanProject).where(TaoyuanProject.id == project_id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="工程不存在")

    # 檢查是否已存在關聯
    existing = await db.execute(
        select(TaoyuanDocumentProjectLink).where(
            TaoyuanDocumentProjectLink.document_id == document_id,
            TaoyuanDocumentProjectLink.taoyuan_project_id == project_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此關聯已存在")

    # 建立關聯
    link = TaoyuanDocumentProjectLink(
        document_id=document_id,
        taoyuan_project_id=project_id,
        link_type=link_type,
        notes=notes
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return {
        "success": True,
        "message": "關聯成功",
        "link_id": link.id
    }


@router.post("/document/{document_id}/unlink-project/{link_id}", summary="移除公文與工程的關聯")
async def unlink_project_from_document(
    document_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    移除公文與工程的直接關聯

    參數說明：
    - document_id: OfficialDocument.id（公文 ID）
    - link_id: TaoyuanDocumentProjectLink.id（關聯記錄 ID，非工程 ID）
    """
    result = await db.execute(
        select(TaoyuanDocumentProjectLink).where(
            TaoyuanDocumentProjectLink.id == link_id,
            TaoyuanDocumentProjectLink.document_id == document_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        # 提供更詳細的錯誤訊息
        link_by_id = await db.execute(
            select(TaoyuanDocumentProjectLink).where(TaoyuanDocumentProjectLink.id == link_id)
        )
        existing_link = link_by_id.scalar_one_or_none()
        if existing_link:
            raise HTTPException(
                status_code=404,
                detail=f"關聯不存在：link_id={link_id} 對應的公文 ID 是 {existing_link.document_id}，而非傳入的 {document_id}"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"關聯記錄 ID {link_id} 不存在。請確認傳入的是 link_id（關聯記錄 ID），而非工程 ID"
            )

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/documents/batch-project-links", summary="批次查詢多筆公文的工程關聯")
async def get_batch_document_project_links(
    document_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    批次查詢多筆公文的工程關聯
    用於「工程關聯」Tab 一次載入所有公文的關聯狀態
    """
    result = await db.execute(
        select(TaoyuanDocumentProjectLink)
        .options(selectinload(TaoyuanDocumentProjectLink.project))
        .where(TaoyuanDocumentProjectLink.document_id.in_(document_ids))
    )
    links = result.scalars().all()

    # 按公文 ID 分組
    links_by_doc = {}
    for link in links:
        doc_id = link.document_id
        if doc_id not in links_by_doc:
            links_by_doc[doc_id] = []
        if link.project:
            links_by_doc[doc_id].append({
                'link_id': link.id,
                'link_type': link.link_type,
                'project_id': link.project.id,
                'project_name': link.project.project_name,
                'district': link.project.district,
            })

    return {
        "success": True,
        "links": links_by_doc
    }
