"""
SchemaReflectorService 單元測試

測試範圍：
- Singleton-like class method pattern (class-level cache)
- Schema cache behavior (TTL, invalidation)
- Table metadata extraction (columns, PK, FK, indexes, unique constraints)
- Graph data generation (nodes for tables, edges for FK relationships)
- Edge cases: empty schema, tables without FKs, duplicate FK edges
- _classify_table helper function
- Async methods (get_full_schema_async, get_graph_data_async)

共 25+ test cases
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai.schema_reflector import SchemaReflectorService, _classify_table


# ── Fixtures ──


def _make_inspector(
    table_names: List[str],
    columns_by_table: Dict[str, List[Dict[str, Any]]] | None = None,
    pk_by_table: Dict[str, Dict[str, Any]] | None = None,
    fk_by_table: Dict[str, List[Dict[str, Any]]] | None = None,
    indexes_by_table: Dict[str, List[Dict[str, Any]]] | None = None,
    unique_by_table: Dict[str, List[Dict[str, Any]]] | None = None,
) -> MagicMock:
    """Build a mock SQLAlchemy Inspector."""
    inspector = MagicMock()
    inspector.get_table_names.return_value = table_names

    def _columns(t):
        if columns_by_table and t in columns_by_table:
            return columns_by_table[t]
        return [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "VARCHAR(255)", "nullable": True},
        ]

    def _pk(t):
        if pk_by_table and t in pk_by_table:
            return pk_by_table[t]
        return {"constrained_columns": ["id"]}

    def _fk(t):
        if fk_by_table and t in fk_by_table:
            return fk_by_table[t]
        return []

    def _indexes(t):
        if indexes_by_table and t in indexes_by_table:
            return indexes_by_table[t]
        return []

    def _unique(t):
        if unique_by_table and t in unique_by_table:
            return unique_by_table[t]
        return []

    inspector.get_columns.side_effect = _columns
    inspector.get_pk_constraint.side_effect = _pk
    inspector.get_foreign_keys.side_effect = _fk
    inspector.get_indexes.side_effect = _indexes
    inspector.get_unique_constraints.side_effect = _unique
    return inspector


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure cache is clean before and after each test."""
    SchemaReflectorService.invalidate_cache()
    # Reset async lock so tests are isolated
    SchemaReflectorService._async_lock = None
    yield
    SchemaReflectorService.invalidate_cache()
    SchemaReflectorService._async_lock = None


# ── _classify_table tests ──


class TestClassifyTable:
    """Table classification helper tests."""

    def test_taoyuan_prefix(self):
        assert _classify_table("taoyuan_dispatch_orders") == "taoyuan"

    def test_ai_prefix(self):
        assert _classify_table("ai_prompts") == "ai"

    def test_canonical_prefix(self):
        assert _classify_table("canonical_entities") == "ai"

    def test_entity_prefix(self):
        assert _classify_table("entity_relations") == "ai"

    def test_alembic_prefix(self):
        assert _classify_table("alembic_version") == "system"

    def test_document_keyword(self):
        assert _classify_table("official_documents") == "document"

    def test_attachment_keyword(self):
        assert _classify_table("attachment_files") == "document"

    def test_user_keyword(self):
        assert _classify_table("users") == "auth"

    def test_session_keyword(self):
        assert _classify_table("session_data") == "auth"

    def test_project_keyword(self):
        assert _classify_table("projects") == "business"

    def test_vendor_keyword(self):
        assert _classify_table("vendors") == "business"

    def test_agency_keyword(self):
        assert _classify_table("government_agency") == "business"

    def test_agencies_plural_is_other(self):
        # "agencies" does not contain substring "agency", so it falls to "other"
        assert _classify_table("agencies") == "other"

    def test_calendar_keyword(self):
        assert _classify_table("calendar_events") == "calendar"

    def test_reminder_keyword(self):
        assert _classify_table("reminders") == "calendar"

    def test_notification_keyword(self):
        assert _classify_table("notifications") == "calendar"

    def test_other_fallback(self):
        assert _classify_table("some_random_table") == "other"


# ── Cache behavior ──


