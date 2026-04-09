"""
Agent 學習注入模組 -- Cross-session Learning 與 Adaptive Few-shot

從 agent_planner.py 提取：
- inject_cross_session_learnings: 從 DB 載入歷史學習記錄作為規劃提示
- filter_learnings_by_similarity: Embedding cosine similarity 篩選
- build_adaptive_fewshot: 從 agent_query_traces 查詢歷史成功案例
- cosine_similarity: 向量餘弦相似度計算
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """計算兩向量的餘弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def filter_learnings_by_similarity(
    question: str,
    learnings: List[Dict[str, Any]],
    inject_limit: int,
    similarity_threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Phase 7.1: 使用 embedding cosine similarity 篩選最相關的學習記錄。

    流程：
    1. 取得 question embedding
    2. 為每個 learning 的 source_question (或 content) 取得 embedding
    3. 計算 cosine similarity，只保留 > threshold 的前 N 筆

    若 embedding 不可用則 fallback 到原始行為（全部注入至 limit）。
    """
    try:
        from app.services.ai.embedding_manager import EmbeddingManager
        from app.core.ai_connector import AIConnector

        connector = AIConnector()
        emb_mgr = EmbeddingManager()

        query_emb = await emb_mgr.get_embedding(question, connector)
        if not query_emb:
            # Embedding 不可用，fallback: 回傳前 N 筆
            logger.debug("Semantic filtering fallback: no query embedding")
            return learnings[:inject_limit]

        # 收集 learning 文字用於批次 embedding
        texts = []
        for l in learnings:
            # 優先用 source_question，其次 content
            text = l.get("source_question") or l.get("content", "")
            texts.append(str(text)[:200])

        embeddings = await emb_mgr.get_embeddings_batch(texts, connector)

        # 計算相似度並排序
        scored: List[tuple] = []
        for i, l in enumerate(learnings):
            emb = embeddings[i] if i < len(embeddings) else None
            if not emb:
                continue
            sim = cosine_similarity(query_emb, emb)
            if sim >= similarity_threshold:
                scored.append((sim, l))

        # 依相似度降序排列，取 top-N
        scored.sort(key=lambda x: x[0], reverse=True)
        result = [item[1] for item in scored[:inject_limit]]

        if result:
            logger.info(
                "Semantic learning filter: %d/%d passed (threshold=%.2f, top sim=%.3f)",
                len(result), len(learnings), similarity_threshold,
                scored[0][0] if scored else 0.0,
            )
        return result

    except Exception as e:
        logger.warning("Semantic learning filtering failed, fallback: %s", e)
        return learnings[:inject_limit]


async def _merge_shared_pool_learnings(
    db_learnings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    R-3: Read from Redis shared learning pool and merge with DB learnings.

    Promoted patterns are written to Redis immediately, making them available
    to ALL concurrent sessions before the next DB read cycle.
    Deduplicates by content_hash.
    """
    try:
        from app.core.redis_client import get_redis

        redis = await get_redis()
        if not redis:
            return db_learnings

        # Collect existing content_hashes for dedup
        existing_hashes = {
            l.get("content_hash") for l in db_learnings if l.get("content_hash")
        }

        shared_learnings: List[Dict[str, Any]] = []
        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor, match="agent:shared_pool:*", count=50,
            )
            for key in keys:
                try:
                    raw = await redis.get(key)
                    if not raw:
                        continue
                    entry = json.loads(raw)
                    content_hash = entry.get("content_hash", "")
                    if content_hash and content_hash not in existing_hashes:
                        existing_hashes.add(content_hash)
                        shared_learnings.append({
                            "type": entry.get("type", "tool_combo"),
                            "content": entry.get("content", ""),
                            "content_hash": content_hash,
                            "source_question": entry.get("source_question", ""),
                            "hit_count": entry.get("hit_count", 1),
                            "confidence": entry.get("confidence", 0.5),
                            "graduation_status": "graduated",
                        })
                except (json.JSONDecodeError, TypeError):
                    continue
            if cursor == 0:
                break

        if shared_learnings:
            logger.info(
                "Shared pool: merged %d learnings (deduped from %d DB learnings)",
                len(shared_learnings), len(db_learnings),
            )
            return db_learnings + shared_learnings

    except Exception as e:
        logger.debug("Shared pool read skipped: %s", e)

    return db_learnings


async def inject_cross_session_learnings(
    question: str,
    db: Any,
    config: Any,
) -> str:
    """
    Cross-session Learning 注入 -- 從 DB 載入歷史學習記錄作為規劃提示。

    Phase 3A+: 對標 OpenClaw cross-session memory injection。
    Phase 7.1: Semantic filtering -- 使用 embedding cosine similarity
    篩選最相關的 top-5 學習（similarity > 0.3），降低雜訊注入。

    Returns:
        格式化的學習提示文字（空字串表示無可用學習）
    """
    from app.repositories.agent_learning_repository import AgentLearningRepository

    repo = AgentLearningRepository(db)
    # 取得候選學習（放寬上限以便語意排序後篩選）
    candidate_limit = max(config.learning_inject_limit * 3, 15)
    learnings = await repo.get_relevant_learnings(
        question,
        limit=candidate_limit,
    )

    # R-3: Merge with Redis shared learning pool for immediate cross-session availability
    learnings = await _merge_shared_pool_learnings(learnings)

    if not learnings:
        return ""

    # Phase 7.1: Semantic similarity filtering
    filtered = await filter_learnings_by_similarity(
        question, learnings, config.learning_inject_limit,
    )

    if not filtered:
        return ""

    items = []
    for l in filtered:
        hit_info = f"(使用 {l['hit_count']} 次)" if l.get("hit_count", 1) > 1 else ""
        # Skip chronic patterns entirely — they add noise, not signal
        if l.get("graduation_status") == "chronic":
            continue
        items.append(f"- [{l['type']}] {l['content']} {hit_info}".strip())

    block = "\n".join(items)
    logger.info(
        "Cross-session learning injected: %d/%d learnings for question '%s'",
        len(filtered), len(learnings), question[:60],
    )
    return f"\n# 歷史學習記錄（跨 session 累積）\n{block}"


async def build_adaptive_fewshot(
    question: str,
    db: Any,
    config: Any,
    context: Optional[str] = None,
) -> str:
    """
    從 agent_query_traces 查詢歷史成功案例，格式化為 few-shot 範例。

    Phase 2B: 對標 OpenClaw Adaptive Few-shot 模式。
    """
    from app.repositories.agent_trace_repository import AgentTraceRepository
    repo = AgentTraceRepository(db)
    traces = await repo.find_similar_successful_traces(
        question,
        context=context,
        limit=config.adaptive_fewshot_limit,
        min_results=config.adaptive_fewshot_min_results,
    )
    if not traces:
        return ""

    examples = []
    for t in traces:
        tools = t.get("tools_used", [])
        if not tools:
            continue
        tool_calls_str = json.dumps(
            [{"name": name, "params": {}} for name in tools],
            ensure_ascii=False,
        )
        examples.append(
            f'使用者：「{t["question"]}」\n'
            f'回應：{{"reasoning": "根據歷史成功查詢", "tool_calls": {tool_calls_str}}}'
        )

    return "\n\n".join(examples)
