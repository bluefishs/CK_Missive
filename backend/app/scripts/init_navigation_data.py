#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化導覽列數據腳本
為系統建立預設的導覽列結構和配置
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加 backend 目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.extended.models import SiteNavigationItem, SiteConfiguration

# 預設導覽列結構數據
DEFAULT_NAVIGATION_ITEMS = [
    # 首頁
    {
        "title": "首頁",
        "key": "dashboard",
        "path": "/dashboard",
        "icon": "dashboard",
        "sort_order": 1,
        "level": 1
    },
    
    # 公文管理
    {
        "title": "公文管理",
        "key": "documents",
        "path": "/documents",
        "icon": "file-text",
        "sort_order": 2,
        "level": 1
    },
    
    # 發文字號管理
    {
        "title": "發文字號管理",
        "key": "document-numbers",
        "path": "/document-numbers",
        "icon": "number",
        "sort_order": 3,
        "level": 1
    },
    
    # 案件管理（父項目）
    {
        "title": "案件管理",
        "key": "case-management",
        "path": None,
        "icon": "folder",
        "sort_order": 4,
        "level": 1
    },
    
    # 案件管理 -> 一般案件
    {
        "title": "一般案件",
        "key": "cases",
        "path": "/cases",
        "icon": "file",
        "sort_order": 1,
        "level": 2,
        "parent_key": "case-management"
    },
    
    # 案件管理 -> 承攬專案
    {
        "title": "承攬專案",
        "key": "projects",
        "path": "/projects",
        "icon": "project",
        "sort_order": 2,
        "level": 2,
        "parent_key": "case-management"
    },
    
    # 案件管理 -> 廠商管理
    {
        "title": "廠商管理",
        "key": "vendors",
        "path": "/vendors",
        "icon": "team",
        "sort_order": 3,
        "level": 2,
        "parent_key": "case-management"
    },
    
    # 系統管理（父項目）
    {
        "title": "系統管理",
        "key": "system-management",
        "path": None,
        "icon": "setting",
        "sort_order": 5,
        "level": 1
    },
    
    # 系統管理 -> 使用者管理
    {
        "title": "使用者管理",
        "key": "users",
        "path": "/users",
        "icon": "user",
        "sort_order": 1,
        "level": 2,
        "parent_key": "system-management"
    },
    
    # 系統管理 -> 網站管理
    {
        "title": "網站管理",
        "key": "site-management",
        "path": "/site-management",
        "icon": "global",
        "sort_order": 2,
        "level": 2,
        "parent_key": "system-management"
    },
    
    # 系統管理 -> 資料庫管理
    {
        "title": "資料庫管理",
        "key": "database-admin",
        "path": "/admin",
        "icon": "database",
        "sort_order": 3,
        "level": 2,
        "parent_key": "system-management"
    },
    
    # 系統管理 -> 系統除錯
    {
        "title": "系統除錯",
        "key": "debug",
        "path": "/debug",
        "icon": "bug",
        "sort_order": 4,
        "level": 2,
        "parent_key": "system-management"
    },
    
    # 統計報表
    {
        "title": "統計報表",
        "key": "reports",
        "path": "/reports",
        "icon": "bar-chart",
        "sort_order": 6,
        "level": 1
    },
    
    # 行事曆
    {
        "title": "行事曆",
        "key": "calendar",
        "path": "/calendar",
        "icon": "calendar",
        "sort_order": 7,
        "level": 1
    }
]

# 預設網站配置
DEFAULT_SITE_CONFIGS = [
    {
        "config_key": "site_title",
        "config_value": "乾坤測繪公文管理系統",
        "config_type": "string",
        "description": "網站標題",
        "category": "general"
    },
    {
        "config_key": "site_logo",
        "config_value": "/assets/logo.png",
        "config_type": "string",
        "description": "網站 Logo 路徑",
        "category": "general"
    },
    {
        "config_key": "company_name",
        "config_value": "乾坤測繪工程有限公司",
        "config_type": "string",
        "description": "公司名稱",
        "category": "general"
    },
    {
        "config_key": "sidebar_collapsed",
        "config_value": "false",
        "config_type": "boolean",
        "description": "側邊欄預設是否摺疊",
        "category": "ui"
    },
    {
        "config_key": "theme_color",
        "config_value": "#1890ff",
        "config_type": "string",
        "description": "主題色彩",
        "category": "ui"
    },
    {
        "config_key": "page_size_options",
        "config_value": "[10, 20, 50, 100]",
        "config_type": "json",
        "description": "分頁大小選項",
        "category": "ui"
    },
    {
        "config_key": "default_page_size",
        "config_value": "20",
        "config_type": "number",
        "description": "預設分頁大小",
        "category": "ui"
    },
    {
        "config_key": "enable_notifications",
        "config_value": "true",
        "config_type": "boolean",
        "description": "是否啟用通知功能",
        "category": "features"
    },
    {
        "config_key": "auto_save_interval",
        "config_value": "30",
        "config_type": "number",
        "description": "自動儲存間隔（秒）",
        "category": "features"
    },
    {
        "config_key": "system_version",
        "config_value": "2.0.0",
        "config_type": "string",
        "description": "系統版本號",
        "category": "system",
        "is_system": True
    }
]

