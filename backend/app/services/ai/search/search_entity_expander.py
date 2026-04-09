"""
搜尋詞彙統一擴展器

整合兩層擴展來源為單一管道：
  Layer 1: SynonymExpander — ai_synonyms 表（DB 管理，前端可維護）
  Layer 2: 知識圖譜 — canonical_entities + entity_aliases

使用場景:
  - 「桃園市工務局」→ SynonymExpander 模糊匹配 → 「桃園市政府工務局」
  - 「王主任」→ entity_aliases → 「王○明」
  - 「工務局」→ SynonymExpander → 「工務處」

Version: 2.0.0
Created: 2026-02-25
Updated: 2026-03-06 - 整合 SynonymExpander + entity_aliases 統一管道
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
    統一搜尋詞彙擴展 — 兩層管道串聯。

    Layer 1: SynonymExpander（ai_synonyms 表，含模糊匹配）
    Layer 2: 知識圖譜（canonical_entities + entity_aliases）

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
        expansions[term] = {term}

    # ── Layer 1: SynonymExpander（ai_synonyms DB 表） ──
    try:
        from app.services.ai.search.synonym_expander import SynonymExpander
        expanded_keywords = SynonymExpander.expand_keywords(list(terms))
        # 將擴展結果歸入對應的原始詞
        original_set = set(terms)
        for kw in expanded_keywords:
            if kw not in original_set:
                # 找出是哪個原始詞的擴展
                for term in terms:
                    synonyms = SynonymExpander.find_synonyms(term)
                    if kw in synonyms or kw == term:
                        expansions[term].add(kw)
                        break
                else:
                    # 無法對應到原始詞，歸入第一個詞的擴展
                    expansions[terms[0]].add(kw)
    except Exception as e:
        logger.debug("SynonymExpander layer failed: %s", e)

    # ── Layer 2: 知識圖譜（canonical_entities + entity_aliases） ──
    try:
        for term in terms:
            clean = term.strip()
            if not clean or len(clean) < MIN_TERM_LENGTH:
                continue

            canonical_ids: List[int] = []

            # Step 1: 別名精確匹配 (limit to avoid runaway results)
            alias_result = await db.execute(
                select(EntityAlias.canonical_entity_id)
                .where(EntityAlias.alias_name == clean)
                .limit(MAX_EXPANSIONS_PER_TERM)
            )
            canonical_ids.extend(row[0] for row in alias_result.all())

            # Step 2: 正規名稱精確匹配 (limit for safety)
            canon_result = await db.execute(
                select(CanonicalEntity.id)
                .where(CanonicalEntity.canonical_name == clean)
                .limit(MAX_EXPANSIONS_PER_TERM)
            )
            canonical_ids.extend(row[0] for row in canon_result.all())

            if not canonical_ids:
                continue

            unique_ids = list(set(canonical_ids))

            # Step 3: 取得所有別名
            all_aliases_result = await db.execute(
                select(EntityAlias.alias_name)
                .where(EntityAlias.canonical_entity_id.in_(unique_ids))
                .limit(MAX_EXPANSIONS_PER_TERM)
            )
            for row in all_aliases_result.all():
                expansions[term].add(row[0])

            # Step 4: 取得正規名稱 (limit for safety)
            canon_names_result = await db.execute(
                select(CanonicalEntity.canonical_name)
                .where(CanonicalEntity.id.in_(unique_ids))
                .limit(MAX_EXPANSIONS_PER_TERM)
            )
            for row in canon_names_result.all():
                expansions[term].add(row[0])

        # 記錄有效擴展
        for term, expanded in expansions.items():
            if len(expanded) > 1:
                logger.info(
                    f"搜尋詞彙擴展: '{term}' → {expanded}"
                )

    except Exception as e:
        logger.warning(f"知識圖譜擴展失敗（降級為同義詞結果）: {e}")

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
