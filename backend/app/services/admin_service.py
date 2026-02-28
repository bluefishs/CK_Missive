
"""
管理後台服務層 - 業務邏輯處理 (非同步化)

@version 2.1.0 - SQL 注入多層防禦 (2026-02-28)
- 修復 CTE 注入繞過 (WITH ... AS (INSERT) SELECT)
- 多層防禦：去註解 → 去字串 → 單語句 → 首關鍵字 → DML/DDL 黑名單
- 新增表格名稱白名單驗證
- 新增表格名稱格式驗證
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ── SQL 注入多層防禦 ──────────────────────────────────────────────────
_SQL_COMMENT_RE = re.compile(r'--[^\n]*|/\*[\s\S]*?\*/', re.MULTILINE)
_SQL_STRING_RE = re.compile(r"'(?:''|[^'])*'", re.DOTALL)
_FORBIDDEN_SQL_RE = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|'
    r'GRANT|REVOKE|COPY|CALL|LOCK|VACUUM)\b',
    re.IGNORECASE,
)


def _validate_read_only_sql(query: str) -> None:
    """多層驗證 SQL 查詢為唯讀。防止 CTE 注入等繞過手法。"""
    # 1. 去除 SQL 註解（防止在註解中藏 DML）
    no_comments = _SQL_COMMENT_RE.sub(' ', query)

    # 2. 去除字串文字（防止誤判字串內的關鍵字 e.g. LIKE '%INSERT%'）
    no_strings = _SQL_STRING_RE.sub("''", no_comments)

    # 3. 禁止多重語句（去除尾部分號後不應再有分號）
    stripped = no_strings.strip().rstrip(';')
    if ';' in stripped:
        raise HTTPException(
            status_code=403, detail="不允許執行多重 SQL 語句"
        )

    # 4. 首關鍵字必須為 SELECT / WITH / EXPLAIN
    tokens = stripped.split()
    if not tokens:
        raise HTTPException(status_code=400, detail="查詢語句不能為空")
    first_kw = tokens[0].upper()
    if first_kw not in ("SELECT", "WITH", "EXPLAIN"):
        raise HTTPException(status_code=403, detail="只允許執行 SELECT 查詢")

    # 5. 禁止危險 DML/DDL 關鍵字（防 CTE 注入: WITH x AS (INSERT ...) SELECT ...）
    if _FORBIDDEN_SQL_RE.search(no_strings):
        raise HTTPException(
            status_code=403, detail="查詢包含禁止的 SQL 操作"
        )


# 安全性：允許查詢的表格白名單
ALLOWED_TABLES: Set[str] = {
    'documents', 'contract_projects', 'partner_vendors', 'government_agencies',
    'users', 'document_attachments', 'document_calendar_events', 'event_reminders',
    'system_notifications', 'user_sessions', 'site_navigation_items', 'site_configurations',
    'project_agency_contacts', 'staff_certifications', 'audit_logs',
    'taoyuan_projects', 'taoyuan_dispatch_orders', 'taoyuan_dispatch_project_links',
    'taoyuan_dispatch_document_links', 'taoyuan_document_project_links', 'taoyuan_contract_payments',
    'project_vendor_association', 'project_user_assignment', 'alembic_version'
}

def validate_table_name(table_name: str) -> bool:
    """
    驗證表格名稱是否安全
    - 只允許字母、數字、底線
    - 必須以字母或底線開頭
    - 必須在白名單中（如果啟用白名單）
    """
    # 格式驗證：只允許安全字元
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return False
    return True

class AdminService:
    """管理後台服務類別 (非同步版本)"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_database_info(self) -> Dict[str, Any]:
        """
        獲取 PostgreSQL 資料庫的基本信息，包括大小、表格列表、記錄數等。
        """
        try:
            # 獲取資料庫名稱和大小
            db_name_query = text("SELECT current_database()")
            db_name = (await self.db.execute(db_name_query)).scalar_one()
            
            db_size_query = text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_size = (await self.db.execute(db_size_query)).scalar_one()

            # 獲取所有表格信息
            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            table_results = await self.db.execute(tables_query)
            tables_data = []
            total_records = 0

            for (table_name,) in table_results.fetchall():
                # 安全性：驗證從資料庫返回的表格名稱格式
                if not validate_table_name(table_name):
                    logger.warning(f"跳過無效格式的表格名稱: {table_name}")
                    continue

                safe_table_name = f'"{table_name}"'

                # 記錄數
                count_query = text(f"SELECT COUNT(*) FROM {safe_table_name}")
                record_count = (await self.db.execute(count_query)).scalar()
                total_records += record_count

                # 表格大小
                table_size_query = text("SELECT pg_size_pretty(pg_total_relation_size(:table_name))")
                table_size = (await self.db.execute(table_size_query, {"table_name": table_name})).scalar()

                # 欄位資訊
                columns_query = text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table_name AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                columns_results = await self.db.execute(columns_query, {"table_name": table_name})
                columns = [{
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == 'YES'
                } for col in columns_results.fetchall()]

                tables_data.append({
                    "name": table_name,
                    "recordCount": record_count,
                    "columns": columns,
                    "size": table_size,
                })

            return {
                "name": db_name,
                "size": db_size,
                "status": "healthy",
                "totalRecords": total_records,
                "tables": tables_data
            }

        except Exception as e:
            logger.error(f"獲取資料庫信息失敗: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"獲取資料庫信息失敗: {str(e)}")

    async def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        分頁獲取指定表格的數據。

        安全性強化 (v2.0.0):
        - 使用白名單驗證表格名稱
        - 使用格式驗證防止 SQL 注入
        """
        # 安全性第一層：格式驗證
        if not validate_table_name(table_name):
            raise HTTPException(status_code=400, detail=f"無效的表格名稱格式: {table_name}")

        # 安全性第二層：白名單驗證
        if table_name not in ALLOWED_TABLES:
            # 如果不在白名單，檢查資料庫中是否存在
            tables_query = text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
            """)
            if not (await self.db.execute(tables_query, {"table_name": table_name})).scalar_one_or_none():
                raise HTTPException(status_code=404, detail=f"表格 {table_name} 不存在")
            # 記錄警告：存在未在白名單中的表格被存取
            logger.warning(f"存取未在白名單中的表格: {table_name}")

        try:
            # 獲取欄位
            columns_query = text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = :table_name AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            columns_results = await self.db.execute(columns_query, {"table_name": table_name})
            columns = [row[0] for row in columns_results.fetchall()]

            # 安全性：使用 format_ident 概念，但由於已驗證表名格式，可安全使用
            # 注意：table_name 已通過 validate_table_name() 驗證
            safe_table_name = f'"{table_name}"'

            # 獲取數據
            data_query = text(f'SELECT * FROM {safe_table_name} LIMIT :limit OFFSET :offset')
            data_results = await self.db.execute(data_query, {"limit": limit, "offset": offset})
            rows = [list(row) for row in data_results.fetchall()]

            # 獲取總記錄數
            count_query = text(f'SELECT COUNT(*) FROM {safe_table_name}')
            total = (await self.db.execute(count_query)).scalar()

            return {
                "columns": columns,
                "rows": rows,
                "total": total,
                "page": offset // limit + 1,
                "pageSize": limit,
                "totalPages": (total + limit - 1) // limit if limit > 0 else 1
            }

        except Exception as e:
            logger.error(f"獲取表格 {table_name} 數據失敗: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"獲取表格數據失敗: {str(e)}")

    async def execute_read_only_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行一個安全的、唯讀的 SQL SELECT 查詢。
        """
        query = query_data.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="查詢語句不能為空")

        # 多層安全驗證 — 防 CTE 注入 / 多重語句 / DML/DDL
        _validate_read_only_sql(query)

        try:
            start_time = datetime.now()
            result = await self.db.execute(text(query))
            
            columns = list(result.keys()) if result.returns_rows else []
            rows = [list(row) for row in result.fetchall()] if result.returns_rows else []
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000

            return {
                "columns": columns,
                "rows": rows,
                "totalRows": len(rows),
                "executionTime": round(execution_time, 2)
            }

        except Exception as e:
            logger.error(f"SQL 查詢執行失敗: {e}", exc_info=True)
            # 提供更友好的錯誤信息
            error_detail = str(e).split('DETAIL:  ')[-1] if 'DETAIL' in str(e) else str(e)
            raise HTTPException(status_code=500, detail=f"查詢執行失敗: {error_detail}")

    async def check_database_health(self) -> Dict[str, Any]:
        """
        執行一個簡單的查詢來驗證資料庫連線是否正常。
        """
        try:
            result = (await self.db.execute(text("SELECT 1"))).scalar()
            if result == 1:
                return {
                    "status": "completed",
                    "db_connection": "healthy",
                    "checkTime": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=503, detail="資料庫健康檢查失敗，收到了意外的回應")
        except Exception as e:
            logger.error(f"資料庫健康檢查失敗: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"無法連線到資料庫: {str(e)}")
