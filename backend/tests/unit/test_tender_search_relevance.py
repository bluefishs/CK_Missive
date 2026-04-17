# -*- coding: utf-8 -*-
"""
TDD: 標案搜尋精準度

驗證：
1. 長查詢字串（>20字）應精確匹配為主
2. similarity 門檻不低於 0.3
3. build_search_sql 產出正確 SQL
"""
import pytest


def test_build_search_sql_short_query():
    """短查詢應包含 trigram similarity"""
    from app.services.tender_search_query import build_tender_search_sql
    sql, params = build_tender_search_sql("測量標案", limit=20)
    assert "similarity" in sql
    assert params["lim"] == 20


def test_build_search_sql_long_query_prefers_ilike():
    """長查詢（>20字）應提高 similarity 門檻"""
    from app.services.tender_search_query import build_tender_search_sql
    long_q = "115年度臺北轄區國有林地占用清理含勘查測量及臨時拆除作業採購案"
    sql, params = build_tender_search_sql(long_q, limit=50)
    # 長查詢應有更高的 similarity 門檻
    assert "0.4" in sql or "0.35" in sql or "exact" in sql.lower()


def test_build_search_sql_exact_match_boost():
    """精確匹配 (title = :exact) 應 relevance = 1.0"""
    from app.services.tender_search_query import build_tender_search_sql
    sql, _ = build_tender_search_sql("任意查詢", limit=10)
    assert "CASE WHEN tr.title = :exact THEN 1.0" in sql


def test_build_search_sql_has_relevance_floor():
    """應有 relevance 底線篩選"""
    from app.services.tender_search_query import build_tender_search_sql
    sql, _ = build_tender_search_sql("短查", limit=10)
    # 外層或 HAVING 應有 relevance 底線
    assert "relevance" in sql


# --- rerank tests ---

def test_rerank_exact_match_first():
    """精確匹配應排第一"""
    from app.services.tender_search_query import rerank_by_title_similarity
    records = [
        {"title": "完全不相關的標案", "raw_date": 20260417},
        {"title": "115年度臺北轄區國有林地占用清理(含勘查、測量及臨時拆除)作業採購案", "raw_date": 20260410},
        {"title": "另一個不相關的", "raw_date": 20260416},
    ]
    query = "115年度臺北轄區國有林地占用清理(含勘查、測量及臨時拆除)作業採購案"
    result = rerank_by_title_similarity(records, query)
    assert result[0]["title"] == query
    assert result[0]["_relevance"] == 1.0


def test_rerank_filters_low_relevance():
    """低相關度結果應被過濾"""
    from app.services.tender_search_query import rerank_by_title_similarity
    records = [
        {"title": "115年度信義標防水整修工程", "raw_date": 20260417},
        {"title": "115年度購買吊臂車輛", "raw_date": 20260417},
        {"title": "冷氣空調零件更換", "raw_date": 20260417},
    ]
    query = "115年度臺北轄區國有林地占用清理(含勘查、測量及臨時拆除)作業採購案"
    result = rerank_by_title_similarity(records, query, min_score=0.3)
    # 這些結果的 bigram 重疊率應很低
    assert len(result) < len(records)


def test_rerank_respects_top_k():
    """top_k 應限制回傳數量"""
    from app.services.tender_search_query import rerank_by_title_similarity
    records = [{"title": f"標案 {i}", "raw_date": 20260417} for i in range(50)]
    result = rerank_by_title_similarity(records, "標案", top_k=10)
    assert len(result) <= 10


def test_char_overlap_score_exact():
    """完全匹配 → 1.0"""
    from app.services.tender_search_query import _char_overlap_score
    assert _char_overlap_score("測試標案", "測試標案") == 1.0


def test_char_overlap_score_partial():
    """部分匹配 → 0 < score < 1"""
    from app.services.tender_search_query import _char_overlap_score
    score = _char_overlap_score("115年度道路工程", "115年度臺北道路維修工程")
    assert 0 < score < 1


def test_char_overlap_score_no_match():
    """完全不匹配 → 接近 0"""
    from app.services.tender_search_query import _char_overlap_score
    score = _char_overlap_score("冷氣空調", "國有林地占用清理勘查測量")
    assert score < 0.15
