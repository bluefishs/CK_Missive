#!/usr/bin/env python3
"""
修復資料庫架構腳本
重新建立 users 和 user_sessions 表格以確保符合模型定義
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.extended.models import Base

async def fix_database_schema():
    """修復資料庫架構"""
    
    # 建立非同步引擎
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    try:
        async with engine.begin() as conn:
            print("正在修復資料庫架構...")
            
            # 1. 先刪除現有的表格 (如果存在)
            print("刪除現有的 user_sessions 表格...")
            await conn.execute(text("DROP TABLE IF EXISTS user_sessions CASCADE;"))
            
            print("刪除現有的 users 表格...")
            await conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
            
            # 2. 重新建立表格
            print("重新建立 users 和 user_sessions 表格...")
            await conn.run_sync(Base.metadata.create_all)
            
            print("資料庫架構修復完成！")
            print("\n建立的資料表:")
            print("- users (使用者表，包含 password_hash 欄位)")
            print("- user_sessions (使用者會話表)")
            
    except Exception as e:
        print(f"修復資料庫架構時發生錯誤: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("開始修復資料庫架構...")
    print(f"資料庫: {settings.DATABASE_URL}")
    
    asyncio.run(fix_database_schema())
    
    print("\n資料庫架構修復完成！")
    print("\n後續步驟:")
    print("1. 執行 python create_test_users.py 建立測試使用者")
    print("2. 啟動後端服務: python main.py")
    print("3. 測試登入功能")