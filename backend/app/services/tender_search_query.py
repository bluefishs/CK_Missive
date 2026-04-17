# -*- coding: utf-8 -*-
"""
標案搜尋查詢建構 + 結果重排序

功能：
1. build_tender_search_sql: DB trigram 查詢 SQL 建構
2. rerank_by_title_similarity: 合併後結果按標題相似度重排序 + 截斷

從 tender_cache_service.py 拆出的純函數，方便測試。
"""
import re
from typing import Dict, Any, List, Tuple


def build_tender_search_sql(query: str, limit: int = 50) -> Tuple[str, Dict[str, Any]]:
    """產生標案搜尋 SQL 和參數。

    Returns:
        (sql_string, params_dict)
    """
    search_q = query[:100] if len(query) > 100 else query
    is_long = len(query) > 20

    # 長查詢提高 similarity 門檻（減少不相關結果）
    sim_threshold = "0.4" if is_long else "0.3"

    sql = f"""
        SELECT tr.*, array_agg(DISTINCT CASE WHEN tcl.role='winner' THEN tcl.company_name END) AS winners,
               array_agg(DISTINCT CASE WHEN tcl.role='bidder' THEN tcl.company_name END) AS bidders,
               CASE WHEN tr.title = :exact THEN 1.0
                    ELSE COALESCE(similarity(tr.title, :sim_q), 0)
               END AS relevance
        FROM tender_records tr
        LEFT JOIN tender_company_links tcl ON tcl.tender_record_id = tr.id
        WHERE tr.title ILIKE :q OR tr.unit_name ILIKE :q
           OR similarity(tr.title, :sim_q) > {sim_threshold}
        GROUP BY tr.id
        HAVING CASE WHEN tr.title = :exact THEN 1.0
                    ELSE COALESCE(similarity(tr.title, :sim_q), 0)
               END >= 0.15
           OR tr.title ILIKE :q
        ORDER BY relevance DESC, tr.announce_date DESC NULLS LAST
        LIMIT :lim
    """

    params = {
        "q": f"%{search_q}%",
        "exact": query,
        "sim_q": search_q,
        "lim": limit,
    }

    return sql.strip(), params


# ---------------------------------------------------------------------------
# 結果重排序 — 用於 g0v/ezbid/DB 三源合併後
# ---------------------------------------------------------------------------

def _char_overlap_score(title: str, query: str) -> float:
    """純 Python 字元重疊率（不依賴 pg_trgm，用於 API 結果重排序）。

    計算 query 中有多少比例的 2-gram 出現在 title 中。
    """
    if not title or not query:
        return 0.0

    # 完全匹配
    if title.strip() == query.strip():
        return 1.0

    # 2-gram overlap
    q_clean = re.sub(r'[()（）、\s]', '', query)
    t_clean = re.sub(r'[()（）、\s]', '', title)

    if len(q_clean) < 2:
        return 1.0 if q_clean in t_clean else 0.0

    q_bigrams = set(q_clean[i:i+2] for i in range(len(q_clean) - 1))
    t_bigrams = set(t_clean[i:i+2] for i in range(len(t_clean) - 1))

    if not q_bigrams:
        return 0.0

    overlap = len(q_bigrams & t_bigrams)
    return overlap / len(q_bigrams)


def rerank_by_title_similarity(
    records: List[Dict[str, Any]],
    query: str,
    top_k: int = 30,
    min_score: float = 0.15,
) -> List[Dict[str, Any]]:
    """按標題與查詢的字元重疊率重排序，截斷低相關結果。

    Args:
        records: 合併後的標案列表
        query: 原始搜尋字串
        top_k: 最多回傳筆數
        min_score: 最低相關度門檻

    Returns:
        重排序後的結果列表
    """
    scored = []
    for r in records:
        title = r.get("title", "")
        score = _char_overlap_score(title, query)
        scored.append((score, r))

    # 按 score 降序，同分按日期降序
    scored.sort(key=lambda x: (x[0], x[1].get("raw_date", 0)), reverse=True)

    # 截斷：至少保留精確匹配和高分結果
    filtered = []
    for score, r in scored:
        if score >= min_score or len(filtered) == 0:
            r["_relevance"] = round(score, 3)
            filtered.append(r)
        if len(filtered) >= top_k:
            break

    return filtered
