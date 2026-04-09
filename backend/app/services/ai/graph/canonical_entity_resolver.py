"""
正規化實體解析器 — 匹配 + 建立 + 連結

從 canonical_entity_service.py 提取的低層解析邏輯：
- 精確匹配 (alias)
- 語意匹配 (pgvector)
- 實體建立 + 別名新增
- 回溯連結 (link_existing_entities)

Version: 1.0.0 (拆分自 canonical_entity_service v1.1.0)
Created: 2026-03-25
"""

import logging
from typing import Optional

from sqlalchemy import select, func as sa_func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import CanonicalEntity, EntityAlias

logger = logging.getLogger(__name__)


class CanonicalEntityResolver:
    """低層實體解析 — 匹配 / 建立 / 連結"""

    def __init__(self, db: AsyncSession, pgvector_enabled: bool = False):
        self.db = db
        self._pgvector_enabled = pgvector_enabled

    async def exact_match(
        self, name: str, entity_type: str,
    ) -> Optional[CanonicalEntity]:
        """Stage 1: 精確匹配別名"""
        result = await self.db.execute(
            select(CanonicalEntity)
            .join(EntityAlias, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(EntityAlias.alias_name == name)
            .where(CanonicalEntity.entity_type == entity_type)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def semantic_match(
        self, name: str, entity_type: str,
    ) -> Optional[CanonicalEntity]:
        """Stage 3: 語意匹配 — pgvector cosine_distance"""
        if not self._pgvector_enabled:
            return None

        try:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            from app.services.ai.core.ai_config import AIConfig

            if not await EmbeddingManager.is_available():
                return None

            query_emb = await EmbeddingManager.get_embedding(name, connector=None)
            if not query_emb:
                return None

            config = AIConfig.get_instance()
            max_distance = config.kg_semantic_distance

            result = await self.db.execute(
                select(CanonicalEntity)
                .where(
                    CanonicalEntity.entity_type == entity_type,
                    CanonicalEntity.embedding.isnot(None),
                    CanonicalEntity.embedding.cosine_distance(query_emb) <= max_distance,
                )
                .order_by(CanonicalEntity.embedding.cosine_distance(query_emb))
                .limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                logger.debug(
                    "語意匹配候選: %s → %s (type=%s)",
                    name, match.canonical_name, entity_type,
                )
            return match
        except Exception as e:
            logger.debug("語意匹配跳過 (%s): %s", name, e)
            return None

    async def create_entity(
        self, name: str, entity_type: str,
    ) -> CanonicalEntity:
        """建立新的正規化實體，並自動連結結構化記錄"""
        entity = CanonicalEntity(
            canonical_name=name,
            entity_type=entity_type,
            alias_count=1,
            mention_count=0,
        )
        if entity_type == "org":
            entity.linked_agency_id = await self._find_agency_id(name)
        elif entity_type == "project":
            entity.linked_project_id = await self._find_project_id(name)
        self.db.add(entity)
        await self.db.flush()
        try:
            from app.services.ai.graph.graph_query_service import invalidate_graph_cache
            await invalidate_graph_cache("entity_graph:*")
        except Exception:
            pass
        return entity

    async def add_alias(
        self,
        canonical: CanonicalEntity,
        alias_name: str,
        source: str = "auto",
        confidence: float = 1.0,
    ) -> EntityAlias:
        """新增別名（去重）"""
        existing = await self.db.execute(
            select(EntityAlias)
            .where(EntityAlias.alias_name == alias_name)
            .where(EntityAlias.canonical_entity_id == canonical.id)
            .limit(1)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

        alias = EntityAlias(
            alias_name=alias_name,
            canonical_entity_id=canonical.id,
            source=source,
            confidence=confidence,
        )
        self.db.add(alias)
        canonical.alias_count = (canonical.alias_count or 0) + 1
        await self.db.flush()
        return alias

    async def link_existing_entities(
        self,
        record_name: str,
        entity_type: str,
        record_id: int,
        field: str = "linked_agency_id",
    ) -> int:
        """回溯連結：新增業務記錄時，自動連結同名 CanonicalEntity"""
        alias_result = await self.db.execute(
            select(EntityAlias.canonical_entity_id)
            .join(CanonicalEntity, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(EntityAlias.alias_name == record_name)
            .where(CanonicalEntity.entity_type == entity_type)
            .where(getattr(CanonicalEntity, field).is_(None))
        )
        entity_ids = list({row[0] for row in alias_result.all()})

        if not entity_ids:
            return 0

        await self.db.execute(
            update(CanonicalEntity)
            .where(CanonicalEntity.id.in_(entity_ids))
            .values({field: record_id})
        )
        await self.db.flush()

        logger.info(
            "回溯連結: %s (%s) → %d 個 CanonicalEntity (field=%s)",
            record_name, entity_type, len(entity_ids), field,
        )

        try:
            from app.services.ai.graph.graph_query_service import invalidate_graph_cache
            await invalidate_graph_cache("entity_graph:*")
        except Exception:
            pass

        return len(entity_ids)

    async def _find_agency_id(self, name: str) -> Optional[int]:
        """精確名稱匹配 government_agencies"""
        from app.extended.models import GovernmentAgency
        result = await self.db.execute(
            select(GovernmentAgency.id)
            .where(
                (GovernmentAgency.agency_name == name)
                | (GovernmentAgency.agency_short_name == name)
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_project_id(self, name: str) -> Optional[int]:
        """精確名稱匹配 taoyuan_projects"""
        from app.extended.models import TaoyuanProject
        result = await self.db.execute(
            select(TaoyuanProject.id)
            .where(TaoyuanProject.project_name == name)
            .limit(1)
        )
        return result.scalar_one_or_none()
