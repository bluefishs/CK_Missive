"""
Code Graph 代碼圖譜服務 (Facade)

將程式碼結構（Python AST + DB Schema）寫入知識圖譜。
重用 CanonicalEntity + EntityRelationship，不建新表。

此模組為 facade，查詢方法保留於此，建構/入圖邏輯委派給
CodeGraphIngestService (code_graph_ingest.py)。

Version: 4.0.0 — 拆分 ingest 至獨立模組
Created: 2026-03-08
Updated: 2026-04-05 — facade 重構 (570L → ~120L)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

# Re-export constants for backward compatibility
from app.core.constants import CODE_ENTITY_TYPES  # noqa: F401
from app.services.ai.graph.code_graph_types import (  # noqa: F401
    CodeEntity,
    CodeRelation,
    CODE_RELATION_TYPES,
    CODE_GRAPH_LABEL,
)
from app.services.ai.graph.code_graph_ast_analyzer import (  # noqa: F401
    EXCLUDE_DIRS,
    PythonASTExtractor,
    SchemaReflector,
)
from app.services.ai.graph.code_graph_analysis import (
    detect_import_cycles,
    analyze_architecture,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CodeGraphIngestionService (facade)
# ---------------------------------------------------------------------------

class CodeGraphIngestionService:
    """Orchestrate extraction -> DB ingestion.

    Query methods (check, get_stats, detect_import_cycles, analyze_architecture)
    live here. Build/ingest logic is delegated to CodeGraphIngestService.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # Lazy import to avoid circular dependency at module level
        from app.services.ai.graph.code_graph_ingest import CodeGraphIngestService
        self._ingest = CodeGraphIngestService(db)

    # -- Delegated ingestion methods --

    async def ingest(
        self,
        backend_app_dir: Path,
        db_url: Optional[str] = None,
        clean: bool = False,
        incremental: bool = False,
        frontend_src_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Full pipeline: extract -> upsert entities -> create relations."""
        return await self._ingest.ingest(
            backend_app_dir=backend_app_dir,
            db_url=db_url,
            clean=clean,
            incremental=incremental,
            frontend_src_dir=frontend_src_dir,
        )

    async def ingest_from_json(
        self,
        file_path: Path,
        clean: bool = True,
    ) -> Dict[str, Any]:
        """Import a pre-generated knowledge_graph.json into the DB."""
        return await self._ingest.ingest_from_json(
            file_path=file_path,
            clean=clean,
        )

    # -- Query methods (kept in facade) --

    async def check(
        self,
        backend_app_dir: Path,
        db_url: Optional[str] = None,
        frontend_src_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Dry run: extract and count without writing to DB."""
        from app.services.ai.graph.code_graph_ast_analyzer import (
            PythonASTExtractor,
            SchemaReflector,
        )
        from app.services.ai.graph.ts_extractor import TypeScriptExtractor

        extractor = PythonASTExtractor(project_prefix="app")
        all_entities: list = []
        all_relations: list = []
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
        from sqlalchemy import func, select
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