class TestCacheBehavior:
    """Schema cache TTL and invalidation tests."""

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_cache_returns_same_result(self, mock_inspect, mock_engine):
        """Second call should use cache, not re-reflect."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(["t1"])

        result1 = SchemaReflectorService.get_full_schema()
        result2 = SchemaReflectorService.get_full_schema()

        assert result1 is result2
        # _reflect should only be called once
        mock_inspect.assert_called_once()

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_cache_invalidation(self, mock_inspect, mock_engine):
        """After invalidate_cache(), next call should re-reflect."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(["t1"])

        SchemaReflectorService.get_full_schema()
        SchemaReflectorService.invalidate_cache()
        SchemaReflectorService.get_full_schema()

        assert mock_inspect.call_count == 2

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    @patch("app.services.ai.schema_reflector.time")
    def test_cache_ttl_expiry(self, mock_time, mock_inspect, mock_engine):
        """Cache should expire after CACHE_TTL seconds."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(["t1"])

        # First call at time 0
        mock_time.time.return_value = 0.0
        SchemaReflectorService.get_full_schema()

        # Second call within TTL (at 300s)
        mock_time.time.return_value = 300.0
        SchemaReflectorService.get_full_schema()
        assert mock_inspect.call_count == 1  # still cached

        # Third call beyond TTL (at 700s)
        mock_time.time.return_value = 700.0
        SchemaReflectorService.get_full_schema()
        assert mock_inspect.call_count == 2  # re-reflected


# ── Table metadata extraction ──


class TestReflection:
    """Core _reflect() logic tests."""

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_empty_schema(self, mock_inspect, mock_engine):
        """Empty database returns empty tables list."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector([])

        result = SchemaReflectorService.get_full_schema()
        assert result == {"tables": []}

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_basic_table_metadata(self, mock_inspect, mock_engine):
        """Table metadata includes columns, PK, FK, indexes."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(
            table_names=["users"],
            columns_by_table={
                "users": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "email", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "role", "type": "VARCHAR(50)", "nullable": True},
                ]
            },
            pk_by_table={"users": {"constrained_columns": ["id"]}},
        )

        result = SchemaReflectorService.get_full_schema()
        table = result["tables"][0]

        assert table["name"] == "users"
        assert len(table["columns"]) == 3
        assert table["primary_key_columns"] == ["id"]
        # id column should be marked as PK
        id_col = next(c for c in table["columns"] if c["name"] == "id")
        assert id_col["primary_key"] is True
        # email column should not be PK
        email_col = next(c for c in table["columns"] if c["name"] == "email")
        assert email_col["primary_key"] is False

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_foreign_key_extraction(self, mock_inspect, mock_engine):
        """Foreign keys are extracted correctly."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(
            table_names=["orders"],
            fk_by_table={
                "orders": [
                    {
                        "constrained_columns": ["user_id"],
                        "referred_table": "users",
                        "referred_columns": ["id"],
                    }
                ]
            },
        )

        result = SchemaReflectorService.get_full_schema()
        table = result["tables"][0]

        assert len(table["foreign_keys"]) == 1
        fk = table["foreign_keys"][0]
        assert fk["constrained_columns"] == ["user_id"]
        assert fk["referred_table"] == "users"
        assert fk["referred_columns"] == ["id"]

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_index_extraction(self, mock_inspect, mock_engine):
        """Indexes are extracted correctly."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(
            table_names=["documents"],
            indexes_by_table={
                "documents": [
                    {
                        "name": "ix_documents_doc_number",
                        "column_names": ["doc_number"],
                        "unique": True,
                    },
                    {
                        "name": "ix_documents_created",
                        "column_names": ["created_at"],
                        "unique": False,
                    },
                ]
            },
        )

        result = SchemaReflectorService.get_full_schema()
        table = result["tables"][0]

        assert len(table["indexes"]) == 2
        unique_idx = next(i for i in table["indexes"] if i["unique"])
        assert unique_idx["name"] == "ix_documents_doc_number"
        assert unique_idx["columns"] == ["doc_number"]

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_unique_constraint_extraction(self, mock_inspect, mock_engine):
        """Unique constraints are extracted correctly."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(
            table_names=["agencies"],
            unique_by_table={
                "agencies": [
                    {"name": "uq_agencies_code", "column_names": ["code"]},
                ]
            },
        )

        result = SchemaReflectorService.get_full_schema()
        table = result["tables"][0]

        assert len(table["unique_constraints"]) == 1
        assert table["unique_constraints"][0]["name"] == "uq_agencies_code"
        assert table["unique_constraints"][0]["columns"] == ["code"]

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_table_without_fks(self, mock_inspect, mock_engine):
        """Table with no foreign keys should have empty FK list."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(
            table_names=["config"],
            fk_by_table={"config": []},
        )

        result = SchemaReflectorService.get_full_schema()
        assert result["tables"][0]["foreign_keys"] == []

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_multiple_tables_sorted(self, mock_inspect, mock_engine):
        """Tables should be returned in sorted order."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(["zebra", "apple", "mango"])

        result = SchemaReflectorService.get_full_schema()
        names = [t["name"] for t in result["tables"]]
        assert names == ["apple", "mango", "zebra"]

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    def test_engine_disposed_after_reflect(self, mock_inspect, mock_engine):
        """Engine should be disposed after reflection (even on success)."""
        engine_mock = MagicMock()
        mock_engine.return_value = engine_mock
        mock_inspect.return_value = _make_inspector(["t1"])

        SchemaReflectorService.get_full_schema()
        engine_mock.dispose.assert_called_once()


