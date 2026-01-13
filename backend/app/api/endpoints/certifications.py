"""
證照管理 API 端點

支援承辦同仁證照 CRUD 操作
所有端點皆使用 POST 方法（安全性考量）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from typing import Optional
from datetime import datetime

from app.db.database import get_async_db
from app.extended.models import StaffCertification, User
from app.schemas.certification import (
    CertificationCreate,
    CertificationUpdate,
    CertificationResponse,
    CertificationListResponse,
    CertificationListParams,
)
from app.schemas.common import PaginationMeta
from app.api.response_helper import (
    success_response,
    error_response,
)

router = APIRouter()


@router.post("/create", response_model=dict)
async def create_certification(
    data: CertificationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    新增證照紀錄
    """
    try:
        # 檢查使用者是否存在
        result = await db.execute(select(User).filter(User.id == data.user_id))
        user = result.scalar_one_or_none()
        if not user:
            return error_response("找不到指定的使用者", code=404)

        # 建立證照紀錄
        certification = StaffCertification(
            user_id=data.user_id,
            cert_type=data.cert_type,
            cert_name=data.cert_name,
            issuing_authority=data.issuing_authority,
            cert_number=data.cert_number,
            issue_date=data.issue_date,
            expiry_date=data.expiry_date,
            status=data.status,
            notes=data.notes,
        )

        db.add(certification)
        await db.commit()
        await db.refresh(certification)

        return success_response(
            data=CertificationResponse.model_validate(certification).model_dump(),
            message="證照新增成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(f"新增證照失敗: {str(e)}")


@router.post("/user/{user_id}/list", response_model=dict)
async def get_user_certifications(
    user_id: int,
    params: Optional[CertificationListParams] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得指定使用者的證照列表
    """
    try:
        if params is None:
            params = CertificationListParams()

        # 檢查使用者是否存在
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return error_response("找不到指定的使用者", code=404)

        # 建立查詢
        query = select(StaffCertification).filter(StaffCertification.user_id == user_id)

        # 證照類型篩選
        if params.cert_type:
            query = query.filter(StaffCertification.cert_type == params.cert_type)

        # 狀態篩選
        if params.status:
            query = query.filter(StaffCertification.status == params.status)

        # 關鍵字搜尋
        if params.keyword:
            keyword = f"%{params.keyword}%"
            query = query.filter(
                or_(
                    StaffCertification.cert_name.ilike(keyword),
                    StaffCertification.issuing_authority.ilike(keyword),
                    StaffCertification.cert_number.ilike(keyword),
                )
            )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分頁
        offset = (params.page - 1) * params.page_size
        query = query.order_by(StaffCertification.created_at.desc()) \
            .offset(offset).limit(params.page_size)

        result = await db.execute(query)
        certifications = result.scalars().all()

        # 轉換為回應格式
        items = [CertificationResponse.model_validate(c).model_dump() for c in certifications]

        return success_response(
            data={
                "items": items,
                "pagination": {
                    "total": total,
                    "page": params.page,
                    "page_size": params.page_size,
                    "total_pages": (total + params.page_size - 1) // params.page_size
                }
            }
        )

    except Exception as e:
        return error_response(f"取得證照列表失敗: {str(e)}")


@router.post("/{cert_id}/detail", response_model=dict)
async def get_certification_detail(
    cert_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得證照詳情
    """
    try:
        result = await db.execute(
            select(StaffCertification).filter(StaffCertification.id == cert_id)
        )
        certification = result.scalar_one_or_none()

        if not certification:
            return error_response("找不到指定的證照", code=404)

        return success_response(
            data=CertificationResponse.model_validate(certification).model_dump()
        )

    except Exception as e:
        return error_response(f"取得證照詳情失敗: {str(e)}")


@router.post("/{cert_id}/update", response_model=dict)
async def update_certification(
    cert_id: int,
    data: CertificationUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    更新證照紀錄
    """
    try:
        result = await db.execute(
            select(StaffCertification).filter(StaffCertification.id == cert_id)
        )
        certification = result.scalar_one_or_none()

        if not certification:
            return error_response("找不到指定的證照", code=404)

        # 更新非空欄位
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            setattr(certification, field, value)

        certification.updated_at = datetime.now()

        await db.commit()
        await db.refresh(certification)

        return success_response(
            data=CertificationResponse.model_validate(certification).model_dump(),
            message="證照更新成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(f"更新證照失敗: {str(e)}")


@router.post("/{cert_id}/delete", response_model=dict)
async def delete_certification(
    cert_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    刪除證照紀錄
    """
    try:
        result = await db.execute(
            select(StaffCertification).filter(StaffCertification.id == cert_id)
        )
        certification = result.scalar_one_or_none()

        if not certification:
            return error_response("找不到指定的證照", code=404)

        await db.delete(certification)
        await db.commit()

        return success_response(message="證照刪除成功")

    except Exception as e:
        await db.rollback()
        return error_response(f"刪除證照失敗: {str(e)}")


@router.post("/stats/{user_id}", response_model=dict)
async def get_certification_stats(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得使用者證照統計
    """
    try:
        # 檢查使用者是否存在
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return error_response("找不到指定的使用者", code=404)

        # 統計各類型證照數量
        type_query = select(
            StaffCertification.cert_type,
            func.count(StaffCertification.id).label('count')
        ).filter(
            StaffCertification.user_id == user_id
        ).group_by(StaffCertification.cert_type)

        type_result = await db.execute(type_query)
        stats = type_result.all()

        # 統計各狀態證照數量
        status_query = select(
            StaffCertification.status,
            func.count(StaffCertification.id).label('count')
        ).filter(
            StaffCertification.user_id == user_id
        ).group_by(StaffCertification.status)

        status_result = await db.execute(status_query)
        status_stats = status_result.all()

        return success_response(data={
            "by_type": {row.cert_type: row.count for row in stats},
            "by_status": {row.status: row.count for row in status_stats},
            "total": sum(row.count for row in stats),
        })

    except Exception as e:
        return error_response(f"取得證照統計失敗: {str(e)}")
