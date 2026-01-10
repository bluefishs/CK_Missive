#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件與承辦同仁關聯管理API端點 (POST-only 資安機制)
所有端點需要認證。
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.extended.models import ContractProject, User, project_user_assignment
from app.schemas.project_staff import (
    ProjectStaffCreate,
    ProjectStaffUpdate,
    ProjectStaffResponse,
    ProjectStaffListResponse
)

router = APIRouter()


# ========== 查詢參數 Schema ==========
class StaffListQuery(BaseModel):
    """承辦同仁列表查詢參數"""
    skip: int = 0
    limit: int = 100
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    status: Optional[str] = None


# ========== POST-only API 端點 ==========

@router.post("", summary="建立案件與承辦同仁關聯")
async def create_project_staff_assignment(
    assignment_data: ProjectStaffCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """建立案件與承辦同仁關聯"""

    # 檢查案件是否存在
    project_query = select(ContractProject).where(
        ContractProject.id == assignment_data.project_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="承攬案件不存在")

    # 檢查使用者是否存在
    user_query = select(User).where(User.id == assignment_data.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")

    # 檢查是否已存在關聯
    existing_query = select(project_user_assignment).where(
        (project_user_assignment.c.project_id == assignment_data.project_id) &
        (project_user_assignment.c.user_id == assignment_data.user_id)
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.fetchone()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="該同仁已與此案件建立關聯"
        )

    # 建立關聯
    insert_stmt = insert(project_user_assignment).values(
        project_id=assignment_data.project_id,
        user_id=assignment_data.user_id,
        role=assignment_data.role or 'member',
        is_primary=assignment_data.is_primary,
        start_date=assignment_data.start_date,
        end_date=assignment_data.end_date,
        status=assignment_data.status or 'active',
        notes=assignment_data.notes
    )

    await db.execute(insert_stmt)
    await db.commit()

    return {
        "message": "案件與承辦同仁關聯建立成功",
        "project_id": assignment_data.project_id,
        "user_id": assignment_data.user_id
    }


@router.post("/project/{project_id}/list", response_model=ProjectStaffListResponse, summary="取得案件承辦同仁列表")
async def get_project_staff_assignments(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得特定案件的所有承辦同仁"""

    # 檢查案件是否存在
    project_query = select(ContractProject).where(ContractProject.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="承攬案件不存在")

    # 查詢關聯資料
    query = select(
        project_user_assignment.c.id,
        project_user_assignment.c.project_id,
        project_user_assignment.c.user_id,
        project_user_assignment.c.role,
        project_user_assignment.c.is_primary,
        project_user_assignment.c.start_date,
        project_user_assignment.c.end_date,
        project_user_assignment.c.status,
        project_user_assignment.c.notes,
        User.full_name,
        User.email,
        User.username
    ).select_from(
        project_user_assignment.join(
            User,
            project_user_assignment.c.user_id == User.id
        )
    ).where(project_user_assignment.c.project_id == project_id)

    result = await db.execute(query)
    assignments_data = result.fetchall()

    staff = []
    for row in assignments_data:
        staff.append(ProjectStaffResponse(
            id=row.id,
            project_id=row.project_id,
            user_id=row.user_id,
            user_name=row.full_name or row.username,
            user_email=row.email,
            department=None,
            phone=None,
            role=row.role,
            is_primary=row.is_primary or False,
            start_date=row.start_date,
            end_date=row.end_date,
            status=row.status,
            notes=row.notes,
            created_at=None,
            updated_at=None
        ))

    return ProjectStaffListResponse(
        project_id=project_id,
        project_name=project.project_name,
        staff=staff,
        total=len(staff)
    )


@router.post("/project/{project_id}/user/{user_id}/update", summary="更新案件與承辦同仁關聯")
async def update_project_staff_assignment(
    project_id: int,
    user_id: int,
    assignment_data: ProjectStaffUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """更新案件與承辦同仁關聯資訊"""

    # 檢查關聯是否存在
    check_query = select(project_user_assignment).where(
        (project_user_assignment.c.project_id == project_id) &
        (project_user_assignment.c.user_id == user_id)
    )
    check_result = await db.execute(check_query)
    existing = check_result.fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="案件與承辦同仁關聯不存在")

    # 更新關聯資料
    update_data = assignment_data.model_dump(exclude_unset=True)
    if update_data:
        update_stmt = update(project_user_assignment).where(
            (project_user_assignment.c.project_id == project_id) &
            (project_user_assignment.c.user_id == user_id)
        ).values(**update_data)

        await db.execute(update_stmt)
        await db.commit()

    return {
        "message": "案件與承辦同仁關聯更新成功",
        "project_id": project_id,
        "user_id": user_id
    }


@router.post("/project/{project_id}/user/{user_id}/delete", summary="刪除案件與承辦同仁關聯")
async def delete_project_staff_assignment(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """刪除案件與承辦同仁關聯"""

    # 檢查關聯是否存在
    check_query = select(project_user_assignment).where(
        (project_user_assignment.c.project_id == project_id) &
        (project_user_assignment.c.user_id == user_id)
    )
    check_result = await db.execute(check_query)
    existing = check_result.fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="案件與承辦同仁關聯不存在")

    # 刪除關聯
    delete_stmt = delete(project_user_assignment).where(
        (project_user_assignment.c.project_id == project_id) &
        (project_user_assignment.c.user_id == user_id)
    )

    await db.execute(delete_stmt)
    await db.commit()

    return {
        "message": "案件與承辦同仁關聯已成功刪除",
        "project_id": project_id,
        "user_id": user_id
    }


@router.post("/list", summary="取得所有承辦同仁關聯列表")
async def get_all_staff_assignments(
    query: StaffListQuery = Body(default=StaffListQuery()),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得所有案件與承辦同仁關聯列表"""

    db_query = select(
        project_user_assignment.c.id,
        project_user_assignment.c.project_id,
        project_user_assignment.c.user_id,
        project_user_assignment.c.role,
        project_user_assignment.c.is_primary,
        project_user_assignment.c.start_date,
        project_user_assignment.c.end_date,
        project_user_assignment.c.status,
        project_user_assignment.c.notes,
        ContractProject.project_name,
        ContractProject.project_code,
        User.full_name,
        User.email,
        User.username
    ).select_from(
        project_user_assignment.join(
            ContractProject,
            project_user_assignment.c.project_id == ContractProject.id
        ).join(
            User,
            project_user_assignment.c.user_id == User.id
        )
    )

    # 篩選條件
    if query.project_id:
        db_query = db_query.where(project_user_assignment.c.project_id == query.project_id)

    if query.user_id:
        db_query = db_query.where(project_user_assignment.c.user_id == query.user_id)

    if query.status:
        db_query = db_query.where(project_user_assignment.c.status == query.status)

    # 分頁
    db_query = db_query.offset(query.skip).limit(query.limit)

    result = await db.execute(db_query)
    assignments_data = result.fetchall()

    assignments = []
    for row in assignments_data:
        assignments.append({
            "id": row.id,
            "project_id": row.project_id,
            "project_name": row.project_name,
            "project_code": row.project_code,
            "user_id": row.user_id,
            "user_name": row.full_name or row.username,
            "user_email": row.email,
            "role": row.role,
            "is_primary": row.is_primary,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "status": row.status,
            "notes": row.notes
        })

    return {
        "assignments": assignments,
        "total": len(assignments),
        "skip": query.skip,
        "limit": query.limit
    }
