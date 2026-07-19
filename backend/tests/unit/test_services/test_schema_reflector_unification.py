"""
程式圖譜↔資料庫圖譜 異質同工整合（單一 schema 反射 SSOT）TDD 測試。

異質同工確證：code_graph ingest 每次反射 DB schema 兩次——
  ① code_graph_ast_analyzer.SchemaReflector.reflect_tables()（自建 sync Inspector）
  ② schema_reflector.SchemaReflectorService（_ingest_fk_relations 用，cached）
兩套 Inspector 讀同一 PostgreSQL。整合＝db_table 實體改由 SchemaReflectorService
的 schema dict 建構（純函式 build_table_entities_from_schema），消除重複 Inspector。

本測試鎖定純建構器：從 SchemaReflectorService 格式的 schema dict 產出等價 db_table
實體（description 形狀保真）。FK 關係交由 _ingest_fk_relations 單一源，建構器不重複產。

RED-GREEN-REFACTOR。相關 HETEROGENEOUS_WORK_REGISTRY.md / code_graph_self_optimization。
"""
from app.services.ai.graph.code_graph_ast_analyzer import (
    build_table_entities_from_schema,
)


# SchemaReflectorService.get_full_schema_async() 的輸出格式
SAMPLE_SCHEMA = {
    "tables": [
        {
            "name": "documents",
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "title", "type": "VARCHAR", "nullable": True, "primary_key": False},
                {"name": "sender_agency_id", "type": "INTEGER", "nullable": True, "primary_key": False},
            ],
            "primary_key_columns": ["id"],
            "foreign_keys": [
                {"constrained_columns": ["sender_agency_id"], "referred_table": "government_agencies", "referred_columns": ["id"]},
            ],
            "indexes": [{"name": "ix_documents_title", "columns": ["title"], "unique": False}],
            "unique_constraints": [{"name": "uq_doc_number", "columns": ["doc_number"]}],
        },
        {
            "name": "government_agencies",
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "name", "type": "VARCHAR", "nullable": False, "primary_key": False},
            ],
            "primary_key_columns": ["id"],
            "foreign_keys": [],
            "indexes": [],
            "unique_constraints": [],
        },
    ]
}


class TestBuildTableEntitiesFromSchema:
    def test_builds_one_entity_per_table(self):
        entities = build_table_entities_from_schema(SAMPLE_SCHEMA)
        names = {e.canonical_name for e in entities}
        assert names == {"documents", "government_agencies"}
        assert all(e.entity_type == "db_table" for e in entities)

    def test_description_shape_preserved(self):
        """description 形狀須與舊 reflect_tables 一致（columns/pk/fk/index）。"""
        entities = build_table_entities_from_schema(SAMPLE_SCHEMA)
        doc = next(e for e in entities if e.canonical_name == "documents")
        d = doc.description
        assert d["columns"] == ["id", "title", "sender_agency_id"]
        assert d["column_types"]["id"] == "INTEGER"
        assert d["primary_key"] == ["id"]
        assert d["has_primary_key"] is True
        assert d["foreign_key_targets"] == ["government_agencies"]
        assert d["index_count"] == 1
        assert d["unique_constraints_count"] == 1
        # FK 明細保真
        assert d["foreign_keys"][0]["referred_table"] == "government_agencies"

    def test_empty_schema_returns_empty(self):
        assert build_table_entities_from_schema({"tables": []}) == []
        assert build_table_entities_from_schema({}) == []

    def test_no_fk_relations_produced(self):
        """建構器只產實體，FK 關係交由 _ingest_fk_relations 單一源（不重複）。"""
        result = build_table_entities_from_schema(SAMPLE_SCHEMA)
        # 回傳純實體 list（非 tuple），無 relations
        assert isinstance(result, list)
        assert all(hasattr(e, "entity_type") for e in result)
