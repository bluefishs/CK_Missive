"""
Code Graph AST Analyzer

PythonASTExtractor: Python AST 解析，提取模組/類別/函式/匯入/呼叫關係。
SchemaReflector: SQLAlchemy Inspector 反射 DB 結構。

Extracted from: code_graph_service.py (v3.0.0)
Version: 1.1.0 — endpoint extraction moved to ast_endpoint_extractor.py
"""

import ast
import logging
import os
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.ai.graph.ast_endpoint_extractor import EndpointExtractorMixin
from app.services.ai.graph.code_graph_types import CodeEntity, CodeRelation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", "alembic", ".claude", ".venv", "venv"}
MIN_INIT_SIZE = 10  # bytes — skip __init__.py smaller than this


# ---------------------------------------------------------------------------
# PythonASTExtractor
# ---------------------------------------------------------------------------

class PythonASTExtractor(EndpointExtractorMixin):
    """Extract entities and relationships from Python source via ast."""

    def __init__(self, project_prefix: str = "app"):
        self.project_prefix = project_prefix

    # -- public API --

    def discover_files(self, root: Path) -> List[Tuple[Path, str]]:
        """Walk directory, return (file_path, dotted_module_name) pairs."""
        results: List[Tuple[Path, str]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded dirs in-place
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for fname in sorted(filenames):
                if not fname.endswith(".py"):
                    continue
                fpath = Path(dirpath) / fname

                # Skip tiny __init__.py
                if fname == "__init__.py" and fpath.stat().st_size < MIN_INIT_SIZE:
                    continue

                # Build dotted module name relative to root's parent
                rel = fpath.relative_to(root.parent)
                parts = list(PurePosixPath(rel.with_suffix("")).as_posix().split("/"))
                if parts[-1] == "__init__":
                    parts.pop()
                module_name = ".".join(parts)
                results.append((fpath, module_name))
        return results

    def extract_file(
        self, file_path: Path, module_name: str
    ) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """Parse a single .py file -> entities + relations."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            logger.warning("AST parse error in %s: %s", file_path, e)
            return [], []

        file_rel = str(file_path).replace("\\", "/")
        line_count = len(source.splitlines())

        entities: List[CodeEntity] = []
        relations: List[CodeRelation] = []

        mod_doc = ast.get_docstring(tree) or ""
        try:
            file_mtime = file_path.stat().st_mtime
        except OSError:
            file_mtime = 0.0

        class_count = 0
        function_count = 0
        method_count = 0
        has_async = False

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_count += 1
                        if isinstance(item, ast.AsyncFunctionDef):
                            has_async = True
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
                if isinstance(node, ast.AsyncFunctionDef):
                    has_async = True

        entities.append(CodeEntity(
            canonical_name=module_name,
            entity_type="py_module",
            description={
                "file_path": file_rel,
                "lines": line_count,
                "docstring": mod_doc[:500] if mod_doc else "",
                "mtime": file_mtime,
                "class_count": class_count,
                "function_count": function_count,
                "method_count": method_count,
                "is_async_module": has_async,
            },
        ))

        # Top-level classes & functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._extract_class(node, module_name, file_rel, entities, relations)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_top_function(node, module_name, file_rel, entities, relations)

        # Imports (intra-project only)
        self._extract_imports(tree, module_name, relations)

        # Call graph (intra-project calls)
        self._extract_calls(tree, module_name, relations)

        # API endpoints (FastAPI router decorators)
        self._extract_endpoints(tree, module_name, file_rel, entities, relations)

        return entities, relations

    # -- private helpers --

    def _classify_class(self, name: str, bases: List[str]) -> Optional[str]:
        """Classify a class into an infrastructure entity type, or None."""
        if name.endswith("Service") and not name.startswith("_"):
            return "service"
        if name.endswith("Repository") and not name.startswith("_"):
            return "repository"
        if name.endswith("Middleware") and not name.startswith("_"):
            return "middleware"
        # Check base classes for known patterns
        for base in bases:
            if "Service" in base and name.endswith("Service"):
                return "service"
            if "Repository" in base and name.endswith("Repository"):
                return "repository"
        return None

    def _extract_class(
        self,
        node: ast.ClassDef,
        module_name: str,
        file_rel: str,
        entities: List[CodeEntity],
        relations: List[CodeRelation],
    ) -> None:
        cls_name = f"{module_name}::{node.name}"
        bases = [self._name_of(b) for b in node.bases]
        doc = ast.get_docstring(node) or ""

        entities.append(CodeEntity(
            canonical_name=cls_name,
            entity_type="py_class",
            description={
                "file_path": file_rel,
                "line_start": node.lineno,
                "line_end": node.end_lineno or node.lineno,
                "bases": bases,
                "docstring": doc[:500] if doc else "",
            },
        ))
        relations.append(CodeRelation(
            source_name=module_name, source_type="py_module",
            target_name=cls_name, target_type="py_class",
            relation_type="defines_class",
        ))

        # ORM model → db_table 確定性橋（整合強化 2026-07-20）：__tablename__ 連 code↔DB。
        # 使圖譜可答「哪些程式碼碰 X 表」；target db_table 實體由 SchemaReflectorService 建。
        tablename = extract_tablename(node)
        if tablename:
            relations.append(CodeRelation(
                source_name=cls_name, source_type="py_class",
                target_name=tablename, target_type="db_table",
                relation_type="maps_to",
            ))

        # Detect infrastructure entity types (service, repository, middleware)
        infra_type = self._classify_class(node.name, bases)
        if infra_type:
            entities.append(CodeEntity(
                canonical_name=cls_name,
                entity_type=infra_type,
                description={
                    "file_path": file_rel,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno or node.lineno,
                    "module": module_name,
                    "name": node.name,
                    "bases": bases,
                },
            ))
            # Detect repository usage inside service classes
            if infra_type == "service":
                self._extract_service_dependencies(
                    node, cls_name, module_name, relations,
                )

        # Inheritance relations
        for base in bases:
            if base and base not in ("object",):
                relations.append(CodeRelation(
                    source_name=cls_name, source_type="py_class",
                    target_name=base, target_type="py_class",
                    relation_type="inherits",
                ))

        # Methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_name = f"{cls_name}.{item.name}"
                is_async = isinstance(item, ast.AsyncFunctionDef)
                doc_m = ast.get_docstring(item) or ""
                args = [a.arg for a in item.args.args if a.arg != "self"]

                entities.append(CodeEntity(
                    canonical_name=method_name,
                    entity_type="py_function",
                    description={
                        "file_path": file_rel,
                        "line_start": item.lineno,
                        "line_end": item.end_lineno or item.lineno,
                        "args": args,
                        "is_async": is_async,
                        "is_private": item.name.startswith("_"),
                        "docstring": doc_m[:300] if doc_m else "",
                    },
                ))
                relations.append(CodeRelation(
                    source_name=cls_name, source_type="py_class",
                    target_name=method_name, target_type="py_function",
                    relation_type="has_method",
                ))

    def _extract_top_function(
        self,
        node,
        module_name: str,
        file_rel: str,
        entities: List[CodeEntity],
        relations: List[CodeRelation],
    ) -> None:
        func_name = f"{module_name}::{node.name}"
        is_async = isinstance(node, ast.AsyncFunctionDef)
        doc = ast.get_docstring(node) or ""
        args = [a.arg for a in node.args.args]

        entities.append(CodeEntity(
            canonical_name=func_name,
            entity_type="py_function",
            description={
                "file_path": file_rel,
                "line_start": node.lineno,
                "line_end": node.end_lineno or node.lineno,
                "args": args,
                "is_async": is_async,
                "is_private": node.name.startswith("_"),
                "docstring": doc[:300] if doc else "",
            },
        ))
        relations.append(CodeRelation(
            source_name=module_name, source_type="py_module",
            target_name=func_name, target_type="py_function",
            relation_type="defines_function",
        ))

    def _extract_imports(
        self,
        tree: ast.Module,
        module_name: str,
        relations: List[CodeRelation],
    ) -> None:
        """Extract intra-project imports as relations."""
        seen: Set[str] = set()
        prefix = self.project_prefix + "."
        for node in ast.walk(tree):
            targets: List[str] = []
            if isinstance(node, ast.ImportFrom):
                mod = node.module
                if mod and mod.startswith(prefix):
                    targets.append(mod)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(prefix):
                        targets.append(alias.name)

            for target in targets:
                if target != module_name and target not in seen:
                    seen.add(target)
                    relations.append(CodeRelation(
                        source_name=module_name, source_type="py_module",
                        target_name=target, target_type="py_module",
                        relation_type="imports",
                    ))

    def _extract_calls(
        self,
        tree: ast.Module,
        module_name: str,
        relations: List[CodeRelation],
    ) -> None:
        """Extract intra-project function/method calls as 'calls' relations."""
        # Build a map of local imports: alias -> dotted module
        import_map: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(self.project_prefix + "."):
                    for alias in (node.names or []):
                        local_name = alias.asname or alias.name
                        import_map[local_name] = f"{node.module}::{alias.name}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(self.project_prefix + "."):
                        local_name = alias.asname or alias.name
                        import_map[local_name] = alias.name

        seen: Set[str] = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            caller = module_name

            callee: Optional[str] = None
            func_node = node.func
            if isinstance(func_node, ast.Name):
                if func_node.id in import_map:
                    callee = import_map[func_node.id]
            elif isinstance(func_node, ast.Attribute):
                if isinstance(func_node.value, ast.Name):
                    base = func_node.value.id
                    if base in import_map:
                        callee = f"{import_map[base]}.{func_node.attr}"

            if callee and callee not in seen:
                seen.add(callee)
                relations.append(CodeRelation(
                    source_name=caller, source_type="py_module",
                    target_name=callee, target_type="py_function",
                    relation_type="calls",
                ))

    def _extract_service_dependencies(
        self,
        class_node: ast.ClassDef,
        cls_name: str,
        module_name: str,
        relations: List[CodeRelation],
    ) -> None:
        """Detect Repository usage inside a Service class (via __init__ type hints)."""
        for item in class_node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != "__init__":
                continue
            for arg in item.args.args:
                if arg.arg == "self":
                    continue
                ann = arg.annotation
                if ann is None:
                    continue
                ann_name = self._name_of(ann)
                if ann_name.endswith("Repository"):
                    relations.append(CodeRelation(
                        source_name=cls_name,
                        source_type="service",
                        target_name=ann_name,
                        target_type="repository",
                        relation_type="uses_repository",
                    ))
                elif ann_name.endswith("Service"):
                    relations.append(CodeRelation(
                        source_name=cls_name,
                        source_type="service",
                        target_name=ann_name,
                        target_type="service",
                        relation_type="depends_on",
                    ))
            # Also scan __init__ body for self.xxx = XxxRepository(...) patterns
            for stmt in item.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                if not isinstance(stmt.value, ast.Call):
                    continue
                call_name = self._name_of(stmt.value.func) if stmt.value.func else ""
                if call_name.endswith("Repository"):
                    relations.append(CodeRelation(
                        source_name=cls_name,
                        source_type="service",
                        target_name=call_name,
                        target_type="repository",
                        relation_type="uses_repository",
                    ))
                elif call_name.endswith("Service") and call_name != cls_name.split("::")[-1]:
                    relations.append(CodeRelation(
                        source_name=cls_name,
                        source_type="service",
                        target_name=call_name,
                        target_type="service",
                        relation_type="depends_on",
                    ))

    @staticmethod
    def _name_of(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{PythonASTExtractor._name_of(node.value)}.{node.attr}"
        return "?"


# ---------------------------------------------------------------------------
# SchemaReflector
# ---------------------------------------------------------------------------

class SchemaReflector:
    """[DEPRECATED 2026-07-20] 自建 sync Inspector 反射 DB → db_table 實體。

    異質同工整合後已無呼叫端：db_table 實體改由 build_table_entities_from_schema()
    從 SchemaReflectorService（單一反射源 SSOT）建構，FK 交由 _ingest_fk_relations。
    保留一版供相容/回滾，下一版移除。新程式勿用。
    """

    def reflect_tables(self, db_url: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """[DEPRECATED] Synchronous reflection using Inspector. 改用 build_table_entities_from_schema。"""
        from sqlalchemy import create_engine, inspect as sa_inspect

        engine = create_engine(db_url)
        try:
            inspector = sa_inspect(engine)
            entities: List[CodeEntity] = []

            for table_name in sorted(inspector.get_table_names()):
                columns = inspector.get_columns(table_name)
                pk = inspector.get_pk_constraint(table_name)
                fks = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)

                try:
                    unique_constraints = inspector.get_unique_constraints(table_name)
                    unique_constraints_count = len(unique_constraints)
                except Exception:
                    unique_constraints_count = 0

                fk_targets = list({
                    fk["referred_table"] for fk in fks
                    if fk.get("referred_table")
                })

                pk_cols = pk.get("constrained_columns", [])

                entities.append(CodeEntity(
                    canonical_name=table_name,
                    entity_type="db_table",
                    description={
                        "columns": [c["name"] for c in columns],
                        "column_types": {c["name"]: str(c["type"]) for c in columns},
                        "primary_key": pk_cols,
                        "has_primary_key": len(pk_cols) > 0,
                        "foreign_keys": [
                            {
                                "columns": fk["constrained_columns"],
                                "referred_table": fk["referred_table"],
                            }
                            for fk in fks
                        ],
                        "foreign_key_targets": sorted(fk_targets),
                        "index_count": len(indexes),
                        "unique_constraints_count": unique_constraints_count,
                        "row_count_estimate": "unknown",
                    },
                ))

            # Build FK relations: table -> referred_table
            relations: List[CodeRelation] = []
            table_set = {e.canonical_name for e in entities}
            for entity in entities:
                for fk in entity.description.get("foreign_keys", []):
                    referred = fk.get("referred_table")
                    if referred and referred in table_set and referred != entity.canonical_name:
                        relations.append(CodeRelation(
                            source_name=entity.canonical_name,
                            source_type="db_table",
                            target_name=referred,
                            target_type="db_table",
                            relation_type="references_table",
                        ))

            return entities, relations
        finally:
            engine.dispose()


# ---------------------------------------------------------------------------
# 單一 schema 反射 SSOT（程式圖譜↔資料庫圖譜異質同工整合，2026-07-20）
# ---------------------------------------------------------------------------
def build_table_entities_from_schema(schema: Dict[str, Any]) -> List["CodeEntity"]:
    """從 SchemaReflectorService 的 schema dict 建 db_table 實體（純函式）。

    異質同工整合：舊 SchemaReflector.reflect_tables 自建 sync Inspector 反射 DB，
    與 SchemaReflectorService（_ingest_fk_relations 用）重複讀同一 PostgreSQL。
    改由本函式從 SchemaReflectorService.get_full_schema_async() 的輸出建實體，
    消除重複 Inspector＝單一反射源。description 形狀與舊 reflect_tables 一致（保真）。

    FK 關係不在此產出——交由 code_graph_persistence._ingest_fk_relations 單一源
    （避免 FK 雙重計算，DB 現況 relation_type='references' 即出自該處）。

    Args:
        schema: {"tables": [{"name", "columns":[{name,type,primary_key}],
                 "primary_key_columns", "foreign_keys":[{constrained_columns,
                 referred_table}], "indexes", "unique_constraints"}]}
    Returns:
        List[CodeEntity]（entity_type='db_table'）。
    """
    entities: List["CodeEntity"] = []
    for table in schema.get("tables", []):
        table_name = table.get("name", "")
        if not table_name:
            continue
        columns = table.get("columns", [])
        col_names = [c.get("name", "") for c in columns]
        pk_cols = list(table.get("primary_key_columns", []))
        fks = table.get("foreign_keys", [])
        fk_targets = sorted({
            fk.get("referred_table", "") for fk in fks if fk.get("referred_table")
        })
        entities.append(CodeEntity(
            canonical_name=table_name,
            entity_type="db_table",
            description={
                "columns": col_names,
                "column_types": {c.get("name", ""): str(c.get("type", "")) for c in columns},
                "primary_key": pk_cols,
                "has_primary_key": len(pk_cols) > 0,
                "foreign_keys": [
                    {
                        "columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table", ""),
                    }
                    for fk in fks
                ],
                "foreign_key_targets": fk_targets,
                "index_count": len(table.get("indexes", [])),
                "unique_constraints_count": len(table.get("unique_constraints", [])),
                "row_count_estimate": "unknown",
            },
        ))
    return entities


def extract_tablename(node: "ast.ClassDef") -> Optional[str]:
    """從 ORM model ClassDef 取 __tablename__ 常數字串（確定性 code↔DB 橋）。

    整合強化（2026-07-20）：程式圖譜的 db_table 與 code 實體原為兩座孤島
    （0 code→table 連結）。SQLAlchemy model 的 `__tablename__ = "documents"`
    是確定性可 AST 取的字面賦值 → 據此建 py_class→db_table `maps_to` edge，
    橋接兩圖使「哪些程式碼碰 X 表」可經圖譜回答（非 LLM 幻覺）。

    僅 ORM model 有 __tablename__（Pydantic schema 無）＝自我 gate、無誤判。
    回傳表名字串或 None。
    """
    for item in node.body:
        if not isinstance(item, ast.Assign):
            continue
        for tgt in item.targets:
            if isinstance(tgt, ast.Name) and tgt.id == "__tablename__":
                val = item.value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    return val.value
    return None
