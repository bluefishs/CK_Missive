"""
案件管理API端點 (非同步化)
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.extended.models import User

router = APIRouter()

@router.get("/", summary="查詢案件列表")
async def get_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """查詢案件列表 (模擬)"""
    return {
        "items": [
            {
                "id": 1,
                "case_number": "CASE-2025-001",
                "case_name": "測試案件",
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
        ],
        "total": 1
    }

@router.get("/{case_id}", summary="取得案件詳情")
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得案件詳細資訊 (模擬)"""
    return {
        "id": case_id,
        "case_number": "CASE-2025-001", 
        "case_name": "測試案件",
        "description": "案件描述...",
        "status": "active"
    }

@router.post("/", summary="建立新案件")
async def create_case(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """建立新案件 (模擬)"""
    return {"id": 2, "message": "案件建立成功"}
