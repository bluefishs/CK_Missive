#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整資料庫初始化腳本
包含所有必要的初始資料
"""

import subprocess
import time

def execute_in_backend(script):
    """在後端容器中執行 Python 腳本"""
    try:
        result = subprocess.run([
            "docker", "exec", "ck_missive_backend", "python", "-c", script
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"[ERROR] {result.stderr}")
            return False

    except Exception as e:
        print(f"[ERROR] 執行失敗: {e}")
        return False

def init_tables():
    """初始化資料庫表結構"""
    print("=== 初始化資料庫表結構 ===")

    script = """
import asyncio
from app.db.database import engine, Base
from app.extended.models import *

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✅ 資料庫表結構創建完成')

asyncio.run(create_tables())
"""
    return execute_in_backend(script)

def init_admin_user():
    """初始化管理員用戶"""
    print("=== 初始化管理員用戶 ===")

    script = """
import asyncio
from app.db.database import get_async_db
from app.extended.models import User
from sqlalchemy import select

async def create_admin():
    async for db in get_async_db():
        # 檢查是否已有管理員
        admin_query = select(User).where(User.role == 'superuser')
        result = await db.execute(admin_query)
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print('✅ 管理員用戶已存在')
            # 更新權限
            existing_admin.is_admin = True
            existing_admin.is_superuser = True
            existing_admin.role = 'superuser'
            existing_admin.permissions = '[\"documents:read\", \"documents:create\", \"documents:edit\", \"documents:delete\", \"projects:read\", \"projects:create\", \"projects:edit\", \"projects:delete\", \"agencies:read\", \"agencies:create\", \"agencies:edit\", \"agencies:delete\", \"vendors:read\", \"vendors:create\", \"vendors:edit\", \"vendors:delete\", \"calendar:read\", \"calendar:edit\", \"reports:view\", \"reports:export\", \"system_docs:read\", \"system_docs:create\", \"system_docs:edit\", \"system_docs:delete\", \"admin:users\", \"admin:settings\", \"admin:site_management\"]'
            await db.commit()
            print('✅ 管理員權限已更新')
        else:
            # 創建新管理員
            admin_user = User(
                username='admin',
                email='admin@ck-missive.com',
                full_name='系統管理員',
                is_active=True,
                is_admin=True,
                is_superuser=True,
                role='superuser',
                auth_provider='email',
                email_verified=True,
                permissions='[\"documents:read\", \"documents:create\", \"documents:edit\", \"documents:delete\", \"projects:read\", \"projects:create\", \"projects:edit\", \"projects:delete\", \"agencies:read\", \"agencies:create\", \"agencies:edit\", \"agencies:delete\", \"vendors:read\", \"vendors:create\", \"vendors:edit\", \"vendors:delete\", \"calendar:read\", \"calendar:edit\", \"reports:view\", \"reports:export\", \"system_docs:read\", \"system_docs:create\", \"system_docs:edit\", \"system_docs:delete\", \"admin:users\", \"admin:settings\", \"admin:site_management\"]'
            )
            db.add(admin_user)
            await db.commit()
            print('✅ 管理員用戶創建完成')
        break

asyncio.run(create_admin())
"""
    return execute_in_backend(script)

def init_navigation():
    """初始化導航資料"""
    print("=== 初始化導航資料 ===")

    script = """
import asyncio
from app.db.database import get_async_db
from app.extended.models import SiteNavigationItem
from sqlalchemy import select

