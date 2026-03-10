"""
Code Graph 代碼圖譜服務

將程式碼結構（Python AST + DB Schema）寫入知識圖譜。
重用 CanonicalEntity + EntityRelationship，不建新表。

Phase 1a MVP: Python AST + SQLAlchemy Schema Reflection

Version: 3.0.0
Created: 2026-03-08
Updated: 2026-03-10 — TypeScript/React 提取 + 架構分析 + 循環偵測 + 增量入圖
"""

import ast
import json
import logging
import os
import re
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.ai.code_graph_types import CodeEntity, CodeRelation
from app.services.ai.ts_extractor import TypeScriptExtractor, TS_EXCLUDE_DIRS

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CODE_ENTITY_TYPES = {
    "py_module", "py_class", "py_function", "db_table",
    "ts_module", "ts_component", "ts_hook",
}
CODE_RELATION_TYPES = {
    "defines_class",
    "defines_function",
    "has_method",
    "imports",
    "inherits",
    "references_table",
    "calls",
    "defines_component",
    "defines_hook",
}
CODE_GRAPH_LABEL = "code_graph"  # relation_label provenance tag

EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", "alembic", ".claude", ".venv", "venv"}
# Only skip truly empty __init__.py (checked by file size)
MIN_INIT_SIZE = 10  # bytes — skip __init__.py smaller than this


# ---------------------------------------------------------------------------
# PythonASTExtractor
# ---------------------------------------------------------------------------

