# -*- coding: utf-8 -*-
"""
TDD: HNSW ef_search 動態配置

驗證：
1. HNSWConfig 根據查詢類型回傳不同 ef_search
2. 精確搜尋 ef_search 較高 (200)
3. 批次/探索搜尋 ef_search 較低 (40)
4. 預設值合理 (100)
"""
import pytest


def test_default_ef_search():
    from app.core.hnsw_config import HNSWConfig

    config = HNSWConfig()
    assert config.get_ef_search("default") == 100


def test_precise_search_higher_ef():
    from app.core.hnsw_config import HNSWConfig

    config = HNSWConfig()
    assert config.get_ef_search("precise") >= 200


def test_batch_search_lower_ef():
    from app.core.hnsw_config import HNSWConfig

    config = HNSWConfig()
    assert config.get_ef_search("batch") <= 60


def test_generate_set_local_sql():
    from app.core.hnsw_config import HNSWConfig

    config = HNSWConfig()
    sql = config.get_set_local_sql("precise")
    assert "SET LOCAL hnsw.ef_search" in sql
    assert "200" in sql
