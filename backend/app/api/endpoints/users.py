"""
使用者管理API端點 (非同步化)
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_async_db
from app.extended.models import User

router = APIRouter()

@router.get("/", summary="查詢使用者列表")
async def get_users(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(20, ge=1, le=100, description="每頁筆數"),
    role: Optional[str] = Query(None, description="角色篩選"),
    is_active: Optional[bool] = Query(None, description="啟用狀態"),
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    db: AsyncSession = Depends(get_async_db)
):
    """查詢使用者列表，支援分頁與篩選"""
    try:
        # 建立基本查詢
        query = select(User)
        count_query = select(func.count()).select_from(User)

        # 篩選條件
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # 取得總數
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分頁並執行查詢
        query = query.offset(skip).limit(limit).order_by(User.id)
        result = await db.execute(query)
        users = result.scalars().all()

        # 轉換為回應格式
        items = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role or "user",
                "is_active": user.is_active if user.is_active is not None else True,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]

        return {
            "items": items,
            "total": total,
            "page": skip // limit + 1 if limit > 0 else 1,
            "page_size": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 1
        }
    except Exception as e:
        # 發生錯誤時返回空列表
        print(f"查詢使用者列表錯誤: {e}")
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0
        }

@router.get("/{user_id}", summary="取得使用者詳情")
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """取得指定使用者的詳細資訊 (模擬)"""
    return {
        "id": user_id,
        "username": "admin",
        "email": "admin@ckyuanda.com.tw",
        "full_name": "系統管理員",
        "role": "admin",
        "is_active": True,
        "last_login": datetime.now().isoformat(),
    }

@router.post("/", summary="建立新使用者")
async def create_user(db: AsyncSession = Depends(get_async_db)):
    """建立新使用者 (模擬)"""
    return {"id": 3, "message": "使用者建立成功"}

@router.put("/{user_id}", summary="更新使用者")
async def update_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """更新指定使用者的資訊 (模擬)"""
    return {"message": f"使用者 {user_id} 更新成功"}

@router.delete("/{user_id}", summary="刪除使用者")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """刪除指定使用者 (模擬)"""
    return {"message": f"使用者 {user_id} 刪除成功"}

@router.put("/{user_id}/status", summary="修改使用者狀態")
async def update_user_status(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """啟用或停用使用者 (模擬)"""
    return {"message": f"使用者 {user_id} 狀態修改成功"}

@router.put("/{user_id}/password", summary="重設使用者密碼")
async def reset_user_password(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """重設指定使用者的密碼 (模擬)"""
    return {"message": f"使用者 {user_id} 密碼重設成功"}
