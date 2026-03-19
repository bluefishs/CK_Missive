"""
Code Graph 代碼圖譜服務

將程式碼結構（Python AST + DB Schema）寫入知識圖譜。
重用 CanonicalEntity + EntityRelationship，不建新表。

Phase 1a MVP: Python AST + SQLAlchemy Schema Reflection

Version: 3.1.0
Created: 2026-03-08
Updated: 2026-03-15 — 模組拆分重構 (ast_analyzer + analysis)
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.ai.code_graph_types import CodeEntity, CodeRelation
from app.services.ai.code_graph_ast_analyzer import (
    EXCLUDE_DIRS,
    PythonASTExtractor,
    SchemaReflector,
)
from app.services.ai.code_graph_analysis import (
    detect_import_cycles,
    analyze_architecture,
    compute_dependency_metrics,
)
from app.services.ai.ts_extractor import TypeScriptExtractor

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from app.core.constants import CODE_ENTITY_TYPES
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


# ---------------------------------------------------------------------------
# CodeGraphIngestionService
# ---------------------------------------------------------------------------

class CodeGraphIngestionService:
    """Orchestrate extraction -> DB ingestion."""

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
        """Full pipeline: extract -> upsert entities -> create relations.

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

        # 6. Compute dependency metrics
        await compute_dependency_metrics(self.db, CanonicalEntity, EntityRelationship)

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

    async def check(
        self,
        backend_app_dir: Path,
        db_url: Optional[str] = None,
        frontend_src_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Dry run: extract and count without writing to DB."""
        extractor = PythonASTExtractor(project_prefix="app")
        all_entities: List[CodeEntity] = []
        all_relations: List[CodeRelation] = []
        errors = 0
        total_files = 0

        files = extractor.discover_files(backend_app_dir)
        total_files += len(files)
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

        if frontend_src_dir and frontend_src_dir.is_dir():
            try:
                ts_extractor = TypeScriptExtractor(project_prefix="src")
                ts_files = ts_extractor.discover_files(frontend_src_dir)
                total_files += len(ts_files)
                for fpath, mod_path in ts_files:
                    try:
                        ents, rels = ts_extractor.extract_file(fpath, mod_path)
                        all_entities.extend(ents)
                        all_relations.extend(rels)
                    except Exception:
                        errors += 1
            except Exception:
                errors += 1

        by_type: Dict[str, int] = {}
        for ent in all_entities:
            by_type[ent.entity_type] = by_type.get(ent.entity_type, 0) + 1

        by_rel: Dict[str, int] = {}
        for rel in all_relations:
            by_rel[rel.relation_type] = by_rel.get(rel.relation_type, 0) + 1

        return {
            "files_scanned": total_files,
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

        rows = (await self.db.execute(
            select(CanonicalEntity.entity_type, func.count())
            .where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
            .group_by(CanonicalEntity.entity_type)
        )).all()
        entity_counts = {r[0]: r[1] for r in rows}

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
        return await detect_import_cycles(self.db)

    async def analyze_architecture(self) -> Dict[str, Any]:
        return await analyze_architecture(self.db)

    # -- private --

    async def _load_mtime_map(self, CanonicalEntity: Any) -> Dict[str, float]:
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

    async def _clean(self, CanonicalEntity: Any, EntityRelationship: Any) -> Tuple[int, int]:
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
        CanonicalEntity: Any,
    ) -> Dict[str, int]:
        """Batch upsert code entities via pg INSERT ON CONFLICT. Returns {key: id}."""
        BATCH_SIZE = 500

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
        EntityRelationship: Any,
    ) -> int:
        """Delete existing code_graph relations, then batch insert new ones."""
        from sqlalchemy import insert

        BATCH_SIZE = 500

        await self.db.execute(
            delete(EntityRelationship)
            .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        )

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
        """Import a pre-generated knowledge_graph.json into the DB."""
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

        all_entities: List[CodeEntity] = []
        for node in nodes:
            entity_type = node.get("type", "")
            canonical_name = node.get("canonical_name", node.get("id", ""))
            if not entity_type or not canonical_name:
                continue
            desc: Dict[str, Any] = {}
            if isinstance(node.get("description"), dict):
                desc = node["description"]
            elif isinstance(node.get("description"), str):
                desc = {"text": node["description"]}
            all_entities.append(CodeEntity(
                canonical_name=canonical_name,
                entity_type=entity_type,
                description=desc,
            ))

        all_relations: List[CodeRelation] = []
        for edge in edges:
            source_id = edge.get("source", "")
            target_id = edge.get("target", "")
            rel_type = edge.get("type", "")
            if not source_id or not target_id or not rel_type:
                continue
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

        entity_map = await self._upsert_entities(all_entities, CanonicalEntity)

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
