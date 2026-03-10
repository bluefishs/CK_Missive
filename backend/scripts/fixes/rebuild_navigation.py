#!/usr/bin/env python3
"""
重建完整導覽列結構腳本
"""
import asyncio
import sys
from pathlib import Path

# 添加專案路徑到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.db.database import AsyncSessionLocal
from app.extended.models import SiteNavigationItem
from sqlalchemy import delete

async def rebuild_navigation():
    """重建完整導覽列結構"""
    
    async with AsyncSessionLocal() as session:
        try:
            # 刪除所有現有項目
            await session.execute(delete(SiteNavigationItem))
            await session.commit()
            print("已清空所有現有導覽項目")
            
            # 重新建立完整的導覽結構
            navigation_items = [
                # 父級項目
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
                    "key": "documents-menu",
                    "path": "",
                    "icon": "file-text",
                    "sort_order": 2,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "公文相關功能"
                },
                {
                    "title": "承攬案件",
                    "key": "projects",
                    "path": "/projects",
                    "icon": "project",
                    "sort_order": 3,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "承攬案件管理"
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
                    "title": "發文字號管理",
                    "key": "document-numbers",
                    "path": "/document-numbers",
                    "icon": "number",
                    "sort_order": 6,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "發文字號管理"
                },
                {
                    "title": "機關單位",
                    "key": "agencies-menu",
                    "path": "",
                    "icon": "database",
                    "sort_order": 7,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "機關單位管理"
                },
                {
                    "title": "廠商管理",
                    "key": "vendors",
                    "path": "/vendors",
                    "icon": "shop",
                    "sort_order": 8,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "廠商資料管理"
                },
                {
                    "title": "API對應",
                    "key": "api-mapping",
                    "path": "/api-mapping",
                    "icon": "api",
                    "sort_order": 9,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "API對應管理"
                },
                {
                    "title": "後端管理",
                    "key": "admin",
                    "path": "",
                    "icon": "setting",
                    "sort_order": 10,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "後端管理功能"
                }
            ]
            
            # 子級項目（需要父級ID）
            child_items = [
                {
                    "title": "公文列表",
                    "key": "documents",
                    "path": "/documents",
                    "icon": "file",
                    "sort_order": 1,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "公文列表查看",
                    "parent_key": "documents-menu"
                },
                {
                    "title": "新增公文",
                    "key": "documents-add",
                    "path": "/documents/create",
                    "icon": "plus",
                    "sort_order": 2,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "新增公文",
                    "parent_key": "documents-menu"
                },
                {
                    "title": "機關列表",
                    "key": "agencies",
                    "path": "/agencies",
                    "icon": "team",
                    "sort_order": 1,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "機關單位列表",
                    "parent_key": "agencies-menu"
                },
                {
                    "title": "新增機關",
                    "key": "agencies-add",
                    "path": "/agencies/create",
                    "icon": "plus",
                    "sort_order": 2,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "新增機關單位",
                    "parent_key": "agencies-menu"
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
                },
                {
                    "title": "資料庫管理",
                    "key": "database-admin",
                    "path": "/admin/database",
                    "icon": "database",
                    "sort_order": 2,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "資料庫維護管理",
                    "parent_key": "admin"
                },
                {
                    "title": "帳號權限",
                    "key": "admin-users",
                    "path": "/admin/users",
                    "icon": "user",
                    "sort_order": 3,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "使用者帳號權限管理",
                    "parent_key": "admin"
                },
                {
                    "title": "系統設定",
                    "key": "admin-settings",
                    "path": "/admin/settings",
                    "icon": "setting",
                    "sort_order": 4,
                    "is_visible": True,
                    "is_enabled": True,
                    "target": "_self",
                    "description": "系統參數設定",
                    "parent_key": "admin"
                }
            ]
            
            # 建立父級項目
            parent_items = {}
            for item_data in navigation_items:
                item = SiteNavigationItem(**item_data)
                session.add(item)
                await session.flush()  # 取得 ID
                parent_items[item_data["key"]] = item.id
                print(f"建立父級項目: {item_data['title']} (ID: {item.id})")
            
            # 建立子級項目
            for item_data in child_items:
                parent_key = item_data.pop("parent_key")
                item_data["parent_id"] = parent_items.get(parent_key)
                item = SiteNavigationItem(**item_data)
                session.add(item)
                await session.flush()
                print(f"建立子級項目: {item_data['title']} (ID: {item.id}, Parent: {item_data['parent_id']})")
            
            await session.commit()
            print(f"\n成功重建導覽列結構，共 {len(navigation_items) + len(child_items)} 個項目")
            
        except Exception as e:
            await session.rollback()
            print(f"重建失敗: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(rebuild_navigation())