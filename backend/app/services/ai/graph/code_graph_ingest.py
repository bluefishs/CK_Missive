"""
Code Graph 入圖服務 (Ingestion)

負責 Code Graph 的建構管線：
- ingest(): 完整管線 (AST 提取 → upsert 實體 → 建立關聯)
- ingest_from_json(): 從預生成 JSON 匯入
- check_and_rebuild_if_changed(): 增量式變更偵測與重建

DB 持久化操作已拆分至 code_graph_persistence.py (v1.0.0)

拆分自 code_graph_service.py (v3.1.0)

Version: 1.1.0
Created: 2026-04-05
Updated: 2026-04-09
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.services.ai.code_graph_types import CodeEntity, CodeRelation
from app.services.ai.code_graph_ast_analyzer import (
    PythonASTExtractor,
    SchemaReflector,
)
from app.services.ai.code_graph_analysis import compute_dependency_metrics
from app.services.ai.ts_extractor import TypeScriptExtractor

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.graph.code_graph_persistence import CodeGraphPersistenceMixin

logger = logging.getLogger(__name__)


class CodeGraphIngestService(CodeGraphPersistenceMixin):
    """Code Graph 建構與 DB 持久化服務。

    DB persistence methods inherited from CodeGraphPersistenceMixin:
    - _clean, _upsert_entities, _recreate_relations
    - _ingest_fk_relations, _ingest_cross_domain_links, _load_mtime_map
    """

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
            "api_endpoints": 0, "services": 0, "repositories": 0,
            "schemas": 0, "configs": 0, "middlewares": 0,
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
            "api_endpoint": "api_endpoints", "service": "services",
            "repository": "repositories", "schema": "schemas",
            "config": "configs", "middleware": "middlewares",
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

        # 5b. Ingest FK relations from DB schema (via SchemaReflectorService)
        fk_count = await self._ingest_fk_relations(entity_map, EntityRelationship)
        stats["fk_relations"] = fk_count
        stats["relations"] += fk_count

        # 5c. Ingest cross-domain causal links (api_endpoint → business entities)
        causal_count = await self._ingest_cross_domain_links(entity_map, EntityRelationship)
        stats["cross_domain_links"] = causal_count
        stats["relations"] += causal_count

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

    async def check_and_rebuild_if_changed(
        self,
        backend_dir: Path,
        frontend_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Check file mtimes vs last ingest and trigger incremental rebuild if changed.

        Designed to be called from the scheduler (e.g., code_graph_update job).
        Compares current file mtimes against stored mtimes to decide whether
        an incremental ingest is needed.

        Args:
            backend_dir: Backend app directory (e.g., project_root/backend/app)
            frontend_dir: Optional frontend src directory

        Returns:
            Stats dict with rebuild info, or {"status": "up_to_date"} if no changes.
        """
        from app.extended.models.knowledge_graph import CanonicalEntity

        start = time.monotonic()

        # Load stored mtimes from DB
        mtime_map = await self._load_mtime_map(CanonicalEntity)
        if not mtime_map:
            logger.info("No existing mtime data — full ingest needed")
            return await self.ingest(
                backend_app_dir=backend_dir,
                frontend_src_dir=frontend_dir,
                incremental=False,
            )

        # Scan current files and compare
        from app.services.ai.code_graph_ast_analyzer import PythonASTExtractor

        changed_count = 0
        extractor = PythonASTExtractor(project_prefix="app")
        for fpath, mod_name in extractor.discover_files(backend_dir):
            try:
                current_mtime = fpath.stat().st_mtime
            except OSError:
                continue
            stored_mtime = mtime_map.get(mod_name, 0.0)
            if current_mtime > stored_mtime:
                changed_count += 1

        # Check frontend files if provided
        if frontend_dir and frontend_dir.is_dir():
            from app.services.ai.ts_extractor import TypeScriptExtractor

            ts_extractor = TypeScriptExtractor(project_prefix="src")
            for fpath, mod_path in ts_extractor.discover_files(frontend_dir):
                try:
                    current_mtime = fpath.stat().st_mtime
                except OSError:
                    continue
                stored_mtime = mtime_map.get(mod_path, 0.0)
                if current_mtime > stored_mtime:
                    changed_count += 1

        elapsed_check = round(time.monotonic() - start, 2)

        if changed_count == 0:
            logger.info(
                "Code graph up to date — no files changed (checked in %.1fs)",
                elapsed_check,
            )
            return {
                "status": "up_to_date",
                "changed_files": 0,
                "check_elapsed_s": elapsed_check,
            }

        logger.info(
            "Code graph: %d files changed — triggering incremental rebuild",
            changed_count,
        )
        result = await self.ingest(
            backend_app_dir=backend_dir,
            frontend_src_dir=frontend_dir,
            incremental=True,
        )
        result["changed_files"] = changed_count
        result["check_elapsed_s"] = elapsed_check
        return result

