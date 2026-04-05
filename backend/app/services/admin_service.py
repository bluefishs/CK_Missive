
"""
管理後台服務層 - 業務邏輯處理 (非同步化)

@version 3.0.0 - Repository 層分離 (2026-04-05)
- 原生 SQL 查詢遷移至 AdminRepository
- Service 層專注業務邏輯（格式化、聚合、驗證）
- 保留 SQL 注入多層防禦（驗證邏輯）

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
from fastapi import HTTPException

from app.repositories.admin_repository import AdminRepository, _validate_table_name_format

logger = logging.getLogger(__name__)

# ── SQL 注入多層防禦 ──────────────────────────────────────────────────
_SQL_COMMENT_RE = re.compile(r'--[^\n]*|/\*[\s\S]*?\*/', re.MULTILINE)
_SQL_STRING_RE = re.compile(r"'(?:''|[^'])*'", re.DOTALL)
_FORBIDDEN_SQL_RE = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|'
    r'GRANT|REVOKE|COPY|CALL|LOCK|VACUUM|'
    r'lo_import|lo_export|pg_read_file|pg_read_binary_file|'
    r'pg_write_file|dblink|dblink_exec)\b',
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


# 安全性：允許查詢的表格白名單（與 ORM models 同步）
ALLOWED_TABLES: Set[str] = {
    # core.py
    'users', 'contract_projects', 'partner_vendors', 'government_agencies',
    # document.py
    'documents', 'document_attachments',
    # calendar.py
    'document_calendar_events', 'event_reminders',
    # system.py
    'system_notifications', 'user_sessions', 'site_navigation_items', 'site_configurations',
    'ai_prompt_versions', 'ai_search_history', 'ai_conversation_feedback', 'ai_synonyms',
    # staff.py
    'project_agency_contacts', 'staff_certifications',
    # taoyuan.py
    'taoyuan_projects', 'taoyuan_dispatch_orders', 'taoyuan_dispatch_project_link',
    'taoyuan_dispatch_document_link', 'taoyuan_document_project_link', 'taoyuan_contract_payments',
    'taoyuan_dispatch_work_types', 'taoyuan_dispatch_attachments', 'taoyuan_work_records',
    # entity.py
    'document_entities', 'entity_relations',
    # knowledge_graph.py
    'canonical_entities', 'entity_aliases', 'document_entity_mentions',
    'entity_relationships', 'graph_ingestion_events',
    # ai_analysis.py
    'document_ai_analyses',
    # associations.py
    'project_vendor_association', 'project_user_assignments',
    # system
    'alembic_version',
}

# Re-export for backward compatibility
validate_table_name = _validate_table_name_format


class AdminService:
    """管理後台服務類別 (非同步版本)"""

    # 查詢超時保護（秒）— 使用 SET LOCAL 僅影響當前交易
    QUERY_TIMEOUT_SECONDS = 30
    COUNT_TIMEOUT_SECONDS = 10

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AdminRepository(db)

    async def get_database_info(self) -> Dict[str, Any]:
        """
        獲取 PostgreSQL 資料庫的基本信息，包括大小、表格列表、記錄數等。
        """
        try:
            await self.repo.set_statement_timeout(self.QUERY_TIMEOUT_SECONDS)

            db_name = await self.repo.get_current_database_name()
            db_size = await self.repo.get_database_size_pretty()

            table_names = await self.repo.get_public_table_names()
            tables_data = []
            total_records = 0

            for table_name in table_names:
                # 安全性：驗證從資料庫返回的表格名稱格式
                if not _validate_table_name_format(table_name):
                    logger.warning(f"跳過無效格式的表格名稱: {table_name}")
                    continue

                record_count = await self.repo.get_table_record_count(table_name)
                total_records += record_count

                table_size = await self.repo.get_table_size_pretty(table_name)
                columns = await self.repo.get_table_columns(table_name)

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
            raise HTTPException(status_code=500, detail="獲取資料庫信息失敗，請稍後再試")

    async def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        分頁獲取指定表格的數據。

        安全性強化 (v2.0.0):
        - 使用白名單驗證表格名稱
        - 使用格式驗證防止 SQL 注入
        - limit 上界 500 防止資源耗盡
        """
        # 安全性：限制分頁大小上界
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)

        # 安全性第一層：格式驗證
        if not _validate_table_name_format(table_name):
            raise HTTPException(status_code=400, detail=f"無效的表格名稱格式: {table_name}")

        # 安全性第二層：白名單嚴格驗證（不在白名單中直接拒絕）
        if table_name not in ALLOWED_TABLES:
            logger.warning("拒絕存取未在白名單中的表格: %s", table_name)
            raise HTTPException(status_code=403, detail=f"表格 {table_name} 不允許存取")

        try:
            await self.repo.set_statement_timeout(self.QUERY_TIMEOUT_SECONDS)

            columns = await self.repo.get_table_column_names(table_name)
            rows = await self.repo.get_table_rows(table_name, limit, offset)
            total = await self.repo.get_table_record_count(table_name)

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
            raise HTTPException(status_code=500, detail="獲取表格數據失敗，請稍後再試")

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
            await self.repo.set_statement_timeout(self.QUERY_TIMEOUT_SECONDS)

            start_time = datetime.now()
            columns, rows = await self.repo.execute_raw_select(query)
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
            raise HTTPException(status_code=500, detail="查詢執行失敗，請檢查 SQL 語法")

    async def check_database_health(self) -> Dict[str, Any]:
        """
        執行一個簡單的查詢來驗證資料庫連線是否正常。
        """
        try:
            result = await self.repo.ping()
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
            raise HTTPException(status_code=503, detail="無法連線到資料庫，請稍後再試")

    async def check_database_integrity(self) -> Dict[str, Any]:
        """
        檢查資料庫完整性：外鍵約束、孤立記錄等。
        """
        issues = []

        await self.repo.set_statement_timeout(self.COUNT_TIMEOUT_SECONDS)

        fk_rows = await self.repo.get_foreign_key_constraints()

        for table, column, ref_table in fk_rows:
            # Security: table/column/ref_table come from information_schema
            # (trusted DB catalog), but we still validate format as defense-in-depth.
            if not (_validate_table_name_format(table)
                    and _validate_table_name_format(ref_table)
                    and re.match(r'^[a-z_][a-z0-9_]*$', column)):
                logger.warning(
                    "Skipping orphan check for invalid identifier: "
                    "table=%s column=%s ref_table=%s", table, column, ref_table
                )
                continue

            orphan_count = await self.repo.count_orphan_records(
                table, column, ref_table
            )
            if orphan_count and orphan_count > 0:
                issues.append({
                    "type": "orphan_record",
                    "table": table,
                    "column": column,
                    "ref_table": ref_table,
                    "count": orphan_count,
                    "severity": "warning",
                })

        return {
            "checkTime": datetime.now().isoformat(),
            "totalIssues": len(issues),
            "issues": issues,
            "status": "healthy" if len(issues) == 0 else "warning",
            "fk_count": len(fk_rows),
        }
