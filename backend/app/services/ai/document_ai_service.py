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

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .ai_prompt_manager import AIPromptManager
from .base_ai_service import BaseAIService
from .search_intent_parser import SearchIntentParser
from app.schemas.ai import (
    ClassificationResponse,
    KeywordsResponse,
    NaturalSearchRequest,
    AttachmentInfo,
    DocumentSearchResult,
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
        AIPromptManager.load_synonyms()
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
                response_schema=KeywordsResponse,
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

            if best_id and confidence >= 0.7:
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
    # 自然語言搜尋
    # ========================================================================

    async def natural_search(
        self,
        db: AsyncSession,
        request: NaturalSearchRequest,
        current_user: Optional[Any] = None,
    ) -> NaturalSearchResponse:
        """執行自然語言公文搜尋"""
        from app.extended.models import DocumentAttachment, ContractProject
        from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder

        start_time = time.monotonic()

        # 1. 解析搜尋意圖
        parsed_intent, source = await self.parse_search_intent(request.query, db=db)

        # 2. QueryBuilder 建構查詢
        qb = DocumentQueryBuilder(db)

        if parsed_intent.keywords:
            # 去重關鍵字（保留順序，忽略大小寫）
            seen = set()
            unique_keywords = []
            for kw in parsed_intent.keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    seen.add(kw_lower)
                    unique_keywords.append(kw)
            if unique_keywords:
                qb = qb.with_keywords_full(unique_keywords)
                logger.debug(f"AI 搜尋關鍵字: {unique_keywords}")
        if parsed_intent.doc_type:
            qb = qb.with_doc_type(parsed_intent.doc_type)
        if parsed_intent.category:
            qb = qb.with_category(parsed_intent.category)
        if parsed_intent.sender:
            qb = qb.with_sender_like(parsed_intent.sender)
        if parsed_intent.receiver:
            qb = qb.with_receiver_like(parsed_intent.receiver)

        # 日期範圍
        date_from_val, date_to_val = None, None
        if parsed_intent.date_from:
            try:
                date_from_val = datetime.strptime(parsed_intent.date_from, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"AI 搜尋：無效的起始日期格式 '{parsed_intent.date_from}'")
        if parsed_intent.date_to:
            try:
                date_to_val = datetime.strptime(parsed_intent.date_to, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"AI 搜尋：無效的結束日期格式 '{parsed_intent.date_to}'")
        if date_from_val or date_to_val:
            qb = qb.with_date_range(date_from_val, date_to_val)

        if parsed_intent.status:
            qb = qb.with_status(parsed_intent.status)
        if parsed_intent.contract_case:
            qb = qb.with_contract_case(parsed_intent.contract_case)
        if parsed_intent.related_entity == "dispatch_order":
            qb = qb.with_dispatch_linked()
            logger.info("AI 搜尋：啟用派工單關聯過濾")

        # 權限過濾 (RLS)
        if current_user:
            is_admin = getattr(current_user, 'role', None) == 'admin'
            if not is_admin:
                user_name = getattr(current_user, 'full_name', None) or getattr(current_user, 'username', '')
                if user_name:
                    qb = qb.with_assignee_access(user_name)

        # 排序策略
        query_embedding = None
        if parsed_intent.keywords:
            relevance_text = " ".join(parsed_intent.keywords)
            try:
                query_embedding = await self.connector.generate_embedding(request.query)
            except Exception as e:
                logger.warning(f"查詢 embedding 生成失敗，降級為 trigram 搜尋: {e}")

            if query_embedding:
                qb = qb.with_relevance_order(relevance_text)
                qb = qb.with_semantic_search(query_embedding, weight=0.4)
            else:
                qb = qb.with_relevance_order(relevance_text)
        else:
            qb = qb.order_by("updated_at", descending=True)

        if request.offset > 0:
            qb = qb.offset(request.offset)
        qb = qb.limit(request.max_results)

        # 3. 執行查詢
        documents, total_count = await qb.execute_with_count()

        # 4. 並行取得附件與專案
        doc_ids = [doc.id for doc in documents]
        project_ids = list({doc.contract_project_id for doc in documents if doc.contract_project_id})

        async def fetch_attachments():
            att_map = {doc_id: [] for doc_id in doc_ids}
            if not (request.include_attachments and doc_ids):
                return att_map
            att_query = (
                select(DocumentAttachment)
                .where(DocumentAttachment.document_id.in_(doc_ids))
                .order_by(DocumentAttachment.created_at)
            )
            att_result = await db.execute(att_query)
            for att in att_result.scalars().all():
                if att.document_id in att_map:
                    att_map[att.document_id].append(AttachmentInfo(
                        id=att.id, file_name=att.file_name,
                        original_name=att.original_name, file_size=att.file_size,
                        mime_type=att.mime_type, created_at=att.created_at,
                    ))
            return att_map

        async def fetch_projects():
            proj_map = {}
            if not project_ids:
                return proj_map
            proj_query = select(ContractProject).where(ContractProject.id.in_(project_ids))
            proj_result = await db.execute(proj_query)
            for proj in proj_result.scalars().all():
                proj_map[proj.id] = proj.project_name
            return proj_map

        # 循序執行（AsyncSession 不支援同 session gather 並行）
        attachment_map = await fetch_attachments()
        project_map = await fetch_projects()

        # 5. 組裝結果
        search_results = []
        for doc in documents:
            doc_attachments = attachment_map.get(doc.id, [])
            search_results.append(DocumentSearchResult(
                id=doc.id, auto_serial=doc.auto_serial,
                doc_number=doc.doc_number, subject=doc.subject,
                doc_type=doc.doc_type, category=doc.category,
                sender=doc.sender, receiver=doc.receiver,
                doc_date=doc.doc_date, status=doc.status,
                contract_project_name=project_map.get(doc.contract_project_id) if doc.contract_project_id else None,
                ck_note=doc.ck_note, attachment_count=len(doc_attachments),
                attachments=doc_attachments,
                created_at=doc.created_at, updated_at=doc.updated_at,
            ))

        search_strategy = "keyword"
        if parsed_intent.keywords and parsed_intent.confidence > 0:
            search_strategy = "hybrid" if query_embedding else "similarity"

        synonym_lookup = AIPromptManager._synonym_lookup
        synonym_expanded = bool(
            parsed_intent.keywords and len(parsed_intent.keywords) > 0 and synonym_lookup
        )

        # 寫入搜尋歷史
        try:
            from app.extended.models import AISearchHistory
            latency_ms = int((time.monotonic() - start_time) * 1000)
            history = AISearchHistory(
                user_id=getattr(current_user, 'id', None) if current_user else None,
                query=request.query,
                parsed_intent=parsed_intent.model_dump(exclude_none=True),
                results_count=total_count,
                search_strategy=search_strategy,
                source=source,
                synonym_expanded=synonym_expanded,
                related_entity=parsed_intent.related_entity,
                latency_ms=latency_ms,
                confidence=parsed_intent.confidence,
            )
            if (isinstance(query_embedding, list)
                    and len(query_embedding) > 0
                    and hasattr(AISearchHistory, 'query_embedding')):
                history.query_embedding = query_embedding
            db.add(history)
            await db.commit()
        except Exception as e:
            logger.warning(f"搜尋歷史寫入失敗: {e}")
            try:
                await db.rollback()
            except Exception:
                pass

        return NaturalSearchResponse(
            success=True,
            query=request.query,
            parsed_intent=parsed_intent,
            results=search_results,
            total=total_count,
            source=source,
            search_strategy=search_strategy,
            synonym_expanded=synonym_expanded,
        )


# 全域服務實例
_document_ai_service: Optional[DocumentAIService] = None


def get_document_ai_service() -> DocumentAIService:
    """獲取公文 AI 服務實例 (Singleton)"""
    global _document_ai_service
    if _document_ai_service is None:
        _document_ai_service = DocumentAIService()
    return _document_ai_service