# ── Graph data generation ──


class TestGraphDataGeneration:
    """_schema_to_graph() conversion tests."""

    def test_nodes_created_for_each_table(self):
        """Each table becomes a node with correct attributes."""
        schema = {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                        {"name": "email", "type": "VARCHAR", "nullable": False, "primary_key": False},
                    ],
                    "primary_key_columns": ["id"],
                    "foreign_keys": [],
                    "indexes": [],
                    "unique_constraints": [],
                },
            ]
        }
        result = SchemaReflectorService._schema_to_graph(schema)

        assert len(result["nodes"]) == 1
        node = result["nodes"][0]
        assert node["id"] == "tbl_users"
        assert node["label"] == "users"
        assert node["type"] == "db_table"
        assert node["category"] == "auth"
        assert node["mention_count"] == 2
        assert "2 cols" in node["status"]

    def test_edges_created_for_fk(self):
        """Foreign keys generate edges between table nodes."""
        schema = {
            "tables": [
                {
                    "name": "orders",
                    "columns": [{"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True}],
                    "primary_key_columns": ["id"],
                    "foreign_keys": [
                        {
                            "constrained_columns": ["user_id"],
                            "referred_table": "users",
                            "referred_columns": ["id"],
                        }
                    ],
                    "indexes": [],
                    "unique_constraints": [],
                },
                {
                    "name": "users",
                    "columns": [{"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True}],
                    "primary_key_columns": ["id"],
                    "foreign_keys": [],
                    "indexes": [],
                    "unique_constraints": [],
                },
            ]
        }
        result = SchemaReflectorService._schema_to_graph(schema)

        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        edge = result["edges"][0]
        assert edge["source"] == "tbl_orders"
        assert edge["target"] == "tbl_users"
        assert edge["type"] == "foreign_key"
        assert "user_id" in edge["label"]

    def test_duplicate_fk_edges_deduplicated(self):
        """Multiple FKs between same table pair should produce only one edge."""
        schema = {
            "tables": [
                {
                    "name": "transfers",
                    "columns": [],
                    "primary_key_columns": [],
                    "foreign_keys": [
                        {
                            "constrained_columns": ["from_account_id"],
                            "referred_table": "accounts",
                            "referred_columns": ["id"],
                        },
                        {
                            "constrained_columns": ["to_account_id"],
                            "referred_table": "accounts",
                            "referred_columns": ["id"],
                        },
                    ],
                    "indexes": [],
                    "unique_constraints": [],
                },
            ]
        }
        result = SchemaReflectorService._schema_to_graph(schema)

        # Only one edge despite two FKs to same table
        assert len(result["edges"]) == 1

    def test_empty_schema_graph(self):
        """Empty schema produces empty graph."""
        result = SchemaReflectorService._schema_to_graph({"tables": []})
        assert result == {"nodes": [], "edges": []}

    def test_fk_with_empty_referred_table_skipped(self):
        """FK with empty referred_table should be skipped."""
        schema = {
            "tables": [
                {
                    "name": "broken",
                    "columns": [],
                    "primary_key_columns": [],
                    "foreign_keys": [
                        {
                            "constrained_columns": ["x"],
                            "referred_table": "",
                            "referred_columns": [],
                        }
                    ],
                    "indexes": [],
                    "unique_constraints": [],
                },
            ]
        }
        result = SchemaReflectorService._schema_to_graph(schema)
        assert len(result["edges"]) == 0

    def test_node_category_classification(self):
        """Nodes should be classified into correct categories."""
        schema = {
            "tables": [
                {"name": "taoyuan_dispatch", "columns": [], "primary_key_columns": [], "foreign_keys": [], "indexes": [], "unique_constraints": []},
                {"name": "ai_prompts", "columns": [], "primary_key_columns": [], "foreign_keys": [], "indexes": [], "unique_constraints": []},
                {"name": "official_documents", "columns": [], "primary_key_columns": [], "foreign_keys": [], "indexes": [], "unique_constraints": []},
                {"name": "config_items", "columns": [], "primary_key_columns": [], "foreign_keys": [], "indexes": [], "unique_constraints": []},
            ]
        }
        result = SchemaReflectorService._schema_to_graph(schema)
        categories = {n["label"]: n["category"] for n in result["nodes"]}

        assert categories["taoyuan_dispatch"] == "taoyuan"
        assert categories["ai_prompts"] == "ai"
        assert categories["official_documents"] == "document"
        assert categories["config_items"] == "other"


# ── Async methods ──


class TestAsyncMethods:
    """Async entry point tests."""

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    @pytest.mark.asyncio
    async def test_get_full_schema_async(self, mock_inspect, mock_engine):
        """Async method returns same data as sync."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(["async_table"])

        result = await SchemaReflectorService.get_full_schema_async()

        assert len(result["tables"]) == 1
        assert result["tables"][0]["name"] == "async_table"

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    @pytest.mark.asyncio
    async def test_get_full_schema_async_caches(self, mock_inspect, mock_engine):
        """Async method uses cache on second call."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(["t1"])

        r1 = await SchemaReflectorService.get_full_schema_async()
        r2 = await SchemaReflectorService.get_full_schema_async()

        assert r1 is r2
        mock_inspect.assert_called_once()

    @patch("app.services.ai.schema_reflector.create_engine")
    @patch("app.services.ai.schema_reflector.sa_inspect")
    @pytest.mark.asyncio
    async def test_get_graph_data_async(self, mock_inspect, mock_engine):
        """Async graph data method returns nodes and edges."""
        mock_engine.return_value = MagicMock()
        mock_inspect.return_value = _make_inspector(
            table_names=["orders", "users"],
            fk_by_table={
                "orders": [
                    {
                        "constrained_columns": ["user_id"],
                        "referred_table": "users",
                        "referred_columns": ["id"],
                    }
                ],
                "users": [],
            },
        )

        result = await SchemaReflectorService.get_graph_data_async()

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1


# ── _get_sync_url tests ──


class TestGetSyncUrl:
    """Database URL construction tests."""

    @patch.dict("os.environ", {"DATABASE_URL": "postgresql+asyncpg://user:pass@host/db"}, clear=False)
    def test_strips_asyncpg_driver(self):
        url = SchemaReflectorService._get_sync_url()
        assert "+asyncpg" not in url
        assert url == "postgresql://user:pass@host/db"

    @patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@host/db"}, clear=False)
    def test_plain_url_unchanged(self):
        url = SchemaReflectorService._get_sync_url()
        assert url == "postgresql://user:pass@host/db"

    @patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "",
            "POSTGRES_HOST": "myhost",
            "POSTGRES_HOST_PORT": "5555",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_DB": "testdb",
        },
        clear=False,
    )
    def test_fallback_to_individual_env_vars(self):
        url = SchemaReflectorService._get_sync_url()
        assert "myhost" in url
        assert "5555" in url
        assert "testuser" in url
        assert "testdb" in url
