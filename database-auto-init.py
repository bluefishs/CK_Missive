#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料庫自動初始化腳本
解決每次重啟後資料庫為空的問題
"""

import subprocess
import time
import json

def check_database_initialized():
    """檢查資料庫是否已初始化"""
    try:
        # 檢查表是否存在
        result = subprocess.run([
            "docker", "exec", "ck_missive_postgres",
            "psql", "-U", "ck_user", "-d", "ck_documents",
            "-c", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            # 提取表的數量
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if line.strip().isdigit():
                    table_count = int(line.strip())
                    print(f"[INFO] 發現 {table_count} 個資料庫表")
                    return table_count > 0

        print("[WARN] 無法檢查資料庫狀態")
        return False

    except Exception as e:
        print(f"[ERROR] 資料庫檢查失敗: {e}")
        return False

def check_navigation_data():
    """檢查導航資料是否存在"""
    try:
        result = subprocess.run([
            "docker", "exec", "ck_missive_postgres",
            "psql", "-U", "ck_user", "-d", "ck_documents",
            "-c", "SELECT COUNT(*) FROM site_navigation_items;"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if line.strip().isdigit():
                    count = int(line.strip())
                    print(f"[INFO] 發現 {count} 個導航項目")
                    return count > 0

        return False

    except Exception as e:
        print(f"[ERROR] 導航資料檢查失敗: {e}")
        return False

def initialize_database_tables():
    """初始化資料庫表結構"""
    print("[INFO] 正在初始化資料庫表結構...")

    try:
        result = subprocess.run([
            "docker", "exec", "ck_missive_backend", "python", "-c",
            """
import asyncio
from app.db.database import engine, Base
from app.extended.models import *

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✅ 表結構創建完成')

asyncio.run(create_tables())
            """
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("[SUCCESS] 資料庫表結構初始化成功")
            return True
        else:
            print(f"[ERROR] 表結構初始化失敗: {result.stderr}")
            return False

    except Exception as e:
        print(f"[ERROR] 執行初始化失敗: {e}")
        return False

def initialize_navigation_data():
    """初始化導航資料"""
    print("[INFO] 正在創建初始導航資料...")

    try:
        result = subprocess.run([
            "docker", "exec", "ck_missive_backend", "python", "-c",
            """
import asyncio
from app.db.database import get_async_db
from app.extended.models import SiteNavigationItem

async def create_navigation():
    async for db in get_async_db():
        nav_items = [
            {'title': '儀表板', 'key': 'dashboard', 'path': '/dashboard', 'icon': 'DashboardOutlined', 'sort_order': 1, 'level': 1},
            {'title': '公文管理', 'key': 'documents', 'path': '/documents', 'icon': 'FileTextOutlined', 'sort_order': 2, 'level': 1},
            {'title': '承攬案件', 'key': 'contract-cases', 'path': '/contract-cases', 'icon': 'ContainerOutlined', 'sort_order': 3, 'level': 1},
            {'title': '機關管理', 'key': 'agencies', 'path': '/agencies', 'icon': 'BankOutlined', 'sort_order': 4, 'level': 1},
            {'title': '廠商管理', 'key': 'vendors', 'path': '/vendors', 'icon': 'ShopOutlined', 'sort_order': 5, 'level': 1},
            {'title': '系統管理', 'key': 'admin', 'path': '/admin', 'icon': 'SettingOutlined', 'sort_order': 6, 'level': 1}
        ]

        for item_data in nav_items:
            nav_item = SiteNavigationItem(**item_data)
            db.add(nav_item)

        await db.commit()
        print(f'✅ 創建了 {len(nav_items)} 個導航項目')
        break

asyncio.run(create_navigation())
            """
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("[SUCCESS] 導航資料初始化成功")
            return True
        else:
            print(f"[ERROR] 導航資料初始化失敗: {result.stderr}")
            return False

    except Exception as e:
        print(f"[ERROR] 導航資料創建失敗: {e}")
        return False

def wait_for_services():
    """等待服務啟動"""
    print("[INFO] 等待資料庫服務就緒...")

    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            result = subprocess.run([
                "docker", "exec", "ck_missive_postgres",
                "pg_isready", "-U", "ck_user", "-d", "ck_documents"
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                print("[SUCCESS] 資料庫服務已就緒")
                time.sleep(2)  # 額外等待確保完全就緒
                return True

        except Exception:
            pass

        print(f"[WAIT] 等待資料庫啟動... ({attempt + 1}/{max_attempts})")
        time.sleep(2)

    print("[ERROR] 資料庫服務啟動逾時")
    return False

def auto_initialize_database():
    """自動檢查並初始化資料庫"""
    print("=== 資料庫自動初始化檢查 ===")

    # 1. 等待服務啟動
    if not wait_for_services():
        return False

    # 2. 檢查表結構
    tables_exist = check_database_initialized()

    # 3. 初始化表結構（如需要）
    if not tables_exist:
        print("[ACTION] 資料庫表不存在，正在初始化...")
        if not initialize_database_tables():
            return False
    else:
        print("[OK] 資料庫表結構已存在")

    # 4. 檢查導航資料
    navigation_exists = check_navigation_data()

    # 5. 初始化導航資料（如需要）
    if not navigation_exists:
        print("[ACTION] 導航資料不存在，正在創建...")
        if not initialize_navigation_data():
            return False
    else:
        print("[OK] 導航資料已存在")

    print("✅ 資料庫自動初始化完成！")
    return True

if __name__ == "__main__":
    success = auto_initialize_database()
    exit(0 if success else 1)