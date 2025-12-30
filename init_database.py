#!/usr/bin/env python3
"""
資料庫初始化腳本
用於創建所有必要的資料庫表格和初始資料
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# 添加backend目錄到Python路徑
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def initialize_database():
    """初始化資料庫"""
    try:
        # 導入必要的模組
        from app.db.database import create_tables
        from app.db.init_data import create_initial_data

        print("🔄 正在創建資料庫表格...")
        await create_tables()
        print("✅ 資料庫表格創建完成")

        print("🔄 正在創建初始資料...")
        await create_initial_data()
        print("✅ 初始資料創建完成")

        print("🎉 資料庫初始化完成！")

    except ImportError as e:
        print(f"❌ 導入模組失敗: {e}")
        print("🔄 嘗試使用 Docker 執行...")

        # 使用Docker執行
        try:
            result = subprocess.run([
                "docker", "exec", "ck_missive_backend",
                "python", "-c",
                """
import asyncio
from app.db.database import create_tables
from app.db.init_data import create_initial_data

async def main():
    await create_tables()
    await create_initial_data()
    print('Database initialized successfully!')

asyncio.run(main())
                """
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Docker 資料庫初始化成功！")
                print(result.stdout)
            else:
                print(f"❌ Docker 執行失敗: {result.stderr}")

        except FileNotFoundError:
            print("❌ Docker 未找到，請確保 Docker 已安裝並正在運行")

    except Exception as e:
        print(f"❌ 初始化失敗: {e}")

if __name__ == "__main__":
    asyncio.run(initialize_database())