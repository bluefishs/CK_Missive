"""
正規化實體解析服務

4 階段解析策略（逐步嘗試，命中即停）：
1. 精確匹配 — entity_aliases WHERE alias_name = :name
2. 模糊匹配 — pg_trgm similarity >= 0.75
3. 語意匹配 — pgvector cosine_distance <= 0.15 (若啟用)
4. 新建實體 — 建立 canonical_entity + 自身別名

Version: 1.0.0
Created: 2026-02-24
"""

import logging
import os
from typing import Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    DocumentEntityMention,
)

logger = logging.getLogger(__name__)

PGVECTOR_ENABLED = os.environ.get("PGVECTOR_ENABLED", "false").lower() == "true"

# pg_trgm 模糊匹配閾值
FUZZY_SIMILARITY_THRESHOLD = 0.75


class CanonicalEntityService:
    """正規化實體解析與管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_entity(
        self,
        entity_name: str,
        entity_type: str,
        source: str = "auto",
    ) -> CanonicalEntity:
        """
        解析實體名稱，返回或建立正規化實體。

        4 階段策略（逐步嘗試，命中即停）：
        1. 精確匹配別名
        2. 模糊匹配 (pg_trgm)
        3. 新建實體
        """
        name = entity_name.strip()
        if not name:
            raise ValueError("entity_name 不可為空")

        # Stage 1: 精確匹配
        canonical = await self._exact_match(name, entity_type)
        if canonical:
            logger.debug(f"實體精確匹配: {name} → {canonical.canonical_name}")
            return canonical

        # Stage 2: 模糊匹配 (pg_trgm)
        canonical = await self._fuzzy_match(name, entity_type)
        if canonical:
            # 新增別名
            await self._add_alias(canonical, name, source="auto", confidence=0.8)
            logger.info(f"實體模糊匹配: {name} → {canonical.canonical_name}")
            return canonical

        # Stage 3: 新建實體
        canonical = await self._create_entity(name, entity_type)
        await self._add_alias(canonical, name, source=source)
        logger.info(f"新建正規實體: {name} ({entity_type})")
        return canonical

    async def add_mention(
        self,
        document_id: int,
        canonical_entity: CanonicalEntity,
        mention_text: str,
        confidence: float = 1.0,
        context: Optional[str] = None,
    ) -> DocumentEntityMention:
        """記錄公文中的實體提及"""
        mention = DocumentEntityMention(
            document_id=document_id,
            canonical_entity_id=canonical_entity.id,
            mention_text=mention_text,
            confidence=confidence,
            context=context[:500] if context else None,
        )
        self.db.add(mention)

        # 更新正規實體的統計
        canonical_entity.mention_count = (canonical_entity.mention_count or 0) + 1
        canonical_entity.last_seen_at = sa_func.now()

        return mention

    async def merge_entities(
        self,
        keep_id: int,
        merge_id: int,
    ) -> CanonicalEntity:
        """合併兩個正規實體（將 merge 的所有別名和提及轉移到 keep）"""
        keep_entity = await self.db.get(CanonicalEntity, keep_id)
        merge_entity = await self.db.get(CanonicalEntity, merge_id)

        if not keep_entity or not merge_entity:
            raise ValueError("實體不存在")

        # 轉移別名（先去重：若 keep_entity 已有同名別名則刪除 merge 的重複項）
        from sqlalchemy import update, delete as sa_delete

        keep_alias_result = await self.db.execute(
            select(EntityAlias.alias_name)
            .where(EntityAlias.canonical_entity_id == keep_id)
        )
        keep_alias_names = {row[0] for row in keep_alias_result.all()}

        merge_alias_result = await self.db.execute(
            select(EntityAlias)
            .where(EntityAlias.canonical_entity_id == merge_id)
        )
        merge_aliases = merge_alias_result.scalars().all()

        dup_ids = []
        transfer_ids = []
        for alias in merge_aliases:
            if alias.alias_name in keep_alias_names:
                dup_ids.append(alias.id)
            else:
                transfer_ids.append(alias.id)

        if dup_ids:
            await self.db.execute(
                sa_delete(EntityAlias).where(EntityAlias.id.in_(dup_ids))
            )
        if transfer_ids:
            await self.db.execute(
                update(EntityAlias)
                .where(EntityAlias.id.in_(transfer_ids))
                .values(canonical_entity_id=keep_id)
            )

        # 轉移提及
        await self.db.execute(
            update(DocumentEntityMention)
            .where(DocumentEntityMention.canonical_entity_id == merge_id)
            .values(canonical_entity_id=keep_id)
        )

        # 更新統計
        keep_entity.mention_count = (keep_entity.mention_count or 0) + (merge_entity.mention_count or 0)
        # 重新計算 alias_count（去重後的實際數量）
        actual_alias_count = await self.db.scalar(
            select(sa_func.count())
            .select_from(EntityAlias)
            .where(EntityAlias.canonical_entity_id == keep_id)
        ) or 0
        keep_entity.alias_count = actual_alias_count

        if merge_entity.first_seen_at and (
            not keep_entity.first_seen_at or merge_entity.first_seen_at < keep_entity.first_seen_at
        ):
            keep_entity.first_seen_at = merge_entity.first_seen_at

        # 刪除被合併的實體
        await self.db.delete(merge_entity)
        await self.db.flush()

        logger.info(f"實體合併: {merge_entity.canonical_name} → {keep_entity.canonical_name}")
        return keep_entity

    async def get_stats(self) -> dict:
        """取得知識圖譜統計"""
        from app.extended.models import EntityRelationship, GraphIngestionEvent

        total_entities = await self.db.scalar(
            select(sa_func.count()).select_from(CanonicalEntity)
        ) or 0

        total_aliases = await self.db.scalar(
            select(sa_func.count()).select_from(EntityAlias)
        ) or 0

        total_mentions = await self.db.scalar(
            select(sa_func.count()).select_from(DocumentEntityMention)
        ) or 0

        total_relationships = await self.db.scalar(
            select(sa_func.count()).select_from(EntityRelationship)
            .where(EntityRelationship.invalidated_at.is_(None))
        ) or 0

        total_events = await self.db.scalar(
            select(sa_func.count()).select_from(GraphIngestionEvent)
        ) or 0

        # 實體類型分佈
        type_dist_result = await self.db.execute(
            select(
                CanonicalEntity.entity_type,
                sa_func.count().label("count"),
            )
            .group_by(CanonicalEntity.entity_type)
        )
        type_distribution = {row.entity_type: row.count for row in type_dist_result.all()}

        return {
            "total_entities": total_entities,
            "total_aliases": total_aliases,
            "total_mentions": total_mentions,
            "total_relationships": total_relationships,
            "total_ingestion_events": total_events,
            "entity_type_distribution": type_distribution,
        }

    # ================================================================
    # 內部方法
    # ================================================================

    async def _exact_match(
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

    async def _fuzzy_match(
        self, name: str, entity_type: str,
    ) -> Optional[CanonicalEntity]:
        """Stage 2: pg_trgm 模糊匹配"""
        try:
            from sqlalchemy import text

            # 使用 pg_trgm similarity 函數
            result = await self.db.execute(
                select(CanonicalEntity)
                .where(CanonicalEntity.entity_type == entity_type)
                .where(
                    sa_func.similarity(CanonicalEntity.canonical_name, name)
                    >= FUZZY_SIMILARITY_THRESHOLD
                )
                .order_by(
                    sa_func.similarity(CanonicalEntity.canonical_name, name).desc()
                )
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            # pg_trgm 擴展未安裝時降級
            logger.debug(f"pg_trgm 模糊匹配失敗 (擴展可能未安裝): {e}")
            return None

    async def _create_entity(
        self, name: str, entity_type: str,
    ) -> CanonicalEntity:
        """建立新的正規化實體"""
        entity = CanonicalEntity(
            canonical_name=name,
            entity_type=entity_type,
            alias_count=1,
            mention_count=0,
        )
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def _add_alias(
        self,
        canonical: CanonicalEntity,
        alias_name: str,
        source: str = "auto",
        confidence: float = 1.0,
    ) -> EntityAlias:
        """新增別名（去重）"""
        # 檢查是否已存在
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
