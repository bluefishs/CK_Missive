"""
PostgreSQL 非同步資料庫連接設定

v2.0.0 - 連線池韌性強化 (2026-02-09)
- 新增 statement_timeout 防止查詢無限等待
- 使用 settings 讀取連線池參數
- 改善 get_async_db 錯誤處理（pool exhaustion、statement_timeout）
- 新增 pool event listeners（DEBUG 模式）
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy import event

from app.core.config import settings

logger = logging.getLogger(__name__)

# -- 非同步設定 --

# PostgreSQL 非同步驅動設定
async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# 建立非同步引擎（增強連接穩定性）
engine = create_async_engine(
    async_db_url,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,                      # 每次取得連接前檢查連接是否有效
    pool_recycle=settings.POOL_RECYCLE,       # 連接回收時間（秒）
    pool_size=settings.POOL_SIZE,            # 連接池大小
    max_overflow=settings.MAX_OVERFLOW,      # 最大溢出連接數
    pool_timeout=30,                          # 等待連接的超時時間
    future=True,                              # SQLAlchemy 2.0 style
    connect_args={
        "server_settings": {
            "application_name": "ck_missive_app",
            "statement_timeout": str(settings.STATEMENT_TIMEOUT),  # PostgreSQL 端查詢超時（毫秒）
        },
        "command_timeout": 60,               # asyncpg 客戶端命令超時（秒）
    }
)

# -- Pool event listeners --

@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """記錄新資料庫連線建立"""
    logger.info("New database connection established")


@event.listens_for(engine.sync_engine, "invalidate")
def receive_invalidate(dbapi_connection, connection_record, exception):
    """記錄連線失效事件（通常由 pool_pre_ping 觸發）"""
    if exception:
        logger.warning(f"Connection invalidated due to: {exception}")
    else:
        logger.info("Connection invalidated (soft)")


# 建立非同步會話工廠
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 別名 - 供 UnitOfWork 等模組使用
async_session_maker = AsyncSessionLocal

# 基礎模型類別 (從 sqlalchemy.orm 匯入)
# 所有資料庫模型(Table)都應繼承此基類，以確保它們被正確註冊到 SQLAlchemy 的 metadata 中。
# 這對於 Alembic 自動生成資料庫遷移腳本至關重要。
Base = declarative_base()

async def get_async_db() -> AsyncSession:
    """
    取得非同步資料庫會話的依賴項

    增強錯誤處理：
    - SATimeoutError: 連線池耗盡
    - statement_timeout: SQL 查詢超時
    - connection_lost: 連線中斷
    """
    try:
        session = AsyncSessionLocal()
    except SATimeoutError:
        logger.error(
            "Database connection pool exhausted. "
            f"pool_size={settings.POOL_SIZE}, max_overflow={settings.MAX_OVERFLOW}"
        )
        raise

    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        error_msg = str(e).lower()
        if "connection_lost" in error_msg:
            logger.warning(f"Database connection lost, session rolled back: {e}")
        elif "statement_timeout" in error_msg or "canceling statement" in error_msg:
            logger.warning(f"Query exceeded statement_timeout ({settings.STATEMENT_TIMEOUT}ms): {e}")
        else:
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
