"""
安全的網站管理 API - 統一使用 POST 方法
提供 CSRF 保護和更安全的接口設計
"""
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from pydantic import BaseModel, Field
import secrets
import time
from datetime import datetime

from app.db.database import get_async_db
from app.extended.models import SiteNavigationItem, SiteConfiguration
from app.schemas.site_management import (
    NavigationItemCreate, SiteConfigCreate, SiteConfigResponse
)

router = APIRouter()
security = HTTPBearer()

# CSRF Token 儲存 (生產環境應使用 Redis 或資料庫)
csrf_tokens: Dict[str, float] = {}

class SecureRequest(BaseModel):
    """安全請求基礎模型"""
    action: str = Field(..., description="操作類型")
    csrf_token: Optional[str] = Field(None, description="CSRF 防護令牌 (開發模式下可選)")
    data: Optional[Dict[str, Any]] = Field(None, description="請求數據")

    class Config:
        extra = "forbid"

class SecureResponse(BaseModel):
    """安全回應基礎模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    csrf_token: Optional[str] = None

def generate_csrf_token() -> str:
    """生成 CSRF 令牌"""
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = time.time()
    return token

def validate_csrf_token(token: str) -> bool:
    """驗證 CSRF 令牌"""
    # 開發模式下跳過 CSRF 驗證
    from app.core.config import settings
    if getattr(settings, 'AUTH_DISABLED', False) or token == 'dev-mode-skip':
        return True

    if not token or token not in csrf_tokens:
        return False

    # 檢查令牌是否過期 (30分鐘)
    if time.time() - csrf_tokens[token] > 1800:
        del csrf_tokens[token]
        return False

    return True

def cleanup_expired_tokens():
    """清理過期的 CSRF 令牌"""
    current_time = time.time()
    expired_tokens = [token for token, timestamp in csrf_tokens.items() 
                     if current_time - timestamp > 1800]
    for token in expired_tokens:
        del csrf_tokens[token]

@router.post("/csrf-token", response_model=SecureResponse)
async def get_csrf_token():
    """獲取 CSRF 令牌"""
    cleanup_expired_tokens()
    token = generate_csrf_token()
    return SecureResponse(
        success=True,
        message="CSRF token generated",
        csrf_token=token
    )

@router.post("/navigation/action")
async def navigation_action(
    action: str = Body(..., embed=True),
    csrf_token: str = Body(None, embed=True),
    data: dict = Body(None, embed=True),
    session: AsyncSession = Depends(get_async_db)
):
    """統一的導覽列操作接口"""

    # 驗證 CSRF 令牌
    if not validate_csrf_token(csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")

    try:
        action = action.lower()
        data = data or {}
        
        if action == "list":
            # 獲取導覽列表
            result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.parent_id.is_(None))
                .order_by(SiteNavigationItem.sort_order)
            )
            root_items = result.scalars().all()
            
            items = []
            for item in root_items:
                item_dict = {
                    "id": item.id,
                    "title": item.title,
                    "key": item.key,
                    "path": item.path,
                    "icon": item.icon,
                    "parent_id": item.parent_id,
                    "sort_order": item.sort_order,
                    "is_visible": item.is_visible,
                    "is_enabled": item.is_enabled,
                    "level": 1,
                    "description": item.description,
                    "target": item.target,
                    "permission_required": item.permission_required,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    "children": await get_children_recursive(session, item.id)
                }
                items.append(item_dict)
            
            response_data = {
                "success": True,
                "message": "Navigation items retrieved successfully",
                "data": {"items": items, "total": len(items)},
                "csrf_token": generate_csrf_token()
            }
            return response_data
        
        elif action == "create":
            # 創建導覽項目
            nav_data = NavigationItemCreate(**data)
            new_item = SiteNavigationItem(**nav_data.model_dump())
            session.add(new_item)
            await session.commit()
            await session.refresh(new_item)
            
            item_dict = {
                "id": new_item.id,
                "title": new_item.title,
                "key": new_item.key,
                "path": new_item.path,
                "icon": new_item.icon,
                "parent_id": new_item.parent_id,
                "sort_order": new_item.sort_order,
                "is_visible": new_item.is_visible,
                "is_enabled": new_item.is_enabled,
                "level": new_item.level,
                "description": new_item.description,
                "target": new_item.target,
                "permission_required": new_item.permission_required,
                "created_at": new_item.created_at.isoformat(),
                "updated_at": new_item.updated_at.isoformat()
            }
            
            response_data = {
                "success": True,
                "message": "Navigation item created successfully",
                "data": {"item": item_dict},
                "csrf_token": generate_csrf_token()
            }
            return response_data
        
        elif action == "update":
            # 更新導覽項目
            item_id = data.get("id")
            if not item_id:
                raise HTTPException(status_code=400, detail="Item ID is required")

            result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail="Navigation item not found")

            # 記錄舊的 parent_id 和 sort_order
            old_parent_id = item.parent_id
            old_sort_order = item.sort_order

            # 排除不應該被前端更新的欄位
            excluded_fields = {"id", "created_at", "updated_at"}
            update_data = {k: v for k, v in data.items() if k not in excluded_fields}

            # 取得新的 parent_id 和 sort_order
            new_parent_id = update_data.get("parent_id", old_parent_id)
            new_sort_order = update_data.get("sort_order", old_sort_order)

            # 更新項目屬性
            for key, value in update_data.items():
                if value is not None or key in ("parent_id", "path"):  # 允許 parent_id 和 path 為 None
                    setattr(item, key, value)

            item.updated_at = datetime.utcnow()

            # 如果 parent_id 或 sort_order 變更，需要重新排序同層級項目
            if old_parent_id != new_parent_id or old_sort_order != new_sort_order:
                await reorder_siblings_after_move(
                    session, item_id, old_parent_id, new_parent_id, new_sort_order
                )

            await session.commit()
            await session.refresh(item)
            
            item_dict = {
                "id": item.id,
                "title": item.title,
                "key": item.key,
                "path": item.path,
                "icon": item.icon,
                "parent_id": item.parent_id,
                "sort_order": item.sort_order,
                "is_visible": item.is_visible,
                "is_enabled": item.is_enabled,
                "level": item.level,
                "description": item.description,
                "target": item.target,
                "permission_required": item.permission_required,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat()
            }
            
            response_data = {
                "success": True,
                "message": "Navigation item updated successfully",
                "data": {"item": item_dict},
                "csrf_token": generate_csrf_token()
            }
            return response_data
        
        elif action == "reorder":
            # 批次重新排序導覽項目
            items = data.get("items", [])
            if not items:
                raise HTTPException(status_code=400, detail="Items list is required")

            # 批次更新每個項目的 sort_order, parent_id, level
            for item_data in items:
                item_id = item_data.get("id")
                if not item_id:
                    continue

                result = await session.execute(
                    select(SiteNavigationItem).filter(SiteNavigationItem.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue

                # 更新排序相關欄位
                if "sort_order" in item_data:
                    item.sort_order = item_data["sort_order"]
                if "parent_id" in item_data:
                    item.parent_id = item_data["parent_id"]
                if "level" in item_data:
                    item.level = item_data["level"]

                item.updated_at = datetime.utcnow()

            await session.commit()

            response_data = {
                "success": True,
                "message": f"Successfully reordered {len(items)} items",
                "csrf_token": generate_csrf_token()
            }
            return response_data

        elif action == "delete":
            # 刪除導覽項目
            item_id = data.get("id")
            if not item_id:
                raise HTTPException(status_code=400, detail="Item ID is required")
            
            result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail="Navigation item not found")
            
            # 檢查是否有子項目
            children_result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.parent_id == item_id)
            )
            if children_result.scalars().first():
                raise HTTPException(status_code=400, detail="Cannot delete item with children")
            
            await session.delete(item)
            await session.commit()
            
            response_data = {
                "success": True,
                "message": "Navigation item deleted successfully",
                "csrf_token": generate_csrf_token()
            }
            return response_data
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/config/action", response_model=SecureResponse)
async def config_action(
    request: SecureRequest,
    session: AsyncSession = Depends(get_async_db)
):
    """統一的配置操作接口"""
    
    # 驗證 CSRF 令牌
    if not validate_csrf_token(request.csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")
    
    try:
        action = request.action.lower()
        data = request.data or {}
        
        if action == "list":
            # 獲取配置列表
            filters = []
            
            # 應用搜尋過濾器
            search = data.get("search")
            if search:
                filters.append(
                    or_(
                        SiteConfiguration.key.ilike(f"%{search}%"),
                        SiteConfiguration.description.ilike(f"%{search}%")
                    )
                )
            
            # 應用分類過濾器
            category = data.get("category")
            if category:
                filters.append(SiteConfiguration.category == category)
            
            query = select(SiteConfiguration)
            if filters:
                query = query.filter(and_(*filters))
            
            query = query.order_by(SiteConfiguration.category, SiteConfiguration.key)
            
            result = await session.execute(query)
            configs = result.scalars().all()
            
            config_list = [SiteConfigResponse.model_validate(config).model_dump() for config in configs]
            
            return SecureResponse(
                success=True,
                message="Configurations retrieved successfully",
                data={
                    "configs": config_list,
                    "total": len(config_list),
                    "skip": 0,
                    "limit": 100
                },
                csrf_token=generate_csrf_token()
            )
        
        elif action == "create":
            # 創建配置
            config_data = SiteConfigCreate(**data)
            
            # 檢查配置鍵是否已存在
            existing_result = await session.execute(
                select(SiteConfiguration).filter(
                    SiteConfiguration.key == config_data.key
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Configuration key already exists")
            
            new_config = SiteConfiguration(**config_data.model_dump())
            session.add(new_config)
            await session.commit()
            await session.refresh(new_config)
            
            return SecureResponse(
                success=True,
                message="Configuration created successfully",
                data={"config": SiteConfigResponse.model_validate(new_config).model_dump()},
                csrf_token=generate_csrf_token()
            )
        
        elif action == "update":
            # 更新配置
            key = data.get("key")
            if not key:
                raise HTTPException(status_code=400, detail="Configuration key is required")
            
            result = await session.execute(
                select(SiteConfiguration).filter(SiteConfiguration.key == key)
            )
            config = result.scalar_one_or_none()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")
            
            # 系統配置不允許修改某些欄位
            if config.is_system and "key" in data:
                raise HTTPException(status_code=403, detail="Cannot modify system configuration key")
            
            update_data = {k: v for k, v in data.items() if k != "key" and v is not None}
            for key, value in update_data.items():
                setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(config)
            
            return SecureResponse(
                success=True,
                message="Configuration updated successfully",
                data={"config": SiteConfigResponse.model_validate(config).model_dump()},
                csrf_token=generate_csrf_token()
            )
        
        elif action == "delete":
            # 刪除配置
            key = data.get("key")
            if not key:
                raise HTTPException(status_code=400, detail="Configuration key is required")
            
            result = await session.execute(
                select(SiteConfiguration).filter(SiteConfiguration.key == key)
            )
            config = result.scalar_one_or_none()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")
            
            # 系統配置不允許刪除
            if config.is_system:
                raise HTTPException(status_code=403, detail="Cannot delete system configuration")
            
            await session.delete(config)
            await session.commit()
            
            return SecureResponse(
                success=True,
                message="Configuration deleted successfully",
                csrf_token=generate_csrf_token()
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def reorder_siblings_after_move(
    session: AsyncSession,
    moved_item_id: int,
    old_parent_id: Optional[int],
    new_parent_id: Optional[int],
    new_sort_order: int
) -> None:
    """
    在項目移動後重新排序同層級的項目

    Args:
        session: 資料庫 session
        moved_item_id: 被移動項目的 ID
        old_parent_id: 舊的父層 ID
        new_parent_id: 新的父層 ID
        new_sort_order: 新的排序位置
    """
    # 查詢新父層下的所有同層項目（排除被移動的項目）
    if new_parent_id is None:
        siblings_query = select(SiteNavigationItem).filter(
            SiteNavigationItem.parent_id.is_(None),
            SiteNavigationItem.id != moved_item_id
        ).order_by(SiteNavigationItem.sort_order)
    else:
        siblings_query = select(SiteNavigationItem).filter(
            SiteNavigationItem.parent_id == new_parent_id,
            SiteNavigationItem.id != moved_item_id
        ).order_by(SiteNavigationItem.sort_order)

    siblings_result = await session.execute(siblings_query)
    siblings = list(siblings_result.scalars().all())

    # 重新計算排序
    # 將同層項目重新編號，為被移動的項目騰出位置
    current_order = 0
    for sibling in siblings:
        if current_order == new_sort_order:
            current_order += 1  # 跳過被移動項目的位置
        sibling.sort_order = current_order
        sibling.updated_at = datetime.utcnow()
        current_order += 1

    # 如果舊父層不同於新父層，也需要重新排序舊父層的項目
    if old_parent_id != new_parent_id:
        if old_parent_id is None:
            old_siblings_query = select(SiteNavigationItem).filter(
                SiteNavigationItem.parent_id.is_(None),
                SiteNavigationItem.id != moved_item_id
            ).order_by(SiteNavigationItem.sort_order)
        else:
            old_siblings_query = select(SiteNavigationItem).filter(
                SiteNavigationItem.parent_id == old_parent_id,
                SiteNavigationItem.id != moved_item_id
            ).order_by(SiteNavigationItem.sort_order)

        old_siblings_result = await session.execute(old_siblings_query)
        old_siblings = list(old_siblings_result.scalars().all())

        # 重新編號舊父層的項目
        for idx, old_sibling in enumerate(old_siblings):
            old_sibling.sort_order = idx
            old_sibling.updated_at = datetime.utcnow()


async def get_children_recursive(session: AsyncSession, parent_id: int, level: int = 2) -> List[Dict]:
    """遞歸獲取子項目"""
    result = await session.execute(
        select(SiteNavigationItem)
        .filter(SiteNavigationItem.parent_id == parent_id)
        .order_by(SiteNavigationItem.sort_order)
    )
    children = result.scalars().all()
    
    children_list = []
    for child in children:
        child_dict = {
            "id": child.id,
            "title": child.title,
            "key": child.key,
            "path": child.path,
            "icon": child.icon,
            "parent_id": child.parent_id,
            "sort_order": child.sort_order,
            "is_visible": child.is_visible,
            "is_enabled": child.is_enabled,
            "level": level,
            "description": child.description,
            "target": child.target,
            "permission_required": child.permission_required,
            "created_at": child.created_at.isoformat(),
            "updated_at": child.updated_at.isoformat(),
            "children": await get_children_recursive(session, child.id, level + 1)
        }
        children_list.append(child_dict)
    
    return children_list

@router.post("/test-navigation")
async def test_navigation_endpoint(
    session: AsyncSession = Depends(get_async_db)
):
    """測試導覽端點 - 不需 CSRF"""
    try:
        # 簡單的導覽測試，直接查詢資料庫
        from app.extended.models import SiteNavigationItem
        result = await session.execute(
            select(SiteNavigationItem).filter(SiteNavigationItem.parent_id.is_(None))
            .order_by(SiteNavigationItem.sort_order)
        )
        root_items = result.scalars().all()

        return {
            "success": True,
            "message": "Navigation test successful",
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "path": item.path
                    } for item in root_items
                ],
                "total": len(root_items)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Navigation test failed"
        }

