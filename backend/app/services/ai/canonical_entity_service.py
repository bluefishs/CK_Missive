"""
正規化實體解析服務

4 階段解析策略（逐步嘗試，命中即停）：
1. 精確匹配 — entity_aliases WHERE alias_name = :name
2. 模糊匹配 — pg_trgm similarity >= 0.85
3. 語意匹配 — pgvector cosine_distance <= 0.15 (若啟用)
4. 新建實體 — 建立 canonical_entity + 自身別名

Version: 1.1.0
Created: 2026-02-24
"""

import logging
import os
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    DocumentEntityMention,
)
from app.services.ai.canonical_entity_matcher import (
    CanonicalEntityMatcher,
    CanonicalEntityMerger,
)

logger = logging.getLogger(__name__)

from app.core.config import settings as _settings
PGVECTOR_ENABLED = _settings.PGVECTOR_ENABLED


# 統一編號前綴正則（8-10 碼英數 + 空格 + 名稱）
_TAX_ID_PREFIX_RE = re.compile(r'^[A-Z0-9]{8,10}\s+')

# 從 entity_extraction_service 匯入共用黑名單
from app.services.ai.entity_extraction_service import _PRONOUN_ENTITY_BLACKLIST


def _preprocess_entity_name(name: str) -> Optional[str]:
    """前處理實體名稱：NFKC 正規化、統一編號前綴剝離、代名詞過濾"""
    name = unicodedata.normalize('NFKC', name).strip()
    if not name:
        return None
    if name in _PRONOUN_ENTITY_BLACKLIST:
        return None
    # 統一編號前綴剝離
    stripped = _TAX_ID_PREFIX_RE.sub('', name)
    if stripped:
        name = stripped
    return name


