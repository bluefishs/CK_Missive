
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# 直接寫死設定，繞過 .env 依賴
os.environ['SECRET_KEY'] = 'temporary_secret_key_for_setup_only_12345'
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://ck_user:ck_password@localhost:5434/ck_documents'

# 延後 import，確保環境變數已設定
from app.extended.models import User, Base
from app.core.auth_service import AuthService

# --- 使用者設定 ---
USER_EMAIL = "user@ck-missive.com"
USER_USERNAME = "user"
USER_PASSWORD = "user123"
USER_FULL_NAME = "一般使用者"

# --- 直接建立資料庫連線 ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_db_and_tables():
    """建立所有資料表"""
    async with engine.begin() as conn:
        print("正在建立資料庫資料表...")
        await conn.run_sync(Base.metadata.create_all)
        print("資料表建立完成。")

async def setup_user():
    """檢查並建立/更新指定的使用者帳號"""
    print("正在初始化資料庫會話...")
    db: AsyncSession = AsyncSessionLocal()
    print(f"正在處理帳號: {USER_EMAIL}")

    try:
        result = await db.execute(select(User).where(User.email == USER_EMAIL))
        user = result.scalar_one_or_none()

        password_hash = AuthService.get_password_hash(USER_PASSWORD)

        if user:
            print(f"找到現有帳號: {user.email}")
            user.password_hash = password_hash
            user.is_active = True
            user.is_admin = False # 確保為一般使用者
            user.is_superuser = False # 確保為一般使用者
            print("帳號已更新並啟用，密碼已重設。")
        else:
            print("找不到該帳號，正在建立新帳號...")
            user = User(
                email=USER_EMAIL, username=USER_USERNAME, full_name=USER_FULL_NAME,
                password_hash=password_hash, is_active=True, is_admin=False, is_superuser=False,
                email_verified=True, auth_provider="email"
            )
            db.add(user)
            print("新帳號建立成功。")
        
        await db.commit()
        print("資料庫操作完成。")

    except Exception as e:
        print(f"發生錯誤: {e}")
        await db.rollback()
    finally:
        await db.close()
        print("資料庫連線已關閉。")

async def main():
    await create_db_and_tables()
    await setup_user()

if __name__ == "__main__":
    print("開始執行使用者建立腳本 (直接連線模式)...")
    asyncio.run(main())
    print("腳本執行完畢。")
