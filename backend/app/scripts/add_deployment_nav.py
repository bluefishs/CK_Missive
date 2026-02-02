#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新增部署管理導航項目

快速腳本：直接新增部署管理到導航選單

用法：
  cd backend
  python -m app.scripts.add_deployment_nav
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.extended.models import SiteNavigationItem


async def add_deployment_navigation():
    """新增部署管理導航項目"""
    async with AsyncSessionLocal() as db:
        # 檢查是否已存在
        query = select(SiteNavigationItem).where(
            SiteNavigationItem.key == "deployment-management"
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"部署管理項目已存在 (ID: {existing.id})")
            return

        # 查找 system-monitoring 父項目 (系統監控，ID=20)
        parent_query = select(SiteNavigationItem).where(
            SiteNavigationItem.key == "system-monitoring"
        )
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

        if not parent:
            print("錯誤: 找不到 system-monitoring 父項目")
            return

        # 新增部署管理項目 (作為系統監控的子項目)
        nav_item = SiteNavigationItem(
            title="部署管理",
            key="deployment-management",
            path="/admin/deployment",
            icon="RocketOutlined",
            sort_order=1,
            level=3,
            parent_id=parent.id,
            description="部署,CI/CD,版本",
            permission_required='["admin:settings"]',
            is_visible=True,
            is_enabled=True
        )

        db.add(nav_item)
        await db.commit()
        await db.refresh(nav_item)

        print(f"成功新增部署管理項目 (ID: {nav_item.id})")
        print(f"  路徑: {nav_item.path}")
        print(f"  父項目: {parent.title} (ID: {parent.id})")


if __name__ == "__main__":
    asyncio.run(add_deployment_navigation())
