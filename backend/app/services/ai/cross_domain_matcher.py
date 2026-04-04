"""
跨域實體匹配引擎 (Cross-Domain Entity Matcher)

提供 trigram + 語意向量回退的兩階段匹配，
以及 DB 層的實體查詢與關係建立工具。

拆分自 cross_domain_linker.py，供 CrossDomainLinker 調用。

Version: 1.0.0
"""
import logging
import re
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
)
from app.services.ai.canonical_entity_matcher import CanonicalEntityMatcher

logger = logging.getLogger(__name__)

# 每次連結批次上限
BATCH_LIMIT = 200
# 語意回退距離門檻
SEMANTIC_MAX_DISTANCE = 0.15


class CrossDomainMatchEngine:
    """兩階段匹配引擎: trigram → 語意向量回退"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_entities(
        self, entity_type: str, source_project: str,
    ) -> List[CanonicalEntity]:
        """取得指定類型 + 來源的實體清單"""
        result = await self.db.execute(
            select(CanonicalEntity).where(
                and_(
                    CanonicalEntity.entity_type == entity_type,
                    CanonicalEntity.source_project == source_project,
                )
            ).limit(BATCH_LIMIT)
        )
        return list(result.scalars().all())

    async def find_best_match(
        self,
        name: str,
        candidates: List[CanonicalEntity],
        threshold: float = 0.85,
        use_false_match_check: bool = True,
    ) -> tuple[Optional[CanonicalEntity], float]:
        """
        在候選清單中尋找最佳匹配（trigram → 語意向量回退）。

        Stage 1: CanonicalEntityMatcher.compute_similarity (Python 端 trigram)
        Stage 2: 若 trigram 無匹配且 pgvector 啟用，以 cosine_distance 嘗試語意匹配

        Returns:
            (best_entity, best_score) — 無匹配時回傳 (None, 0.0)
        """
        if not candidates or not name:
            return None, 0.0

        # ── Stage 1: Trigram 模糊匹配 ──
        best_entity: Optional[CanonicalEntity] = None
        best_score = 0.0

        for candidate in candidates:
            score = CanonicalEntityMatcher.compute_similarity(
                name, candidate.canonical_name,
            )
            if score >= threshold and score > best_score:
                if use_false_match_check and CanonicalEntityMatcher.is_false_fuzzy_match(
                    name, candidate.canonical_name,
                ):
                    continue
                best_entity = candidate
                best_score = score

        if best_entity is not None:
            return best_entity, best_score

        # ── Stage 2: 語意向量回退 (KG-3) ──
        semantic_result = await self._semantic_fallback(name, candidates)
        if semantic_result is not None:
            return semantic_result

        return None, 0.0

    async def _semantic_fallback(
        self,
        name: str,
        candidates: List[CanonicalEntity],
    ) -> Optional[tuple[CanonicalEntity, float]]:
        """
        KG-3: 當 trigram 匹配失敗時，以 pgvector cosine_distance 嘗試語意匹配。

        使用 DB-level pgvector 查詢（利用 ivfflat/hnsw 索引），
        限定在候選實體 ID 範圍內搜尋，避免 Python 端 O(N) 向量比較。
        """
        from app.core.config import settings as _settings
        if not _settings.PGVECTOR_ENABLED:
            return None

        candidate_ids = [c.id for c in candidates]
        if not candidate_ids:
            return None

        try:
            from app.services.ai.embedding_manager import EmbeddingManager
            if not await EmbeddingManager.is_available():
                return None

            query_emb = await EmbeddingManager.get_embedding(name, connector=None)
            if not query_emb:
                return None
        except Exception:
            return None

        try:
            result = await self.db.execute(
                select(CanonicalEntity)
                .where(
                    CanonicalEntity.id.in_(candidate_ids),
                    CanonicalEntity.embedding.isnot(None),
                    CanonicalEntity.embedding.cosine_distance(query_emb)
                    <= SEMANTIC_MAX_DISTANCE,
                )
                .order_by(
                    CanonicalEntity.embedding.cosine_distance(query_emb)
                )
                .limit(1)
            )
            best_entity = result.scalar_one_or_none()
        except Exception as e:
            logger.debug("Semantic fallback DB query failed: %s", e)
            return None

        if best_entity is not None:
            try:
                dist_result = await self.db.execute(
                    select(
                        CanonicalEntity.embedding.cosine_distance(query_emb)
                    ).where(CanonicalEntity.id == best_entity.id)
                )
                dist = dist_result.scalar_one_or_none() or 0.0
                similarity = 1.0 - dist
            except Exception:
                similarity = 0.85

            logger.info(
                "KG-3 semantic fallback: '%s' → '%s' (sim=%.3f)",
                name, best_entity.canonical_name, similarity,
            )
            return best_entity, similarity

        return None

    async def create_relation_if_absent(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        source_project: str,
    ) -> bool:
        """建立關係（若不存在）。回傳 True 表示新建。"""
        existing = await self.db.execute(
            select(EntityRelationship.id).where(
                and_(
                    EntityRelationship.source_entity_id == source_id,
                    EntityRelationship.target_entity_id == target_id,
                    EntityRelationship.relation_type == relation_type,
                    EntityRelationship.invalidated_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            return False

        self.db.add(EntityRelationship(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type=relation_type,
            relation_label=relation_type.replace("_", " "),
            weight=0.8,
            source_project=source_project,
            document_count=0,
        ))
        return True

    @staticmethod
    def extract_section_name(parcel_name: str) -> Optional[str]:
        """從地段名稱擷取段名 (去掉地號)

        典型格式: "桃園市桃園區大興段0001-0000"
        擷取: "桃園市桃園區大興段"
        """
        match = re.match(r'^(.+?段)', parcel_name)
        return match.group(1) if match else None
