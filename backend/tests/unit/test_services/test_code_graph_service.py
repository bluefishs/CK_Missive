"""
Code Graph 代碼圖譜服務單元測試

測試範圍：
- PythonASTExtractor.discover_files: 檔案探索
- PythonASTExtractor.extract_file: Python AST 提取
- CodeEntity / CodeRelation: 資料結構
- CODE_ENTITY_TYPES / CODE_RELATION_TYPES: 常數
- 類別繼承關係提取
- 函數/方法提取
- import 關係提取

共 8 test cases
"""

import ast
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.ai.code_graph_service import (
    PythonASTExtractor,
    CODE_RELATION_TYPES,
    EXCLUDE_DIRS,
)
from app.services.ai.code_graph_types import CodeEntity, CodeRelation
from app.core.constants import CODE_ENTITY_TYPES


# ============================================================================
# Constants
# ============================================================================

class TestConstants:
    """常數測試"""

    def test_code_entity_types_has_expected(self):
        assert "py_module" in CODE_ENTITY_TYPES
        assert "py_class" in CODE_ENTITY_TYPES
        assert "py_function" in CODE_ENTITY_TYPES

    def test_code_relation_types_has_expected(self):
        assert "defines_class" in CODE_RELATION_TYPES
        assert "defines_function" in CODE_RELATION_TYPES
        assert "imports" in CODE_RELATION_TYPES
        assert "inherits" in CODE_RELATION_TYPES

    def test_exclude_dirs(self):
        assert "__pycache__" in EXCLUDE_DIRS
        assert "node_modules" in EXCLUDE_DIRS


# ============================================================================
# CodeEntity / CodeRelation dataclasses
# ============================================================================

class TestDataClasses:
    """資料結構測試"""

    def test_code_entity_creation(self):
        entity = CodeEntity(
            canonical_name="app.services.test",
            entity_type="py_module",
            description={"lines": 100},
        )
        assert entity.canonical_name == "app.services.test"
        assert entity.entity_type == "py_module"
        assert entity.description["lines"] == 100

    def test_code_relation_creation(self):
        rel = CodeRelation(
            source_name="app.services.test",
            source_type="py_module",
            target_name="app.services.test::MyClass",
            target_type="py_class",
            relation_type="defines_class",
        )
        assert rel.relation_type == "defines_class"


# ============================================================================
# PythonASTExtractor
# ============================================================================

class TestPythonASTExtractor:
    """Python AST 提取器測試"""

    @pytest.fixture
    def extractor(self):
        return PythonASTExtractor(project_prefix="app")

    @pytest.fixture
    def temp_project(self, tmp_path):
        """建立臨時 Python 專案結構"""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("", encoding="utf-8")

        services_dir = app_dir / "services"
        services_dir.mkdir()
        (services_dir / "__init__.py").write_text("", encoding="utf-8")

        # 寫入一個包含 class 的 Python 檔案
        (services_dir / "sample_service.py").write_text(
            '''"""Sample service."""

from app.core.config import settings

class SampleService:
    """A sample service."""

    def __init__(self, db):
        self.db = db

    async def get_items(self):
        """Get items."""
        return []

def helper_function():
    """A helper."""
    pass
''',
            encoding="utf-8",
        )
        return tmp_path

    def test_discover_files(self, extractor, temp_project):
        app_dir = temp_project / "app"
        files = extractor.discover_files(app_dir)
        # Should find sample_service.py (tiny __init__.py filtered)
        module_names = [m for _, m in files]
        assert any("sample_service" in m for m in module_names)

    def test_extract_file_entities(self, extractor, temp_project):
        sample_path = temp_project / "app" / "services" / "sample_service.py"
        entities, relations = extractor.extract_file(
            sample_path, "app.services.sample_service"
        )

        entity_names = [e.canonical_name for e in entities]
        entity_types = [e.entity_type for e in entities]

        # Module entity
        assert "app.services.sample_service" in entity_names
        assert "py_module" in entity_types

        # Class entity
        assert "app.services.sample_service::SampleService" in entity_names

        # Function entity
        assert any("helper_function" in n for n in entity_names)

    def test_extract_file_relations(self, extractor, temp_project):
        sample_path = temp_project / "app" / "services" / "sample_service.py"
        entities, relations = extractor.extract_file(
            sample_path, "app.services.sample_service"
        )

        relation_types = [r.relation_type for r in relations]
        # Should have defines_class and defines_function
        assert "defines_class" in relation_types
        assert "defines_function" in relation_types

    def test_extract_file_class_methods(self, extractor, temp_project):
        sample_path = temp_project / "app" / "services" / "sample_service.py"
        entities, relations = extractor.extract_file(
            sample_path, "app.services.sample_service"
        )

        # Check method entities
        method_entities = [e for e in entities if e.entity_type == "py_function"]
        method_names = [e.canonical_name for e in method_entities]
        assert any("get_items" in m for m in method_names)

    def test_extract_file_import_relations(self, extractor, temp_project):
        sample_path = temp_project / "app" / "services" / "sample_service.py"
        entities, relations = extractor.extract_file(
            sample_path, "app.services.sample_service"
        )

        import_rels = [r for r in relations if r.relation_type == "imports"]
        # Should detect "from app.core.config import settings"
        assert any("app.core.config" in r.target_name for r in import_rels)

    def test_syntax_error_returns_empty(self, extractor, tmp_path):
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        bad_file = app_dir / "bad.py"
        bad_file.write_text("def broken(:\n  pass", encoding="utf-8")

        entities, relations = extractor.extract_file(bad_file, "app.bad")
        assert entities == []
        assert relations == []
