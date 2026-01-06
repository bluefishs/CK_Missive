# -*- coding: utf-8 -*-
"""
資料庫 Schema 驗證工具
Database Schema Validation Utility

用途：
1. 啟動時驗證 SQLAlchemy 模型與資料庫 schema 是否一致
2. 記錄不一致的欄位，協助開發者快速發現問題
3. 可選擇性地阻止啟動或僅發出警告

使用方式：
    from app.core.schema_validator import validate_schema
    await validate_schema(engine, strict=False)
"""
import logging
from typing import Dict, List, Set, Optional, Tuple
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection
from sqlalchemy.orm import DeclarativeMeta

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Schema 驗證錯誤"""
    pass


class SchemaMismatch:
    """Schema 不匹配記錄"""
    def __init__(self, table: str, issue_type: str, details: str):
        self.table = table
        self.issue_type = issue_type
        self.details = details

    def __repr__(self):
        return f"[{self.table}] {self.issue_type}: {self.details}"


async def get_database_columns(conn: AsyncConnection, table_name: str) -> Dict[str, dict]:
    """取得資料庫表格的欄位資訊"""
    query = text("""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = :table_name
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    result = await conn.execute(query, {"table_name": table_name})
    columns = {}
    for row in result:
        columns[row.column_name] = {
            "data_type": row.data_type,
            "is_nullable": row.is_nullable == "YES",
            "default": row.column_default
        }
    return columns


async def get_database_tables(conn: AsyncConnection) -> Set[str]:
    """取得資料庫中所有表格名稱"""
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    """)
    result = await conn.execute(query)
    return {row.table_name for row in result}


def get_model_columns(model_class) -> Dict[str, dict]:
    """取得 SQLAlchemy 模型的欄位資訊"""
    columns = {}
    mapper = inspect(model_class)
    for column in mapper.columns:
        columns[column.name] = {
            "python_type": str(column.type),
            "nullable": column.nullable,
            "primary_key": column.primary_key
        }
    return columns


async def validate_table(
    conn: AsyncConnection,
    table_name: str,
    model_columns: Dict[str, dict]
) -> List[SchemaMismatch]:
    """驗證單一表格的 schema"""
    mismatches = []

    # 取得資料庫欄位
    db_columns = await get_database_columns(conn, table_name)

    if not db_columns:
        mismatches.append(SchemaMismatch(
            table_name, "TABLE_NOT_FOUND",
            f"資料庫中找不到表格 '{table_name}'"
        ))
        return mismatches

    db_column_names = set(db_columns.keys())
    model_column_names = set(model_columns.keys())

    # 檢查模型有但資料庫沒有的欄位
    missing_in_db = model_column_names - db_column_names
    for col in missing_in_db:
        mismatches.append(SchemaMismatch(
            table_name, "COLUMN_MISSING_IN_DB",
            f"模型欄位 '{col}' 在資料庫中不存在"
        ))

    # 檢查資料庫有但模型沒有的欄位
    missing_in_model = db_column_names - model_column_names
    for col in missing_in_model:
        mismatches.append(SchemaMismatch(
            table_name, "COLUMN_MISSING_IN_MODEL",
            f"資料庫欄位 '{col}' 在模型中未定義"
        ))

    return mismatches


async def validate_schema(
    engine: AsyncEngine,
    base: DeclarativeMeta,
    strict: bool = False,
    tables_to_check: Optional[List[str]] = None
) -> Tuple[bool, List[SchemaMismatch]]:
    """
    驗證 SQLAlchemy 模型與資料庫 schema 是否一致

    Args:
        engine: AsyncEngine 實例
        base: SQLAlchemy Base 類別
        strict: 是否在發現不一致時拋出錯誤
        tables_to_check: 指定要檢查的表格，None 表示檢查所有

    Returns:
        Tuple[bool, List[SchemaMismatch]]: (是否通過驗證, 不一致列表)
    """
    all_mismatches = []

    logger.info("🔍 開始資料庫 Schema 驗證...")

    async with engine.connect() as conn:
        # 取得資料庫中所有表格
        db_tables = await get_database_tables(conn)

        # 遍歷所有模型
        for table_name, table in base.metadata.tables.items():
            # 如果指定了要檢查的表格，則只檢查指定的
            if tables_to_check and table_name not in tables_to_check:
                continue

            # 檢查表格是否存在
            if table_name not in db_tables:
                all_mismatches.append(SchemaMismatch(
                    table_name, "TABLE_NOT_FOUND",
                    f"模型定義的表格 '{table_name}' 在資料庫中不存在"
                ))
                continue

            # 取得模型欄位
            model_columns = {col.name: {
                "python_type": str(col.type),
                "nullable": col.nullable,
                "primary_key": col.primary_key
            } for col in table.columns}

            # 驗證表格
            mismatches = await validate_table(conn, table_name, model_columns)
            all_mismatches.extend(mismatches)

    # 輸出結果
    if all_mismatches:
        logger.warning(f"⚠️ 發現 {len(all_mismatches)} 個 Schema 不一致:")
        for mismatch in all_mismatches:
            logger.warning(f"   {mismatch}")

        if strict:
            raise SchemaValidationError(
                f"Schema 驗證失敗: 發現 {len(all_mismatches)} 個不一致"
            )
    else:
        logger.info("✅ Schema 驗證通過，模型與資料庫一致")

    return len(all_mismatches) == 0, all_mismatches


async def generate_migration_hints(mismatches: List[SchemaMismatch]) -> str:
    """根據不一致生成遷移建議"""
    hints = ["# Schema 修復建議\n"]

    for mismatch in mismatches:
        if mismatch.issue_type == "COLUMN_MISSING_IN_DB":
            hints.append(f"# 需要新增欄位到資料庫:")
            hints.append(f"# ALTER TABLE {mismatch.table} ADD COLUMN ...;")
        elif mismatch.issue_type == "COLUMN_MISSING_IN_MODEL":
            hints.append(f"# 考慮在模型中新增欄位或從資料庫移除:")
            hints.append(f"# 表格: {mismatch.table}, 欄位: {mismatch.details}")
        elif mismatch.issue_type == "TABLE_NOT_FOUND":
            hints.append(f"# 需要建立資料表或執行 alembic upgrade:")
            hints.append(f"# CREATE TABLE {mismatch.table} ...;")

    return "\n".join(hints)
