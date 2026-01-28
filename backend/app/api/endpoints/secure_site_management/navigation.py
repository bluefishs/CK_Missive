"""
安全網站管理模組 - 導覽列端點

包含: /navigation/action, /test-navigation, /navigation/valid-paths
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import SiteNavigationItem
from app.schemas.site_management import NavigationItemCreate
from app.core.navigation_validator import validate_navigation_path, get_all_valid_paths

from .common import (
    validate_csrf_token, generate_csrf_token,
    get_children_recursive, reorder_siblings_after_move,
)

router = APIRouter()


@router.post("/navigation/action")
async def navigation_action(
    action: str = Body(..., embed=True),
    csrf_token: str = Body(None, embed=True),
    data: dict = Body(None, embed=True),
    session: AsyncSession = Depends(get_async_db)
):
    """統一的導覽列操作接口"""

    if not validate_csrf_token(csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")

    try:
        action = action.lower()
        data = data or {}

        if action == "list":
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

            return {
                "success": True,
                "message": "Navigation items retrieved successfully",
                "data": {"items": items, "total": len(items)},
                "csrf_token": generate_csrf_token()
            }

        elif action == "create":
            path = data.get("path")
            is_valid, error_msg = validate_navigation_path(path)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)

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

            return {
                "success": True,
                "message": "Navigation item created successfully",
                "data": {"item": item_dict},
                "csrf_token": generate_csrf_token()
            }

        elif action == "update":
            item_id = data.get("id")
            if not item_id:
                raise HTTPException(status_code=400, detail="Item ID is required")

            if "path" in data:
                path = data.get("path")
                is_valid, error_msg = validate_navigation_path(path)
                if not is_valid:
                    raise HTTPException(status_code=400, detail=error_msg)

            result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail="Navigation item not found")

            old_parent_id = item.parent_id
            old_sort_order = item.sort_order

            excluded_fields = {"id", "created_at", "updated_at"}
            update_data = {k: v for k, v in data.items() if k not in excluded_fields}

            if "sort_order" in update_data and update_data["sort_order"] is not None:
                update_data["sort_order"] = int(update_data["sort_order"])
            if "level" in update_data and update_data["level"] is not None:
                update_data["level"] = int(update_data["level"])
            if "parent_id" in update_data and update_data["parent_id"] is not None:
                update_data["parent_id"] = int(update_data["parent_id"])

            new_parent_id = update_data.get("parent_id", old_parent_id)
            new_sort_order = update_data.get("sort_order", old_sort_order)

            for key, value in update_data.items():
                if value is not None or key in ("parent_id", "path"):
                    setattr(item, key, value)

            item.updated_at = datetime.utcnow()

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

            return {
                "success": True,
                "message": "Navigation item updated successfully",
                "data": {"item": item_dict},
                "csrf_token": generate_csrf_token()
            }

        elif action == "reorder":
            items = data.get("items", [])
            if not items:
                raise HTTPException(status_code=400, detail="Items list is required")

            for item_data in items:
                item_id = item_data.get("id")
                if not item_id:
                    continue

                result = await session.execute(
                    select(SiteNavigationItem).filter(SiteNavigationItem.id == int(item_id))
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue

                if "sort_order" in item_data and item_data["sort_order"] is not None:
                    item.sort_order = int(item_data["sort_order"])
                if "parent_id" in item_data:
                    item.parent_id = int(item_data["parent_id"]) if item_data["parent_id"] is not None else None
                if "level" in item_data and item_data["level"] is not None:
                    item.level = int(item_data["level"])

                item.updated_at = datetime.utcnow()

            await session.commit()

            return {
                "success": True,
                "message": f"Successfully reordered {len(items)} items",
                "csrf_token": generate_csrf_token()
            }

        elif action == "delete":
            item_id = data.get("id")
            if not item_id:
                raise HTTPException(status_code=400, detail="Item ID is required")

            result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail="Navigation item not found")

            children_result = await session.execute(
                select(SiteNavigationItem).filter(SiteNavigationItem.parent_id == item_id)
            )
            if children_result.scalars().first():
                raise HTTPException(status_code=400, detail="Cannot delete item with children")

            await session.delete(item)
            await session.commit()

            return {
                "success": True,
                "message": "Navigation item deleted successfully",
                "csrf_token": generate_csrf_token()
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/test-navigation")
async def test_navigation_endpoint(
    session: AsyncSession = Depends(get_async_db)
):
    """測試導覽端點 - 不需 CSRF"""
    try:
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


@router.post("/navigation/valid-paths")
async def get_valid_navigation_paths():
    """獲取所有有效的導覽路徑列表"""
    try:
        paths = get_all_valid_paths()
        return {
            "success": True,
            "message": "Valid paths retrieved successfully",
            "data": {
                "paths": paths,
                "total": len(paths)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve valid paths"
        }
