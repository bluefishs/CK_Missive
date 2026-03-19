"""
draw_diagram (Tool #9) 單元測試

測試範圍：
- build_er_diagram: scope 過濾、detail_level=brief vs normal
- build_flowchart: 已知流程(document/dispatch)、未知流程(LLM fallback)、終極 fallback
- build_dependency_graph: DB mock 回傳模組與 import 關聯
- build_class_diagram: DB mock 回傳類別
- _draw_diagram: auto-detect diagram_type、related_entities 填充、er-model 快取缺失

共 25 test cases
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.agent_tools import AgentToolExecutor
from app.services.ai.tool_executor_analysis import AnalysisToolExecutor
from app.services.ai.agent_diagram_builder import (
    build_er_diagram,
    build_dependency_graph,
    build_flowchart,
    build_class_diagram,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_er_model_cache():
    """Reset class-level ER model cache before and after each test."""
    AnalysisToolExecutor._er_model_cache = None
    AnalysisToolExecutor._er_model_loaded = False
    yield
    AnalysisToolExecutor._er_model_cache = None
    AnalysisToolExecutor._er_model_loaded = False


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_ai():
    ai = AsyncMock()
    ai.chat_completion = AsyncMock(return_value={"content": ""})
    return ai


@pytest.fixture
def mock_embedding_mgr():
    mgr = MagicMock()
    mgr.get_embedding = AsyncMock(return_value=None)
    return mgr


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.hybrid_semantic_weight = 0.3
    return config


@pytest.fixture
def sample_er_data():
    """Minimal er-model.json structure for testing."""
    return {
        "tables": {
            "official_documents": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "doc_number", "type": "CHARACTER VARYING"},
                    {"name": "subject", "type": "TEXT"},
                    {"name": "project_id", "type": "INTEGER"},
                ],
                "primary_key": ["id"],
                "foreign_keys": [
                    {"column": "project_id", "ref_table": "contract_projects"}
                ],
            },
            "contract_projects": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "project_code", "type": "CHARACTER VARYING"},
                    {"name": "name", "type": "TEXT"},
                ],
                "primary_key": ["id"],
                "foreign_keys": [],
            },
            "attachments": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "document_id", "type": "INTEGER"},
                    {"name": "file_name", "type": "TEXT"},
                ],
                "primary_key": ["id"],
                "foreign_keys": [
                    {"column": "document_id", "ref_table": "official_documents"}
                ],
            },
        }
    }


@pytest.fixture
def executor(mock_db, mock_ai, mock_embedding_mgr, mock_config):
    """Create executor with ER model cache bypassed (loaded=True)."""
    AnalysisToolExecutor._er_model_loaded = True
    return AgentToolExecutor(mock_db, mock_ai, mock_embedding_mgr, mock_config)


# ============================================================================
# build_er_diagram (standalone function)
# ============================================================================

class TestBuildErDiagram:
    """ER 圖表建構測試"""

    def test_no_scope_returns_all_tables(self, sample_er_data):
        """No scope filter should include all tables."""
        title, desc, lines = build_er_diagram(sample_er_data, "", "normal")
        mermaid = "\n".join(lines)
        assert "erDiagram" in mermaid
        assert "official_documents" in mermaid
        assert "contract_projects" in mermaid
        assert "attachments" in mermaid
        assert "3 表" in title

    def test_scope_filters_tables(self, sample_er_data):
        """Scope 'document' should filter to matching tables + referenced tables."""
        title, desc, lines = build_er_diagram(sample_er_data, "document", "normal")
        mermaid = "\n".join(lines)
        # official_documents matches directly
        assert "official_documents" in mermaid
        # contract_projects is referenced via FK
        assert "contract_projects" in mermaid

    def test_scope_no_match(self, sample_er_data):
        """Scope with no match returns fallback message."""
        title, desc, lines = build_er_diagram(sample_er_data, "nonexistent_xyz", "normal")
        assert "無匹配" in title
        assert lines == ["erDiagram"]

    def test_detail_level_brief_only_pk_fk(self, sample_er_data):
        """detail_level=brief should only show PK and FK columns."""
        _, _, lines = build_er_diagram(sample_er_data, "", "brief")
        mermaid = "\n".join(lines)
        # official_documents has PK=id, FK=project_id; subject/doc_number should be excluded
        assert "subject" not in mermaid
        assert "doc_number" not in mermaid
        # PK and FK columns should be present
        assert "id" in mermaid
        assert "project_id" in mermaid

    def test_detail_level_normal_includes_all_columns(self, sample_er_data):
        """detail_level=normal should include all columns."""
        _, _, lines = build_er_diagram(sample_er_data, "", "normal")
        mermaid = "\n".join(lines)
        assert "subject" in mermaid
        assert "doc_number" in mermaid

    def test_foreign_key_relationships_rendered(self, sample_er_data):
        """FK relationships should produce ||--o{ lines."""
        _, _, lines = build_er_diagram(sample_er_data, "", "normal")
        rel_lines = [l for l in lines if "||--o{" in l]
        assert len(rel_lines) >= 1
        # contract_projects ||--o{ official_documents
        assert any("contract_projects" in l and "official_documents" in l for l in rel_lines)

    def test_type_mapping(self, sample_er_data):
        """SQL types should be mapped to short forms."""
        _, _, lines = build_er_diagram(sample_er_data, "contract_projects", "normal")
        mermaid = "\n".join(lines)
        assert "int" in mermaid
        assert "varchar" in mermaid


# ============================================================================
# build_flowchart (standalone function)
# ============================================================================

class TestBuildFlowchart:
    """流程圖建構測試"""

    @pytest.mark.asyncio
    async def test_known_flow_document(self):
        """Known flow 'document' should return predefined chart."""
        title, desc, lines = await build_flowchart("document 流程")
        mermaid = "\n".join(lines)
        assert "flowchart TD" in mermaid
        assert "收文登錄" in mermaid
        assert "發文" in mermaid
        assert "document" in title

    @pytest.mark.asyncio
    async def test_known_flow_dispatch(self):
        """Known flow 'dispatch' should return predefined chart."""
        title, desc, lines = await build_flowchart("dispatch 作業")
        mermaid = "\n".join(lines)
        assert "flowchart TD" in mermaid
        assert "接收派工單" in mermaid
        assert "結案歸檔" in mermaid

    @pytest.mark.asyncio
    async def test_known_flow_ai(self):
        """Known flow 'ai' should return predefined chart."""
        title, desc, lines = await build_flowchart("ai pipeline")
        mermaid = "\n".join(lines)
        assert "意圖解析" in mermaid

    @pytest.mark.asyncio
    async def test_unknown_flow_llm_fallback(self, mock_ai):
        """Unknown flow should call LLM for generation."""
        mock_ai.chat_completion = AsyncMock(return_value={
            "content": "```mermaid\nflowchart TD\n    A[開始] --> B[結束]\n```"
        })
        title, desc, lines = await build_flowchart("採購審核流程", ai_connector=mock_ai)
        assert "AI 生成" in desc
        assert lines[0].strip().startswith("flowchart")

    @pytest.mark.asyncio
    async def test_unknown_flow_llm_failure_ultimate_fallback(self, mock_ai):
        """When LLM fails, should return generic template."""
        mock_ai.chat_completion = AsyncMock(side_effect=Exception("LLM error"))
        title, desc, lines = await build_flowchart("未知流程", ai_connector=mock_ai)
        mermaid = "\n".join(lines)
        assert "flowchart TD" in mermaid
        assert "基本流程圖模板" in desc

    @pytest.mark.asyncio
    async def test_unknown_flow_no_ai_connector(self):
        """When ai connector is None, should return generic template."""
        title, desc, lines = await build_flowchart("自訂流程", ai_connector=None)
        assert "基本流程圖模板" in desc

    @pytest.mark.asyncio
    async def test_llm_response_without_mermaid_fence(self, mock_ai):
        """LLM returns code block without mermaid tag."""
        mock_ai.chat_completion = AsyncMock(return_value={
            "content": "```\nflowchart TD\n    X[步驟] --> Y[完成]\n```"
        })
        title, desc, lines = await build_flowchart("其他流程", ai_connector=mock_ai)
        assert lines[0].strip().startswith("flowchart")
        assert "AI 生成" in desc


# ============================================================================
# build_dependency_graph (standalone function)
# ============================================================================

class TestBuildDependencyGraph:
    """模組依賴圖建構測試"""

    @pytest.mark.asyncio
    async def test_no_modules_found(self, mock_db):
        """No matching modules returns fallback."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        title, desc, lines = await build_dependency_graph(mock_db, "nonexistent", "normal")
        assert "無匹配模組" in title
        assert lines == ["graph LR"]

    @pytest.mark.asyncio
    async def test_modules_with_relations(self, mock_db):
        """Modules with import relations should produce graph edges."""
        # First call: module query
        mod_result = MagicMock()
        mod_result.all.return_value = [
            (1, "app.services.document_service", "py_module"),
            (2, "app.repositories.document_repository", "py_module"),
        ]
        # Second call: relations query
        rel_result = MagicMock()
        rel_result.all.return_value = [
            (1, 2),  # document_service imports document_repository
        ]

        mock_db.execute = AsyncMock(side_effect=[mod_result, rel_result])

        title, desc, lines = await build_dependency_graph(mock_db, "service", "normal")
        mermaid = "\n".join(lines)
        assert "graph LR" in mermaid
        assert "-->" in mermaid
        assert "2 模組" in title

    @pytest.mark.asyncio
    async def test_scope_filtering(self, mock_db):
        """Scope should be passed to ilike filter."""
        mod_result = MagicMock()
        mod_result.all.return_value = []
        mock_db.execute.return_value = mod_result

        await build_dependency_graph(mock_db, "taoyuan", "normal")
        # Verify execute was called (the scope goes into the SQL query)
        mock_db.execute.assert_called()


# ============================================================================
# build_class_diagram (standalone function)
# ============================================================================

class TestBuildClassDiagram:
    """類別圖建構測試"""

    @pytest.mark.asyncio
    async def test_no_classes_found(self, mock_db):
        """No matching classes returns fallback."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        title, desc, lines = await build_class_diagram(mock_db, "nonexistent", "normal")
        assert "無匹配類別" in title
        assert lines == ["classDiagram"]

    @pytest.mark.asyncio
    async def test_classes_with_methods(self, mock_db):
        """Classes with method descriptions should render methods."""
        class_result = MagicMock()
        class_result.all.return_value = [
            (1, "app.services.DocumentService", json.dumps({"methods": ["get_list", "create", "update"]})),
        ]
        rel_result = MagicMock()
        rel_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[class_result, rel_result])

        title, desc, lines = await build_class_diagram(mock_db, "Document", "normal")
        mermaid = "\n".join(lines)
        assert "classDiagram" in mermaid
        assert "class DocumentService" in mermaid
        assert "+get_list()" in mermaid

    @pytest.mark.asyncio
    async def test_brief_limits_methods(self, mock_db):
        """detail_level=brief should limit methods to 3."""
        methods = [f"method_{i}" for i in range(10)]
        class_result = MagicMock()
        class_result.all.return_value = [
            (1, "app.services.BigService", json.dumps({"methods": methods})),
        ]
        rel_result = MagicMock()
        rel_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[class_result, rel_result])

        _, _, lines = await build_class_diagram(mock_db, "Big", "brief")
        method_lines = [l for l in lines if "+()" in l or "+method_" in l]
        assert len(method_lines) == 3


# ============================================================================
# _draw_diagram (orchestrator method — delegates to standalone builders)
# ============================================================================

class TestDrawDiagram:
    """draw_diagram 主方法測試"""

    @pytest.mark.asyncio
    async def test_auto_detect_er_from_table_keyword(self, executor, sample_er_data):
        """scope containing 'table' should auto-detect erDiagram."""
        AnalysisToolExecutor._er_model_cache = sample_er_data
        result = await executor._analysis.draw_diagram({"scope": "table schema overview"})
        assert result["diagram_type"] == "erDiagram"
        assert "erDiagram" in result["mermaid"]

    @pytest.mark.asyncio
    async def test_auto_detect_er_from_chinese_keyword(self, executor, sample_er_data):
        """scope containing '資料' should auto-detect erDiagram."""
        AnalysisToolExecutor._er_model_cache = sample_er_data
        result = await executor._analysis.draw_diagram({"scope": "資料表結構"})
        assert result["diagram_type"] == "erDiagram"

    @pytest.mark.asyncio
    async def test_auto_detect_flowchart(self, executor):
        """scope containing '流程' should auto-detect flowchart."""
        result = await executor._analysis.draw_diagram({"scope": "document 流程"})
        assert result["diagram_type"] == "flowchart"
        assert "flowchart" in result["mermaid"]

    @pytest.mark.asyncio
    async def test_auto_detect_graph_from_module_keyword(self, executor, mock_db):
        """scope containing '模組' should auto-detect graph."""
        mod_result = MagicMock()
        mod_result.all.return_value = []
        mock_db.execute.return_value = mod_result

        result = await executor._analysis.draw_diagram({"scope": "模組依賴"})
        assert result["diagram_type"] == "graph"

    @pytest.mark.asyncio
    async def test_auto_detect_class_diagram(self, executor, mock_db):
        """scope containing 'class' should auto-detect classDiagram."""
        class_result = MagicMock()
        class_result.all.return_value = []
        mock_db.execute.return_value = class_result

        result = await executor._analysis.draw_diagram({"scope": "class 繼承結構"})
        assert result["diagram_type"] == "classDiagram"

    @pytest.mark.asyncio
    async def test_default_to_er_when_no_keyword(self, executor, sample_er_data):
        """No recognized keyword should default to erDiagram."""
        AnalysisToolExecutor._er_model_cache = sample_er_data
        result = await executor._analysis.draw_diagram({"scope": "一般概覽"})
        assert result["diagram_type"] == "erDiagram"

    @pytest.mark.asyncio
    async def test_no_er_data_returns_error(self, executor):
        """When ER model is not loaded, fallback should indicate error."""
        AnalysisToolExecutor._er_model_cache = None
        result = await executor._analysis.draw_diagram({"scope": "table", "diagram_type": "erDiagram"})
        assert result["mermaid"] == ""
        assert "無法" in result["title"]

    @pytest.mark.asyncio
    async def test_related_entities_extraction(self, executor, sample_er_data):
        """related_entities should be populated from Mermaid lines."""
        AnalysisToolExecutor._er_model_cache = sample_er_data
        result = await executor._analysis.draw_diagram({"scope": "document"})
        assert isinstance(result["related_entities"], list)
        # Should extract table names from ER diagram
        assert any("document" in e.lower() for e in result["related_entities"])
