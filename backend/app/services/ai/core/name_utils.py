"""
名稱正規化工具函數

集中管理實體名稱清理與比對用的工具函數，
供 graph_helpers、graph_merge_strategy 等模組共用。

Version: 1.0.0
Created: 2026-04-08
"""

import re
import unicodedata


# 公司 / 機關名稱正規化用的後綴
_ORG_SUFFIXES = re.compile(r'(股份有限公司|有限公司|事務所|分公司|分局|工務段)$')


def normalize_for_match(name: str) -> str:
    """正規化名稱用於模糊比對（NFKC + 去空白 + 去常見後綴）"""
    s = unicodedata.normalize("NFKC", name)
    s = re.sub(r'\s+', '', s).strip()
    s = _ORG_SUFFIXES.sub('', s)
    return s


def clean_agency_name(raw: str) -> str:
    """清理機關名稱：去除統編前綴、換行符"""
    s = raw.strip().replace('\n', '').replace('\r', '')
    s = re.sub(r'^\d{8,10}\s*', '', s)
    return s.strip() if s.strip() else raw.strip()
