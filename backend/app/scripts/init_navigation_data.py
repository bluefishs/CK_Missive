#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化導覽列數據腳本
為系統建立預設的導覽列結構和配置

@version 2.0.0
@date 2026-01-11

變更記錄：
- v2.0.0: 同步前端路由定義，修正欄位名稱，新增缺失項目
- v1.0.0: 初始版本
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

# =============================================================================
# 導覽項目定義
# 注意：路徑必須與前端 frontend/src/router/types.ts 中的 ROUTES 保持一致
# =============================================================================
DEFAULT_NAVIGATION_ITEMS = [
    # =========================================================================
    # 頂層項目
    # =========================================================================

    # 儀表板 (對應 ROUTES.DASHBOARD)
    {
        "title": "儀表板",
        "key": "dashboard",
        "path": "/dashboard",
        "icon": "DashboardOutlined",
        "sort_order": 1,
        "level": 1,
        "description": "首頁,儀表板,總覽",
        "permission_required": "[]"
    },

    # 公文管理 (群組)
    {
        "title": "公文管理",
        "key": "documents",
        "path": "/documents",
        "icon": "FileTextOutlined",
        "sort_order": 2,
        "level": 1,
        "description": "公文,文件,管理",
        "permission_required": "[]"
    },

    # 專案管理 (群組，對應前端「案件資料」)
    {
        "title": "專案管理",
        "key": "project-management",
        "path": None,
        "icon": "FolderOutlined",
        "sort_order": 3,
        "level": 1,
        "description": "專案,案件,管理",
        "permission_required": "[\"documents:read\"]"
    },

    # 行事曆管理 (對應 ROUTES.CALENDAR)
    {
        "title": "行事曆管理",
        "key": "calendar",
        "path": "/calendar",
        "icon": "CalendarOutlined",
        "sort_order": 4,
        "level": 1,
        "description": "行事曆,排程",
        "permission_required": "[\"calendar:read\"]"
    },

    # 報表分析 (群組)
    {
        "title": "報表分析",
        "key": "reports",
        "path": None,
        "icon": "BarChartOutlined",
        "sort_order": 5,
        "level": 1,
        "description": "報表,分析,統計",
        "permission_required": "[\"reports:view\"]"
    },

    # 系統管理 (群組)
    {
        "title": "系統管理",
        "key": "system-management",
        "path": None,
        "icon": "SettingOutlined",
        "sort_order": 6,
        "level": 1,
        "description": "系統,管理,設定",
        "permission_required": "[\"admin:users\"]"
    },

    # 個人設定 (對應 ROUTES.PROFILE)
    {
        "title": "個人設定",
        "key": "settings",
        "path": "/profile",
        "icon": "UserOutlined",
        "sort_order": 7,
        "level": 1,
        "description": "個人,設定,偏好",
        "permission_required": "[]"
    },

    # =========================================================================
    # 公文管理 子項目
    # =========================================================================

    # 文件瀏覽 (對應 ROUTES.DOCUMENTS)
    {
        "title": "文件瀏覽",
        "key": "document-browse",
        "path": "/documents",
        "icon": "EyeOutlined",
        "sort_order": 1,
        "level": 2,
        "parent_key": "documents",
        "description": "瀏覽,查看",
        "permission_required": "[\"documents:read\"]"
    },

    # 文號管理 (對應 ROUTES.DOCUMENT_NUMBERS)
    {
        "title": "文號管理",
        "key": "document-numbers",
        "path": "/document-numbers",
        "icon": "NumberOutlined",
        "sort_order": 2,
        "level": 2,
        "parent_key": "documents",
        "description": "文號,編號,發文",
        "permission_required": "[\"documents:write\"]"
    },

    # =========================================================================
    # 專案管理 子項目
    # =========================================================================

    # 承攬計畫 (對應 ROUTES.CONTRACT_CASES)
    {
        "title": "承攬計畫",
        "key": "contract-cases",
        "path": "/contract-cases",
        "icon": "ProjectOutlined",
        "sort_order": 1,
        "level": 2,
        "parent_key": "project-management",
        "description": "專案,計畫,承攬",
        "permission_required": "[\"projects:read\"]"
    },

    # 機關管理 (對應 ROUTES.AGENCIES)
    {
        "title": "機關管理",
        "key": "agencies",
        "path": "/agencies",
        "icon": "BankOutlined",
        "sort_order": 2,
        "level": 2,
        "parent_key": "project-management",
        "description": "機關,單位",
        "permission_required": "[\"agencies:read\"]"
    },

    # 廠商管理 (對應 ROUTES.VENDORS)
    {
        "title": "廠商管理",
        "key": "vendors",
        "path": "/vendors",
        "icon": "ShopOutlined",
        "sort_order": 3,
        "level": 2,
        "parent_key": "project-management",
        "description": "廠商,供應商",
        "permission_required": "[\"vendors:read\"]"
    },

    # 承辦同仁 (對應 ROUTES.STAFF)
    {
        "title": "承辦同仁",
        "key": "staff",
        "path": "/staff",
        "icon": "TeamOutlined",
        "sort_order": 4,
        "level": 2,
        "parent_key": "project-management",
        "description": "承辦,同仁,人員",
        "permission_required": "[]"
    },

    # =========================================================================
    # 行事曆管理 子項目
    # =========================================================================

    # 專案行事曆 (對應 ROUTES.PURE_CALENDAR)
    {
        "title": "專案行事曆",
        "key": "pure-calendar",
        "path": "/pure-calendar",
        "icon": "ScheduleOutlined",
        "sort_order": 1,
        "level": 2,
        "parent_key": "calendar",
        "description": "行事曆",
        "permission_required": "[\"calendar:read\"]"
    },

    # =========================================================================
    # 報表分析 子項目
    # =========================================================================

    # 統計報表 (對應 ROUTES.REPORTS)
    {
        "title": "統計報表",
        "key": "reports-stats",
        "path": "/reports",
        "icon": "LineChartOutlined",
        "sort_order": 1,
        "level": 2,
        "parent_key": "reports",
        "description": "統計,圖表",
        "permission_required": "[\"reports:view\"]"
    },

    # API 文件 (對應 ROUTES.API_DOCS)
    {
        "title": "API文件",
        "key": "api-docs",
        "path": "/api/docs",
        "icon": "ApiOutlined",
        "sort_order": 2,
        "level": 2,
        "parent_key": "reports",
        "description": "API,文件",
        "permission_required": "[]"
    },

    # API 對應表 (對應 ROUTES.API_MAPPING)
    {
        "title": "API對應表",
        "key": "api-mapping",
        "path": "/api-mapping",
        "icon": "LinkOutlined",
        "sort_order": 3,
        "level": 2,
        "parent_key": "reports",
        "description": "API,對應",
        "permission_required": "[]"
    },

    # =========================================================================
    # 系統管理 子項目
    # =========================================================================

    # 使用者管理 (對應 ROUTES.USER_MANAGEMENT)
    {
        "title": "使用者管理",
        "key": "user-management",
        "path": "/admin/user-management",
        "icon": "UserOutlined",
        "sort_order": 1,
        "level": 2,
        "parent_key": "system-management",
        "description": "使用者,帳號",
        "permission_required": "[\"admin:users\"]"
    },

    # 權限管理 (對應 ROUTES.PERMISSION_MANAGEMENT)
    {
        "title": "權限管理",
        "key": "permission-management",
        "path": "/admin/permissions",
        "icon": "SecurityScanOutlined",
        "sort_order": 2,
        "level": 2,
        "parent_key": "system-management",
        "description": "權限,角色",
        "permission_required": "[\"admin:users\"]"
    },

    # 資料庫管理 (對應 ROUTES.DATABASE)
    {
        "title": "資料庫管理",
        "key": "database-management",
        "path": "/admin/database",
        "icon": "DatabaseOutlined",
        "sort_order": 3,
        "level": 2,
        "parent_key": "system-management",
        "description": "資料庫,維護",
        "permission_required": "[\"admin:settings\"]"
    },

    # 網站管理 (對應 ROUTES.SITE_MANAGEMENT)
    {
        "title": "網站管理",
        "key": "site-management",
        "path": "/admin/site-management",
        "icon": "GlobalOutlined",
        "sort_order": 4,
        "level": 2,
        "parent_key": "system-management",
        "description": "網站,設定",
        "permission_required": "[\"admin:site_management\"]"
    },

    # 系統監控 (對應 ROUTES.SYSTEM)
    {
        "title": "系統監控",
        "key": "system-monitoring",
        "path": "/system",
        "icon": "MonitorOutlined",
        "sort_order": 5,
        "level": 2,
        "parent_key": "system-management",
        "description": "監控,狀態",
        "permission_required": "[\"admin:settings\"]"
    },

    # 管理員面板 (對應 ROUTES.ADMIN_DASHBOARD)
    {
        "title": "管理員面板",
        "key": "admin-dashboard",
        "path": "/admin/dashboard",
        "icon": "DashboardOutlined",
        "sort_order": 6,
        "level": 2,
        "parent_key": "system-management",
        "description": "管理,面板",
        "permission_required": "[\"admin:users\"]"
    },

    # Google 認證診斷 (對應 ROUTES.GOOGLE_AUTH_DIAGNOSTIC)
    {
        "title": "Google認證診斷",
        "key": "google-auth-diagnostic",
        "path": "/google-auth-diagnostic",
        "icon": "GoogleOutlined",
        "sort_order": 7,
        "level": 2,
        "parent_key": "system-management",
        "description": "Google,認證",
        "permission_required": "[\"admin:settings\"]"
    },
]

