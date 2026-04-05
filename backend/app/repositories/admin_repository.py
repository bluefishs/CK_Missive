"""
AdminRepository - 管理後台資料存取層

封裝所有管理後台相關的原生 SQL 查詢，將資料庫操作從 AdminService 分離。

本 Repository 不繼承 BaseRepository[T]，因為管理後台操作使用
information_schema 及原生 SQL 查詢，不綁定特定 ORM 模型。

版本: 1.0.0
建立日期: 2026-04-05
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _validate_table_name_format(table_name: str) -> bool:
    """
    驗證表格名稱格式是否安全（嚴格小寫識別符）。

    Security: Table names cannot be SQL-parameterized, so we enforce a
    strict lowercase identifier pattern as defense-in-depth.
    """
    if not re.match(r'^[a-z_][a-z0-9_]*$', table_name):
        return False
    return True


class AdminRepository:
    """
    管理後台資料存取類別

    封裝 information_schema 查詢、表格資料讀取、資料庫健康檢查
    及完整性驗證等原生 SQL 操作。

    Attributes:
        db: AsyncSession 資料庫連線
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 超時設定
    # =========================================================================

    async def set_statement_timeout(self, seconds: int) -> None:
        """設定當前交易的語句超時（SET LOCAL 僅影響當前交易）。"""
        await self.db.execute(
            text(f"SET LOCAL statement_timeout = '{seconds}s'")
        )

    # =========================================================================
    # 資料庫基本資訊
    # =========================================================================

    async def get_current_database_name(self) -> str:
        """取得當前資料庫名稱。"""
        result = await self.db.execute(text("SELECT current_database()"))
        return result.scalar_one()

    async def get_database_size_pretty(self) -> str:
        """取得當前資料庫大小（人類可讀格式）。"""
        result = await self.db.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        )
        return result.scalar_one()

    # =========================================================================
    # 表格資訊查詢
    # =========================================================================

    async def get_public_table_names(self) -> List[str]:
        """取得 public schema 中所有基礎表格名稱（按名稱排序）。"""
        result = await self.db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        return [row[0] for row in result.fetchall()]

    async def get_table_record_count(self, table_name: str) -> int:
        """
        取得指定表格的記錄數。

        Security: table_name 必須已通過 _validate_table_name_format() 驗證。
        使用雙引號包裹防止保留字衝突。
        """
        safe_name = f'"{table_name}"'
        result = await self.db.execute(text(f"SELECT COUNT(*) FROM {safe_name}"))
        return result.scalar() or 0

    async def get_table_size_pretty(self, table_name: str) -> str:
        """取得指定表格的大小（人類可讀格式，使用參數化查詢）。"""
        result = await self.db.execute(
            text("SELECT pg_size_pretty(pg_total_relation_size(:table_name))"),
            {"table_name": table_name},
        )
        return result.scalar()

    async def get_table_columns(
        self, table_name: str
    ) -> List[Dict[str, Any]]:
        """
        取得指定表格的欄位資訊。

        Returns:
            欄位列表，每項包含 name, type, nullable
        """
        result = await self.db.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = :table_name AND table_schema = 'public'
                ORDER BY ordinal_position
            """),
            {"table_name": table_name},
        )
        return [
            {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
            for row in result.fetchall()
        ]

    async def get_table_column_names(self, table_name: str) -> List[str]:
        """取得指定表格的欄位名稱列表（按欄位順序）。"""
        result = await self.db.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = :table_name AND table_schema = 'public'
                ORDER BY ordinal_position
            """),
            {"table_name": table_name},
        )
        return [row[0] for row in result.fetchall()]

    # =========================================================================
    # 表格資料讀取
    # =========================================================================

    async def get_table_rows(
        self, table_name: str, limit: int, offset: int
    ) -> List[list]:
        """
        分頁讀取指定表格的資料列。

        Security: table_name 必須已通過格式驗證與白名單檢查。
        """
        safe_name = f'"{table_name}"'
        result = await self.db.execute(
            text(f"SELECT * FROM {safe_name} LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        )
        return [list(row) for row in result.fetchall()]

    # =========================================================================
    # 任意唯讀查詢執行
    # =========================================================================

    async def execute_raw_select(
        self, query: str
    ) -> Tuple[List[str], List[list]]:
        """
        執行經過驗證的唯讀 SQL 查詢。

        Args:
            query: 已通過 _validate_read_only_sql() 驗證的 SQL 字串

        Returns:
            (columns, rows) 元組
        """
        result = await self.db.execute(text(query))
        columns = list(result.keys()) if result.returns_rows else []
        rows = (
            [list(row) for row in result.fetchall()]
            if result.returns_rows
            else []
        )
        return columns, rows

    # =========================================================================
    # 健康檢查
    # =========================================================================

    async def ping(self) -> int:
        """執行 SELECT 1 驗證資料庫連線。回傳查詢結果。"""
        result = await self.db.execute(text("SELECT 1"))
        return result.scalar()

    # =========================================================================
    # 完整性檢查 — 外鍵
    # =========================================================================

    async def get_foreign_key_constraints(self) -> List[Tuple[str, str, str]]:
        """
        取得 public schema 的所有外鍵約束資訊。

        Returns:
            (table_name, column_name, foreign_table_name) 的列表
        """
        result = await self.db.execute(text("""
            SELECT tc.table_name, kcu.column_name,
                   ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
        """))
        return [(row[0], row[1], row[2]) for row in result.fetchall()]

    async def count_orphan_records(
        self, table: str, column: str, ref_table: str
    ) -> Optional[int]:
        """
        計算指定外鍵關係的孤立記錄數。

        Security: table/column/ref_table 來自 information_schema 且必須
        已通過格式驗證。

        Returns:
            孤立記錄數，若查詢失敗則返回 None
        """
        try:
            result = await self.db.execute(text(f"""
                SELECT COUNT(*) FROM "{table}" t
                LEFT JOIN "{ref_table}" r ON t."{column}" = r.id
                WHERE t."{column}" IS NOT NULL AND r.id IS NULL
            """))
            return result.scalar()
        except Exception:
            # 跳過無法檢查的 FK（可能是非 id 欄位）
            return None
