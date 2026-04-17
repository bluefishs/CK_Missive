# -*- coding: utf-8 -*-
"""
HNSW Vector Search 動態配置

pgvector HNSW index 的 ef_search 參數控制搜尋精確度 vs 速度：
- 越高：recall 越好，延遲越高
- 越低：速度快，可能漏 recall

用法：在 vector 查詢前：
    await db.execute(text(hnsw_config.get_set_local_sql("precise")))
"""
from typing import Dict


class HNSWConfig:
    """HNSW ef_search 動態配置管理。"""

    # 查詢類型 → ef_search 值
    _EF_SEARCH_MAP: Dict[str, int] = {
        "precise": 200,    # 精確搜尋（RAG top-k, entity resolution）
        "default": 100,    # 一般搜尋（document search, KG query）
        "fast": 60,        # 快速搜尋（autocomplete, suggestion）
        "batch": 40,       # 批次處理（embedding backfill, bulk matching）
    }

    def get_ef_search(self, search_type: str = "default") -> int:
        return self._EF_SEARCH_MAP.get(search_type, self._EF_SEARCH_MAP["default"])

    def get_set_local_sql(self, search_type: str = "default") -> str:
        ef = self.get_ef_search(search_type)
        return f"SET LOCAL hnsw.ef_search = {ef}"


# 全域單例
_config = HNSWConfig()


def get_hnsw_config() -> HNSWConfig:
    return _config