class CanonicalEntityService:
    """正規化實體解析與管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._matcher = CanonicalEntityMatcher(db)
        self._merger = CanonicalEntityMerger(db)

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
        3. 語意匹配 (pgvector cosine_distance <= 0.15)
        4. 新建實體
        """
        name = _preprocess_entity_name(entity_name)
        if not name:
            raise ValueError("entity_name 不可為空或為代名詞")

        # Stage 1: 精確匹配
        canonical = await self._exact_match(name, entity_type)
        if canonical:
            logger.debug(f"實體精確匹配: {name} → {canonical.canonical_name}")
            return canonical

        # Stage 2: 模糊匹配 (pg_trgm)
        canonical = await self._matcher.fuzzy_match(name, entity_type)
        if canonical:
            await self._add_alias(canonical, name, source="auto", confidence=0.8)
            logger.info(f"實體模糊匹配: {name} → {canonical.canonical_name}")
            return canonical

        # Stage 3: 語意匹配 (pgvector cosine_distance)
        canonical = await self._semantic_match(name, entity_type)
        if canonical:
            await self._add_alias(canonical, name, source="auto", confidence=0.75)
            logger.info(f"實體語意匹配: {name} → {canonical.canonical_name}")
            return canonical

        # Stage 4: 新建實體
        canonical = await self._create_entity(name, entity_type)
        await self._add_alias(canonical, name, source=source)
        logger.info(f"新建正規實體: {name} ({entity_type})")
        return canonical

    async def resolve_entities_batch(
        self,
        entities: List[Tuple[str, str]],
        source: str = "auto",
    ) -> Dict[str, "CanonicalEntity"]:
        """
        批次解析實體名稱，最小化 DB round-trips。

        將 N 次 per-entity 查詢壓縮為：
        - 1 次批次精確匹配
        - M 次模糊匹配（僅未匹配者）
        - 2 次 flush（建實體 + 建別名）

        Args:
            entities: [(entity_name, entity_type), ...]
            source: 來源標記

        Returns:
            {"entity_type:entity_name": CanonicalEntity} 映射
        """
        result: Dict[str, CanonicalEntity] = {}

        # 去重（保留順序）+ 前處理（代名詞過濾、統一編號前綴剝離）
        deduped: List[Tuple[str, str]] = []
        seen: Set[str] = set()
        for name_raw, etype in entities:
            name = _preprocess_entity_name(name_raw)
            if not name:
                continue
            key = f"{etype}:{name}"
            if key not in seen:
                seen.add(key)
                deduped.append((name, etype))

        if not deduped:
            return result

        # ── Stage 1: 批次精確匹配（1 次查詢取代 N 次）──────────
        all_names = [n for n, _ in deduped]
        exact_result = await self.db.execute(
            select(EntityAlias.alias_name, CanonicalEntity)
            .join(CanonicalEntity, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(EntityAlias.alias_name.in_(all_names))
        )
        # 建立 (alias_name, entity_type) → CanonicalEntity 映射
        exact_lookup: Dict[Tuple[str, str], CanonicalEntity] = {}
        for row in exact_result.all():
            alias_name = row[0]
            canonical = row[1]
            exact_lookup[(alias_name, canonical.entity_type)] = canonical

        unmatched: List[Tuple[str, str]] = []
        for name, etype in deduped:
            key = f"{etype}:{name}"
            canonical = exact_lookup.get((name, etype))
            if canonical:
                result[key] = canonical
                logger.debug(f"批次精確匹配: {name} → {canonical.canonical_name}")
            else:
                unmatched.append((name, etype))

        if not unmatched:
            return result

        # ── Stage 2: 批次模糊匹配（按 entity_type 分組，每組 1 查詢）────
        fuzzy_aliases_to_add: List[Tuple[CanonicalEntity, str]] = []
        still_unmatched: List[Tuple[str, str]] = []

        # 按 entity_type 分組以減少查詢數
        by_type: Dict[str, List[str]] = {}
        for name, etype in unmatched:
            by_type.setdefault(etype, []).append(name)

        for etype, names in by_type.items():
            matched_names = await self._matcher.fuzzy_match_batch(names, etype)
            for name in names:
                canonical = matched_names.get(name)
                if canonical:
                    key = f"{etype}:{name}"
                    result[key] = canonical
                    fuzzy_aliases_to_add.append((canonical, name))
                    logger.info(f"批次模糊匹配: {name} → {canonical.canonical_name}")
                else:
                    still_unmatched.append((name, etype))

        # 批次新增模糊匹配的別名（1 次去重查詢）
        if fuzzy_aliases_to_add:
            fuzzy_names = [n for _, n in fuzzy_aliases_to_add]
            existing_aliases_result = await self.db.execute(
                select(EntityAlias.alias_name, EntityAlias.canonical_entity_id)
                .where(EntityAlias.alias_name.in_(fuzzy_names))
            )
            existing_alias_set: Set[Tuple[str, int]] = {
                (row[0], row[1]) for row in existing_aliases_result.all()
            }
            for canonical, name in fuzzy_aliases_to_add:
                if (name, canonical.id) not in existing_alias_set:
                    self.db.add(EntityAlias(
                        alias_name=name,
                        canonical_entity_id=canonical.id,
                        source="auto",
                        confidence=0.8,
                    ))
                    canonical.alias_count = (canonical.alias_count or 0) + 1

        # ── Stage 3: 批次語意匹配（預批次 embedding + pgvector）────
        if still_unmatched and PGVECTOR_ENABLED:
            semantic_remaining: List[Tuple[str, str]] = []
            # 上限 50 筆，避免大批次 embedding + pgvector 風暴
            semantic_candidates = still_unmatched[:50]
            if len(still_unmatched) > 50:
                semantic_remaining.extend(still_unmatched[50:])
                logger.warning(
                    "語意匹配批次上限 50，跳過 %d 筆",
                    len(still_unmatched) - 50,
                )

            # 預批次取得所有 embeddings（消除 N+1 embedding 計算）
            embeddings_map: Dict[str, list] = {}
            try:
                from app.services.ai.embedding_manager import EmbeddingManager
                if await EmbeddingManager.is_available():
                    for name, _ in semantic_candidates:
                        emb = await EmbeddingManager.get_embedding(name, connector=None)
                        if emb:
                            embeddings_map[name] = emb
            except Exception as e:
                logger.debug("批次 embedding 取得失敗: %s", e)

            if embeddings_map:
                from app.services.ai.ai_config import AIConfig
                config = AIConfig.get_instance()
                max_distance = config.kg_semantic_distance

                for name, etype in semantic_candidates:
                    query_emb = embeddings_map.get(name)
                    if not query_emb:
                        semantic_remaining.append((name, etype))
                        continue
                    try:
                        match_result = await self.db.execute(
                            select(CanonicalEntity)
                            .where(
                                CanonicalEntity.entity_type == etype,
                                CanonicalEntity.embedding.isnot(None),
                                CanonicalEntity.embedding.cosine_distance(query_emb) <= max_distance,
                            )
                            .order_by(CanonicalEntity.embedding.cosine_distance(query_emb))
                            .limit(1)
                        )
                        canonical = match_result.scalar_one_or_none()
                        if canonical:
                            key = f"{etype}:{name}"
                            result[key] = canonical
                            fuzzy_aliases_to_add.append((canonical, name))
                            logger.info(f"批次語意匹配: {name} → {canonical.canonical_name}")
                        else:
                            semantic_remaining.append((name, etype))
                    except Exception as e:
                        logger.debug("語意匹配跳過 (%s): %s", name, e)
                        semantic_remaining.append((name, etype))
            else:
                semantic_remaining.extend(semantic_candidates)

            still_unmatched = semantic_remaining

        # ── Stage 4: 批次建立新實體（2 次 flush：建實體 + 建別名）──
        if still_unmatched:
            new_entities: List[Tuple[str, str, CanonicalEntity]] = []
            for name, etype in still_unmatched:
                entity = CanonicalEntity(
                    canonical_name=name,
                    entity_type=etype,
                    alias_count=1,
                    mention_count=0,
                )
                self.db.add(entity)
                new_entities.append((name, etype, entity))

            # 單次 flush 取得所有新 entity 的 ID
            await self.db.flush()

            # 批次建立自身別名
            for name, etype, entity in new_entities:
                self.db.add(EntityAlias(
                    alias_name=name,
                    canonical_entity_id=entity.id,
                    source=source,
                    confidence=1.0,
                ))
                key = f"{etype}:{name}"
                result[key] = entity
                logger.info(f"批次新建實體: {name} ({etype})")

            await self.db.flush()

        return result

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
        """合併兩個正規實體（委派至 CanonicalEntityMerger）"""
        return await self._merger.merge_entities(keep_id, merge_id)

    # 程式碼圖譜實體類型 (SSOT: constants.py)
    from app.core.constants import CODE_ENTITY_TYPES as _CODE_ENTITY_TYPES

    async def get_stats(self) -> dict:
        """取得知識圖譜統計（公文圖譜 + 程式碼圖譜分離）"""
        from app.extended.models import EntityRelationship, GraphIngestionEvent

        # 公文圖譜實體數
        doc_entities = await self.db.scalar(
            select(sa_func.count()).select_from(CanonicalEntity)
            .where(CanonicalEntity.entity_type.notin_(self._CODE_ENTITY_TYPES))
        ) or 0

        # 程式碼圖譜實體數
        code_entities = await self.db.scalar(
            select(sa_func.count()).select_from(CanonicalEntity)
            .where(CanonicalEntity.entity_type.in_(self._CODE_ENTITY_TYPES))
        ) or 0

        total_aliases = await self.db.scalar(
            select(sa_func.count()).select_from(EntityAlias)
        ) or 0

        total_mentions = await self.db.scalar(
            select(sa_func.count()).select_from(DocumentEntityMention)
        ) or 0

        # 公文圖譜關係數（排除 code entity 的關係）
        total_relationships = await self.db.scalar(
            select(sa_func.count()).select_from(EntityRelationship)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.source_entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
            .where(CanonicalEntity.entity_type.notin_(self._CODE_ENTITY_TYPES))
        ) or 0

        total_events = await self.db.scalar(
            select(sa_func.count()).select_from(GraphIngestionEvent)
        ) or 0

        # 實體類型分佈（僅公文圖譜）
        type_dist_result = await self.db.execute(
            select(
                CanonicalEntity.entity_type,
                sa_func.count().label("count"),
            )
            .where(CanonicalEntity.entity_type.notin_(self._CODE_ENTITY_TYPES))
            .group_by(CanonicalEntity.entity_type)
        )
        type_distribution = {row.entity_type: row.count for row in type_dist_result.all()}

        # KG-3: 實體 embedding 覆蓋率
        entities_with_embedding = await self.db.scalar(
            select(sa_func.count()).select_from(CanonicalEntity)
            .where(
                CanonicalEntity.entity_type.notin_(self._CODE_ENTITY_TYPES),
                CanonicalEntity.embedding.isnot(None),
            )
        ) or 0

        # KG Federation: per-source_project 分布
        project_dist_result = await self.db.execute(
            select(
                sa_func.coalesce(CanonicalEntity.source_project, "ck-missive").label("project"),
                sa_func.count().label("count"),
            )
            .where(CanonicalEntity.entity_type.notin_(self._CODE_ENTITY_TYPES))
            .group_by("project")
        )
        source_project_distribution = {
            row.project: row.count for row in project_dist_result.all()
        }

        return {
            "total_entities": doc_entities,
            "total_code_entities": code_entities,
            "total_aliases": total_aliases,
            "total_mentions": total_mentions,
            "total_relationships": total_relationships,
            "total_ingestion_events": total_events,
            "entity_type_distribution": type_distribution,
            "source_project_distribution": source_project_distribution,
            "entities_with_embedding": entities_with_embedding,
            "embedding_coverage_percent": round(
                (entities_with_embedding / doc_entities * 100) if doc_entities > 0 else 0, 1
            ),
            "entities_without_embedding": max(0, doc_entities - entities_with_embedding),
            "embedding_backfill_needed": (doc_entities - entities_with_embedding) > 10,
        }

    # ================================================================
    # 內部方法
    # ================================================================

    async def _semantic_match(
        self, name: str, entity_type: str,
    ) -> Optional[CanonicalEntity]:
        """
        Stage 3: 語意匹配 — pgvector cosine_distance <= kg_semantic_distance

        僅在 PGVECTOR_ENABLED=true 時啟用。
        透過 EmbeddingManager 取得查詢向量，以 cosine_distance 搜尋同類型實體。
        """
        if not PGVECTOR_ENABLED:
            return None

        try:
            from app.services.ai.embedding_manager import EmbeddingManager
            from app.services.ai.ai_config import AIConfig

            if not await EmbeddingManager.is_available():
                return None

            query_emb = await EmbeddingManager.get_embedding(name, connector=None)
            if not query_emb:
                return None

            config = AIConfig.get_instance()
            max_distance = config.kg_semantic_distance  # default 0.15

            # pgvector cosine_distance search on CanonicalEntity.embedding
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
                distance = None  # logged for debugging
                logger.debug(
                    "語意匹配候選: %s → %s (type=%s)",
                    name, match.canonical_name, entity_type,
                )
            return match
        except Exception as e:
            logger.debug("語意匹配跳過 (%s): %s", name, e)
            return None

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

    async def _create_entity(
        self, name: str, entity_type: str,
    ) -> CanonicalEntity:
        """建立新的正規化實體，並自動嘗試連結結構化記錄"""
        entity = CanonicalEntity(
            canonical_name=name,
            entity_type=entity_type,
            alias_count=1,
            mention_count=0,
        )
        # 自動連結 org → government_agencies
        if entity_type == "org":
            entity.linked_agency_id = await self._find_agency_id(name)
        # 自動連結 project → taoyuan_projects
        elif entity_type == "project":
            entity.linked_project_id = await self._find_project_id(name)
        self.db.add(entity)
        await self.db.flush()
        # 快取失效：新實體影響圖譜查詢結果
        try:
            from app.services.ai.graph_query_service import invalidate_graph_cache
            await invalidate_graph_cache("entity_graph:*")
        except Exception:
            pass  # 快取失效不應影響主流程
        return entity

    async def _find_agency_id(self, name: str) -> int | None:
        """嘗試以精確名稱或簡稱匹配 government_agencies（單一查詢）"""
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

    async def _find_project_id(self, name: str) -> int | None:
        """嘗試以精確名稱匹配 taoyuan_projects"""
        from app.extended.models import TaoyuanProject
        result = await self.db.execute(
            select(TaoyuanProject.id)
            .where(TaoyuanProject.project_name == name)
            .limit(1)
        )
        return result.scalar_one_or_none()

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

    async def link_existing_entities(
        self,
        record_name: str,
        entity_type: str,
        record_id: int,
        field: str = "linked_agency_id",
    ) -> int:
        """
        回溯連結：當新增業務記錄（機關/專案）時，
        自動將已存在的同名 CanonicalEntity 連結到該記錄。

        Args:
            record_name: 業務記錄名稱
            entity_type: 實體類型 ("org" or "project")
            record_id: 業務記錄 ID
            field: 要更新的 FK 欄位名 ("linked_agency_id" or "linked_project_id")

        Returns:
            連結的實體數量
        """
        from sqlalchemy import update

        # 精確匹配：canonical_name 或別名完全相同
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

        # 批次更新
        await self.db.execute(
            update(CanonicalEntity)
            .where(CanonicalEntity.id.in_(entity_ids))
            .values({field: record_id})
        )
        await self.db.flush()

        logger.info(
            f"回溯連結: {record_name} ({entity_type}) → "
            f"{len(entity_ids)} 個 CanonicalEntity (field={field})"
        )

        # 快取失效
        try:
            from app.services.ai.graph_query_service import invalidate_graph_cache
            await invalidate_graph_cache("entity_graph:*")
        except Exception:
            pass

        return len(entity_ids)
