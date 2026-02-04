"""
公文 AI 服務

Version: 1.1.0
Created: 2026-02-04
Updated: 2026-02-05 - 整合速率限制與快取機制

功能:
- 公文摘要生成 (帶快取)
- 分類建議 (doc_type, category) (帶快取)
- 關鍵字提取 (帶快取)
- 機關匹配強化
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base_ai_service import BaseAIService

logger = logging.getLogger(__name__)


class DocumentAIService(BaseAIService):
    """公文專用 AI 服務"""

    # 公文類型選項
    DOC_TYPES = ["函", "令", "公告", "書函", "開會通知單", "簽", "箋函", "便箋", "其他"]

    # 收發類別
    CATEGORIES = ["收文", "發文"]

    async def generate_summary(
        self,
        subject: str,
        content: Optional[str] = None,
        sender: Optional[str] = None,
        max_length: int = 100,
    ) -> Dict[str, Any]:
        """
        生成公文摘要

        Args:
            subject: 公文主旨
            content: 公文內容（可選）
            sender: 發文機關（可選）
            max_length: 摘要最大長度

        Returns:
            {
                "summary": "摘要內容",
                "confidence": 0.85,
                "source": "groq" | "ollama" | "fallback"
            }
        """
        if not self.is_enabled():
            return {
                "summary": subject[:max_length] if subject else "",
                "confidence": 0.0,
                "source": "disabled",
            }

        system_prompt = f"""你是一位專業的公文處理助理。請根據以下公文資訊生成簡潔的摘要。

