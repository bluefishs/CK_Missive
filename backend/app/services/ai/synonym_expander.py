"""
共用同義詞擴展服務

從 AIPromptManager 抽離的同義詞邏輯，作為共用基礎設施。
AI 搜尋、圖譜查詢、實體解析等服務均可使用。

SSOT 來源：
  1. DB ai_synonyms 表（優先）
  2. synonyms.yaml 檔案（fallback）

Version: 1.0.0
Created: 2026-02-24
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class SynonymExpander:
    """
    同義詞擴展 Singleton 服務

    提供三大功能：
    1. expand_keywords — 關鍵字擴展（加入同組詞彙）
    2. expand_agency — 機關縮寫轉全稱
    3. find_synonyms — 查詢某詞的所有同義詞
    """

    _instance: Optional["SynonymExpander"] = None
    _lookup: Optional[Dict[str, List[str]]] = None
    _raw_data: Optional[dict] = None

    def __new__(cls) -> "SynonymExpander":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_lookup(cls) -> Dict[str, List[str]]:
        """取得同義詞查找索引，未載入則自動初始化（DB 優先 → YAML fallback）"""
        if cls._lookup is not None:
            return cls._lookup
        cls._auto_load()
        return cls._lookup or {}

    @classmethod
    def _auto_load(cls) -> None:
        """自動載入：嘗試同步從 DB 載入，失敗則 fallback YAML"""
        try:
            from sqlalchemy.orm import Session
            from app.db.database import sync_engine
            from app.extended.models import AISynonym
            with Session(sync_engine) as session:
                records = session.query(AISynonym).filter(
                    AISynonym.is_active.is_(True)
                ).all()
                if records:
                    cls.reload_from_db(records)
                    logger.info("同義詞已從 DB 自動載入 (%d 組)", len(records))
                    return
        except Exception as e:
            logger.debug("同義詞 DB 自動載入失敗（降級 YAML）: %s", e)
        cls._load_from_yaml()

    @classmethod
    def _load_from_yaml(cls) -> None:
        """從 synonyms.yaml 載入同義詞"""
        synonyms_path = Path(__file__).parent / "synonyms.yaml"
        try:
            with open(synonyms_path, "r", encoding="utf-8") as f:
                cls._raw_data = yaml.safe_load(f) or {}
            logger.info(f"同義詞字典已載入: {synonyms_path}")
        except FileNotFoundError:
            logger.warning(f"同義詞字典檔案不存在: {synonyms_path}")
            cls._raw_data = {}
        except Exception as e:
            logger.error(f"載入同義詞字典失敗: {e}")
            cls._raw_data = {}

        cls._lookup = cls._build_lookup(cls._raw_data)

    @classmethod
    def _build_lookup(cls, data: dict) -> Dict[str, List[str]]:
        """建立快速查找索引: {任一詞 -> [同組所有詞]}"""
        lookup: Dict[str, List[str]] = {}
        for group_key in data:
            groups = data.get(group_key, [])
            if not isinstance(groups, list):
                continue
            for group in groups:
                if not isinstance(group, list):
                    continue
                for word in group:
                    lookup[word] = group
        logger.info(f"同義詞查找索引已建立: {len(lookup)} 個詞彙")
        return lookup

    @classmethod
    def reload_from_db(cls, synonym_records: list) -> int:
        """
        從 DB ai_synonyms 表重建查找索引

        Args:
            synonym_records: DB 查詢結果列表，每筆有 words 屬性

        Returns:
            載入的詞彙數
        """
        lookup: Dict[str, List[str]] = {}
        total_words = 0

        for record in synonym_records:
            words = [w.strip() for w in record.words.split(",") if w.strip()]
            total_words += len(words)
            for word in words:
                lookup[word] = words

        cls._lookup = lookup
        cls._raw_data = None
        logger.info(f"同義詞查找索引已從 DB 重建: {total_words} 個詞彙")
        return total_words

    @classmethod
    def invalidate(cls) -> None:
        """清除快取，下次使用時自動重新載入"""
        cls._lookup = None
        cls._raw_data = None
        logger.info("同義詞快取已清除")

    # ========================================================================
    # 公開 API
    # ========================================================================

    @classmethod
    def expand_keywords(cls, keywords: List[str]) -> List[str]:
        """
        擴展關鍵字列表：每個詞加入同組同義詞

        兩階段匹配：
        1. 精確匹配：直接查找 lookup[keyword]
        2. 模糊匹配（精確無結果時）：搜尋 lookup 中包含/被包含的詞
           例：「桃園市工務局」精確無匹配 → 發現 lookup 有「桃園市政府工務局」
           → 回傳同組所有詞

        Args:
            keywords: 原始關鍵字列表

        Returns:
            擴展後的關鍵字列表（去重、保序）
        """
        lookup = cls.get_lookup()
        if not lookup:
            return keywords

        seen: set = set()
        result: List[str] = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)

            # 階段 1: 精確匹配
            synonyms = lookup.get(kw)

            # 階段 2: 模糊匹配（含/被含子字串）
            if not synonyms and len(kw) >= 3:
                synonyms = cls._fuzzy_lookup(kw, lookup)

            if synonyms:
                for syn in synonyms:
                    if syn not in seen:
                        seen.add(syn)
                        result.append(syn)

        if len(result) > len(keywords):
            logger.info(f"關鍵字擴展: {keywords} -> {result}")
        return result

    @classmethod
    def _fuzzy_lookup(cls, keyword: str, lookup: Dict[str, List[str]]) -> Optional[List[str]]:
        """
        模糊匹配：在 lookup 中搜尋包含/被包含的詞。

        規則：
        - keyword 包含 lookup 中某個詞 → 回傳該詞同組
        - lookup 中某個詞包含 keyword → 回傳該詞同組
        - 優先選擇最長匹配

        例：keyword=「桃園市工務局」, lookup 有「工務局」→ 回傳 [「工務局」,「工務處」]
        例：keyword=「桃園市工務局」, lookup 有「桃園市政府工務局」→ 回傳同組
        """
        best_match: Optional[List[str]] = None
        best_len = 0
        for term, group in lookup.items():
            if term in keyword or keyword in term:
                if len(term) > best_len:
                    best_match = group
                    best_len = len(term)
        if best_match:
            logger.info(f"同義詞模糊匹配: '{keyword}' → 最佳匹配長度 {best_len}")
        return best_match

    @classmethod
    def expand_agency(cls, name: str) -> str:
        """
        機關縮寫轉全稱

        同義詞組中第一項為正規名稱（全稱）。

        Args:
            name: 原始機關名稱

        Returns:
            全稱名稱，無匹配時返回原值
        """
        lookup = cls.get_lookup()
        synonyms = lookup.get(name, [])
        if synonyms:
            return synonyms[0]
        return name

    @classmethod
    def find_synonyms(cls, word: str) -> List[str]:
        """
        查詢某詞的所有同義詞（不含自身）

        用途：圖譜搜尋擴展、實體模糊匹配輔助

        Args:
            word: 查詢詞

        Returns:
            同義詞列表（不含 word 本身）
        """
        lookup = cls.get_lookup()
        group = lookup.get(word, [])
        return [w for w in group if w != word]

    @classmethod
    def get_status_normalize(cls) -> Dict[str, str]:
        """
        取得狀態正規化表: {變體 -> 正規名稱}

        從 lookup 中提取 status_synonyms 分類的映射。
        同義詞組第一項為正規名稱，其餘為變體。

        用途：規則引擎的 normalize_status() 函數
        """
        lookup = cls.get_lookup()
        status_map: Dict[str, str] = {}

        # 狀態相關關鍵字特徵：包含「處理」「結案」「完成」「歸檔」「辦理」「逾期」等
        # 從 lookup 反推：找出包含狀態詞的同義詞組
        _STATUS_MARKERS = {"待處理", "處理中", "已結案", "已歸檔", "待辦",
                           "未處理", "進行中", "已完成", "結案", "完成",
                           "辦畢", "歸檔", "存查", "尚未處理", "已辦畢"}

        seen_groups: set = set()
        for marker in _STATUS_MARKERS:
            group = lookup.get(marker)
            if group:
                group_key = id(group)
                if group_key not in seen_groups:
                    seen_groups.add(group_key)
                    canonical = group[0]
                    for variant in group:
                        status_map[variant] = canonical

        return status_map

    @classmethod
    def expand_search_terms(cls, query: str) -> List[str]:
        """
        將搜尋查詢擴展為多個搜尋詞

        用於圖譜實體搜尋：輸入「工務局」可同時搜「桃園市政府工務局」。

        Args:
            query: 原始查詢字串

        Returns:
            包含原始查詢 + 所有同義詞的列表
        """
        terms = [query]
        synonyms = cls.find_synonyms(query)
        terms.extend(synonyms)
        return terms
