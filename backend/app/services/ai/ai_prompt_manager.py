"""
AI Prompt 與同義詞管理器

從 DocumentAIService 提取的配置管理模組。
負責 Prompt 模板 (DB/YAML/內建) 和同義詞字典的載入、快取與擴展。

Version: 1.0.0
Created: 2026-02-11
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy import select

logger = logging.getLogger(__name__)


class AIPromptManager:
    """AI Prompt 模板與同義詞管理器（class-level 快取）"""

    # Prompt 模板快取
    _prompts: Optional[Dict[str, Any]] = None

    # 內建預設 Prompt (當 prompts.yaml 載入失敗時使用)
    _DEFAULT_PROMPTS: Dict[str, Any] = {
        "summary": {
            "system": (
                "你是一位專業的公文處理助理。請根據公文資訊生成簡潔的摘要。"
                "摘要必須在 {max_length} 字以內，使用正式簡潔的語言，"
                "保留關鍵資訊。只輸出摘要內容，不要加說明文字。"
            ),
        },
        "classify": {
            "system": (
                "你是一位專業的公文分類助理。公文類型選項：{doc_types_str}。"
                "收發類別選項：收文、發文。"
                '請以 JSON 格式回覆：{{"doc_type": "類型", "category": "收文或發文", '
                '"doc_type_confidence": 0.0, "category_confidence": 0.0, "reasoning": "理由"}}'
            ),
        },
        "keywords": {
            "system": (
                "你是一位專業的公文關鍵字提取助理。"
                "請從公文中提取最重要的 {max_keywords} 個關鍵字。"
                "優先提取專有名詞、機關名稱、地點。"
                '只輸出 JSON 格式：{{"keywords": ["關鍵字1", "關鍵字2"]}}'
            ),
        },
        "match_agency": {
            "system": (
                "你是一位專業的機關名稱匹配助理。"
                "請根據輸入的機關名稱，從候選列表中找出最可能匹配的機關。"
                '輸出 JSON 格式：{{"best_match_id": 1, "confidence": 0.95, "reasoning": "理由"}}。'
                '無匹配時：{{"best_match_id": null, "confidence": 0, "reasoning": "原因"}}'
            ),
        },
        "search_intent": {
            "system": (
                "你是一個公文搜尋助手。當前日期：{today}，民國{roc_year}年。"
                "請分析自然語言查詢，以 JSON 回應搜尋條件："
                "keywords(關鍵字陣列)、doc_type(公文類型)、category(收文/發文)、"
                "sender(發文單位)、receiver(受文單位)、"
                "date_from/date_to(YYYY-MM-DD)、status(處理狀態)、"
                "has_deadline(布林)、contract_case(案件名稱)、confidence(0-1)。"
                "無法確定的欄位設為 null。"
            ),
        },
    }

    # 同義詞：委託給 SynonymExpander（保留屬性供向後相容讀取）
    _synonyms: Optional[Dict[str, List[List[str]]]] = None
    _synonym_lookup: Optional[Dict[str, List[str]]] = None

    # DB Prompt 版本快取
    _db_prompt_cache: Optional[Dict[str, Dict[str, Any]]] = None
    _db_prompts_loaded: bool = False

    @classmethod
    async def ensure_db_prompts_loaded(cls) -> None:
        """確保 DB Prompt 版本已載入至記憶體快取"""
        if cls._db_prompts_loaded:
            return

        cache: Dict[str, Dict[str, Any]] = {}
        try:
            from app.db.database import AsyncSessionLocal
            from app.extended.models import AIPromptVersion

            async with AsyncSessionLocal() as db:
                query = select(AIPromptVersion).where(AIPromptVersion.is_active == True)
                result = await db.execute(query)
                active_versions = result.scalars().all()

                for v in active_versions:
                    cache[v.feature] = {
                        "system": v.system_prompt,
                        "user_template": v.user_template,
                    }

            if cache:
                logger.info(f"已從 DB 載入 {len(cache)} 個 active Prompt 版本: {list(cache.keys())}")
        except Exception as e:
            logger.warning(f"從 DB 載入 Prompt 版本失敗，將使用 YAML fallback: {e}")

        cls._db_prompt_cache = cache
        cls._db_prompts_loaded = True

    @classmethod
    def get_system_prompt(cls, feature: str) -> str:
        """
        取得指定功能的 system prompt

        優先順序: DB active 版本 > YAML 檔案 > 內建預設值
        """
        # 1. 嘗試從 DB 快取取得
        if cls._db_prompt_cache and feature in cls._db_prompt_cache:
            return cls._db_prompt_cache[feature]["system"]

        # 2. Fallback 到 YAML / 內建預設
        yaml_prompts = cls.load_prompts()
        return yaml_prompts.get(feature, {}).get("system", "")

    @classmethod
    def load_prompts(cls) -> Dict[str, Any]:
        """從 YAML 檔案載入 Prompt 模板，失敗時使用內建預設值"""
        if cls._prompts is not None:
            return cls._prompts

        prompts_path = Path(__file__).parent / "prompts.yaml"
        try:
            with open(prompts_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            if not isinstance(loaded, dict) or not loaded:
                raise ValueError("YAML 內容為空或格式不正確")
            cls._prompts = loaded
            logger.info(f"已載入 Prompt 模板: {prompts_path}")
        except FileNotFoundError:
            logger.error(
                f"Prompt 模板檔案不存在: {prompts_path}，"
                "將使用內建預設 Prompt"
            )
            cls._prompts = dict(cls._DEFAULT_PROMPTS)
        except Exception as e:
            logger.error(
                f"載入 Prompt 模板失敗: {e}，"
                "將使用內建預設 Prompt"
            )
            cls._prompts = dict(cls._DEFAULT_PROMPTS)

        return cls._prompts

    @classmethod
    def load_synonyms(cls) -> Dict[str, List[str]]:
        """載入同義詞字典並建立快速查找索引（委託 SynonymExpander）"""
        from app.services.ai.synonym_expander import SynonymExpander
        lookup = SynonymExpander.get_lookup()
        cls._synonym_lookup = lookup  # 同步向後相容屬性
        return lookup

    @classmethod
    def reload_synonyms_from_db(cls, synonym_records: list) -> int:
        """從 DB 記錄重建同義詞查找索引（委託 SynonymExpander）"""
        from app.services.ai.synonym_expander import SynonymExpander
        total = SynonymExpander.reload_from_db(synonym_records)
        cls._synonym_lookup = SynonymExpander.get_lookup()  # 同步
        return total

    @classmethod
    def invalidate_prompt_cache(cls) -> None:
        """清除 prompt 快取，強制重新載入"""
        cls._prompts = None
        cls._db_prompt_cache = None
        cls._db_prompts_loaded = False
        logger.info("Prompt 快取已清除")

    @staticmethod
    def expand_keywords_with_synonyms(
        keywords: List[str],
        lookup: Dict[str, List[str]],
    ) -> List[str]:
        """擴展關鍵字列表：加入同義詞（委託 SynonymExpander）"""
        from app.services.ai.synonym_expander import SynonymExpander
        return SynonymExpander.expand_keywords(keywords)

    @staticmethod
    def expand_agency_name(name: str, lookup: Dict[str, List[str]]) -> str:
        """擴展機關名稱：縮寫 -> 全稱（委託 SynonymExpander）"""
        from app.services.ai.synonym_expander import SynonymExpander
        return SynonymExpander.expand_agency(name)