async def check_item_exists(db: AsyncSession, key: str) -> bool:
    """檢查導覽項目是否已存在"""
    query = select(SiteNavigationItem).where(SiteNavigationItem.key == key)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

async def check_config_exists(db: AsyncSession, config_key: str) -> bool:
    """檢查配置項目是否已存在"""
    query = select(SiteConfiguration).where(SiteConfiguration.config_key == config_key)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

async def create_navigation_items(db: AsyncSession):
    """創建導覽列項目"""
    print("開始創建導覽列項目...")
    
    # 第一階段：創建所有父級項目
    parent_items = {}
    for item_data in DEFAULT_NAVIGATION_ITEMS:
        if item_data.get("parent_key") is None:  # 頂級項目
            if await check_item_exists(db, item_data["key"]):
                print(f"導覽項目 '{item_data['title']}' 已存在，跳過...")
                # 獲取已存在的項目用於建立關聯
                query = select(SiteNavigationItem).where(SiteNavigationItem.key == item_data["key"])
                result = await db.execute(query)
                parent_items[item_data["key"]] = result.scalar_one()
                continue
            
            navigation_item = SiteNavigationItem(
                title=item_data["title"],
                key=item_data["key"],
                path=item_data.get("path"),
                icon=item_data.get("icon"),
                sort_order=item_data["sort_order"],
                level=item_data["level"],
                is_visible=True,
                is_enabled=True
            )
            
            db.add(navigation_item)
            parent_items[item_data["key"]] = navigation_item
            print(f"創建頂級導覽項目: {item_data['title']}")
    
    # 提交第一階段
    await db.commit()
    
    # 重新查詢所有父級項目以獲取正確的 ID
    for key in parent_items.keys():
        query = select(SiteNavigationItem).where(SiteNavigationItem.key == key)
        result = await db.execute(query)
        parent_items[key] = result.scalar_one()
    
    # 第二階段：創建子級項目
    for item_data in DEFAULT_NAVIGATION_ITEMS:
        if item_data.get("parent_key") is not None:  # 子級項目
            if await check_item_exists(db, item_data["key"]):
                print(f"導覽項目 '{item_data['title']}' 已存在，跳過...")
                continue
            
            parent_item = parent_items.get(item_data["parent_key"])
            if not parent_item:
                print(f"警告：找不到父級項目 '{item_data['parent_key']}'，跳過 '{item_data['title']}'")
                continue
            
            navigation_item = SiteNavigationItem(
                title=item_data["title"],
                key=item_data["key"],
                path=item_data.get("path"),
                icon=item_data.get("icon"),
                parent_id=parent_item.id,
                sort_order=item_data["sort_order"],
                level=item_data["level"],
                is_visible=True,
                is_enabled=True
            )
            
            db.add(navigation_item)
            print(f"創建子級導覽項目: {item_data['title']} (父級: {parent_item.title})")
    
    await db.commit()
    print("導覽列項目創建完成！")

async def create_site_configs(db: AsyncSession):
    """創建網站配置"""
    print("開始創建網站配置...")
    
    for config_data in DEFAULT_SITE_CONFIGS:
        if await check_config_exists(db, config_data["config_key"]):
            print(f"配置項目 '{config_data['config_key']}' 已存在，跳過...")
            continue
        
        site_config = SiteConfiguration(
            config_key=config_data["config_key"],
            config_value=config_data["config_value"],
            config_type=config_data["config_type"],
            description=config_data["description"],
            category=config_data["category"],
            is_system=config_data.get("is_system", False)
        )
        
        db.add(site_config)
        print(f"創建配置項目: {config_data['config_key']} = {config_data['config_value']}")
    
    await db.commit()
    print("網站配置創建完成！")

async def init_navigation_data():
    """初始化導覽列數據的主函數"""
    print("=== 初始化導覽列數據 ===")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        async with AsyncSessionLocal() as db:
            # 創建導覽列項目
            await create_navigation_items(db)
            
            # 創建網站配置
            await create_site_configs(db)
            
        print("=== 初始化完成 ===")
        print(f"結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"初始化失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def main():
    """主執行函數"""
    success = await init_navigation_data()
    if success:
        print("導覽列數據初始化成功！")
        return 0
    else:
        print("導覽列數據初始化失敗！")
        return 1

if __name__ == "__main__":
    # 執行初始化
    exit_code = asyncio.run(main())
    sys.exit(exit_code)