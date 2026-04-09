# -*- coding: utf-8 -*-
"""
導覽自動同步服務

啟動時比對 init_navigation_data.py 與 DB，自動插入缺少的項目。
解決 init_data 與 DB 不一致的根本問題。

Version: 1.0.0
Created: 2026-04-08
"""

import logging
from typing import Dict, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def sync_navigation_defaults(db: AsyncSession) -> Dict[str, int]:
    """
    從 init_navigation_data.py 同步缺少的導覽項目到 DB。

    策略: 只新增缺少的，不修改已存在的（避免覆蓋管理員自定義）。

    Returns:
        {"checked": N, "inserted": N, "skipped": N}
    """
    from app.scripts.init_navigation_data import DEFAULT_NAVIGATION_ITEMS
    from app.extended.models.system import SiteNavigationItem

    # 1. 載入 DB 現有 key → id 映射
    rows = (await db.execute(
        select(SiteNavigationItem.id, SiteNavigationItem.key)
    )).all()
    existing_keys: Dict[str, int] = {r[1]: r[0] for r in rows}

    # 2. 載入 DB 的 key → id (含 level-1 群組，用於 parent 查找)
    all_items_by_key = existing_keys.copy()

    # 載入 DB title → key 映射 (用於偵測等效群組)
    title_rows = (await db.execute(
        select(SiteNavigationItem.title, SiteNavigationItem.key, SiteNavigationItem.level)
    )).all()
    existing_titles_by_level: Dict[str, set] = {}
    for r in title_rows:
        existing_titles_by_level.setdefault(r[2], set()).add(r[0])

    inserted = 0
    skipped = 0

    for item in DEFAULT_NAVIGATION_ITEMS:
        key = item.get("key")
        if not key:
            continue

        if key in existing_keys:
            skipped += 1
            continue

        # 跳過 init_data 中與 DB 已有等效群組的項目 (避免重複)
        # 等效映射: init_data key → DB 中已存在的等效 key
        EQUIVALENT_GROUPS = {
            "system-management": "system",       # init: 系統管理 → DB: system (id=5)
            "ai-features": "system",             # init: AI 智慧功能 → DB: system 下的子群組
        }
        if key in EQUIVALENT_GROUPS and EQUIVALENT_GROUPS[key] in existing_keys:
            all_items_by_key[key] = existing_keys[EQUIVALENT_GROUPS[key]]
            logger.debug("Nav sync: mapped '%s' → existing '%s'", key, EQUIVALENT_GROUPS[key])
            skipped += 1
            continue

        # 跳過與 DB 中已有同名 level-1 群組的項目
        title = item.get("title", "")
        level = item.get("level", 2)
        if level == 1 and not item.get("path") and title in existing_titles_by_level.get(1, set()):
            logger.info("Nav sync: skipped '%s' — equivalent group '%s' already exists at level 1", key, title)
            skipped += 1
            continue

        # 解析 parent
        parent_key = item.get("parent_key")
        parent_id: Optional[int] = None
        if parent_key:
            parent_id = all_items_by_key.get(parent_key)
            if not parent_id:
                # 嘗試模糊查找（DB key 可能與 init_data 不同）
                parent_id = await _fuzzy_find_parent(db, parent_key)

        new_item = SiteNavigationItem(
            title=item.get("title", key),
            key=key,
            path=item.get("path"),
            icon=item.get("icon", "AppstoreOutlined"),
            sort_order=item.get("sort_order", 99),
            level=item.get("level", 2),
            parent_id=parent_id,
            description=item.get("description", ""),
            permission_required=item.get("permission_required", "[]"),
            is_enabled=True,
        )
        db.add(new_item)
        await db.flush()  # 取得 id
        all_items_by_key[key] = new_item.id
        inserted += 1
        logger.info("Nav sync: inserted '%s' (path=%s, parent_id=%s)", key, item.get("path"), parent_id)

    if inserted > 0:
        await db.commit()

    return {
        "checked": len(DEFAULT_NAVIGATION_ITEMS),
        "inserted": inserted,
        "skipped": skipped,
    }


async def _fuzzy_find_parent(db: AsyncSession, parent_key: str) -> Optional[int]:
    """
    模糊查找 parent — 處理 init_data key 與 DB key 不一致的情況。

    映射規則：
    - "ai-features" → DB 中的 "Knowledge Map" 或 "AI Agents"
    - "system-management" → DB 中的 "system"
    """
    # init_data parent_key → DB 中實際可能存在的 key（按優先級）
    KNOWN_MAPPINGS = {
        "ai-features": ["Knowledge Map", "AI Agents", "ai-features"],
        "Knowledge Map": ["Knowledge Map"],
        "AI Agents": ["AI Agents"],
        "system-management": ["system", "system-management", "Site_Management"],
        "reports": ["reports"],
    }

    candidates = KNOWN_MAPPINGS.get(parent_key, [parent_key])
    for candidate in candidates:
        from app.extended.models.system import SiteNavigationItem
        row = (await db.execute(
            select(SiteNavigationItem.id)
            .where(SiteNavigationItem.key == candidate)
            .limit(1)
        )).scalar()
        if row:
            return row

    # 最後嘗試 title 模糊匹配
    from app.extended.models.system import SiteNavigationItem
    row = (await db.execute(
        select(SiteNavigationItem.id)
        .where(SiteNavigationItem.title.ilike(f"%{parent_key.replace('-', '%')}%"))
        .where(SiteNavigationItem.level == 1)
        .limit(1)
    )).scalar()
    return row
