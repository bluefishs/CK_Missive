"""
圖譜查詢服務

使用 PostgreSQL Recursive CTE 實作圖譜遍歷：
- K 跳鄰居查詢
- 實體時間軸
- 高頻實體排名
- 圖譜統計

Version: 1.0.0
Created: 2026-02-24
"""

import logging
from typing import List, Optional

import re

from sqlalchemy import select, func as sa_func, literal_column, union_all, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    EntityRelationship,
    DocumentEntityMention,
    GraphIngestionEvent,
)

logger = logging.getLogger(__name__)


class GraphQueryService:
    """圖譜查詢服務"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_entity_detail(self, entity_id: int) -> Optional[dict]:
        """取得實體詳情（含別名、提及公文、關係）"""
        entity = await self.db.get(CanonicalEntity, entity_id)
        if not entity:
            return None

        # 別名
        alias_result = await self.db.execute(
            select(EntityAlias)
            .where(EntityAlias.canonical_entity_id == entity_id)
        )
        aliases = [a.alias_name for a in alias_result.scalars().all()]

        # 提及的公文
        from app.extended.models import OfficialDocument
        mention_result = await self.db.execute(
            select(
                DocumentEntityMention.document_id,
                DocumentEntityMention.mention_text,
                DocumentEntityMention.confidence,
                OfficialDocument.subject,
                OfficialDocument.doc_number,
                OfficialDocument.doc_date,
            )
            .join(OfficialDocument, OfficialDocument.id == DocumentEntityMention.document_id)
            .where(DocumentEntityMention.canonical_entity_id == entity_id)
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(50)
        )
        documents = [
            {
                "document_id": row.document_id,
                "mention_text": row.mention_text,
                "confidence": row.confidence,
                "subject": row.subject,
                "doc_number": row.doc_number,
                "doc_date": str(row.doc_date) if row.doc_date else None,
            }
            for row in mention_result.all()
        ]

        # 關係（出邊 + 入邊）
        out_result = await self.db.execute(
            select(EntityRelationship, CanonicalEntity.canonical_name, CanonicalEntity.entity_type)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.target_entity_id)
            .where(EntityRelationship.source_entity_id == entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
        )
        in_result = await self.db.execute(
            select(EntityRelationship, CanonicalEntity.canonical_name, CanonicalEntity.entity_type)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.source_entity_id)
            .where(EntityRelationship.target_entity_id == entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
        )

        relationships = []
        for row in out_result.all():
            rel = row[0]
            relationships.append({
                "id": rel.id,
                "direction": "outgoing",
                "relation_type": rel.relation_type,
                "relation_label": rel.relation_label,
                "target_name": row[1],
                "target_type": row[2],
                "target_id": rel.target_entity_id,
                "weight": rel.weight,
                "valid_from": str(rel.valid_from) if rel.valid_from else None,
                "valid_to": str(rel.valid_to) if rel.valid_to else None,
                "document_count": rel.document_count,
            })
        for row in in_result.all():
            rel = row[0]
            relationships.append({
                "id": rel.id,
                "direction": "incoming",
                "relation_type": rel.relation_type,
                "relation_label": rel.relation_label,
                "source_name": row[1],
                "source_type": row[2],
                "source_id": rel.source_entity_id,
                "weight": rel.weight,
                "valid_from": str(rel.valid_from) if rel.valid_from else None,
                "valid_to": str(rel.valid_to) if rel.valid_to else None,
                "document_count": rel.document_count,
            })

        return {
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "alias_count": entity.alias_count,
            "mention_count": entity.mention_count,
            "first_seen_at": str(entity.first_seen_at) if entity.first_seen_at else None,
            "last_seen_at": str(entity.last_seen_at) if entity.last_seen_at else None,
            "aliases": aliases,
            "documents": documents,
            "relationships": relationships,
        }

    async def get_neighbors(
        self,
        entity_id: int,
        max_hops: int = 2,
        limit: int = 50,
    ) -> dict:
        """K 跳鄰居查詢"""
        visited = {entity_id}
        current_level = {entity_id}
        all_nodes = []
        all_edges = []

        # 取得根實體
        root = await self.db.get(CanonicalEntity, entity_id)
        if not root:
            return {"nodes": [], "edges": []}
        all_nodes.append({
            "id": root.id,
            "name": root.canonical_name,
            "type": root.entity_type,
            "mention_count": root.mention_count,
            "hop": 0,
        })

        for hop in range(1, max_hops + 1):
            if not current_level:
                break

            next_level = set()
            for eid in current_level:
                # 出邊
                out_result = await self.db.execute(
                    select(EntityRelationship, CanonicalEntity)
                    .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.target_entity_id)
                    .where(EntityRelationship.source_entity_id == eid)
                    .where(EntityRelationship.invalidated_at.is_(None))
                    .limit(limit)
                )
                for rel, target in out_result.all():
                    all_edges.append({
                        "source_id": eid,
                        "target_id": target.id,
                        "relation_type": rel.relation_type,
                        "relation_label": rel.relation_label,
                        "weight": rel.weight,
                    })
                    if target.id not in visited:
                        visited.add(target.id)
                        next_level.add(target.id)
                        all_nodes.append({
                            "id": target.id,
                            "name": target.canonical_name,
                            "type": target.entity_type,
                            "mention_count": target.mention_count,
                            "hop": hop,
                        })

                # 入邊
                in_result = await self.db.execute(
                    select(EntityRelationship, CanonicalEntity)
                    .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.source_entity_id)
                    .where(EntityRelationship.target_entity_id == eid)
                    .where(EntityRelationship.invalidated_at.is_(None))
                    .limit(limit)
                )
                for rel, source in in_result.all():
                    all_edges.append({
                        "source_id": source.id,
                        "target_id": eid,
                        "relation_type": rel.relation_type,
                        "relation_label": rel.relation_label,
                        "weight": rel.weight,
                    })
                    if source.id not in visited:
                        visited.add(source.id)
                        next_level.add(source.id)
                        all_nodes.append({
                            "id": source.id,
                            "name": source.canonical_name,
                            "type": source.entity_type,
                            "mention_count": source.mention_count,
                            "hop": hop,
                        })

            current_level = next_level

        return {"nodes": all_nodes, "edges": all_edges}

    async def get_entity_timeline(self, entity_id: int) -> list:
        """取得實體的關係時間軸"""
        result = await self.db.execute(
            select(
                EntityRelationship,
                CanonicalEntity.canonical_name.label("other_name"),
                CanonicalEntity.entity_type.label("other_type"),
            )
            .join(
                CanonicalEntity,
                CanonicalEntity.id == sa_func.case(
                    (EntityRelationship.source_entity_id == entity_id,
                     EntityRelationship.target_entity_id),
                    else_=EntityRelationship.source_entity_id,
                )
            )
            .where(
                (EntityRelationship.source_entity_id == entity_id)
                | (EntityRelationship.target_entity_id == entity_id)
            )
            .order_by(EntityRelationship.valid_from.asc().nullslast())
        )

        timeline = []
        for row in result.all():
            rel = row[0]
            direction = "outgoing" if rel.source_entity_id == entity_id else "incoming"
            timeline.append({
                "id": rel.id,
                "direction": direction,
                "relation_type": rel.relation_type,
                "relation_label": rel.relation_label,
                "other_name": row.other_name,
                "other_type": row.other_type,
                "weight": rel.weight,
                "valid_from": str(rel.valid_from) if rel.valid_from else None,
                "valid_to": str(rel.valid_to) if rel.valid_to else None,
                "invalidated_at": str(rel.invalidated_at) if rel.invalidated_at else None,
                "document_count": rel.document_count,
            })

        return timeline

    async def get_top_entities(
        self,
        entity_type: Optional[str] = None,
        sort_by: str = "mention_count",
        limit: int = 20,
    ) -> list:
        """高頻實體排名"""
        query = select(CanonicalEntity)

        if entity_type:
            query = query.where(CanonicalEntity.entity_type == entity_type)

        if sort_by == "alias_count":
            query = query.order_by(CanonicalEntity.alias_count.desc().nullslast())
        else:
            query = query.order_by(CanonicalEntity.mention_count.desc().nullslast())

        query = query.limit(limit)
        result = await self.db.execute(query)

        return [
            {
                "id": e.id,
                "canonical_name": e.canonical_name,
                "entity_type": e.entity_type,
                "mention_count": e.mention_count,
                "alias_count": e.alias_count,
                "first_seen_at": str(e.first_seen_at) if e.first_seen_at else None,
                "last_seen_at": str(e.last_seen_at) if e.last_seen_at else None,
            }
            for e in result.scalars().all()
        ]

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """
        搜尋實體（名稱模糊匹配 + 同義詞擴展）

        同義詞擴展：輸入「工務局」會同時搜尋「桃園市政府工務局」等同義詞。
        也搜尋別名表 (entity_alias)，確保縮寫能匹配到正規實體。
        """
        from app.services.ai.synonym_expander import SynonymExpander

        # 擴展搜尋詞（原始 + 同義詞）
        search_terms = SynonymExpander.expand_search_terms(query)

        # 建構 ILIKE OR 條件
        ilike_conditions = []
        for term in search_terms:
            escaped = re.sub(r'([%_\\])', r'\\\1', term)
            ilike_conditions.append(
                CanonicalEntity.canonical_name.ilike(f"%{escaped}%")
            )

        # 也搜尋別名表
        alias_conditions = []
        for term in search_terms:
            escaped = re.sub(r'([%_\\])', r'\\\1', term)
            alias_conditions.append(
                EntityAlias.alias_name.ilike(f"%{escaped}%")
            )

        # 主查詢：canonical_name 匹配（獨立 ID 子查詢）
        main_id_query = select(CanonicalEntity.id).where(or_(*ilike_conditions))
        if entity_type:
            main_id_query = main_id_query.where(CanonicalEntity.entity_type == entity_type)

        # 別名查詢：alias_name 匹配（獨立 ID 子查詢，JOIN 保留在完整語句中）
        alias_id_query = (
            select(CanonicalEntity.id)
            .join(EntityAlias, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(or_(*alias_conditions))
        )
        if entity_type:
            alias_id_query = alias_id_query.where(CanonicalEntity.entity_type == entity_type)

        # 合併去重（兩個子查詢都直接 select ID，無需 with_only_columns）
        combined = union_all(main_id_query, alias_id_query).subquery()

        final_query = (
            select(CanonicalEntity)
            .where(CanonicalEntity.id.in_(select(combined.c.id)))
            .order_by(CanonicalEntity.mention_count.desc().nullslast())
            .limit(limit)
        )

        result = await self.db.execute(final_query)

        return [
            {
                "id": e.id,
                "canonical_name": e.canonical_name,
                "entity_type": e.entity_type,
                "mention_count": e.mention_count,
                "alias_count": e.alias_count,
                "description": e.description,
                "first_seen_at": str(e.first_seen_at) if e.first_seen_at else None,
                "last_seen_at": str(e.last_seen_at) if e.last_seen_at else None,
            }
            for e in result.scalars().all()
        ]

    async def get_graph_stats(self) -> dict:
        """圖譜統計"""
        from .canonical_entity_service import CanonicalEntityService
        svc = CanonicalEntityService(self.db)
        return await svc.get_stats()
