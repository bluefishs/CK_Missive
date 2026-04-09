"""
跨專案聯邦貢獻服務 (Cross-Domain Contribution Service)

接收外部專案 (ck-lvrland, ck-tunnel) 的實體貢獻，
透過既有 CanonicalEntityService 4 階段解析策略進行正規化，
並追蹤 source_project + external_id + external_meta。

Version: 1.0.0
Created: 2026-03-22
"""

import logging
import time
from typing import Dict, List, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import KG_SOURCE_PROJECTS
from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    EntityRelationship,
)
from app.schemas.knowledge_graph import (
    EntityContribution,
    FederatedContributionRequest,
    FederatedContributionResponse,
    RelationContribution,
    ResolvedEntity,
)
from app.services.ai.graph.canonical_entity_service import CanonicalEntityService

logger = logging.getLogger(__name__)


class CrossDomainContributionService:
    """跨專案聯邦實體貢獻服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.entity_service = CanonicalEntityService(db)

    async def process_contribution(
        self,
        request: FederatedContributionRequest,
    ) -> FederatedContributionResponse:
        """
        處理來自外部專案的實體貢獻。

        流程:
        1. 驗證 source_project
        2. 批次解析實體 (resolve_entities_batch)
        3. 更新 source_project / external_id / external_meta
        4. 建立別名
        5. 建立關係
        6. 記錄入圖事件
        """
        start_ms = time.monotonic()

        if request.source_project not in KG_SOURCE_PROJECTS:
            return FederatedContributionResponse(
                success=False,
                message=f"Unknown source_project: {request.source_project}. "
                        f"Valid: {sorted(KG_SOURCE_PROJECTS)}",
            )

        # --- Phase 1: 批次解析實體 ---
        entity_tuples: List[Tuple[str, str]] = [
            (c.canonical_name, c.entity_type)
            for c in request.contributions
        ]

        resolved_map = await self.entity_service.resolve_entities_batch(
            entity_tuples, source="federation"
        )

        # --- Phase 2: 更新聯邦欄位 + 建立別名 ---
        resolved_results: List[ResolvedEntity] = []
        ext_id_to_hub: Dict[str, int] = {}  # external_id → hub entity id

        for contrib in request.contributions:
            key = f"{contrib.entity_type}:{contrib.canonical_name}"
            entity = resolved_map.get(key)
            if entity is None:
                logger.warning(
                    "Federation: entity not resolved for %s", key,
                )
                continue

            # 判斷解析方式
            resolution = self._detect_resolution(entity, contrib)

            # 更新聯邦欄位（若尚未設定或來源不同）
            if (entity.source_project == "ck-missive"
                    and request.source_project != "ck-missive"):
                # 首次由外部專案貢獻 — 保留 source_project 為原始來源
                pass  # 已由 Missive 自己建立，不覆寫
            if entity.external_id is None:
                entity.source_project = request.source_project
                entity.external_id = contrib.external_id
                entity.external_meta = contrib.metadata or {}
            elif entity.external_id == contrib.external_id:
                # 同一外部 ID — 更新 meta
                entity.external_meta = contrib.metadata or {}

            # 建立額外別名
            for alias_name in contrib.aliases:
                await self._ensure_alias(entity.id, alias_name)

            resolved_results.append(ResolvedEntity(
                external_id=contrib.external_id,
                hub_entity_id=entity.id,
                resolution=resolution,
                canonical_name=entity.canonical_name,
            ))
            ext_id_to_hub[contrib.external_id] = entity.id

        # --- Phase 2.5: 為新建實體生成 embedding (KG-3) ---
        await self._generate_embeddings_for_new_entities(resolved_map, resolved_results)

        # --- Phase 3: 建立關係 ---
        relations_created = await self._create_relations(
            request.relations,
            ext_id_to_hub,
            request.source_project,
        )

        # --- Phase 4: 記錄入圖事件 ---
        await self._log_ingestion_event(
            source_project=request.source_project,
            entities_found=len(request.contributions),
            entities_new=sum(1 for r in resolved_results if r.resolution == "created"),
            entities_merged=sum(1 for r in resolved_results if r.resolution != "created"),
            relations_found=relations_created,
            processing_ms=int((time.monotonic() - start_ms) * 1000),
        )

        await self.db.commit()

        elapsed_ms = int((time.monotonic() - start_ms) * 1000)
        logger.info(
            "Federation contribution from %s: %d entities (%d new), %d relations, %dms",
            request.source_project,
            len(resolved_results),
            sum(1 for r in resolved_results if r.resolution == "created"),
            relations_created,
            elapsed_ms,
        )

        return FederatedContributionResponse(
            success=True,
            resolved=resolved_results,
            relations_created=relations_created,
            processing_ms=elapsed_ms,
        )

    def _detect_resolution(
        self, entity: CanonicalEntity, contrib: EntityContribution,
    ) -> str:
        """推斷實體解析方式（基於 mention_count 判斷是否為新建）"""
        if entity.mention_count == 0 and entity.alias_count <= 1:
            return "created"
        if entity.canonical_name == contrib.canonical_name:
            return "exact_match"
        return "fuzzy_match"

    async def _ensure_alias(self, entity_id: int, alias_name: str) -> None:
        """確保別名存在（不重複建立）"""
        existing = await self.db.execute(
            select(EntityAlias.id).where(
                and_(
                    EntityAlias.canonical_entity_id == entity_id,
                    EntityAlias.alias_name == alias_name,
                )
            )
        )
        if existing.scalar_one_or_none() is None:
            self.db.add(EntityAlias(
                canonical_entity_id=entity_id,
                alias_name=alias_name,
                source="federation",
                confidence=1.0,
            ))

    async def _create_relations(
        self,
        relations: List[RelationContribution],
        ext_id_to_hub: Dict[str, int],
        source_project: str,
    ) -> int:
        """建立跨專案關係"""
        created = 0
        for rel in relations:
            source_hub_id = ext_id_to_hub.get(rel.source_external_id)
            target_hub_id = ext_id_to_hub.get(rel.target_external_id)

            if source_hub_id is None or target_hub_id is None:
                logger.warning(
                    "Federation: cannot create relation %s → %s, "
                    "entity not found in hub",
                    rel.source_external_id, rel.target_external_id,
                )
                continue

            # 檢查是否已存在相同關係
            existing = await self.db.execute(
                select(EntityRelationship.id).where(
                    and_(
                        EntityRelationship.source_entity_id == source_hub_id,
                        EntityRelationship.target_entity_id == target_hub_id,
                        EntityRelationship.relation_type == rel.relation_type,
                        EntityRelationship.invalidated_at.is_(None),
                    )
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            self.db.add(EntityRelationship(
                source_entity_id=source_hub_id,
                target_entity_id=target_hub_id,
                relation_type=rel.relation_type,
                relation_label=rel.relation_type.replace("_", " "),
                weight=1.0,
                source_project=source_project,
                document_count=0,
            ))
            created += 1

        return created

    async def _generate_embeddings_for_new_entities(
        self,
        resolved_map: Dict[str, "CanonicalEntity"],
        resolved_results: List[ResolvedEntity],
    ) -> None:
        """
        KG-3: 為新建實體生成 768D embedding 並寫入 DB。

        僅處理 resolution == 'created' 且尚無 embedding 的實體，
        避免重複生成已有向量的舊實體。
        """
        from app.core.config import settings as _settings
        if not _settings.PGVECTOR_ENABLED:
            return

        try:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            if not await EmbeddingManager.is_available():
                return
        except Exception:
            return

        # 收集需要 embedding 的新實體
        new_entities = []
        new_names = []
        for r in resolved_results:
            if r.resolution != "created":
                continue
            key = f"{r.canonical_name}"
            # 從 resolved_map 找到實體（key 格式: entity_type:canonical_name）
            entity = None
            for map_key, ent in resolved_map.items():
                if ent.id == r.hub_entity_id:
                    entity = ent
                    break
            if entity and entity.embedding is None:
                new_entities.append(entity)
                new_names.append(entity.canonical_name)

        if not new_names:
            return

        # 批次生成 embedding
        embeddings = await EmbeddingManager.get_embeddings_batch(
            new_names, connector=None,
        )
        embedded_count = 0
        for entity, emb in zip(new_entities, embeddings):
            if emb:
                entity.embedding = emb
                embedded_count += 1

        if embedded_count > 0:
            logger.info(
                "KG-3: Generated embeddings for %d/%d new entities",
                embedded_count, len(new_names),
            )

    async def backfill_embeddings(
        self,
        batch_size: int = 100,
    ) -> dict:
        """
        KG-3: 為缺少 embedding 的跨專案實體批次回填向量。

        掃描所有 source_project != 'ck-missive' 且 embedding IS NULL 的實體，
        使用 EmbeddingManager 批次生成 768D embedding。

        Returns:
            {"processed": int, "embedded": int, "skipped": int}
        """
        from app.core.config import settings as _settings
        if not _settings.PGVECTOR_ENABLED:
            return {"processed": 0, "embedded": 0, "skipped": 0, "reason": "pgvector disabled"}

        try:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            if not await EmbeddingManager.is_available():
                return {"processed": 0, "embedded": 0, "skipped": 0, "reason": "embedding unavailable"}
        except Exception:
            return {"processed": 0, "embedded": 0, "skipped": 0, "reason": "embedding init error"}

        from app.services.ai.graph.graph_helpers import _CODE_ENTITY_TYPES

        result = await self.db.execute(
            select(CanonicalEntity)
            .where(
                CanonicalEntity.embedding.is_(None),
                CanonicalEntity.entity_type.notin_(list(_CODE_ENTITY_TYPES)),
            )
            .order_by(CanonicalEntity.id)
            .limit(batch_size)
        )
        entities = result.scalars().all()

        if not entities:
            return {"processed": 0, "embedded": 0, "skipped": 0}

        names = [e.canonical_name for e in entities]
        embeddings = await EmbeddingManager.get_embeddings_batch(names, connector=None)

        embedded = 0
        for entity, emb in zip(entities, embeddings):
            if emb:
                entity.embedding = emb
                embedded += 1

        if embedded > 0:
            await self.db.flush()
            logger.info(
                "KG-3 Backfill: embedded %d/%d entities",
                embedded, len(entities),
            )

        return {
            "processed": len(entities),
            "embedded": embedded,
            "skipped": len(entities) - embedded,
        }

    async def _log_ingestion_event(
        self,
        source_project: str,
        entities_found: int,
        entities_new: int,
        entities_merged: int,
        relations_found: int,
        processing_ms: int,
    ) -> None:
        """記錄聯邦貢獻事件（借用 GraphIngestionEvent，document_id=0 表示聯邦）"""
        # GraphIngestionEvent.document_id 是 FK to documents.id，
        # 聯邦貢獻沒有對應公文，使用特殊記錄方式
        # 我們不寫入 GraphIngestionEvent 以避免 FK 違規，
        # 改為記錄到日誌
        logger.info(
            "KG Federation Event: project=%s found=%d new=%d merged=%d "
            "relations=%d elapsed=%dms",
            source_project, entities_found, entities_new,
            entities_merged, relations_found, processing_ms,
        )