要求：
1. 摘要必須在 {max_length} 字以內
2. 使用正式、簡潔的語言
3. 保留關鍵資訊：目的、對象、重要日期或事項
4. 只輸出摘要內容，不要加任何說明文字"""

        user_content = f"主旨：{subject}"
        if sender:
            user_content += f"\n發文機關：{sender}"
        if content:
            user_content += f"\n內容摘要：{content[:500]}"  # 限制輸入長度

        try:
            # 生成快取鍵
            cache_key = self._generate_cache_key(
                "summary", subject, content or "", sender or "", str(max_length)
            )

            response = await self._call_ai_with_cache(
                cache_key=cache_key,
                ttl=self.config.cache_ttl_summary,
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=0.3,  # 較低溫度以保持一致性
                max_tokens=self.config.summary_max_tokens,
            )

            # 清理回應
            summary = response.strip()
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."

            return {
                "summary": summary,
                "confidence": 0.85,
                "source": "ai",
            }
        except RuntimeError as e:
            # 速率限制錯誤
            logger.warning(f"速率限制: {e}")
            return {
                "summary": subject[:max_length] if subject else "",
                "confidence": 0.0,
                "source": "rate_limited",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"生成摘要失敗: {e}")
            return {
                "summary": subject[:max_length] if subject else "",
                "confidence": 0.0,
                "source": "fallback",
                "error": str(e),
            }

    async def suggest_classification(
        self,
        subject: str,
        content: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        建議公文分類

        Args:
            subject: 公文主旨
            content: 公文內容（可選）
            sender: 發文/來文機關（可選）

        Returns:
            {
                "doc_type": "函",
                "category": "收文",
                "doc_type_confidence": 0.85,
                "category_confidence": 0.90,
                "reasoning": "判斷理由"
            }
        """
        if not self.is_enabled():
            return {
                "doc_type": "函",
                "category": "收文",
                "doc_type_confidence": 0.0,
                "category_confidence": 0.0,
                "source": "disabled",
            }

        doc_types_str = "、".join(self.DOC_TYPES)

        system_prompt = f"""你是一位專業的公文分類助理。請根據公文資訊判斷分類。

公文類型選項：{doc_types_str}
收發類別選項：收文、發文

請以 JSON 格式回覆：
{{
    "doc_type": "類型",
    "category": "收文或發文",
    "doc_type_confidence": 0.0-1.0,
    "category_confidence": 0.0-1.0,
    "reasoning": "簡短說明判斷理由"
}}

判斷提示：
- 「函」：一般公務往來、答復、通知
- 「令」：法令發布、人事任免
- 「公告」：對外公開事項
- 「書函」：非正式聯繫
- 「開會通知單」：會議召開通知
- 「簽」：內部簽呈
- 收文：由外部機關發來的公文
- 發文：本機關對外發出的公文"""

        user_content = f"主旨：{subject}"
        if sender:
            user_content += f"\n發文機關：{sender}"
        if content:
            user_content += f"\n內容：{content[:300]}"

        try:
            # 生成快取鍵
            cache_key = self._generate_cache_key(
                "classify", subject, content or "", sender or ""
            )

            response = await self._call_ai_with_cache(
                cache_key=cache_key,
                ttl=self.config.cache_ttl_classify,
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=0.3,
                max_tokens=self.config.classify_max_tokens,
            )

            # 解析 JSON 回應
            result = self._parse_json_response(response)

            # 驗證並設定預設值
            doc_type = result.get("doc_type", "函")
            if doc_type not in self.DOC_TYPES:
                doc_type = "函"

            category = result.get("category", "收文")
            if category not in self.CATEGORIES:
                category = "收文"

            return {
                "doc_type": doc_type,
                "category": category,
                "doc_type_confidence": float(result.get("doc_type_confidence", 0.7)),
                "category_confidence": float(result.get("category_confidence", 0.7)),
                "reasoning": result.get("reasoning", ""),
                "source": "ai",
            }
        except RuntimeError as e:
            logger.warning(f"速率限制: {e}")
            return {
                "doc_type": "函",
                "category": "收文",
                "doc_type_confidence": 0.0,
                "category_confidence": 0.0,
                "source": "rate_limited",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"分類建議失敗: {e}")
            return {
                "doc_type": "函",
                "category": "收文",
                "doc_type_confidence": 0.0,
                "category_confidence": 0.0,
                "source": "fallback",
                "error": str(e),
            }

    async def extract_keywords(
        self,
        subject: str,
        content: Optional[str] = None,
        max_keywords: int = 5,
    ) -> Dict[str, Any]:
        """
        提取公文關鍵字

        Args:
            subject: 公文主旨
            content: 公文內容（可選）
            max_keywords: 最大關鍵字數量

        Returns:
            {
                "keywords": ["關鍵字1", "關鍵字2"],
                "confidence": 0.85
            }
        """
        if not self.is_enabled():
            return {
                "keywords": [],
                "confidence": 0.0,
                "source": "disabled",
            }

        system_prompt = f"""你是一位專業的公文關鍵字提取助理。

請從公文中提取最重要的 {max_keywords} 個關鍵字。

要求：
1. 關鍵字應能代表公文的核心主題
2. 優先提取專有名詞、機關名稱、地點、重要日期
3. 避免過於通用的詞彙（如「關於」「有關」「請」等）
4. 只輸出 JSON 格式，不要加任何說明

輸出格式：
{{"keywords": ["關鍵字1", "關鍵字2", ...]}}"""

        user_content = f"主旨：{subject}"
        if content:
            user_content += f"\n內容：{content[:500]}"

        try:
            # 生成快取鍵
            cache_key = self._generate_cache_key(
                "keywords", subject, content or "", str(max_keywords)
            )

            response = await self._call_ai_with_cache(
                cache_key=cache_key,
                ttl=self.config.cache_ttl_keywords,
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=0.3,
                max_tokens=self.config.keywords_max_tokens,
            )

            result = self._parse_json_response(response)
            keywords = result.get("keywords", [])

            # 確保是列表且長度不超過限制
            if not isinstance(keywords, list):
                keywords = []
            keywords = keywords[:max_keywords]

            return {
                "keywords": keywords,
                "confidence": 0.85 if keywords else 0.0,
                "source": "ai",
            }
        except RuntimeError as e:
            logger.warning(f"速率限制: {e}")
            return {
                "keywords": [],
                "confidence": 0.0,
                "source": "rate_limited",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"關鍵字提取失敗: {e}")
            return {
                "keywords": [],
                "confidence": 0.0,
                "source": "fallback",
                "error": str(e),
            }

    async def match_agency_enhanced(
        self,
        agency_name: str,
        candidates: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        AI 強化機關匹配

        Args:
            agency_name: 輸入的機關名稱
            candidates: 候選機關列表 [{"id": 1, "name": "機關名稱", "short_name": "簡稱"}]

        Returns:
            {
                "best_match": {"id": 1, "name": "xxx", "score": 0.95},
                "alternatives": [...],
                "is_new": True/False
            }
        """
        if not self.is_enabled():
            return {
                "best_match": None,
                "alternatives": [],
                "is_new": True,
                "source": "disabled",
            }

        if not candidates:
            return {
                "best_match": None,
                "alternatives": [],
                "is_new": True,
                "source": "ai",
            }

        # 準備候選列表字串
        candidates_str = "\n".join(
            [f"- ID {c.get('id')}: {c.get('name')} ({c.get('short_name', '')})"
             for c in candidates[:20]]  # 限制候選數量
        )

        system_prompt = """你是一位專業的機關名稱匹配助理。

請根據輸入的機關名稱，從候選列表中找出最可能匹配的機關。

考慮因素：
1. 名稱相似度（包含簡稱、全稱）
2. 常見縮寫或別稱
3. 層級對應（如：局、處、科）

輸出 JSON 格式：
{
    "best_match_id": 1,
    "confidence": 0.95,
    "reasoning": "匹配理由"
}

如果沒有匹配的機關，輸出：
{
    "best_match_id": null,
    "confidence": 0,
    "reasoning": "原因"
}"""

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

            if best_id and confidence >= 0.7:
                # 找到匹配
                matched = next(
                    (c for c in candidates if c.get("id") == best_id),
                    None
                )
                if matched:
                    return {
                        "best_match": {
                            "id": matched.get("id"),
                            "name": matched.get("name"),
                            "score": confidence,
                        },
                        "alternatives": [],
                        "is_new": False,
                        "reasoning": result.get("reasoning", ""),
                        "source": "ai",
                    }

            return {
                "best_match": None,
                "alternatives": [],
                "is_new": True,
                "reasoning": result.get("reasoning", ""),
                "source": "ai",
            }
        except Exception as e:
            logger.error(f"機關匹配失敗: {e}")
            return {
                "best_match": None,
                "alternatives": [],
                "is_new": True,
                "source": "fallback",
                "error": str(e),
            }

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析 AI 回應中的 JSON

        支援處理：
        - 純 JSON
        - 包含 ```json``` 代碼塊
        - 包含其他文字的回應
        """
        # 嘗試直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 嘗試提取 JSON 代碼塊
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 嘗試提取 {...} 內容
        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"無法解析 JSON 回應: {response[:100]}...")
        return {}


# 全域服務實例
_document_ai_service: Optional[DocumentAIService] = None


def get_document_ai_service() -> DocumentAIService:
    """獲取公文 AI 服務實例 (Singleton)"""
    global _document_ai_service
    if _document_ai_service is None:
        _document_ai_service = DocumentAIService()
    return _document_ai_service
