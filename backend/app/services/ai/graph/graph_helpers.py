"""
圖譜查詢工具函數

從 graph_query_service.py 抽出的純工具函數、常數與快取管理。

Version: 1.0.0
Created: 2026-03-13
"""

import logging
import re

from app.services.ai.core.base_ai_service import RedisCache
from app.services.ai.core.name_utils import (
    normalize_for_match as _normalize_for_match_impl,
    clean_agency_name as _clean_agency_name_impl,
)

logger = logging.getLogger(__name__)

# 程式碼圖譜實體類型 — 公文圖譜查詢需排除這些類型 (SSOT: constants.py)
from app.core.constants import CODE_ENTITY_TYPES as _CODE_ENTITY_TYPES

# 模組級快取實例（所有 GraphQueryService 共用）
_graph_cache = RedisCache(prefix="graph:query")


async def invalidate_graph_cache(pattern: str | None = None) -> int:
    """
    主動失效圖譜快取。

    Args:
        pattern: Redis key pattern (如 "entity_graph:*")。
                 None 時清除所有圖譜快取。
    Returns:
        清除的 key 數量
    """
    if pattern is None:
        return await _graph_cache.clear()
    try:
        r = await _graph_cache._get_redis()
        if r is None:
            return 0
        full_pattern = f"{_graph_cache._prefix}:{pattern}"
        keys = []
        async for key in r.scan_iter(full_pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
        logger.info(f"圖譜快取失效: {len(keys)} keys (pattern={pattern})")
        return len(keys)
    except Exception as e:
        logger.debug(f"圖譜快取失效失敗: {e}")
        return 0


# 行政區域提取 regex（從地址中提取區/鄉/鎮/市）
# 要求2-3字 + 區/鄉/鎮，排除「市」避免匹配到縣市級
_DISTRICT_RE = re.compile(r'([\u4e00-\u9fff]{2,3}[區鄉鎮])')
# 非行政區的誤匹配詞彙
_DISTRICT_EXCLUDE = {'遊樂區', '工業區', '科技區', '園區', '社區', '校區', '廠區'}

# 公司 / 機關名稱正規化用的後綴（保留供 _names_overlap 等本地使用）
_ORG_SUFFIXES = re.compile(r'(股份有限公司|有限公司|事務所|分公司|分局|工務段)$')


def _clean_agency_name(raw: str) -> str:
    """清理機關名稱：委派至 name_utils.clean_agency_name"""
    return _clean_agency_name_impl(raw)


def _normalize_for_match(name: str) -> str:
    """正規化名稱用於模糊比對：委派至 name_utils.normalize_for_match"""
    return _normalize_for_match_impl(name)


def _names_overlap(a: str, b: str) -> bool:
    """雙向 includes 比對，至少 4 字元且短名 >= 長名 60% 才比對"""
    na, nb = _normalize_for_match(a), _normalize_for_match(b)
    if len(na) < 4 or len(nb) < 4:
        return na == nb
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    # 短名長度需 >= 長名的 50%，避免 "桃園市政府" 匹配 "桃園市政府工務局"
    if len(shorter) < len(longer) * 0.6:
        return False
    if shorter in longer:
        logger.debug(f"Name overlap: '{a}' ↔ '{b}' (ratio={len(shorter)/len(longer):.0%})")
        return True
    return False


def _extract_district(location_name: str) -> str | None:
    """從地址中提取行政區域（區/鄉/鎮）"""
    m = _DISTRICT_RE.search(location_name)
    if not m:
        return None
    district = m.group(1)
    # 排除非行政區詞彙
    if any(district.endswith(ex) for ex in _DISTRICT_EXCLUDE):
        return None
    # 去除誤包含的「市」前綴（如 "市楊梅區" → "楊梅區"）
    if district.startswith('市') and len(district) > 2:
        district = district[1:]
    # 去除誤包含的「縣」前綴（如 "縣仁愛鄉" → "仁愛鄉"）
    if district.startswith('縣') and len(district) > 2:
        district = district[1:]
    return district
