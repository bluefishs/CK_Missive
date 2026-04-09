"""
Pattern Semantic Matcher — 模式語意匹配

提供 embedding 餘弦相似度和 Jaccard 降級方案。
從 agent_pattern_learner.py 提取。

Version: 1.0.0
Created: 2026-03-26
"""

import logging
import math
import re
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.ai.agent_pattern_learner import QueryPattern

logger = logging.getLogger(__name__)


async def semantic_match(
    template: str,
    candidates: List["QueryPattern"],
    redis: Any,
    prefix: str,
    config: Any,
) -> List["QueryPattern"]:
    """
    語意匹配 — 使用 embedding 餘弦相似度。

    策略：
    1. 取得查詢 template 的 embedding
    2. 與候選模式 template 的 embedding 計算 cosine similarity
    3. 超過閾值且最高分者回傳

    Embedding 不可用時自動降級為字元 Jaccard。
    """
    try:
        if not config.pattern_semantic_enabled:
            return []

        # 中文字符少於 4 個時跳過
        cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', template))
        if cjk_chars < 4:
            return []

        if not candidates:
            return []

        # 嘗試 embedding cosine similarity
        best_match, best_score = await _embedding_cosine_match(template, candidates)

        # Embedding 不可用時降級為 Jaccard
        if best_match is None:
            best_match, best_score = _jaccard_match(template, candidates)

        if best_match and best_score >= config.pattern_semantic_threshold:
            logger.debug(
                "Semantic match: %.2f (%s → %s)",
                best_score, template[:30], best_match.template[:30],
            )
            return [best_match]

        return []

    except Exception as e:
        logger.debug("semantic_match failed: %s", e)
        return []


async def _embedding_cosine_match(
    template: str,
    candidates: List["QueryPattern"],
) -> tuple:
    """使用 embedding 餘弦相似度匹配。回傳 (best_pattern, score) 或 (None, 0)。"""
    try:
        from app.services.ai.embedding_manager import EmbeddingManager
        from app.services.ai.base_ai_service import BaseAIService

        connector = BaseAIService.get_shared_connector()
        if not connector:
            return (None, 0.0)

        texts = [template] + [p.template for p in candidates]
        embeddings = await EmbeddingManager.get_embeddings_batch(texts, connector)

        query_emb = embeddings[0]
        if not query_emb:
            return (None, 0.0)

        best_match = None
        best_score = 0.0

        for i, p in enumerate(candidates):
            cand_emb = embeddings[i + 1]
            if not cand_emb:
                continue
            similarity = _cosine_similarity(query_emb, cand_emb)
            if similarity > best_score:
                best_score = similarity
                best_match = p

        return (best_match, best_score)

    except Exception as e:
        logger.debug("_embedding_cosine_match unavailable: %s", e)
        return (None, 0.0)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """計算兩向量的餘弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _jaccard_match(
    template: str,
    candidates: List["QueryPattern"],
) -> tuple:
    """Jaccard 字元相似度降級方案"""
    best_match = None
    best_score = 0.0

    template_chars = set(template)
    for p in candidates:
        p_chars = set(p.template)
        intersection = template_chars & p_chars
        union = template_chars | p_chars
        if not union:
            continue
        jaccard = len(intersection) / len(union)
        if jaccard > best_score:
            best_score = jaccard
            best_match = p

    return (best_match, best_score)
