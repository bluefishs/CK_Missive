"""
使用者管理API端點 (非同步化)
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_async_db

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
    """查詢使用者列表，支援分頁與篩選 (模擬)"""
    return {
        "items": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@ckyuanda.com.tw",
                "full_name": "系統管理員",
                "role": "admin",
                "is_active": True,
                "last_login": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
        ],
        "total": 1,
        "page": skip // limit + 1,
        "page_size": limit,
        "total_pages": 1
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
