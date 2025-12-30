#!/usr/bin/env python3
"""
初始化導覽列數據腳本
"""
import asyncio
import sys
from pathlib import Path

# 添加專案路徑到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.db.database import AsyncSessionLocal
from app.extended.models import SiteNavigationItem
from sqlalchemy import select

async def init_navigation():
    """初始化導覽列項目"""
    
    # 預設導覽列配置
    navigation_items = [
        {
            "title": "首頁",
            "key": "home", 
            "path": "/",
            "icon": "home",
            "sort_order": 1,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "系統首頁"
        },
        {
            "title": "公文管理",
            "key": "documents",
            "path": "/documents",
            "icon": "file-text",
            "sort_order": 2,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "公文列表和管理"
        },
        {
            "title": "新增公文",
            "key": "documents-add",
            "path": "/documents/add",
            "icon": "plus",
            "sort_order": 3,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "新增公文"
        },
        {
            "title": "行事曆",
            "key": "calendar",
            "path": "/calendar",
            "icon": "calendar",
            "sort_order": 4,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "行事曆管理"
        },
        {
            "title": "統計報表",
            "key": "reports",
            "path": "/reports",
            "icon": "bar-chart",
            "sort_order": 5,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "統計分析報表"
        },
        {
            "title": "後端管理",
            "key": "admin",
            "path": "",
            "icon": "setting",
            "sort_order": 6,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "後端管理功能"
        },
        {
            "title": "網站管理",
            "key": "site-management",
            "path": "/admin/site-management",
            "icon": "global",
            "sort_order": 1,
            "is_visible": True,
            "is_enabled": True,
            "target": "_self",
            "description": "網站導覽列和配置管理",
            "parent_key": "admin"
        }
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            # 檢查是否已有導覽列項目
            result = await session.execute(select(SiteNavigationItem))
            existing_items = result.scalars().all()
            
            if existing_items:
                print(f"已存在 {len(existing_items)} 個導覽列項目")
                for item in existing_items:
                    print(f"- {item.title} ({item.key})")
                print("是否要重新初始化？(y/N): ", end="")
                response = input().strip().lower()
                if response != 'y':
                    print("取消初始化")
                    return
                
                # 刪除現有項目
                for item in existing_items:
                    await session.delete(item)
            
            # 建立新的導覽列項目
            parent_items = {}
            
            # 先建立父級項目
            for item_data in navigation_items:
                if "parent_key" not in item_data:
                    item = SiteNavigationItem(**item_data)
                    session.add(item)
                    await session.flush()  # 取得 ID
                    parent_items[item_data["key"]] = item.id
            
            # 再建立子級項目
            for item_data in navigation_items:
                if "parent_key" in item_data:
                    parent_key = item_data.pop("parent_key")
                    item_data["parent_id"] = parent_items.get(parent_key)
                    item = SiteNavigationItem(**item_data)
                    session.add(item)
            
            await session.commit()
            print(f"成功初始化 {len(navigation_items)} 個導覽列項目")
            
        except Exception as e:
            await session.rollback()
            print(f"初始化失敗: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(init_navigation())