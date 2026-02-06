"""
安全網站管理模組 - 導覽列端點

包含: /navigation/action, /test-navigation, /navigation/valid-paths
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import SiteNavigationItem
from app.schemas.site_management import NavigationItemCreate
from app.core.navigation_validator import validate_navigation_path, get_all_valid_paths
from app.repositories.navigation_repository import NavigationRepository

from .common import validate_csrf_token, generate_csrf_token

router = APIRouter()


def _item_to_dict(item: SiteNavigationItem) -> dict:
    """將導覽項目 ORM 物件轉換為字典"""
    return {
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
        "updated_at": item.updated_at.isoformat(),
    }


async def _reorder_siblings_after_move(
    nav_repo: NavigationRepository,
    moved_item_id: int,
    old_parent_id: Optional[int],
    new_parent_id: Optional[int],
    new_sort_order: int,
) -> None:
    """在項目移動後重新排序同層級的項目"""
    siblings = await nav_repo.get_siblings(new_parent_id, exclude_item_id=moved_item_id)

    current_order = 0
    for sibling in siblings:
        if current_order == new_sort_order:
            current_order += 1
        sibling.sort_order = current_order
        sibling.updated_at = datetime.utcnow()
        current_order += 1

    if old_parent_id != new_parent_id:
        old_siblings = await nav_repo.get_siblings(
            old_parent_id, exclude_item_id=moved_item_id
        )
        for idx, old_sibling in enumerate(old_siblings):
            old_sibling.sort_order = idx
            old_sibling.updated_at = datetime.utcnow()


@router.post("/navigation/action")
async def navigation_action(
    action: str = Body(..., embed=True),
    csrf_token: str = Body(None, embed=True),
    data: dict = Body(None, embed=True),
    session: AsyncSession = Depends(get_async_db),
):
    """統一的導覽列操作接口"""

    if not validate_csrf_token(csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")

    nav_repo = NavigationRepository(session)

    try:
        action = action.lower()
        data = data or {}

        if action == "list":
            root_items = await nav_repo.get_root_items()

            items = []
            for item in root_items:
                item_dict = _item_to_dict(item)
                item_dict["level"] = 1
                item_dict["children"] = await nav_repo.get_children_recursive(item.id)
                items.append(item_dict)

            return {
                "success": True,
                "message": "Navigation items retrieved successfully",
                "data": {"items": items, "total": len(items)},
                "csrf_token": generate_csrf_token(),
            }

        elif action == "create":
            path = data.get("path")
            is_valid, error_msg = validate_navigation_path(path)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)

            nav_data = NavigationItemCreate(**data)
            new_item = await nav_repo.create(nav_data.model_dump())

            return {
                "success": True,
                "message": "Navigation item created successfully",
                "data": {"item": _item_to_dict(new_item)},
                "csrf_token": generate_csrf_token(),
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

            item = await nav_repo.get_by_id(item_id)
            if not item:
                raise HTTPException(
                    status_code=404, detail="Navigation item not found"
                )

            old_parent_id = item.parent_id
            old_sort_order = item.sort_order

            excluded_fields = {"id", "created_at", "updated_at"}
            update_data = {
                k: v for k, v in data.items() if k not in excluded_fields
            }

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
                await _reorder_siblings_after_move(
                    nav_repo,
                    item_id,
                    old_parent_id,
                    new_parent_id,
                    new_sort_order,
                )

            await session.commit()
            await session.refresh(item)

            return {
                "success": True,
                "message": "Navigation item updated successfully",
                "data": {"item": _item_to_dict(item)},
                "csrf_token": generate_csrf_token(),
            }

        elif action == "reorder":
            reorder_data = data.get("items", [])
            if not reorder_data:
                raise HTTPException(
                    status_code=400, detail="Items list is required"
                )

            updated_count = await nav_repo.reorder_items(reorder_data)

            return {
                "success": True,
                "message": f"Successfully reordered {len(reorder_data)} items",
                "csrf_token": generate_csrf_token(),
            }

        elif action == "delete":
            item_id = data.get("id")
            if not item_id:
                raise HTTPException(
                    status_code=400, detail="Item ID is required"
                )

            item = await nav_repo.get_by_id(item_id)
            if not item:
                raise HTTPException(
                    status_code=404, detail="Navigation item not found"
                )

            if await nav_repo.has_children(item_id):
                raise HTTPException(
                    status_code=400, detail="Cannot delete item with children"
                )

            await nav_repo.delete(item_id)

            return {
                "success": True,
                "message": "Navigation item deleted successfully",
                "csrf_token": generate_csrf_token(),
            }

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown action: {action}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.post("/test-navigation")
async def test_navigation_endpoint(
    session: AsyncSession = Depends(get_async_db),
):
    """測試導覽端點 - 不需 CSRF"""
    try:
        nav_repo = NavigationRepository(session)
        root_items = await nav_repo.get_root_items()

        return {
            "success": True,
            "message": "Navigation test successful",
            "data": {
                "items": [
                    {"id": item.id, "title": item.title, "path": item.path}
                    for item in root_items
                ],
                "total": len(root_items),
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Navigation test failed",
        }


@router.post("/navigation/valid-paths")
async def get_valid_navigation_paths():
    """獲取所有有效的導覽路徑列表"""
    try:
        paths = get_all_valid_paths()
        return {
            "success": True,
            "message": "Valid paths retrieved successfully",
            "data": {"paths": paths, "total": len(paths)},
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve valid paths",
        }