async def create_navigation():
    async for db in get_async_db():
        # 檢查是否已有導航資料
        nav_query = select(SiteNavigationItem)
        result = await db.execute(nav_query)
        existing_nav = result.scalars().all()

        if existing_nav:
            print(f'✅ 導航資料已存在 ({len(existing_nav)} 項)')
        else:
            nav_items = [
                {
                    'title': '儀表板',
                    'key': 'dashboard',
                    'path': '/dashboard',
                    'icon': 'DashboardOutlined',
                    'sort_order': 1,
                    'level': 1,
                    'description': '系統概覽和統計資訊'
                },
                {
                    'title': '公文管理',
                    'key': 'documents',
                    'path': '/documents',
                    'icon': 'FileTextOutlined',
                    'sort_order': 2,
                    'level': 1,
                    'description': '公文收發和管理'
                },
                {
                    'title': '承攬案件',
                    'key': 'contract-cases',
                    'path': '/contract-cases',
                    'icon': 'ContainerOutlined',
                    'sort_order': 3,
                    'level': 1,
                    'description': '專案和合約管理'
                },
                {
                    'title': '機關管理',
                    'key': 'agencies',
                    'path': '/agencies',
                    'icon': 'BankOutlined',
                    'sort_order': 4,
                    'level': 1,
                    'description': '政府機關資料管理'
                },
                {
                    'title': '廠商管理',
                    'key': 'vendors',
                    'path': '/vendors',
                    'icon': 'ShopOutlined',
                    'sort_order': 5,
                    'level': 1,
                    'description': '協力廠商資料管理'
                },
                {
                    'title': '系統管理',
                    'key': 'admin',
                    'path': '/admin',
                    'icon': 'SettingOutlined',
                    'sort_order': 6,
                    'level': 1,
                    'description': '系統設定和用戶管理',
                    'permission_required': '[\"admin:settings\"]'
                }
            ]

            for item_data in nav_items:
                nav_item = SiteNavigationItem(**item_data)
                db.add(nav_item)

            await db.commit()
            print(f'✅ 創建了 {len(nav_items)} 個導航項目')
        break

asyncio.run(create_navigation())
"""
    return execute_in_backend(script)

def init_sample_data():
    """初始化範例資料"""
    print("=== 初始化範例資料 ===")

    script = """
import asyncio
from app.db.database import get_async_db
from app.extended.models import GovernmentAgency, PartnerVendor
from sqlalchemy import select

async def create_sample_data():
    async for db in get_async_db():
        # 檢查政府機關資料
        agency_query = select(GovernmentAgency)
        result = await db.execute(agency_query)
        existing_agencies = result.scalars().all()

        if not existing_agencies:
            # 創建範例政府機關
            agencies = [
                {
                    'agency_name': '內政部',
                    'agency_code': 'MOI',
                    'agency_type': '中央政府',
                    'contact_person': '承辦人員',
                    'phone': '02-8195-8151',
                    'address': '台北市中正區徐州路5號'
                },
                {
                    'agency_name': '台北市政府',
                    'agency_code': 'TCG',
                    'agency_type': '地方政府',
                    'contact_person': '承辦人員',
                    'phone': '02-2720-8889',
                    'address': '台北市信義區市府路1號'
                }
            ]

            for agency_data in agencies:
                agency = GovernmentAgency(**agency_data)
                db.add(agency)

            print(f'✅ 創建了 {len(agencies)} 個政府機關')

        # 檢查廠商資料
        vendor_query = select(PartnerVendor)
        result = await db.execute(vendor_query)
        existing_vendors = result.scalars().all()

        if not existing_vendors:
            # 創建範例廠商
            vendors = [
                {
                    'vendor_name': '測繪技術有限公司',
                    'vendor_code': 'SURVEY001',
                    'business_type': '測量製圖',
                    'contact_person': '業務經理',
                    'phone': '02-1234-5678',
                    'email': 'contact@survey.com',
                    'address': '台北市大安區復興南路一段',
                    'rating': 4
                },
                {
                    'vendor_name': '工程顧問股份有限公司',
                    'vendor_code': 'ENG001',
                    'business_type': '工程顧問',
                    'contact_person': '專案經理',
                    'phone': '02-8765-4321',
                    'email': 'info@engineering.com',
                    'address': '台北市中山區南京東路二段',
                    'rating': 5
                }
            ]

            for vendor_data in vendors:
                vendor = PartnerVendor(**vendor_data)
                db.add(vendor)

            print(f'✅ 創建了 {len(vendors)} 個協力廠商')

        await db.commit()
        break

asyncio.run(create_sample_data())
"""
    return execute_in_backend(script)

def main():
    """主要執行函數"""
    print("=== 完整資料庫初始化開始 ===")

    # 等待服務啟動
    print("[INFO] 等待資料庫服務就緒...")
    time.sleep(5)

    success = True

    # 1. 初始化表結構
    if not init_tables():
        success = False

    # 2. 初始化管理員用戶
    if not init_admin_user():
        success = False

    # 3. 初始化導航資料
    if not init_navigation():
        success = False

    # 4. 初始化範例資料
    if not init_sample_data():
        success = False

    if success:
        print("\n🎉 完整資料庫初始化完成！")
        print("\n管理員登入資訊：")
        print("  用戶名: admin")
        print("  電子郵件: admin@ck-missive.com")
        print("  角色: 系統管理員")
        print("\n系統現在可以正常使用了！")
    else:
        print("\n❌ 資料庫初始化過程中發生錯誤")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)