#!/usr/bin/env python3
"""
建立認證系統的資料庫遷移腳本
執行此腳本來建立使用者認證和會話管理所需的資料表
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.extended.models import Base

async def create_auth_tables():
    """建立認證相關的資料表"""
    
    # 建立非同步引擎
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    try:
        async with engine.begin() as conn:
            print("正在建立認證系統相關資料表...")
            
            # 建立所有表格
            await conn.run_sync(Base.metadata.create_all)
            
            print("認證系統資料表建立完成！")
            print("\n建立的資料表:")
            print("- users (使用者表)")
            print("- user_sessions (使用者會話表)")
            
    except Exception as e:
        print(f"建立資料表時發生錯誤: {e}")
        raise
    finally:
        await engine.dispose()

async def insert_demo_data():
    """插入示範資料"""
    from app.core.auth_service import AuthService
    from app.extended.models import User
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    try:
        async with async_session() as session:
            print("\n正在建立示範使用者...")
            
            # 建立管理員使用者
            admin_user = User(
                email="admin@ck-missive.com",
                username="admin",
                full_name="系統管理員",
                password_hash=AuthService.get_password_hash("admin123"),
                auth_provider="email",
                is_active=True,
                is_admin=True,
                role="admin",
                email_verified=True,
                permissions='["documents:read", "documents:create", "documents:edit", "documents:delete", "projects:read", "projects:create", "projects:edit", "projects:delete", "agencies:read", "agencies:create", "agencies:edit", "agencies:delete", "vendors:read", "vendors:create", "vendors:edit", "vendors:delete", "admin:users", "admin:settings", "admin:site_management", "reports:view", "reports:export", "calendar:read", "calendar:edit"]'
            )
            
            # 建立測試使用者
            test_user = User(
                email="user@ck-missive.com",
                username="testuser",
                full_name="測試使用者",
                password_hash=AuthService.get_password_hash("user123"),
                auth_provider="email",
                is_active=True,
                is_admin=False,
                role="user",
                email_verified=True,
                permissions='["documents:read", "projects:read", "agencies:read", "vendors:read", "calendar:read", "reports:view"]'
            )
            
            session.add(admin_user)
            session.add(test_user)
            await session.commit()
            
            print("示範使用者建立完成！")
            print("\n可用的測試帳號:")
            print("管理員: admin@ck-missive.com / admin123")
            print("一般使用者: user@ck-missive.com / user123")
            
    except Exception as e:
        print(f"建立示範資料時發生錯誤: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("開始建立認證系統...")
    print(f"資料庫: {settings.DATABASE_URL}")
    
    # 建立資料表
    asyncio.run(create_auth_tables())
    
    # 詢問是否要建立示範資料
    create_demo = input("\n是否要建立示範使用者資料？(y/N): ").lower().strip()
    if create_demo in ['y', 'yes']:
        asyncio.run(insert_demo_data())
    
    print("\n認證系統初始化完成！")
    print("\n後續步驟:")
    print("1. 啟動後端服務: python main.py")
    print("2. 啟動前端服務: cd frontend && npm run dev")
    print("3. 訪問 http://localhost:3008/login 進行登入測試")
    print("4. 設定 Google OAuth Client ID (如需要 Google 登入功能)")