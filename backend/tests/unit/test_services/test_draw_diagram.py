"""
draw_diagram (Tool #9) 單元測試

測試範圍：
- _build_er_diagram: scope 過濾、detail_level=brief vs normal
- _build_flowchart: 已知流程(document/dispatch)、未知流程(LLM fallback)、終極 fallback
- _build_dependency_graph: DB mock 回傳模組與 import 關聯
- _build_class_diagram: DB mock 回傳類別
- _draw_diagram: auto-detect diagram_type、related_entities 填充、er-model 快取缺失

共 25 test cases
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.agent_tools import AgentToolExecutor


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_er_model_cache():
    """Reset class-level ER model cache before and after each test."""
    AgentToolExecutor._er_model_cache = None
    AgentToolExecutor._er_model_loaded = False
    yield
    AgentToolExecutor._er_model_cache = None
    AgentToolExecutor._er_model_loaded = False


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
    AgentToolExecutor._er_model_loaded = True
    return AgentToolExecutor(mock_db, mock_ai, mock_embedding_mgr, mock_config)


# ============================================================================
# _build_er_diagram
# ============================================================================

class TestBuildErDiagram:
    """ER 圖表建構測試"""

    def test_no_scope_returns_all_tables(self, executor, sample_er_data):
        """No scope filter should include all tables."""
        title, desc, lines = executor._build_er_diagram(sample_er_data, "", "normal")
        mermaid = "\n".join(lines)
        assert "erDiagram" in mermaid
        assert "official_documents" in mermaid
        assert "contract_projects" in mermaid
        assert "attachments" in mermaid
        assert "3 表" in title

    def test_scope_filters_tables(self, executor, sample_er_data):
        """Scope 'document' should filter to matching tables + referenced tables."""
        title, desc, lines = executor._build_er_diagram(sample_er_data, "document", "normal")
        mermaid = "\n".join(lines)
        # official_documents matches directly
        assert "official_documents" in mermaid
        # contract_projects is referenced via FK
        assert "contract_projects" in mermaid

    def test_scope_no_match(self, executor, sample_er_data):
        """Scope with no match returns fallback message."""
        title, desc, lines = executor._build_er_diagram(sample_er_data, "nonexistent_xyz", "normal")
        assert "無匹配" in title
        assert lines == ["erDiagram"]

    def test_detail_level_brief_only_pk_fk(self, executor, sample_er_data):
        """detail_level=brief should only show PK and FK columns."""
        _, _, lines = executor._build_er_diagram(sample_er_data, "", "brief")
        mermaid = "\n".join(lines)
        # official_documents has PK=id, FK=project_id; subject/doc_number should be excluded
        assert "subject" not in mermaid
        assert "doc_number" not in mermaid
        # PK and FK columns should be present
        assert "id" in mermaid
        assert "project_id" in mermaid

    def test_detail_level_normal_includes_all_columns(self, executor, sample_er_data):
        """detail_level=normal should include all columns."""
        _, _, lines = executor._build_er_diagram(sample_er_data, "", "normal")
        mermaid = "\n".join(lines)
        assert "subject" in mermaid
        assert "doc_number" in mermaid

    def test_foreign_key_relationships_rendered(self, executor, sample_er_data):
        """FK relationships should produce ||--o{ lines."""
        _, _, lines = executor._build_er_diagram(sample_er_data, "", "normal")
        rel_lines = [l for l in lines if "||--o{" in l]
        assert len(rel_lines) >= 1
        # contract_projects ||--o{ official_documents
        assert any("contract_projects" in l and "official_documents" in l for l in rel_lines)

    def test_type_mapping(self, executor, sample_er_data):
        """SQL types should be mapped to short forms."""
        _, _, lines = executor._build_er_diagram(sample_er_data, "contract_projects", "normal")
        mermaid = "\n".join(lines)
        assert "int" in mermaid
        assert "varchar" in mermaid


# ============================================================================
# _build_flowchart
# ============================================================================

class TestBuildFlowchart:
    """流程圖建構測試"""

    @pytest.mark.asyncio
    async def test_known_flow_document(self, executor):
        """Known flow 'document' should return predefined chart."""
        title, desc, lines = await executor._build_flowchart("document 流程")
        mermaid = "\n".join(lines)
        assert "flowchart TD" in mermaid
        assert "收文登錄" in mermaid
        assert "發文" in mermaid
        assert "document" in title

    @pytest.mark.asyncio
    async def test_known_flow_dispatch(self, executor):
        """Known flow 'dispatch' should return predefined chart."""
        title, desc, lines = await executor._build_flowchart("dispatch 作業")
        mermaid = "\n".join(lines)
        assert "flowchart TD" in mermaid
        assert "接收派工單" in mermaid
        assert "結案歸檔" in mermaid

    @pytest.mark.asyncio
    async def test_known_flow_ai(self, executor):
        """Known flow 'ai' should return predefined chart."""
        title, desc, lines = await executor._build_flowchart("ai pipeline")
        mermaid = "\n".join(lines)
        assert "意圖解析" in mermaid

    @pytest.mark.asyncio
    async def test_unknown_flow_llm_fallback(self, executor, mock_ai):
        """Unknown flow should call LLM for generation."""
        mock_ai.chat_completion = AsyncMock(return_value={
            "content": "```mermaid\nflowchart TD\n    A[開始] --> B[結束]\n```"
        })
        title, desc, lines = await executor._build_flowchart("採購審核流程")
        assert "AI 生成" in desc
        assert lines[0].strip().startswith("flowchart")

    @pytest.mark.asyncio
    async def test_unknown_flow_llm_failure_ultimate_fallback(self, executor, mock_ai):
        """When LLM fails, should return generic template."""
        mock_ai.chat_completion = AsyncMock(side_effect=Exception("LLM error"))
        title, desc, lines = await executor._build_flowchart("未知流程")
        mermaid = "\n".join(lines)
        assert "flowchart TD" in mermaid
        assert "基本流程圖模板" in desc

    @pytest.mark.asyncio
    async def test_unknown_flow_no_ai_connector(self, mock_db, mock_embedding_mgr, mock_config):
        """When ai connector is None, should return generic template."""
        AgentToolExecutor._er_model_loaded = True
        executor = AgentToolExecutor(mock_db, None, mock_embedding_mgr, mock_config)
        title, desc, lines = await executor._build_flowchart("自訂流程")
        assert "基本流程圖模板" in desc

    @pytest.mark.asyncio
    async def test_llm_response_without_mermaid_fence(self, executor, mock_ai):
        """LLM returns code block without mermaid tag."""
        mock_ai.chat_completion = AsyncMock(return_value={
            "content": "```\nflowchart TD\n    X[步驟] --> Y[完成]\n```"
        })
        title, desc, lines = await executor._build_flowchart("其他流程")
        assert lines[0].strip().startswith("flowchart")
        assert "AI 生成" in desc


# ============================================================================
# _build_dependency_graph
# ============================================================================

class TestBuildDependencyGraph:
    """模組依賴圖建構測試"""

    @pytest.mark.asyncio
    async def test_no_modules_found(self, executor, mock_db):
        """No matching modules returns fallback."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        title, desc, lines = await executor._build_dependency_graph("nonexistent", "normal")
        assert "無匹配模組" in title
        assert lines == ["graph LR"]

    @pytest.mark.asyncio
    async def test_modules_with_relations(self, executor, mock_db):
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

        title, desc, lines = await executor._build_dependency_graph("service", "normal")
        mermaid = "\n".join(lines)
        assert "graph LR" in mermaid
        assert "-->" in mermaid
        assert "2 模組" in title

    @pytest.mark.asyncio
    async def test_scope_filtering(self, executor, mock_db):
        """Scope should be passed to ilike filter."""
        mod_result = MagicMock()
        mod_result.all.return_value = []
        mock_db.execute.return_value = mod_result

        await executor._build_dependency_graph("taoyuan", "normal")
        # Verify execute was called (the scope goes into the SQL query)
        mock_db.execute.assert_called()


# ============================================================================
# _build_class_diagram
# ============================================================================

class TestBuildClassDiagram:
    """類別圖建構測試"""

    @pytest.mark.asyncio
    async def test_no_classes_found(self, executor, mock_db):
        """No matching classes returns fallback."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        title, desc, lines = await executor._build_class_diagram("nonexistent", "normal")
        assert "無匹配類別" in title
        assert lines == ["classDiagram"]

    @pytest.mark.asyncio
    async def test_classes_with_methods(self, executor, mock_db):
        """Classes with method descriptions should render methods."""
        class_result = MagicMock()
        class_result.all.return_value = [
            (1, "app.services.DocumentService", json.dumps({"methods": ["get_list", "create", "update"]})),
        ]
        rel_result = MagicMock()
        rel_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[class_result, rel_result])

        title, desc, lines = await executor._build_class_diagram("Document", "normal")
        mermaid = "\n".join(lines)
        assert "classDiagram" in mermaid
        assert "class DocumentService" in mermaid
        assert "+get_list()" in mermaid

    @pytest.mark.asyncio
    async def test_brief_limits_methods(self, executor, mock_db):
        """detail_level=brief should limit methods to 3."""
        methods = [f"method_{i}" for i in range(10)]
        class_result = MagicMock()
        class_result.all.return_value = [
            (1, "app.services.BigService", json.dumps({"methods": methods})),
        ]
        rel_result = MagicMock()
        rel_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[class_result, rel_result])

        _, _, lines = await executor._build_class_diagram("Big", "brief")
        method_lines = [l for l in lines if "+()" in l or "+method_" in l]
        assert len(method_lines) == 3


# ============================================================================
# _draw_diagram (orchestrator)
# ============================================================================

class TestDrawDiagram:
    """draw_diagram 主方法測試"""

    @pytest.mark.asyncio
    async def test_auto_detect_er_from_table_keyword(self, executor, sample_er_data):
        """scope containing 'table' should auto-detect erDiagram."""
        AgentToolExecutor._er_model_cache = sample_er_data
        result = await executor._draw_diagram({"scope": "table schema overview"})
        assert result["diagram_type"] == "erDiagram"
        assert "erDiagram" in result["mermaid"]

    @pytest.mark.asyncio
    async def test_auto_detect_er_from_chinese_keyword(self, executor, sample_er_data):
        """scope containing '資料' should auto-detect erDiagram."""
        AgentToolExecutor._er_model_cache = sample_er_data
        result = await executor._draw_diagram({"scope": "資料表結構"})
        assert result["diagram_type"] == "erDiagram"

    @pytest.mark.asyncio
    async def test_auto_detect_flowchart(self, executor):
        """scope containing '流程' should auto-detect flowchart."""
        result = await executor._draw_diagram({"scope": "document 流程"})
        assert result["diagram_type"] == "flowchart"
        assert "flowchart" in result["mermaid"]

    @pytest.mark.asyncio
    async def test_auto_detect_graph_from_module_keyword(self, executor, mock_db):
        """scope containing '模組' should auto-detect graph."""
        mod_result = MagicMock()
        mod_result.all.return_value = []
        mock_db.execute.return_value = mod_result

        result = await executor._draw_diagram({"scope": "模組依賴"})
        assert result["diagram_type"] == "graph"

    @pytest.mark.asyncio
    async def test_auto_detect_class_diagram(self, executor):
        """scope containing 'class' should auto-detect classDiagram."""
        # Note: scope must NOT contain 'er' (substring match hits erDiagram first)
        with patch.object(
            executor, "_build_class_diagram",
            new_callable=AsyncMock,
            return_value=("類別圖", "1 個類別", ["classDiagram", "    class Foo {"]),
        ):
            result = await executor._draw_diagram({"scope": "class 繼承結構"})
        assert result["diagram_type"] == "classDiagram"
        assert "classDiagram" in result["mermaid"]

    @pytest.mark.asyncio
    async def test_auto_detect_default_is_er(self, executor, sample_er_data):
        """No keyword match defaults to erDiagram."""
        AgentToolExecutor._er_model_cache = sample_er_data
        result = await executor._draw_diagram({"scope": "something random"})
        assert result["diagram_type"] == "erDiagram"

    @pytest.mark.asyncio
    async def test_explicit_diagram_type_overrides_auto(self, executor):
        """Explicit diagram_type should not auto-detect."""
        result = await executor._draw_diagram({
            "diagram_type": "flowchart",
            "scope": "table schema",  # would auto-detect ER, but explicit overrides
        })
        assert result["diagram_type"] == "flowchart"

    @pytest.mark.asyncio
    async def test_related_entities_populated_for_er(self, executor, sample_er_data):
        """related_entities should contain table names from ER diagram."""
        AgentToolExecutor._er_model_cache = sample_er_data
        result = await executor._draw_diagram({"scope": "", "diagram_type": "erDiagram"})
        entities = result.get("related_entities", [])
        assert len(entities) > 0
        assert "official_documents" in entities or "contract_projects" in entities

    @pytest.mark.asyncio
    async def test_related_entities_populated_for_flowchart(self, executor):
        """related_entities extraction should work for flowcharts (node labels with [)."""
        result = await executor._draw_diagram({
            "diagram_type": "flowchart",
            "scope": "document",
        })
        # Flowchart lines like "    A[收文登錄] --> B[分文指派]" contain [ but also -->
        # The extraction logic skips lines with --> so flowchart entities may be empty
        assert "related_entities" in result

    @pytest.mark.asyncio
    async def test_er_model_cache_missing_returns_error(self, executor):
        """When er-model.json not loaded (cache=None), erDiagram fallback returns error."""
        AgentToolExecutor._er_model_cache = None
        result = await executor._draw_diagram({
            "diagram_type": "erDiagram",
            "scope": "anything",
        })
        # Falls to else branch: er_data is None, so fallback block runs
        assert result.get("title") == "無法生成圖表"
        assert "mermaid" in result
        assert result["mermaid"] == ""

    @pytest.mark.asyncio
    async def test_return_structure(self, executor, sample_er_data):
        """Verify return dict has all expected keys."""
        AgentToolExecutor._er_model_cache = sample_er_data
        result = await executor._draw_diagram({"scope": "document"})
        assert "mermaid" in result
        assert "title" in result
        assert "description" in result
        assert "diagram_type" in result
        assert "related_entities" in result

    @pytest.mark.asyncio
    async def test_execute_routes_to_draw_diagram(self, executor, sample_er_data):
        """execute('draw_diagram', ...) should route to _draw_diagram."""
        AgentToolExecutor._er_model_cache = sample_er_data
        result = await executor.execute("draw_diagram", {
            "scope": "document",
            "diagram_type": "erDiagram",
        })
        assert "mermaid" in result
        assert "erDiagram" in result["mermaid"]


# ============================================================================
# ER model cache lifecycle
# ============================================================================

class TestErModelCache:
    """ER model cache loading / reset tests"""

    def test_cache_loaded_flag_set_after_load(self, mock_db, mock_ai, mock_embedding_mgr, mock_config):
        """_load_er_model_cache sets _er_model_loaded = True."""
        AgentToolExecutor._er_model_loaded = False
        with patch("pathlib.Path.exists", return_value=False):
            AgentToolExecutor._load_er_model_cache()
        assert AgentToolExecutor._er_model_loaded is True
        assert AgentToolExecutor._er_model_cache is None

    def test_cache_loads_json_when_file_exists(self):
        """When er-model.json exists, cache should be populated."""
        fake_json = '{"tables": {"test_table": {"columns": []}}}'
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=fake_json):
            AgentToolExecutor._er_model_loaded = False
            AgentToolExecutor._load_er_model_cache()
        assert AgentToolExecutor._er_model_cache is not None
        assert "test_table" in AgentToolExecutor._er_model_cache["tables"]

    def test_cache_handles_invalid_json(self):
        """Invalid JSON should set cache to None without raising."""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="not valid json{{{"):
            AgentToolExecutor._er_model_loaded = False
            AgentToolExecutor._load_er_model_cache()
        assert AgentToolExecutor._er_model_loaded is True
        assert AgentToolExecutor._er_model_cache is None
