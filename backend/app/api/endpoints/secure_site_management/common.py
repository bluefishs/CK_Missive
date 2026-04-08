"""
安全網站管理模組 - 共用工具

包含：CSRF 管理（Redis 後端）、遞迴查詢、重排序
"""

import logging
import secrets
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import SiteNavigationItem

logger = logging.getLogger(__name__)

# CSRF Token TTL (秒)
_CSRF_TOKEN_TTL = 3600  # 1 小時


async def generate_csrf_token() -> str:
    """生成 CSRF 令牌並存入 Redis (1 小時 TTL，單次使用)"""
    from app.core.redis_client import get_redis

    token = secrets.token_urlsafe(32)
    redis = await get_redis()
    if redis:
        try:
            await redis.setex(f"csrf:{token}", _CSRF_TOKEN_TTL, "1")
        except Exception as e:
            logger.warning("Failed to store CSRF token in Redis: %s", e)
    else:
        logger.warning("Redis unavailable — CSRF token not persisted")
    return token


async def validate_csrf_token(token: str) -> bool:
    """驗證 CSRF 令牌（單次使用：驗證後立即刪除）"""
    from app.core.config import settings
    if getattr(settings, 'AUTH_DISABLED', False):
        return True

    if not token:
        return False

    from app.core.redis_client import get_redis
    redis = await get_redis()
    if not redis:
        logger.warning("Redis unavailable — CSRF validation skipped (deny)")
        return False

    try:
        exists = await redis.get(f"csrf:{token}")
        if exists:
            await redis.delete(f"csrf:{token}")
            return True
        return False
    except Exception as e:
        logger.warning("Failed to validate CSRF token in Redis: %s", e)
        return False


async def cleanup_expired_tokens():
    """清理過期的 CSRF 令牌 (Redis TTL 自動過期，此函數保留相容性)"""
    # Redis 的 SETEX 會自動過期，無需手動清理
    pass


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


async def reorder_siblings_after_move(
    session: AsyncSession,
    moved_item_id: int,
    old_parent_id: Optional[int],
    new_parent_id: Optional[int],
    new_sort_order: int
) -> None:
    """在項目移動後重新排序同層級的項目"""
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

    current_order = 0
    for sibling in siblings:
        if current_order == new_sort_order:
            current_order += 1
        sibling.sort_order = current_order
        sibling.updated_at = datetime.utcnow()
        current_order += 1

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

        for idx, old_sibling in enumerate(old_siblings):
            old_sibling.sort_order = idx
            old_sibling.updated_at = datetime.utcnow()
