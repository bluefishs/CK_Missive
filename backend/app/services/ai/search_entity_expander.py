"""
搜尋實體擴展器

利用知識圖譜的正規化實體和別名系統，
擴展搜尋詞彙以提升搜尋召回率。

使用場景:
  使用者搜尋「王主任」→ 在 canonical_entities/entity_aliases 中
  發現「王主任」是「王○明」的別名 → 自動擴展搜尋為
  「王主任 OR 王○明」，提升召回率。

Version: 1.0.0
Created: 2026-02-25
"""

import logging
from typing import Dict, List, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import CanonicalEntity, EntityAlias

logger = logging.getLogger(__name__)

# 擴展的最小詞彙長度（避免對單字做擴展查詢）
MIN_TERM_LENGTH = 2

# 單一詞彙的最大擴展數量（防止過度擴展導致查詢效能下降）
MAX_EXPANSIONS_PER_TERM = 10


async def expand_search_terms(
    db: AsyncSession,
    terms: List[str],
) -> Dict[str, Set[str]]:
    """
    擴展搜尋詞彙，返回每個原始詞的擴展集合。

    利用 canonical_entities 和 entity_aliases 表，
    將搜尋詞映射到正規化實體的所有別名，從而擴展搜尋範圍。

    Args:
        db: 資料庫 session
        terms: 原始搜尋詞彙列表

    Returns:
        {original_term: {expanded_term_1, expanded_term_2, ...}}
        包含原始詞本身。若無擴展，集合中僅有原始詞。
    """
    if not terms:
        return {}

    expansions: Dict[str, Set[str]] = {}
    for term in terms:
        expansions[term] = {term}  # always include original

    try:
        for term in terms:
            clean = term.strip()
            if not clean or len(clean) < MIN_TERM_LENGTH:
                continue

            canonical_ids: List[int] = []

            # Step 1: 查找別名匹配（例如「王主任」是某正規實體的別名）
            alias_result = await db.execute(
                select(EntityAlias.canonical_entity_id)
                .where(EntityAlias.alias_name == clean)
            )
            canonical_ids.extend(row[0] for row in alias_result.all())

            # Step 2: 查找正規名稱匹配（例如直接搜尋「王○明」）
            canon_result = await db.execute(
                select(CanonicalEntity.id)
                .where(CanonicalEntity.canonical_name == clean)
            )
            canonical_ids.extend(row[0] for row in canon_result.all())

            if not canonical_ids:
                continue

            # 去重 canonical_ids
            unique_ids = list(set(canonical_ids))

            # Step 3: 取得所有匹配正規實體的別名
            all_aliases_result = await db.execute(
                select(EntityAlias.alias_name)
                .where(EntityAlias.canonical_entity_id.in_(unique_ids))
                .limit(MAX_EXPANSIONS_PER_TERM)
            )
            for row in all_aliases_result.all():
                expansions[term].add(row[0])

            # Step 4: 取得正規名稱本身
            canon_names_result = await db.execute(
                select(CanonicalEntity.canonical_name)
                .where(CanonicalEntity.id.in_(unique_ids))
            )
            for row in canon_names_result.all():
                expansions[term].add(row[0])

        # 記錄有效擴展（僅記錄確實有擴展的詞彙）
        for term, expanded in expansions.items():
            if len(expanded) > 1:
                logger.info(
                    f"搜尋實體擴展: '{term}' → {expanded}"
                )

    except Exception as e:
        logger.warning(f"搜尋實體擴展失敗（降級為原始詞彙）: {e}")
        # Fallback: return original terms only (already set above)

    return expansions


def flatten_expansions(expansions: Dict[str, Set[str]]) -> List[str]:
    """
    將擴展結果扁平化為去重的關鍵字列表。

    Args:
        expansions: expand_search_terms() 的返回值

    Returns:
        去重的關鍵字列表（保留原始順序在前，擴展詞在後）
    """
    seen: Set[str] = set()
    result: List[str] = []

    # 先加入原始詞彙（保留原始順序）
    for term in expansions:
        lower = term.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(term)

    # 再加入擴展詞彙
    for term, expanded in expansions.items():
        for exp in expanded:
            lower = exp.lower()
            if lower not in seen:
                seen.add(lower)
                result.append(exp)

    return result
