"""
檢索結果重排序服務

三層混合重排策略：
1. 向量相似度 (已有，由 pgvector cosine_distance 提供)
2. 關鍵字覆蓋度 (BM25-like 精確匹配)
3. LLM 相關性評分 (Gemma 4 預設啟用，>5 筆自動觸發)

最終分數 = w_vector * vector_sim + w_keyword * keyword_score + w_llm * llm_score

Version: 2.0.0
Created: 2026-02-26
Updated: 2026-04-05 - v2.0.0 Gemma 4 預設 reranking + adaptive weights + quick rerank
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 預設權重配置 (向後相容)
W_VECTOR = 0.5
W_KEYWORD = 0.3
W_LLM = 0.2

# 中文停用詞集合（唯一來源 — 供 reranker / RAG / Agent 共用）
STOPWORDS = {
    # 語法虛詞
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "這", "中", "大", "為", "上", "個", "國", "到", "說", "們", "以", "要",
    "會", "與", "及", "等", "或", "被", "由", "其", "所", "之", "後", "前",
    "已", "將", "對", "從", "可", "也", "如", "而", "又", "但", "能", "應",
    "該", "於", "依", "據",
    # 公文常見低區分度詞
    "辦理", "有關", "相關", "案", "請", "函",
    # 搜尋意圖語助詞
    "嗎", "呢", "吧", "啊", "哪", "什麼", "怎麼", "請問", "想",
    "知道", "找", "查", "看", "有沒有", "是否", "能否", "可以",
    "上個", "哪些", "那些", "關於", "最近",
}

# 向後相容別名
_STOPWORDS = STOPWORDS


def _adaptive_weights(query_terms: List[str]) -> Tuple[float, float, float]:
    """Adaptive weights based on query characteristics.

    Short queries (1-2 terms): favor keyword matching (precision)
    Medium queries (3-5 terms): balanced
    Long queries (6+ terms): favor semantic (recall)

    Returns:
        (vector_weight, keyword_weight, llm_weight)
    """
    # Filter stopwords for accurate term count
    effective = [t for t in query_terms if t not in _STOPWORDS and len(t) >= 2]
    n = len(effective)
    if n <= 2:
        return (0.3, 0.5, 0.2)  # keyword-heavy for precision
    elif n <= 5:
        return (0.5, 0.3, 0.2)  # balanced (original default)
    else:
        return (0.6, 0.2, 0.2)  # semantic-heavy for recall


def compute_keyword_score(
    query_terms: List[str],
    doc_text: str,
) -> float:
    """
    計算關鍵字覆蓋度分數 (0-1)

    策略：
    - 精確匹配：查詢詞完全出現在文件中 → 高分
    - 部分匹配：查詢詞的子字串出現 → 部分分
    - IDF 加權：罕見詞命中比常見詞更重要
    """
    if not query_terms or not doc_text:
        return 0.0

    # 過濾停用詞
    effective_terms = [t for t in query_terms if t not in _STOPWORDS and len(t) >= 2]
    if not effective_terms:
        return 0.0

    doc_lower = doc_text.lower()
    total_score = 0.0
    max_possible = 0.0

    for term in effective_terms:
        term_lower = term.lower()
        # 較長的詞給予更高權重 (IDF-like)
        weight = min(len(term_lower) / 2.0, 3.0)
        max_possible += weight

        if term_lower in doc_lower:
            # 精確匹配
            total_score += weight
        else:
            # 部分匹配 — 超過 2 字的詞，檢查是否有部分重疊
            if len(term_lower) >= 3:
                # 滑動窗口檢查
                for i in range(len(term_lower) - 1):
                    bigram = term_lower[i:i + 2]
                    if bigram in doc_lower:
                        total_score += weight * 0.3  # 部分匹配打折
                        break

    return min(total_score / max_possible, 1.0) if max_possible > 0 else 0.0


def build_doc_text(doc: Dict[str, Any]) -> str:
    """將公文各欄位合併為可搜尋文字"""
    parts = [
        doc.get("subject", ""),
        doc.get("doc_number", ""),
        doc.get("sender", ""),
        doc.get("receiver", ""),
        doc.get("doc_type", ""),
        doc.get("category", ""),
        doc.get("ck_note", ""),
    ]
    return " ".join(p for p in parts if p)


def rerank_documents(
    documents: List[Dict[str, Any]],
    query_terms: List[str],
    vector_weight: Optional[float] = None,
    keyword_weight: Optional[float] = None,
    use_adaptive: bool = True,
) -> List[Dict[str, Any]]:
    """
    混合重排序

    Args:
        documents: 檢索到的公文列表（需含 similarity 欄位）
        query_terms: 查詢關鍵字列表
        vector_weight: 向量相似度權重 (None = 自動)
        keyword_weight: 關鍵字覆蓋度權重 (None = 自動)
        use_adaptive: 是否使用自適應權重 (預設 True)

    Returns:
        重排序後的公文列表（附加 rerank_score 欄位）
    """
    if not documents:
        return documents

    # Determine weights
    if vector_weight is not None and keyword_weight is not None:
        # Explicit weights provided — use them (backward compatible)
        v_w, k_w = vector_weight, keyword_weight
    elif use_adaptive and query_terms:
        v_w, k_w, _ = _adaptive_weights(query_terms)
    else:
        v_w, k_w = W_VECTOR, W_KEYWORD

    scored = []
    for doc in documents:
        vector_sim = float(doc.get("similarity", 0))
        doc_text = build_doc_text(doc)
        keyword_score = compute_keyword_score(query_terms, doc_text)

        # 混合分數
        final_score = (
            v_w * vector_sim
            + k_w * keyword_score
        )

        scored.append({
            **doc,
            "rerank_score": round(final_score, 4),
            "keyword_score": round(keyword_score, 4),
        })

    # 按混合分數降序排列
    scored.sort(key=lambda d: d["rerank_score"], reverse=True)

    logger.debug(
        "Reranked %d documents (weights: v=%.2f k=%.2f): top score=%.4f, keyword_boost=%d",
        len(scored),
        v_w,
        k_w,
        scored[0]["rerank_score"] if scored else 0,
        sum(1 for d in scored if d["keyword_score"] > 0),
    )

    return scored


async def rerank_with_llm(
    ai_connector: Any,
    documents: List[Dict[str, Any]],
    query: str,
    query_terms: List[str],
    top_n: int = 10,
    auto_llm_threshold: int = 5,
) -> List[Dict[str, Any]]:
    """
    完整重排管線：keyword+vector rerank → optional LLM rerank

    當結果數量超過 auto_llm_threshold 時，自動調用 Gemma 4 進行 LLM 重排。

    Args:
        ai_connector: AIConnector 實例 (None 時跳過 LLM)
        documents: 候選公文列表
        query: 原始查詢字串
        query_terms: 分詞後的查詢詞
        top_n: 最終回傳數量
        auto_llm_threshold: 自動觸發 LLM rerank 的結果數量閾值

    Returns:
        重排序後的公文列表
    """
    # Step 1: keyword + vector hybrid rerank
    reranked = rerank_documents(documents, query_terms)

    # Step 2: LLM rerank if enough candidates and connector available
    if ai_connector and len(reranked) > auto_llm_threshold:
        try:
            reranked = await gemma4_quick_rerank(
                ai_connector, reranked, query, top_k=top_n
            )
        except Exception as e:
            logger.warning("LLM rerank skipped: %s", e)

    return reranked[:top_n]


async def gemma4_quick_rerank(
    ai_connector: Any,
    documents: List[Dict[str, Any]],
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fast Gemma 4 reranking — single-call batch scoring.

    Uses a compact Chinese prompt optimized for Gemma 4 to rank
    up to 10 candidates in a single LLM call.

    Args:
        ai_connector: AIConnector 實例
        documents: 候選公文列表 (已經過 keyword+vector rerank)
        query: 使用者查詢
        top_k: 回傳前 K 篇

    Returns:
        重排序後的公文列表（附加 llm_relevance 欄位）
    """
    if not documents or len(documents) <= 1:
        return documents[:top_k]

    # Limit to 10 candidates for speed
    candidates = documents[:10]

    # Build compact doc summaries
    doc_lines = []
    for i, doc in enumerate(candidates):
        subject = doc.get("subject", "")[:50]
        sender = doc.get("sender", "")[:20]
        doc_num = doc.get("doc_number", "")
        doc_lines.append(f"{i + 1}. [{doc_num}] {subject} ({sender})")

    docs_text = "\n".join(doc_lines)

    system_prompt = (
        "你是公文相關性排序專家。"
        "根據問題從公文列表選出最相關的，按相關性高→低排序。"
        "只回傳數字編號（逗號分隔），例如：3,1,5,2"
    )

    user_content = f"問題：{query}\n\n公文：\n{docs_text}"

    try:
        response = await ai_connector.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=48,
            task_type="rerank",
        )

        # Parse ranked indices
        numbers = re.findall(r"\d+", response)
        ranked_indices = []
        seen = set()
        for n in numbers:
            idx = int(n) - 1  # 1-based → 0-based
            if 0 <= idx < len(candidates) and idx not in seen:
                ranked_indices.append(idx)
                seen.add(idx)

        if not ranked_indices:
            logger.warning("Gemma4 quick rerank returned no valid indices: %s", response)
            return documents[:top_k]

        # Rebuild ranked list with LLM relevance scores
        reranked = []
        for rank, idx in enumerate(ranked_indices[:top_k]):
            doc = {**candidates[idx]}
            doc["llm_relevance"] = round(1.0 - rank * 0.1, 2)
            reranked.append(doc)

        # Fill remaining from candidates not yet included
        for idx, doc in enumerate(candidates):
            if idx not in seen and len(reranked) < top_k:
                reranked.append({**doc, "llm_relevance": 0.0})

        # If still short, append from remaining documents beyond candidates
        if len(reranked) < top_k:
            for doc in documents[len(candidates):]:
                if len(reranked) >= top_k:
                    break
                reranked.append({**doc, "llm_relevance": 0.0})

        logger.info(
            "Gemma4 quick reranked %d → top %d: order=%s",
            len(candidates),
            len(reranked),
            ranked_indices[:top_k],
        )
        return reranked

    except Exception as e:
        logger.warning("Gemma4 quick rerank failed, keeping original order: %s", e)
        return documents[:top_k]


async def llm_rerank(
    ai_connector: Any,
    question: str,
    documents: List[Dict[str, Any]],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    LLM 批次相關性重排序（向後相容入口）

    Uses Gemma 4 optimized prompt with reduced candidates (10 max).

    Args:
        ai_connector: AIConnector 實例
        question: 使用者問題
        documents: 候選公文列表
        top_n: 回傳前 N 篇

    Returns:
        重排序後的前 N 篇公文（附加 llm_relevance 欄位）
    """
    if not documents or len(documents) <= 1:
        return documents[:top_n]

    # Delegate to Gemma 4 quick rerank (backward compatible)
    return await gemma4_quick_rerank(
        ai_connector, documents, question, top_k=top_n
    )