class PythonASTExtractor:
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
        """Parse a single .py file → entities + relations."""
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

        # Module entity
        mod_doc = ast.get_docstring(tree) or ""
        try:
            file_mtime = file_path.stat().st_mtime
        except OSError:
            file_mtime = 0.0
        entities.append(CodeEntity(
            canonical_name=module_name,
            entity_type="py_module",
            description={
                "file_path": file_rel,
                "lines": line_count,
                "docstring": mod_doc[:500] if mod_doc else "",
                "mtime": file_mtime,
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

        return entities, relations

    # -- private helpers --

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
        """Extract intra-project function/method calls as 'calls' relations.

        Resolves call targets to module-level or class-level qualified names
        when the callee is within the project prefix.
        """
        # Build a map of local imports: alias → dotted module
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

            # Determine caller context (enclosing function/class)
            caller = module_name

            # Resolve callee name
            callee: Optional[str] = None
            func_node = node.func
            if isinstance(func_node, ast.Name):
                # Direct call: e.g. some_function()
                if func_node.id in import_map:
                    callee = import_map[func_node.id]
            elif isinstance(func_node, ast.Attribute):
                # Attribute call: e.g. obj.method()
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

    @staticmethod
    def _name_of(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{PythonASTExtractor._name_of(node.value)}.{node.attr}"
        return "?"


# ---------------------------------------------------------------------------
# TypeScriptExtractor — extracted to ts_extractor.py
# (imported at top of file)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SchemaReflector
# ---------------------------------------------------------------------------

class SchemaReflector:
    """Extract database table entities via SQLAlchemy inspection."""

    def reflect_tables(self, db_url: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """Synchronous reflection using Inspector."""
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

                entities.append(CodeEntity(
                    canonical_name=table_name,
                    entity_type="db_table",
                    description={
                        "columns": [c["name"] for c in columns],
                        "column_types": {c["name"]: str(c["type"]) for c in columns},
                        "primary_key": pk.get("constrained_columns", []),
                        "foreign_keys": [
                            {
                                "columns": fk["constrained_columns"],
                                "referred_table": fk["referred_table"],
                            }
                            for fk in fks
                        ],
                        "index_count": len(indexes),
                    },
                ))

            # Build FK relations: table → referred_table
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
# CodeGraphIngestionService
# ---------------------------------------------------------------------------

class CodeGraphIngestionService:
    """Orchestrate extraction → DB ingestion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest(
        self,
        backend_app_dir: Path,
        db_url: Optional[str] = None,
        clean: bool = False,
        incremental: bool = False,
        frontend_src_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Full pipeline: extract → upsert entities → create relations.

        Args:
            incremental: 若為 True，比對檔案 mtime 跳過未變更的模組。
            frontend_src_dir: 前端 src 目錄路徑（啟用 TypeScript 提取）。
        """
        from app.extended.models.knowledge_graph import (
            CanonicalEntity,
            EntityRelationship,
        )

        start = time.monotonic()
        stats: Dict[str, Any] = {
            "modules": 0, "classes": 0, "functions": 0, "tables": 0,
            "ts_modules": 0, "ts_components": 0, "ts_hooks": 0,
            "relations": 0, "errors": 0, "skipped": 0,
        }

        # 1. Clean if requested (overrides incremental)
        if clean:
            cleaned = await self._clean(CanonicalEntity, EntityRelationship)
            logger.info("Cleaned %d entities, %d relations", cleaned[0], cleaned[1])
            incremental = False

        # 1b. Load existing mtime map for incremental mode
        mtime_map: Dict[str, float] = {}
        if incremental:
            mtime_map = await self._load_mtime_map(CanonicalEntity)
            logger.info("Incremental mode: loaded %d existing module mtimes", len(mtime_map))

        # 2. Extract Python AST
        extractor = PythonASTExtractor(project_prefix="app")
        all_entities: List[CodeEntity] = []
        all_relations: List[CodeRelation] = []

        files = extractor.discover_files(backend_app_dir)
        logger.info("Discovered %d Python files", len(files))
        for idx, (fpath, mod_name) in enumerate(files, 1):
            # Skip unchanged files in incremental mode
            if incremental:
                try:
                    current_mtime = fpath.stat().st_mtime
                except OSError:
                    current_mtime = 0.0
                stored_mtime = mtime_map.get(mod_name, 0.0)
                if current_mtime > 0 and current_mtime <= stored_mtime:
                    stats["skipped"] += 1
                    continue

            try:
                ents, rels = extractor.extract_file(fpath, mod_name)
                all_entities.extend(ents)
                all_relations.extend(rels)
            except Exception as e:
                logger.warning("Failed to extract %s: %s", fpath, e)
                stats["errors"] += 1
            if idx % 100 == 0:
                logger.info("Extracted %d/%d files", idx, len(files))

        # 3. Extract DB schema (optional)
        if db_url:
            try:
                reflector = SchemaReflector()
                schema_ents, schema_rels = reflector.reflect_tables(db_url)
                all_entities.extend(schema_ents)
                all_relations.extend(schema_rels)
                logger.info("Reflected %d DB tables", len(schema_ents))
            except Exception as e:
                logger.warning("Schema reflection failed: %s", e)
                stats["errors"] += 1

        # 3b. Extract frontend TypeScript/React (optional)
        if frontend_src_dir and frontend_src_dir.is_dir():
            try:
                ts_extractor = TypeScriptExtractor(project_prefix="src")
                ts_files = ts_extractor.discover_files(frontend_src_dir)
                logger.info("Discovered %d TypeScript files", len(ts_files))
                ts_skipped = 0
                for idx, (fpath, mod_path) in enumerate(ts_files, 1):
                    if incremental:
                        try:
                            current_mtime = fpath.stat().st_mtime
                        except OSError:
                            current_mtime = 0.0
                        stored_mtime = mtime_map.get(mod_path, 0.0)
                        if current_mtime > 0 and current_mtime <= stored_mtime:
                            ts_skipped += 1
                            stats["skipped"] += 1
                            continue
                    try:
                        ents, rels = ts_extractor.extract_file(fpath, mod_path)
                        all_entities.extend(ents)
                        all_relations.extend(rels)
                    except Exception as e:
                        logger.warning("Failed to extract TS %s: %s", fpath, e)
                        stats["errors"] += 1
                if ts_skipped > 0:
                    logger.info("Skipped %d unchanged TypeScript files", ts_skipped)
            except Exception as e:
                logger.warning("TypeScript extraction failed: %s", e)
                stats["errors"] += 1

        logger.info(
            "Extraction complete: %d entities, %d relations",
            len(all_entities), len(all_relations),
        )

        # 4. Batch upsert entities
        entity_map = await self._upsert_entities(all_entities, CanonicalEntity)

        # Count unique entities from this run
        _type_map = {
            "py_module": "modules", "py_class": "classes",
            "py_function": "functions", "db_table": "tables",
            "ts_module": "ts_modules", "ts_component": "ts_components",
            "ts_hook": "ts_hooks",
        }
        seen_keys: Set[str] = set()
        for ent in all_entities:
            key = f"{ent.entity_type}:{ent.canonical_name}"
            if key not in seen_keys:
                seen_keys.add(key)
                stats_key = _type_map.get(ent.entity_type)
                if stats_key:
                    stats[stats_key] += 1

        # 5. Batch recreate relations (delete-then-insert for idempotency)
        rel_count = await self._recreate_relations(
            all_relations, entity_map, EntityRelationship
        )
        stats["relations"] = rel_count

        await self.db.commit()

        elapsed = time.monotonic() - start
        stats["elapsed_s"] = round(elapsed, 2)
        logger.info(
            "Code graph ingestion: %d modules, %d classes, %d functions, "
            "%d tables, %d relations in %.1fs",
            stats["modules"], stats["classes"], stats["functions"],
            stats["tables"], stats["relations"], elapsed,
        )
        return stats

    async def check(self, backend_app_dir: Path, db_url: Optional[str] = None) -> Dict[str, Any]:
        """Dry run: extract and count without writing to DB."""
        extractor = PythonASTExtractor(project_prefix="app")
        all_entities: List[CodeEntity] = []
        all_relations: List[CodeRelation] = []
        errors = 0

        files = extractor.discover_files(backend_app_dir)
        for fpath, mod_name in files:
            try:
                ents, rels = extractor.extract_file(fpath, mod_name)
                all_entities.extend(ents)
                all_relations.extend(rels)
            except Exception:
                errors += 1

        if db_url:
            try:
                reflector = SchemaReflector()
                schema_ents, schema_rels = reflector.reflect_tables(db_url)
                all_entities.extend(schema_ents)
                all_relations.extend(schema_rels)
            except Exception:
                errors += 1

        by_type: Dict[str, int] = {}
        for ent in all_entities:
            by_type[ent.entity_type] = by_type.get(ent.entity_type, 0) + 1

        by_rel: Dict[str, int] = {}
        for rel in all_relations:
            by_rel[rel.relation_type] = by_rel.get(rel.relation_type, 0) + 1

        return {
            "files_scanned": len(files),
            "entities_by_type": by_type,
            "relations_by_type": by_rel,
            "total_entities": len(all_entities),
            "total_relations": len(all_relations),
            "errors": errors,
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Query existing code graph statistics from DB."""
        from app.extended.models.knowledge_graph import (
            CanonicalEntity,
            EntityRelationship,
        )

        # Entity counts by type
        rows = (await self.db.execute(
            select(CanonicalEntity.entity_type, func.count())
            .where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
            .group_by(CanonicalEntity.entity_type)
        )).all()
        entity_counts = {r[0]: r[1] for r in rows}

        # Relation counts by type
        rel_rows = (await self.db.execute(
            select(EntityRelationship.relation_type, func.count())
            .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
            .group_by(EntityRelationship.relation_type)
        )).all()
        relation_counts = {r[0]: r[1] for r in rel_rows}

        return {
            "entities": entity_counts,
            "relations": relation_counts,
            "total_entities": sum(entity_counts.values()),
            "total_relations": sum(relation_counts.values()),
        }

    async def detect_import_cycles(self) -> Dict[str, Any]:
        """Detect circular import dependencies in the code graph.

        Uses DFS to find all import cycles among py_module entities.
        Returns cycle paths for diagnostic purposes.
        """
        from app.extended.models.knowledge_graph import (
            CanonicalEntity,
            EntityRelationship,
        )

        # Load all module names
        mod_rows = (await self.db.execute(
            select(CanonicalEntity.id, CanonicalEntity.canonical_name)
            .where(CanonicalEntity.entity_type == "py_module")
        )).all()
        id_to_name = {r[0]: r[1] for r in mod_rows}
        name_to_id = {r[1]: r[0] for r in mod_rows}

        # Load import edges
        edge_rows = (await self.db.execute(
            select(
                EntityRelationship.source_entity_id,
                EntityRelationship.target_entity_id,
            )
            .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
            .where(EntityRelationship.relation_type == "imports")
        )).all()

        # Build adjacency list
        adj: Dict[int, List[int]] = {}
        for src_id, tgt_id in edge_rows:
            if src_id in id_to_name and tgt_id in id_to_name:
                adj.setdefault(src_id, []).append(tgt_id)

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[int, int] = {nid: WHITE for nid in id_to_name}
        path: List[int] = []
        cycles: List[List[str]] = []

        def dfs(u: int) -> None:
            color[u] = GRAY
            path.append(u)
            for v in adj.get(u, []):
                if color[v] == GRAY:
                    # Found cycle — extract from v to current position
                    idx = path.index(v)
                    cycle = [id_to_name[nid] for nid in path[idx:]]
                    cycle.append(id_to_name[v])  # close the cycle
                    cycles.append(cycle)
                elif color[v] == WHITE:
                    dfs(v)
            path.pop()
            color[u] = BLACK

        for nid in id_to_name:
            if color[nid] == WHITE:
                dfs(nid)

        return {
            "total_modules": len(id_to_name),
            "total_import_edges": len(edge_rows),
            "cycles_found": len(cycles),
            "cycles": cycles[:50],  # limit output
        }

    async def analyze_architecture(self) -> Dict[str, Any]:
        """Analyze code graph for architecture insights.

        Computes:
        - Complexity hotspots: modules with most outgoing dependencies
        - Hub modules: modules imported by the most other modules
        - Large modules: modules with highest line count
        - Unused modules: modules with no incoming imports
        - God classes: classes with the most methods
        """
        from app.extended.models.knowledge_graph import (
            CanonicalEntity,
            EntityRelationship,
        )

        # Load all code entities
        entity_rows = (await self.db.execute(
            select(
                CanonicalEntity.id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
                CanonicalEntity.description,
            ).where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
        )).all()

        id_to_name = {r[0]: r[1] for r in entity_rows}
        id_to_type = {r[0]: r[2] for r in entity_rows}
        id_to_desc = {}
        for r in entity_rows:
            desc = r[3]
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except (json.JSONDecodeError, TypeError):
                    desc = {}
            id_to_desc[r[0]] = desc if isinstance(desc, dict) else {}

        # Load all code relations
        rel_rows = (await self.db.execute(
            select(
                EntityRelationship.source_entity_id,
                EntityRelationship.target_entity_id,
                EntityRelationship.relation_type,
            ).where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        )).all()

        # Compute metrics
        outgoing: Dict[int, int] = {}  # source → count of outgoing imports
        incoming: Dict[int, int] = {}  # target → count of incoming imports
        method_count: Dict[int, int] = {}  # class → method count

        for src_id, tgt_id, rel_type in rel_rows:
            if rel_type == "imports":
                outgoing[src_id] = outgoing.get(src_id, 0) + 1
                incoming[tgt_id] = incoming.get(tgt_id, 0) + 1
            elif rel_type == "has_method":
                method_count[src_id] = method_count.get(src_id, 0) + 1

        # 1. Complexity hotspots (modules with most outgoing deps)
        complexity_hotspots = sorted(
            [
                {"module": id_to_name[nid], "outgoing_deps": cnt}
                for nid, cnt in outgoing.items()
                if nid in id_to_name and id_to_type.get(nid) in ("py_module", "ts_module")
            ],
            key=lambda x: x["outgoing_deps"],
            reverse=True,
        )[:15]

        # 2. Hub modules (most imported by others)
        hub_modules = sorted(
            [
                {"module": id_to_name[nid], "imported_by": cnt}
                for nid, cnt in incoming.items()
                if nid in id_to_name and id_to_type.get(nid) in ("py_module", "ts_module")
            ],
            key=lambda x: x["imported_by"],
            reverse=True,
        )[:15]

        # 3. Large modules (by line count)
        large_modules = sorted(
            [
                {
                    "module": id_to_name[nid],
                    "lines": id_to_desc[nid].get("lines", 0),
                    "type": id_to_type[nid],
                }
                for nid in id_to_name
                if id_to_type.get(nid) in ("py_module", "ts_module")
                and id_to_desc.get(nid, {}).get("lines", 0) > 0
            ],
            key=lambda x: x["lines"],
            reverse=True,
        )[:15]

        # 4. Orphan modules (no incoming imports, exclude __init__)
        all_module_ids = {
            nid for nid in id_to_name
            if id_to_type.get(nid) in ("py_module", "ts_module")
        }
        imported_ids = {tgt for _, tgt, rt in rel_rows if rt == "imports" and tgt in all_module_ids}
        orphan_modules = [
            id_to_name[nid]
            for nid in (all_module_ids - imported_ids)
            if not id_to_name[nid].endswith("__init__")
            and not id_to_name[nid].endswith("/index")
        ][:30]

        # 5. God classes (classes with most methods)
        god_classes = sorted(
            [
                {"class": id_to_name[nid], "method_count": cnt}
                for nid, cnt in method_count.items()
                if nid in id_to_name and id_to_type.get(nid) == "py_class"
            ],
            key=lambda x: x["method_count"],
            reverse=True,
        )[:15]

        return {
            "complexity_hotspots": complexity_hotspots,
            "hub_modules": hub_modules,
            "large_modules": large_modules,
            "orphan_modules": orphan_modules,
            "god_classes": god_classes,
            "summary": {
                "total_entities": len(entity_rows),
                "total_relations": len(rel_rows),
                "py_modules": sum(1 for r in entity_rows if r[2] == "py_module"),
                "ts_modules": sum(1 for r in entity_rows if r[2] == "ts_module"),
                "classes": sum(1 for r in entity_rows if r[2] == "py_class"),
                "components": sum(1 for r in entity_rows if r[2] == "ts_component"),
                "hooks": sum(1 for r in entity_rows if r[2] == "ts_hook"),
            },
        }

    # -- private --

    async def _load_mtime_map(self, CanonicalEntity) -> Dict[str, float]:
        """Load {module_name: mtime} from existing py_module entities."""
        rows = (await self.db.execute(
            select(
                CanonicalEntity.canonical_name,
                CanonicalEntity.description,
            ).where(CanonicalEntity.entity_type == "py_module")
        )).all()

        result: Dict[str, float] = {}
        for name, desc in rows:
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except (json.JSONDecodeError, TypeError):
                    continue
            if isinstance(desc, dict):
                mtime = desc.get("mtime", 0.0)
                if isinstance(mtime, (int, float)):
                    result[name] = float(mtime)
        return result

    async def _clean(self, CanonicalEntity, EntityRelationship) -> Tuple[int, int]:
        """Remove all code graph entities and relations."""
        rel_result = await self.db.execute(
            delete(EntityRelationship)
            .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        )
        ent_result = await self.db.execute(
            delete(CanonicalEntity)
            .where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
        )
        await self.db.flush()
        return ent_result.rowcount, rel_result.rowcount

    async def _upsert_entities(
        self,
        entities: List[CodeEntity],
        CanonicalEntity,
    ) -> Dict[str, int]:
        """Batch upsert code entities via pg INSERT ON CONFLICT. Returns {key: id}."""
        BATCH_SIZE = 500

        # Deduplicate
        seen: Set[str] = set()
        unique: List[Dict[str, Any]] = []
        for ent in entities:
            key = f"{ent.entity_type}:{ent.canonical_name}"
            if key in seen:
                continue
            seen.add(key)
            unique.append({
                "canonical_name": ent.canonical_name,
                "entity_type": ent.entity_type,
                "description": json.dumps(ent.description, ensure_ascii=False),
                "alias_count": 0,
                "mention_count": 0,
            })

        # Batch upsert via ON CONFLICT
        total_batches = (len(unique) + BATCH_SIZE - 1) // BATCH_SIZE
        for i in range(0, len(unique), BATCH_SIZE):
            batch = unique[i:i + BATCH_SIZE]
            stmt = pg_insert(CanonicalEntity).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_canonical_name_type",
                set_={
                    "description": stmt.excluded.description,
                    "last_seen_at": func.now(),
                },
            )
            await self.db.execute(stmt)
            batch_num = i // BATCH_SIZE + 1
            logger.info("Upserted entities batch %d/%d (%d rows)", batch_num, total_batches, len(batch))

        await self.db.flush()

        # Load all code entity IDs in one query
        rows = (await self.db.execute(
            select(
                CanonicalEntity.id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
            ).where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
        )).all()

        return {f"{r[2]}:{r[1]}": r[0] for r in rows}

    async def _recreate_relations(
        self,
        relations: List[CodeRelation],
        entity_map: Dict[str, int],
        EntityRelationship,
    ) -> int:
        """Delete existing code_graph relations, then batch insert new ones."""
        BATCH_SIZE = 500

        await self.db.execute(
            delete(EntityRelationship)
            .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        )

        # Build deduplicated relation values
        seen: Set[Tuple[int, int, str]] = set()
        values: List[Dict[str, Any]] = []

        for rel in relations:
            src_key = f"{rel.source_type}:{rel.source_name}"
            tgt_key = f"{rel.target_type}:{rel.target_name}"
            if src_key not in entity_map or tgt_key not in entity_map:
                continue
            src_id = entity_map[src_key]
            tgt_id = entity_map[tgt_key]

            dedup_key = (src_id, tgt_id, rel.relation_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            values.append({
                "source_entity_id": src_id,
                "target_entity_id": tgt_id,
                "relation_type": rel.relation_type,
                "relation_label": CODE_GRAPH_LABEL,
                "weight": 1.0,
                "document_count": 0,
            })

        # Batch insert
        total_batches = (len(values) + BATCH_SIZE - 1) // BATCH_SIZE if values else 0
        for i in range(0, len(values), BATCH_SIZE):
            batch = values[i:i + BATCH_SIZE]
            await self.db.execute(insert(EntityRelationship), batch)
            batch_num = i // BATCH_SIZE + 1
            logger.info("Inserted relations batch %d/%d (%d rows)", batch_num, total_batches, len(batch))

        await self.db.flush()
        return len(values)

    async def ingest_from_json(
        self,
        file_path: Path,
        clean: bool = True,
    ) -> Dict[str, Any]:
        """Import a pre-generated knowledge_graph.json into the DB.

        This supports the local-first architecture: GitNexus generates the JSON
        locally, and this method ingests it into the knowledge graph DB.

        Args:
            file_path: Path to the knowledge_graph.json file.
            clean: Whether to clear existing code_graph data before import.

        Returns:
            Dict with nodes_imported, edges_imported, elapsed_seconds.
        """
        from app.extended.models.knowledge_graph import (
            CanonicalEntity,
            EntityRelationship,
        )

        start = time.monotonic()

        if not file_path.exists():
            return {
                "nodes_imported": 0,
                "edges_imported": 0,
                "elapsed_seconds": 0.0,
                "message": f"檔案不存在: {file_path}",
            }

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {
                "nodes_imported": 0,
                "edges_imported": 0,
                "elapsed_seconds": 0.0,
                "message": f"JSON 讀取失敗: {e}",
            }

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        if not nodes:
            return {
                "nodes_imported": 0,
                "edges_imported": 0,
                "elapsed_seconds": 0.0,
                "message": "JSON 中無節點資料",
            }

        if clean:
            cleaned = await self._clean(CanonicalEntity, EntityRelationship)
            logger.info("JSON import: cleaned %d entities, %d relations", cleaned[0], cleaned[1])

        # Convert JSON nodes → CodeEntity
        all_entities: List[CodeEntity] = []
        for node in nodes:
            entity_type = node.get("type", "")
            canonical_name = node.get("canonical_name", node.get("id", ""))
            if not entity_type or not canonical_name:
                continue
            desc = {}
            if isinstance(node.get("description"), dict):
                desc = node["description"]
            elif isinstance(node.get("description"), str):
                desc = {"text": node["description"]}
            all_entities.append(CodeEntity(
                canonical_name=canonical_name,
                entity_type=entity_type,
                description=desc,
            ))

        # Convert JSON edges → CodeRelation
        all_relations: List[CodeRelation] = []
        for edge in edges:
            source_id = edge.get("source", "")
            target_id = edge.get("target", "")
            rel_type = edge.get("type", "")
            if not source_id or not target_id or not rel_type:
                continue
            # Parse "entity_type:canonical_name" format
            src_parts = source_id.split(":", 1)
            tgt_parts = target_id.split(":", 1)
            if len(src_parts) != 2 or len(tgt_parts) != 2:
                continue
            all_relations.append(CodeRelation(
                source_name=src_parts[1],
                source_type=src_parts[0],
                target_name=tgt_parts[1],
                target_type=tgt_parts[0],
                relation_type=rel_type,
            ))

        # Upsert entities
        entity_map = await self._upsert_entities(all_entities, CanonicalEntity)

        # Recreate relations
        rel_count = await self._recreate_relations(
            all_relations, entity_map, EntityRelationship
        )

        await self.db.commit()
        elapsed = round(time.monotonic() - start, 2)

        logger.info(
            "JSON import complete: %d nodes, %d edges in %.1fs",
            len(all_entities), rel_count, elapsed,
        )
        return {
            "nodes_imported": len(all_entities),
            "edges_imported": rel_count,
            "elapsed_seconds": elapsed,
            "message": f"匯入完成: {len(all_entities)} 節點, {rel_count} 條邊",
        }