# =============================================================================
# 網站配置定義
# 注意：欄位名稱必須與 SiteConfiguration 模型匹配 (key, value)
# =============================================================================
DEFAULT_SITE_CONFIGS = [
    {
        "key": "site_title",
        "value": "乾坤測繪公文管理系統",
        "description": "網站標題",
        "category": "general"
    },
    {
        "key": "site_logo",
        "value": "/assets/logo.png",
        "description": "網站 Logo 路徑",
        "category": "general"
    },
    {
        "key": "company_name",
        "value": "乾坤測繪工程有限公司",
        "description": "公司名稱",
        "category": "general"
    },
    {
        "key": "sidebar_collapsed",
        "value": "false",
        "description": "側邊欄預設是否摺疊",
        "category": "ui"
    },
    {
        "key": "theme_color",
        "value": "#1890ff",
        "description": "主題色彩",
        "category": "ui"
    },
    {
        "key": "page_size_options",
        "value": "[10, 20, 50, 100]",
        "description": "分頁大小選項",
        "category": "ui"
    },
    {
        "key": "default_page_size",
        "value": "20",
        "description": "預設分頁大小",
        "category": "ui"
    },
    {
        "key": "enable_notifications",
        "value": "true",
        "description": "是否啟用通知功能",
        "category": "features"
    },
    {
        "key": "auto_save_interval",
        "value": "30",
        "description": "自動儲存間隔（秒）",
        "category": "features"
    },
    {
        "key": "system_version",
        "value": "2.0.0",
        "description": "系統版本號",
        "category": "system"
    }
]

async def check_item_exists(db: AsyncSession, key: str) -> bool:
    """檢查導覽項目是否已存在"""
    query = select(SiteNavigationItem).where(SiteNavigationItem.key == key)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

async def check_config_exists(db: AsyncSession, config_key: str) -> bool:
    """檢查配置項目是否已存在"""
    # 使用正確的欄位名稱 'key'（不是 'config_key'）
    query = select(SiteConfiguration).where(SiteConfiguration.key == config_key)
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
                description=item_data.get("description", ""),
                permission_required=item_data.get("permission_required", "[]"),
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
                description=item_data.get("description", ""),
                permission_required=item_data.get("permission_required", "[]"),
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
        if await check_config_exists(db, config_data["key"]):
            print(f"配置項目 '{config_data['key']}' 已存在，跳過...")
            continue

        # 使用正確的欄位名稱
        site_config = SiteConfiguration(
            key=config_data["key"],
            value=config_data["value"],
            description=config_data["description"],
            category=config_data["category"]
        )

        db.add(site_config)
        print(f"創建配置項目: {config_data['key']} = {config_data['value']}")

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
