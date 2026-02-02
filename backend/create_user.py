#!/usr/bin/env python3
"""
使用者建立腳本

@version 2.0.0 - 安全性修正：移除硬編碼密碼 (2026-02-02)

使用方式:
    python create_user.py --email <email> --password <password>

環境變數:
    必須在 .env 中設定資料庫連線資訊
"""
import asyncio
import os
import sys
import argparse
import getpass
import logging
from dotenv import load_dotenv

# 先載入環境變數
load_dotenv('../.env')
load_dotenv('.env')

# 驗證必要的環境變數
required_vars = ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'SECRET_KEY']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"❌ 缺少必要的環境變數: {', '.join(missing_vars)}")
    print("請確認 .env 檔案設定正確")
    sys.exit(1)

# 確保 DATABASE_URL 設定正確
db_user = os.environ.get('POSTGRES_USER')
db_password = os.environ.get('POSTGRES_PASSWORD')
db_host = os.environ.get('POSTGRES_HOST', 'localhost')
db_port = os.environ.get('POSTGRES_PORT', '5434')
db_name = os.environ.get('POSTGRES_DB')

os.environ['DATABASE_URL'] = f'postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# 延後 import，確保環境變數已設定
from app.extended.models import User, Base
from app.core.auth_service import AuthService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 直接建立資料庫連線 ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables():
    """建立所有資料表"""
    async with engine.begin() as conn:
        logger.info("正在建立資料庫資料表...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("資料表建立完成。")


async def setup_user(email: str, username: str, password: str, full_name: str, is_admin: bool = False):
    """檢查並建立/更新指定的使用者帳號"""
    logger.info("正在初始化資料庫會話...")
    db: AsyncSession = AsyncSessionLocal()
    logger.info(f"正在處理帳號: {email}")

    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        password_hash = AuthService.get_password_hash(password)

        if user:
            logger.info(f"找到現有帳號: {user.email}")
            user.password_hash = password_hash
            user.is_active = True
            user.is_admin = is_admin
            user.is_superuser = False
            logger.info("帳號已更新並啟用，密碼已重設。")
        else:
            logger.info("找不到該帳號，正在建立新帳號...")
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                password_hash=password_hash,
                is_active=True,
                is_admin=is_admin,
                is_superuser=False,
                email_verified=True,
                auth_provider="email"
            )
            db.add(user)
            logger.info("新帳號建立成功。")

        await db.commit()
        logger.info("資料庫操作完成。")

    except Exception as e:
        logger.error(f"發生錯誤: {e}")
        await db.rollback()
        return False
    finally:
        await db.close()
        logger.info("資料庫連線已關閉。")

    return True


async def main(email: str, username: str, password: str, full_name: str, is_admin: bool):
    await create_db_and_tables()
    return await setup_user(email, username, password, full_name, is_admin)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='建立使用者帳號')
    parser.add_argument('--email', '-e', required=True, help='使用者電子郵件')
    parser.add_argument('--username', '-u', help='使用者名稱 (預設從 email 產生)')
    parser.add_argument('--password', '-p', help='使用者密碼 (如未提供將互動式輸入)')
    parser.add_argument('--full-name', '-n', default='使用者', help='使用者全名')
    parser.add_argument('--admin', '-a', action='store_true', help='設為管理員')
    args = parser.parse_args()

    # 取得密碼
    password = args.password
    if not password:
        password = getpass.getpass("請輸入使用者密碼: ")

    if len(password) < 6:
        logger.error("密碼長度至少需要 6 個字元")
        sys.exit(1)

    # 取得使用者名稱
    username = args.username or args.email.split('@')[0]

    logger.info("開始執行使用者建立腳本...")
    success = asyncio.run(main(args.email, username, password, args.full_name, args.admin))

    if success:
        logger.info("✅ 腳本執行完畢。")
    else:
        logger.error("❌ 腳本執行失敗。")
        sys.exit(1)
