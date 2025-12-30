# -*- coding: utf-8 -*-
"""清除快取工具"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.cache import cache

def clear_documents_cache():
    """清除公文相關的快取"""
    keys_to_delete = []
    for key in cache.cache.keys():
        if "documents" in key:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        cache.delete(key)

    print(f"已清除 {len(keys_to_delete)} 個文件相關的快取項目")
    print(f"快取統計: {cache.stats()}")

if __name__ == "__main__":
    clear_documents_cache()