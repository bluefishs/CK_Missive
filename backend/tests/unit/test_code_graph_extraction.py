"""
Code Graph Extraction 單元測試

測試 PythonASTExtractor 的 AST 解析邏輯（純邏輯，無需 DB）。

@version 1.0.0
@date 2026-03-08
"""

import textwrap
from pathlib import Path

import pytest

from app.services.ai.graph.code_graph_service import (
    CodeEntity,
    CodeRelation,
    PythonASTExtractor,
    CODE_ENTITY_TYPES,
    CODE_GRAPH_LABEL,
)


@pytest.fixture
def extractor():
    return PythonASTExtractor(project_prefix="app")


@pytest.fixture
def sample_py(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    code = textwrap.dedent('''\
        """Sample module docstring."""

        from app.services.ai.agent.agent_tools import AgentToolExecutor
        from app.core.dependencies import get_async_db
        import sqlalchemy

        class MyService:
            """A sample service class."""

            def __init__(self, db):
                self.db = db

            async def process(self, data: dict) -> dict:
                """Process the data."""
                return data

            def _private_helper(self):
                pass

        def top_level_function(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        async def async_top_function():
            pass
    ''')
    fpath = tmp_path / "app" / "services" / "sample_service.py"
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(code, encoding="utf-8")
    return fpath


class TestPythonASTExtractor:
    """PythonASTExtractor 核心測試."""

    def test_extract_module_entity(self, extractor, sample_py):
        """Module entity is created with correct metadata."""
        entities, _ = extractor.extract_file(sample_py, "app.services.sample_service")

        modules = [e for e in entities if e.entity_type == "py_module"]
        assert len(modules) == 1
        mod = modules[0]
        assert mod.canonical_name == "app.services.sample_service"
        assert mod.description["lines"] > 0
        assert "Sample module docstring" in mod.description["docstring"]

    def test_module_has_mtime(self, extractor, sample_py):
        """Module description includes file mtime for incremental tracking."""
        entities, _ = extractor.extract_file(sample_py, "app.services.sample_service")
        mod = next(e for e in entities if e.entity_type == "py_module")
        assert "mtime" in mod.description
        assert isinstance(mod.description["mtime"], float)
        assert mod.description["mtime"] > 0

    def test_extract_class(self, extractor, sample_py):
        """Classes are extracted with bases and docstring."""
        entities, relations = extractor.extract_file(sample_py, "app.services.sample_service")

        classes = [e for e in entities if e.entity_type == "py_class"]
        assert len(classes) == 1
        cls = classes[0]
        assert cls.canonical_name == "app.services.sample_service::MyService"
        assert "A sample service class" in cls.description["docstring"]

        # defines_class relation
        dc_rels = [r for r in relations if r.relation_type == "defines_class"]
        assert len(dc_rels) == 1
        assert dc_rels[0].source_name == "app.services.sample_service"
        assert dc_rels[0].target_name == "app.services.sample_service::MyService"

    def test_extract_methods(self, extractor, sample_py):
        """Class methods (including private) are extracted."""
        entities, relations = extractor.extract_file(sample_py, "app.services.sample_service")

        methods = [
            e for e in entities
            if e.entity_type == "py_function"
            and "::MyService." in e.canonical_name
        ]
        method_names = {m.canonical_name.split(".")[-1] for m in methods}
        assert "__init__" in method_names
        assert "process" in method_names
        assert "_private_helper" in method_names

        # Check async flag
        process = next(m for m in methods if "process" in m.canonical_name)
        assert process.description["is_async"] is True

        # Check private flag
        helper = next(m for m in methods if "_private_helper" in m.canonical_name)
        assert helper.description["is_private"] is True

        # has_method relations
        hm_rels = [r for r in relations if r.relation_type == "has_method"]
        assert len(hm_rels) == 3  # __init__, process, _private_helper

    def test_extract_top_level_functions(self, extractor, sample_py):
        """Top-level functions are extracted with defines_function relation."""
        entities, relations = extractor.extract_file(sample_py, "app.services.sample_service")

        top_funcs = [
            e for e in entities
            if e.entity_type == "py_function"
            and "::" in e.canonical_name
            and "." not in e.canonical_name.split("::")[-1]
        ]
        func_names = {f.canonical_name.split("::")[-1] for f in top_funcs}
        assert "top_level_function" in func_names
        assert "async_top_function" in func_names

        # Check args
        tlf = next(f for f in top_funcs if "top_level_function" in f.canonical_name)
        assert tlf.description["args"] == ["x", "y"]
        assert tlf.description["is_async"] is False

        atf = next(f for f in top_funcs if "async_top_function" in f.canonical_name)
        assert atf.description["is_async"] is True

        # defines_function relations
        df_rels = [r for r in relations if r.relation_type == "defines_function"]
        assert len(df_rels) == 2

    def test_extract_imports_intra_project_only(self, extractor, sample_py):
        """Only intra-project imports (app.*) are tracked."""
        _, relations = extractor.extract_file(sample_py, "app.services.sample_service")

        import_rels = [r for r in relations if r.relation_type == "imports"]
        import_targets = {r.target_name for r in import_rels}

        # app.* imports should be captured
        assert "app.services.ai.agent.agent_tools" in import_targets
        assert "app.core.dependencies" in import_targets

        # External (sqlalchemy) should NOT be captured
        assert not any("sqlalchemy" in t for t in import_targets)

    def test_multi_alias_import(self, extractor, tmp_path: Path):
        """Multiple aliases in a single import statement are all captured."""
        code = "import app.foo, app.bar, app.baz\n"
        fpath = tmp_path / "app" / "multi.py"
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(code, encoding="utf-8")

        _, relations = extractor.extract_file(fpath, "app.multi")
        import_rels = [r for r in relations if r.relation_type == "imports"]
        import_targets = {r.target_name for r in import_rels}
        assert "app.foo" in import_targets
        assert "app.bar" in import_targets
        assert "app.baz" in import_targets
        assert len(import_rels) == 3

    def test_self_import_excluded(self, extractor, tmp_path: Path):
        """Module importing itself is excluded."""
        code = "from app.my_module import something\n"
        fpath = tmp_path / "app" / "my_module.py"
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(code, encoding="utf-8")

        _, relations = extractor.extract_file(fpath, "app.my_module")
        import_rels = [r for r in relations if r.relation_type == "imports"]
        assert len(import_rels) == 0

    def test_syntax_error_file(self, extractor, tmp_path: Path):
        """Files with syntax errors return empty results."""
        fpath = tmp_path / "app" / "broken.py"
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text("def broken(:\n  pass\n", encoding="utf-8")

        entities, relations = extractor.extract_file(fpath, "app.broken")
        assert entities == []
        assert relations == []

    def test_discover_files_excludes_pycache(self, extractor, tmp_path: Path):
        """discover_files skips __pycache__ directories."""
        app_dir = tmp_path / "app"
        (app_dir / "real_module.py").parent.mkdir(parents=True, exist_ok=True)
        (app_dir / "real_module.py").write_text("x = 1\n")
        (app_dir / "__pycache__").mkdir()
        (app_dir / "__pycache__" / "cached.py").write_text("x = 1\n")

        files = extractor.discover_files(app_dir)
        file_names = {f[0].name for f in files}
        assert "real_module.py" in file_names
        assert "cached.py" not in file_names

    def test_empty_init_skipped(self, extractor, tmp_path: Path):
        """Empty __init__.py files are skipped."""
        app_dir = tmp_path / "app"
        app_dir.mkdir(parents=True)
        (app_dir / "__init__.py").write_text("")
        (app_dir / "real.py").write_text("x = 1\n")

        files = extractor.discover_files(app_dir)
        modules = {f[1] for f in files}
        assert "app.real" in modules
        # empty __init__.py should be skipped (< MIN_INIT_SIZE)


class TestCodeConstants:
    """Constants validation."""

    def test_code_entity_types(self):
        assert "py_module" in CODE_ENTITY_TYPES
        assert "py_class" in CODE_ENTITY_TYPES
        assert "py_function" in CODE_ENTITY_TYPES
        assert "db_table" in CODE_ENTITY_TYPES

    def test_code_graph_label(self):
        assert CODE_GRAPH_LABEL == "code_graph"


class TestCodeEntityDataclass:
    """CodeEntity / CodeRelation dataclass tests."""

    def test_code_entity_creation(self):
        ent = CodeEntity(
            canonical_name="app.services.my_service",
            entity_type="py_module",
            description={"file_path": "backend/app/services/my_service.py", "lines": 42},
        )
        assert ent.canonical_name == "app.services.my_service"
        assert ent.entity_type == "py_module"
        assert ent.description["lines"] == 42

    def test_code_relation_creation(self):
        rel = CodeRelation(
            source_name="app.services.my_service",
            source_type="py_module",
            target_name="app.services.my_service::MyClass",
            target_type="py_class",
            relation_type="defines_class",
        )
        assert rel.relation_type == "defines_class"
