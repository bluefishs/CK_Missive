"""
PostgreSQL 非同步資料庫連接設定
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# -- 非同步設定 --

# PostgreSQL 非同步驅動設定
async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# 建立非同步引擎（簡化配置以修復連接問題）
engine = create_async_engine(
    async_db_url,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    future=True,  # SQLAlchemy 2.0 style
    connect_args={
        "server_settings": {
            "application_name": "ck_missive_app",
        }
    }
)

# 建立非同步會話工廠
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 基礎模型類別 (從 sqlalchemy.orm 匯入)
# 所有資料庫模型(Table)都應繼承此基類，以確保它們被正確註冊到 SQLAlchemy 的 metadata 中。
# 這對於 Alembic 自動生成資料庫遷移腳本至關重要。
Base = declarative_base()

async def get_async_db() -> AsyncSession:
    """取得非同步資料庫會話的依賴項"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}", exc_info=True)
            raise
        finally:
            await session.close()

# -- (可選) 同步操作，用於腳本或 Alembic --
# 雖然應用程式本身是非同步的，但某些腳本可能需要同步操作
from sqlalchemy import create_engine

sync_engine = create_engine(settings.DATABASE_URL)
Base.metadata.bind = sync_engine

def create_tables():
    """建立所有資料表 (同步操作)"""
    Base.metadata.create_all(sync_engine)
    logger.info("Database tables created successfully")

def drop_tables():
    """刪除所有資料表 (同步操作, 謹慎使用)"""
    Base.metadata.drop_all(sync_engine)
    logger.warning("All database tables dropped")
