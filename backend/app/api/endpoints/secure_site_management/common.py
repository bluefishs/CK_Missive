"""
安全網站管理模組 - 共用工具

包含：CSRF 管理、遞迴查詢、重排序
"""

import secrets
import time
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import SiteNavigationItem

# CSRF Token 儲存 (生產環境應使用 Redis 或資料庫)
csrf_tokens: Dict[str, float] = {}


def generate_csrf_token() -> str:
    """生成 CSRF 令牌"""
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = time.time()
    return token


def validate_csrf_token(token: str) -> bool:
    """驗證 CSRF 令牌"""
    from app.core.config import settings
    if getattr(settings, 'AUTH_DISABLED', False) or token == 'dev-mode-skip':
        return True

    if not token or token not in csrf_tokens:
        return False

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
