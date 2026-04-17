# -*- coding: utf-8 -*-
"""
標案搜尋 SQL 建構器

根據查詢長度動態調整搜尋策略：
- 短查詢（≤20字）：trigram similarity ≥ 0.3 + ILIKE
- 長查詢（>20字）：精確匹配優先 + ILIKE + trigram similarity ≥ 0.4
- 所有結果都有 relevance 分數，底線 0.15

從 tender_cache_service.py 拆出的純函數，方便測試。
"""
from typing import Dict, Any, Tuple


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
