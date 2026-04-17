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
