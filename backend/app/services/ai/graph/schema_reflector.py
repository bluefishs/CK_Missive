"""
資料庫 Schema 反射服務

使用 SQLAlchemy inspect() 讀取實際資料庫結構，
提供 ER 圖譜所需的表、欄位、外鍵、索引資訊。

Version: 1.1.0
Created: 2026-03-11
Updated: 2026-03-12 - 重構為 async-safe 模式（asyncio.to_thread + asyncio.Lock）
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect as sa_inspect

logger = logging.getLogger(__name__)


class SchemaReflectorService:
    """
    資料庫 Schema 反射器。

    使用 SQLAlchemy inspect() 讀取 PostgreSQL information_schema，
    並快取結果以避免重複反射。

    async 入口使用 asyncio.to_thread 避免阻塞事件循環。
    """

    _cache: Optional[Dict[str, Any]] = None
    _cache_time: float = 0
    _async_lock: Optional[asyncio.Lock] = None
    # Cache TTL: 10 minutes
    CACHE_TTL = 600

    @classmethod
    def _get_async_lock(cls) -> asyncio.Lock:
        """取得或建立 asyncio.Lock（延遲初始化，確保在正確的 event loop 中建立）。"""
        if cls._async_lock is None:
            cls._async_lock = asyncio.Lock()
        return cls._async_lock

    @classmethod
    def _get_sync_url(cls) -> str:
        """從環境變數建構同步 DB URL。"""
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            # Strip async driver suffixes
            return (
                db_url
                .replace("+asyncpg", "")
                .replace("postgresql+asyncpg", "postgresql")
            )

        # Fallback: build from individual env vars (使用 URL.create 防止密碼特殊字元問題)
        from sqlalchemy.engine import URL
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = int(os.environ.get(
            "POSTGRES_HOST_PORT",
            os.environ.get("POSTGRES_PORT", "5434"),
        ))
        user = os.environ.get("POSTGRES_USER", "ck_user")
        password = os.environ.get("POSTGRES_PASSWORD", "")
        db_name = os.environ.get("POSTGRES_DB", "ck_documents")
        return str(URL.create(
            drivername="postgresql",
            username=user,
            password=password,
            host=host,
            port=port,
            database=db_name,
        ))

    @classmethod
    def _reflect(cls) -> Dict[str, Any]:
        """執行一次完整的 schema 反射（同步，在 thread pool 中執行）。"""
        sync_url = cls._get_sync_url()
        engine = create_engine(sync_url, pool_pre_ping=True)
        try:
            inspector = sa_inspect(engine)
            tables: List[Dict[str, Any]] = []

            for table_name in sorted(inspector.get_table_names()):
                columns = []
                for col in inspector.get_columns(table_name):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "primary_key": False,  # filled below
                    })

                # Mark primary key columns
                pk = inspector.get_pk_constraint(table_name)
                pk_cols = set(pk.get("constrained_columns", []) if pk else [])
                for c in columns:
                    if c["name"] in pk_cols:
                        c["primary_key"] = True

                # Foreign keys
                fks = []
                for fk in inspector.get_foreign_keys(table_name):
                    fks.append({
                        "constrained_columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table", ""),
                        "referred_columns": fk.get("referred_columns", []),
                    })

                # Indexes
                indexes = []
                for idx in inspector.get_indexes(table_name):
                    indexes.append({
                        "name": idx.get("name", ""),
                        "columns": idx.get("column_names", []),
                        "unique": idx.get("unique", False),
                    })

                # Unique constraints
                unique_constraints = []
                for uc in inspector.get_unique_constraints(table_name):
                    unique_constraints.append({
                        "name": uc.get("name", ""),
                        "columns": uc.get("column_names", []),
                    })

                tables.append({
                    "name": table_name,
                    "columns": columns,
                    "primary_key_columns": sorted(pk_cols),
                    "foreign_keys": fks,
                    "indexes": indexes,
                    "unique_constraints": unique_constraints,
                })

            return {"tables": tables}
        finally:
            engine.dispose()

    @classmethod
    def invalidate_cache(cls) -> None:
        """手動清除快取。"""
        cls._cache = None
        cls._cache_time = 0

    @classmethod
    async def get_full_schema_async(cls) -> Dict[str, Any]:
        """
        非同步取得完整資料庫 schema（推薦：FastAPI 端點使用此方法）。

        使用 asyncio.Lock 避免多個請求同時反射，
        使用 asyncio.to_thread 避免阻塞事件循環。
        """
        now = time.time()
        if cls._cache is not None and (now - cls._cache_time) < cls.CACHE_TTL:
            return cls._cache

        async with cls._get_async_lock():
            # Double-check after acquiring lock
            now = time.time()
            if cls._cache is not None and (now - cls._cache_time) < cls.CACHE_TTL:
                return cls._cache

            # Run sync reflection in thread pool
            data = await asyncio.to_thread(cls._reflect)

            cls._cache = data
            cls._cache_time = time.time()
            return data

    @classmethod
    def get_full_schema(cls) -> Dict[str, Any]:
        """
        同步取得完整資料庫 schema（腳本/CLI 使用）。
        """
        now = time.time()
        if cls._cache is not None and (now - cls._cache_time) < cls.CACHE_TTL:
            return cls._cache

        data = cls._reflect()
        cls._cache = data
        cls._cache_time = time.time()
        return data

    @classmethod
    async def get_graph_data_async(cls) -> Dict[str, Any]:
        """非同步取得圖譜格式資料（推薦：FastAPI 端點使用此方法）。"""
        schema = await cls.get_full_schema_async()
        return cls._schema_to_graph(schema)

    @classmethod
    def get_graph_data(cls) -> Dict[str, Any]:
        """同步取得圖譜格式資料。"""
        schema = cls.get_full_schema()
        return cls._schema_to_graph(schema)

    @classmethod
    def _schema_to_graph(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        將 schema 轉換為前端 ExternalGraphData 格式。

        Returns:
            {"nodes": [...], "edges": [...]}
            nodes: {id, label, type, category, status, mention_count}
            edges: {source, target, label, type, weight}
        """
        nodes = []
        edges = []
        seen_edges: set = set()

        for table in schema["tables"]:
            table_name = table["name"]
            col_count = len(table["columns"])
            pk_count = len(table["primary_key_columns"])
            fk_count = len(table["foreign_keys"])

            # Determine group/category based on table name prefix
            category = _classify_table(table_name)

            nodes.append({
                "id": f"tbl_{table_name}",
                "label": table_name,
                "type": "db_table",
                "category": category,
                "status": f"{col_count} cols, {pk_count} PK, {fk_count} FK",
                "mention_count": col_count,
            })

            # Create edges for each FK
            for fk in table["foreign_keys"]:
                referred = fk.get("referred_table", "")
                if not referred:
                    continue

                src_cols = ", ".join(fk.get("constrained_columns", []))
                ref_cols = ", ".join(fk.get("referred_columns", []))
                edge_key = (f"tbl_{table_name}", f"tbl_{referred}")

                # Avoid duplicate edges for same pair
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                edges.append({
                    "source": f"tbl_{table_name}",
                    "target": f"tbl_{referred}",
                    "label": f"{src_cols} -> {ref_cols}",
                    "type": "foreign_key",
                    "weight": 1,
                })

        return {"nodes": nodes, "edges": edges}


def _classify_table(name: str) -> str:
    """根據表名前綴分類。"""
    if name.startswith("taoyuan_"):
        return "taoyuan"
    if name.startswith("ai_") or name.startswith("canonical_") or name.startswith("entity_"):
        return "ai"
    if name.startswith("alembic"):
        return "system"
    if "document" in name or "attachment" in name:
        return "document"
    if "user" in name or "session" in name or "permission" in name:
        return "auth"
    if "project" in name or "vendor" in name or "agency" in name:
        return "business"
    if "calendar" in name or "reminder" in name or "notification" in name:
        return "calendar"
    return "other"
