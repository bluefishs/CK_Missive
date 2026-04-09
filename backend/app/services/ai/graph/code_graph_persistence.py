"""
Code Graph DB 持久化服務

負責 Code Graph 的 DB CRUD 操作：
- _clean(): 清除所有 code graph 資料
- _upsert_entities(): 批次 upsert 實體
- _recreate_relations(): 刪除後重建關聯
- _ingest_fk_relations(): FK 關聯入圖
- _ingest_cross_domain_links(): 跨域因果連結
- _load_mtime_map(): 增量模式的 mtime 快取

拆分自 code_graph_ingest.py (v1.0.0)

Version: 1.0.0
Created: 2026-04-09
"""

import json
import logging
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CODE_ENTITY_TYPES
from app.services.ai.code_graph_types import CODE_GRAPH_LABEL, CodeEntity, CodeRelation

logger = logging.getLogger(__name__)


class CodeGraphPersistenceMixin:
    """DB persistence operations for Code Graph.

    Mixed into CodeGraphIngestService to provide all DB write/read helpers.
    Expects `self.db: AsyncSession` to be available.
    """

    db: AsyncSession

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

    async def _ingest_fk_relations(
        self,
        entity_map: Dict[str, int],
        EntityRelationship: Any,
    ) -> int:
        """Ingest FK relationships from DB schema via SchemaReflectorService.

        For each FK constraint, creates a 'references' relation from
        source_table entity to target_table entity.
        """
        from sqlalchemy import insert as sa_insert

        try:
            from app.services.ai.schema_reflector import SchemaReflectorService
            schema = await SchemaReflectorService.get_full_schema_async()
        except Exception as e:
            logger.warning("FK relation ingestion skipped — schema reflection failed: %s", e)
            return 0

        tables = schema.get("tables", [])
        seen: Set[Tuple[int, int]] = set()
        values: List[Dict[str, Any]] = []

        for table in tables:
            table_name = table.get("name", "")
            src_key = f"db_table:{table_name}"
            if src_key not in entity_map:
                continue

            src_id = entity_map[src_key]
            for fk in table.get("foreign_keys", []):
                referred = fk.get("referred_table", "")
                if not referred or referred == table_name:
                    continue
                tgt_key = f"db_table:{referred}"
                if tgt_key not in entity_map:
                    continue
                tgt_id = entity_map[tgt_key]

                dedup = (src_id, tgt_id)
                if dedup in seen:
                    continue
                seen.add(dedup)

                values.append({
                    "source_entity_id": src_id,
                    "target_entity_id": tgt_id,
                    "relation_type": "references",
                    "relation_label": CODE_GRAPH_LABEL,
                    "weight": 1.0,
                    "document_count": 0,
                    "confidence_level": "extracted",
                })

        if not values:
            return 0

        for i in range(0, len(values), 500):
            batch = values[i:i + 500]
            await self.db.execute(sa_insert(EntityRelationship), batch)

        await self.db.flush()
        logger.info("Ingested %d FK relations from DB schema", len(values))
        return len(values)

    async def _ingest_cross_domain_links(
        self,
        entity_map: Dict[str, int],
        EntityRelationship: Any,
    ) -> int:
        """Create cross-domain links from api_endpoint entities to business entities.

        Heuristic mapping:
        - /documents -> entity_type 'project' (document management)
        - /erp -> entity_type 'org'
        - /tender -> entity_type 'org'

        Uses relation_type='serves_domain' with confidence_level='inferred'.
        """
        from sqlalchemy import insert as sa_insert

        # Collect business entities by type
        business_entities: Dict[str, List[Tuple[str, int]]] = {}
        for key, eid in entity_map.items():
            etype, _, ename = key.partition(":")
            if etype in ("org", "person", "project", "location", "topic"):
                business_entities.setdefault(etype, []).append((ename, eid))

        if not business_entities:
            logger.debug("No business entities found for cross-domain linking")
            return 0

        # Path prefix -> target business entity type
        domain_map = {
            "/documents": "project",
            "/erp": "org",
            "/tender": "org",
        }

        # Collect api_endpoint entities
        api_endpoints: List[Tuple[str, int]] = []
        for key, eid in entity_map.items():
            if key.startswith("api_endpoint:"):
                api_endpoints.append((key[len("api_endpoint:"):], eid))

        if not api_endpoints:
            return 0

        seen: Set[Tuple[int, int]] = set()
        values: List[Dict[str, Any]] = []

        for ep_path, ep_id in api_endpoints:
            for prefix, target_type in domain_map.items():
                if prefix not in ep_path:
                    continue
                targets = business_entities.get(target_type, [])
                for _, target_id in targets:
                    dedup = (ep_id, target_id)
                    if dedup in seen:
                        continue
                    seen.add(dedup)

                    values.append({
                        "source_entity_id": ep_id,
                        "target_entity_id": target_id,
                        "relation_type": "serves_domain",
                        "relation_label": CODE_GRAPH_LABEL,
                        "weight": 0.5,
                        "document_count": 0,
                        "confidence_level": "inferred",
                    })

        if not values:
            return 0

        for i in range(0, len(values), 500):
            batch = values[i:i + 500]
            await self.db.execute(sa_insert(EntityRelationship), batch)

        await self.db.flush()
        logger.info("Ingested %d cross-domain links (api_endpoint -> business)", len(values))
        return len(values)
