"""
公文 AI 服務

Version: 5.0.0
Created: 2026-02-04
Updated: 2026-02-11 - 拆分為 4 模組：PromptManager/IntentParser/Features/Search

模組拆分結構:
- ai_prompt_manager.py: Prompt 模板與同義詞管理（class-level 快取）
- search_intent_parser.py: 四組件意圖解析（規則→向量→LLM→合併）
- document_ai_service.py (本檔): 公文 AI 功能 + 自然語言搜尋

功能:
- 公文摘要生成 (帶快取)
- 分類建議 (doc_type, category) (帶快取 + schema 驗證)
- 關鍵字提取 (帶快取 + schema 驗證)
- 機關匹配強化
- 自然語言公文搜尋
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.ai_config import get_ai_config
from app.services.ai.ai_prompt_manager import AIPromptManager
from app.services.ai.base_ai_service import BaseAIService
from app.services.ai.search_intent_parser import SearchIntentParser
from app.schemas.ai.search import (
    ClassificationResponse,
    KeywordsValidationResponse,
    NaturalSearchRequest,
    NaturalSearchResponse,
)

logger = logging.getLogger(__name__)


class DocumentAIService(BaseAIService):
    """公文專用 AI 服務"""

    # 公文類型選項
    DOC_TYPES = ["函", "令", "公告", "書函", "開會通知單", "簽", "箋函", "便箋", "其他"]

    # 收發類別
    CATEGORIES = ["收文", "發文"]

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        AIPromptManager.load_prompts()
        # SynonymExpander 自動 lazy load（DB 優先 → YAML fallback），無需手動初始化
        self._intent_parser = SearchIntentParser(self)

    # ========================================================================
    # 摘要生成
    # ========================================================================

    def _build_summary_prompt(
        self,
        subject: str,
        content: Optional[str] = None,
        sender: Optional[str] = None,
        max_length: int = 100,
    ) -> Dict[str, str]:
        """建構摘要生成的 prompt"""
        system_prompt = AIPromptManager.get_system_prompt("summary").format(
            max_length=max_length
        )
        user_content = f"主旨：{subject}"
        if sender:
            user_content += f"\n發文機關：{sender}"
        if content:
            user_content += f"\n內容摘要：{content[:500]}"
        return {"system": system_prompt, "user": user_content}

    async def stream_summary(
        self,
        subject: str,
        content: Optional[str] = None,
        sender: Optional[str] = None,
        max_length: int = 100,
    ) -> AsyncGenerator[str, None]:
        """串流生成公文摘要"""
        if not self.is_enabled():
            yield subject[:max_length] if subject else ""
            return

        await AIPromptManager.ensure_db_prompts_loaded()

        if not self._rate_limiter.can_proceed():
            wait_time = self._rate_limiter.get_wait_time()
            await self._stats_manager.record_rate_limit_hit()
            raise RuntimeError(
                f"AI 服務請求過於頻繁，請等待 {int(wait_time)} 秒後重試"
            )

        prompt_data = self._build_summary_prompt(subject, content, sender, max_length)
        messages = [
            {"role": "system", "content": prompt_data["system"]},
            {"role": "user", "content": prompt_data["user"]},
        ]
        self._rate_limiter.record_request()

        async for token in self.connector.stream_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=self.config.summary_max_tokens,
        ):
            yield token

    async def generate_summary(
        self,
        subject: str,
        content: Optional[str] = None,
        sender: Optional[str] = None,
        max_length: int = 100,
    ) -> Dict[str, Any]:
        """生成公文摘要"""
        if not self.is_enabled():
            return {
                "summary": subject[:max_length] if subject else "",
                "confidence": 0.0,
                "source": "disabled",
            }

        await AIPromptManager.ensure_db_prompts_loaded()
        prompt_data = self._build_summary_prompt(subject, content, sender, max_length)

        try:
            cache_key = self._generate_cache_key(
                "summary", subject, content or "", sender or "", str(max_length)
            )
            response = await self._call_ai_with_cache(
                cache_key=cache_key,
                ttl=self.config.cache_ttl_summary,
                system_prompt=prompt_data["system"],
                user_content=prompt_data["user"],
                temperature=0.3,
                max_tokens=self.config.summary_max_tokens,
            )
            summary = response.strip()
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            return {"summary": summary, "confidence": 0.85, "source": "ai"}
        except RuntimeError as e:
            logger.warning(f"速率限制: {e}")
            return {
                "summary": subject[:max_length] if subject else "",
                "confidence": 0.0, "source": "rate_limited", "error": str(e),
            }
        except Exception as e:
            logger.error(f"生成摘要失敗: {e}")
            return {
                "summary": subject[:max_length] if subject else "",
                "confidence": 0.0, "source": "fallback", "error": str(e),
            }

    # ========================================================================
    # 分類建議
    # ========================================================================

    async def suggest_classification(
        self,
        subject: str,
        content: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> Dict[str, Any]:
        """建議公文分類"""
        if not self.is_enabled():
            return {
                "doc_type": "函", "category": "收文",
                "doc_type_confidence": 0.0, "category_confidence": 0.0,
                "source": "disabled",
            }

        await AIPromptManager.ensure_db_prompts_loaded()
        doc_types_str = "、".join(self.DOC_TYPES)
        system_prompt = AIPromptManager.get_system_prompt("classify").format(
            doc_types_str=doc_types_str
        )
        user_content = f"主旨：{subject}"
        if sender:
            user_content += f"\n發文機關：{sender}"
        if content:
            user_content += f"\n內容：{content[:300]}"

        try:
            cache_key = self._generate_cache_key(
                "classify", subject, content or "", sender or ""
            )
            validated = await self._call_ai_with_validation(
                cache_key=cache_key,
                ttl=self.config.cache_ttl_classify,
                system_prompt=system_prompt,
                user_content=user_content,
                response_schema=ClassificationResponse,
                temperature=0.3,
                max_tokens=self.config.classify_max_tokens,
            )
            if isinstance(validated, str):
                result = self._parse_json_response(validated)
            else:
                result = validated

            doc_type = result.get("doc_type", "函")
            if doc_type not in self.DOC_TYPES:
                doc_type = "函"
            category = result.get("category", "收文")
            if category not in self.CATEGORIES:
                category = "收文"

            return {
                "doc_type": doc_type, "category": category,
                "doc_type_confidence": float(result.get("doc_type_confidence", 0.7)),
                "category_confidence": float(result.get("category_confidence", 0.7)),
                "reasoning": result.get("reasoning", ""), "source": "ai",
            }
        except RuntimeError as e:
            logger.warning(f"速率限制: {e}")
            return {
                "doc_type": "函", "category": "收文",
                "doc_type_confidence": 0.0, "category_confidence": 0.0,
                "source": "rate_limited", "error": str(e),
            }
        except Exception as e:
            logger.error(f"分類建議失敗: {e}")
            return {
                "doc_type": "函", "category": "收文",
                "doc_type_confidence": 0.0, "category_confidence": 0.0,
                "source": "fallback", "error": str(e),
            }

    # ========================================================================
    # 關鍵字提取
    # ========================================================================

    async def extract_keywords(
        self,
        subject: str,
        content: Optional[str] = None,
        max_keywords: int = 5,
    ) -> Dict[str, Any]:
        """提取公文關鍵字"""
        if not self.is_enabled():
            return {"keywords": [], "confidence": 0.0, "source": "disabled"}

        await AIPromptManager.ensure_db_prompts_loaded()
        system_prompt = AIPromptManager.get_system_prompt("keywords").format(
            max_keywords=max_keywords
        )
        user_content = f"主旨：{subject}"
        if content:
            user_content += f"\n內容：{content[:500]}"

        try:
            cache_key = self._generate_cache_key(
                "keywords", subject, content or "", str(max_keywords)
            )
            validated = await self._call_ai_with_validation(
                cache_key=cache_key,
                ttl=self.config.cache_ttl_keywords,
                system_prompt=system_prompt,
                user_content=user_content,
                response_schema=KeywordsValidationResponse,
                temperature=0.3,
                max_tokens=self.config.keywords_max_tokens,
            )
            if isinstance(validated, str):
                result = self._parse_json_response(validated)
            else:
                result = validated

            keywords = result.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = []
            keywords = keywords[:max_keywords]
            return {"keywords": keywords, "confidence": 0.85 if keywords else 0.0, "source": "ai"}
        except RuntimeError as e:
            logger.warning(f"速率限制: {e}")
            return {"keywords": [], "confidence": 0.0, "source": "rate_limited", "error": str(e)}
        except Exception as e:
            logger.error(f"關鍵字提取失敗: {e}")
            return {"keywords": [], "confidence": 0.0, "source": "fallback", "error": str(e)}

    # ========================================================================
    # 機關匹配
    # ========================================================================

    async def match_agency_enhanced(
        self,
        agency_name: str,
        candidates: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """AI 強化機關匹配"""
        if not self.is_enabled():
            return {"best_match": None, "alternatives": [], "is_new": True, "source": "disabled"}
        if not candidates:
            return {"best_match": None, "alternatives": [], "is_new": True, "source": "ai"}

        await AIPromptManager.ensure_db_prompts_loaded()
        candidates_str = "\n".join(
            [f"- ID {c.get('id')}: {c.get('name')} ({c.get('short_name', '')})"
             for c in candidates[:20]]
        )
        system_prompt = AIPromptManager.get_system_prompt("match_agency")
        user_content = f"輸入機關名稱：{agency_name}\n\n候選機關：\n{candidates_str}"

        try:
            response = await self._call_ai(
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=0.3,
                max_tokens=128,
            )
            result = self._parse_json_response(response)
            best_id = result.get("best_match_id")
            confidence = float(result.get("confidence", 0))

            if best_id and confidence >= get_ai_config().agency_match_threshold:
                matched = next((c for c in candidates if c.get("id") == best_id), None)
                if matched:
                    return {
                        "best_match": {"id": matched.get("id"), "name": matched.get("name"), "score": confidence},
                        "alternatives": [], "is_new": False,
                        "reasoning": result.get("reasoning", ""), "source": "ai",
                    }
            return {
                "best_match": None, "alternatives": [], "is_new": True,
                "reasoning": result.get("reasoning", ""), "source": "ai",
            }
        except Exception as e:
            logger.error(f"機關匹配失敗: {e}")
            return {"best_match": None, "alternatives": [], "is_new": True, "source": "fallback", "error": str(e)}

    # ========================================================================
    # 意圖解析委託 (向後相容)
    # ========================================================================

    async def parse_search_intent(self, query: str, db=None):
        """委託至 SearchIntentParser"""
        return await self._intent_parser.parse_search_intent(query, db)

    # ========================================================================
    # 自然語言搜尋 (委託至 document_natural_search 模組)
    # ========================================================================

    async def natural_search(
        self,
        db: AsyncSession,
        request: NaturalSearchRequest,
        current_user: Optional[Any] = None,
    ) -> NaturalSearchResponse:
        """執行自然語言公文搜尋（含韌性降級）"""
        from app.services.ai.document_natural_search import execute_natural_search
        return await execute_natural_search(self, db, request, current_user)



# 全域服務實例
_document_ai_service: Optional[DocumentAIService] = None


def get_document_ai_service() -> DocumentAIService:
    """獲取公文 AI 服務實例 (Singleton)"""
    global _document_ai_service
    if _document_ai_service is None:
        _document_ai_service = DocumentAIService()
    return _document_ai_service
