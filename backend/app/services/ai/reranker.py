"""
檢索結果重排序服務

三層混合重排策略：
1. 向量相似度 (已有，由 pgvector cosine_distance 提供)
2. 關鍵字覆蓋度 (新增，BM25-like 精確匹配)
3. 批次 LLM 相關性評分 (可選，高延遲但高精度)

最終分數 = w_vector * vector_sim + w_keyword * keyword_score + w_llm * llm_score

Version: 1.1.0
Created: 2026-02-26
Updated: 2026-02-27 - v1.1.0 統一 STOPWORDS 為唯一來源（合併 RAG + reranker）
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 權重配置
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
    vector_weight: float = W_VECTOR,
    keyword_weight: float = W_KEYWORD,
) -> List[Dict[str, Any]]:
    """
    混合重排序

    Args:
        documents: 檢索到的公文列表（需含 similarity 欄位）
        query_terms: 查詢關鍵字列表
        vector_weight: 向量相似度權重
        keyword_weight: 關鍵字覆蓋度權重

    Returns:
        重排序後的公文列表（附加 rerank_score 欄位）
    """
    if not documents:
        return documents

    scored = []
    for doc in documents:
        vector_sim = float(doc.get("similarity", 0))
        doc_text = build_doc_text(doc)
        keyword_score = compute_keyword_score(query_terms, doc_text)

        # 混合分數
        final_score = (
            vector_weight * vector_sim
            + keyword_weight * keyword_score
        )

        scored.append({
            **doc,
            "rerank_score": round(final_score, 4),
            "keyword_score": round(keyword_score, 4),
        })

    # 按混合分數降序排列
    scored.sort(key=lambda d: d["rerank_score"], reverse=True)

    logger.debug(
        "Reranked %d documents: top score=%.4f, keyword_boost=%d",
        len(scored),
        scored[0]["rerank_score"] if scored else 0,
        sum(1 for d in scored if d["keyword_score"] > 0),
    )

    return scored


async def llm_rerank(
    ai_connector: Any,
    question: str,
    documents: List[Dict[str, Any]],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    LLM 批次相關性重排序（可選，高品質但高延遲）

    使用單次 LLM 呼叫對所有文件進行相關性排序。

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

    # 建構文件描述（精簡，控制 token 消耗）
    doc_list = []
    for i, doc in enumerate(documents[:15]):  # 最多 15 篇
        doc_list.append(
            f"{i + 1}. [{doc.get('doc_number', '')}] "
            f"{doc.get('subject', '')[:60]} "
            f"({doc.get('sender', '')} → {doc.get('receiver', '')})"
        )

    docs_text = "\n".join(doc_list)

    system_prompt = (
        "你是公文相關性評估專家。根據使用者問題，"
        "從以下公文列表中選出最相關的文件編號，按相關性從高到低排列。"
        "僅回傳數字編號（以逗號分隔），不要其他文字。"
        f"例如：3,1,5,2"
    )

    user_content = f"問題：{question}\n\n公文列表：\n{docs_text}"

    try:
        response = await ai_connector.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=64,
            task_type="classify",
        )

        # 解析排序結果
        numbers = re.findall(r"\d+", response)
        ranked_indices = []
        seen = set()
        for n in numbers:
            idx = int(n) - 1  # 1-based → 0-based
            if 0 <= idx < len(documents) and idx not in seen:
                ranked_indices.append(idx)
                seen.add(idx)

        if not ranked_indices:
            logger.warning("LLM rerank returned no valid indices: %s", response)
            return documents[:top_n]

        # 重建排序列表
        reranked = []
        for rank, idx in enumerate(ranked_indices[:top_n]):
            doc = {**documents[idx]}
            doc["llm_relevance"] = round(1.0 - rank * 0.1, 2)
            reranked.append(doc)

        # 補足 top_n（LLM 可能未返回足夠數量）
        for idx, doc in enumerate(documents):
            if idx not in seen and len(reranked) < top_n:
                reranked.append({**doc, "llm_relevance": 0.0})

        logger.info(
            "LLM reranked %d → top %d: order=%s",
            len(documents),
            len(reranked),
            ranked_indices[:top_n],
        )
        return reranked

    except Exception as e:
        logger.warning("LLM rerank failed, keeping original order: %s", e)
        return documents[:top_n]
