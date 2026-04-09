"""
公文搜尋輔助函數

從 document_ai_service.py 拆分，提供搜尋相關的工具函數。

Functions:
- resolve_search_entities: 從搜尋意圖和結果中解析正規化實體（橋接圖譜）

Version: 1.0.0
Created: 2026-03-19
"""

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import CanonicalEntity, EntityAlias
from app.schemas.ai.search import DocumentSearchResult, MatchedEntity


async def resolve_search_entities(
    db: AsyncSession,
    parsed_intent: Any,
    search_results: List[DocumentSearchResult],
) -> List[MatchedEntity]:
    """
    從搜尋意圖和結果中解析正規化實體（橋接圖譜）

    嘗試將 sender/receiver 映射到 canonical_entities 表。
    僅做快速精確匹配 + 別名匹配，不涉及 LLM。
    """
    names_to_resolve: List[tuple] = []  # (name, source)

    # 從意圖解析中取得 sender/receiver
    if getattr(parsed_intent, 'sender', None):
        names_to_resolve.append((parsed_intent.sender, "sender"))
    if getattr(parsed_intent, 'receiver', None):
        names_to_resolve.append((parsed_intent.receiver, "receiver"))

    # 從搜尋結果中取得高頻 sender/receiver
    sender_counts: Dict[str, int] = {}
    for r in search_results[:20]:
        if r.sender:
            sender_counts[r.sender] = sender_counts.get(r.sender, 0) + 1
    for name, count in sorted(sender_counts.items(), key=lambda x: -x[1])[:3]:
        if not any(n == name for n, _ in names_to_resolve):
            names_to_resolve.append((name, "sender"))

    if not names_to_resolve:
        return []

    # --- Batch query: collect all names first ---
    all_names = [name for name, _ in names_to_resolve]
    name_to_source = {name: source for name, source in names_to_resolve}

    # 1) Batch canonical_name lookup
    canonical_result = await db.execute(
        select(CanonicalEntity)
        .where(CanonicalEntity.canonical_name.in_(all_names))
    )
    canonical_map: Dict[str, "CanonicalEntity"] = {
        e.canonical_name: e for e in canonical_result.scalars().all()
    }

    # 2) Batch alias lookup for unmatched names
    unmatched_names = [n for n in all_names if n not in canonical_map]
    alias_map: Dict[str, "CanonicalEntity"] = {}
    if unmatched_names:
        alias_result = await db.execute(
            select(CanonicalEntity, EntityAlias.alias_name)
            .join(EntityAlias, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(EntityAlias.alias_name.in_(unmatched_names))
        )
        for row in alias_result.all():
            entity, alias_name = row[0], row[1]
            if alias_name not in alias_map:
                alias_map[alias_name] = entity

    # 3) Build results from batch maps
    matched: List[MatchedEntity] = []
    seen_ids: set = set()

    for name, source in names_to_resolve:
        entity = canonical_map.get(name) or alias_map.get(name)
        if entity and entity.id not in seen_ids:
            seen_ids.add(entity.id)
            matched.append(MatchedEntity(
                entity_id=entity.id,
                canonical_name=entity.canonical_name,
                entity_type=entity.entity_type,
                mention_count=entity.mention_count or 0,
                match_source=source,
            ))

    return matched
