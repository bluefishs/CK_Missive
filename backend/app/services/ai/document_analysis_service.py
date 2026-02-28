"""
DocumentAnalysisService - AI 分析結果持久化服務

Wrapper 模式：組合 DocumentAIService (Singleton LLM 呼叫) +
AIAnalysisRepository (DB 持久化)。

版本: 1.0.0
建立日期: 2026-02-28
"""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.extended.models import OfficialDocument, DocumentAIAnalysis
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.services.ai.document_ai_service import get_document_ai_service

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = "1.0.0"


class DocumentAnalysisService:
    """AI 分析結果持久化服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIAnalysisRepository(db)
        self.ai_service = get_document_ai_service()

    async def get_analysis(self, document_id: int) -> Optional[DocumentAIAnalysis]:
        """取得已存在的分析結果（不觸發新分析）"""
        analysis = await self.repo.get_by_document_id(document_id)
        if not analysis:
            return None

        # 檢查 hash 是否過期
        doc = await self._get_document(document_id)
        if doc and analysis.source_text_hash:
            current_hash = self.compute_text_hash(
                doc.subject, doc.content, doc.sender
            )
            if current_hash != analysis.source_text_hash and not analysis.is_stale:
                await self.repo.mark_stale(document_id)
                await self.db.commit()
                analysis.is_stale = True

        # 附加 NER 計數
        analysis = await self._attach_ner_counts(analysis)
        return analysis

    async def get_or_analyze(
        self, document_id: int, force: bool = False
    ) -> DocumentAIAnalysis:
        """取得分析結果；若不存在/過期/force 則執行分析"""
        doc = await self._get_document(document_id)
        if not doc:
            raise NotFoundException(resource="公文", resource_id=document_id)

        if not force:
            existing = await self.repo.get_by_document_id(document_id)
            if existing and not existing.is_stale and existing.status == "completed":
                return await self._attach_ner_counts(existing)

        analysis = await self._run_analysis(doc)
        return await self._attach_ner_counts(analysis)

    async def mark_document_stale(self, document_id: int) -> None:
        """公文更新後標記分析過期"""
        await self.repo.mark_stale(document_id)

    async def get_analysis_stats(self) -> Dict[str, Any]:
        """覆蓋率統計"""
        return await self.repo.get_stats()

    async def batch_analyze(
        self, limit: int = 50, force: bool = False
    ) -> Dict[str, int]:
        """批次分析（背景用）"""
        pending_ids = await self.repo.get_pending_documents(limit)

        counts = {"processed": 0, "success": 0, "error": 0, "skip": 0}
        for doc_id in pending_ids:
            counts["processed"] += 1
            try:
                doc = await self._get_document(doc_id)
                if not doc or not (doc.subject or doc.content):
                    counts["skip"] += 1
                    continue
                await self._run_analysis(doc)
                counts["success"] += 1
            except Exception as e:
                logger.warning(f"批次分析失敗 doc_id={doc_id}: {e}")
                counts["error"] += 1

        return counts

    # =========================================================================
    # Private
    # =========================================================================

    async def _get_document(self, document_id: int) -> Optional[OfficialDocument]:
        result = await self.db.execute(
            select(OfficialDocument)
            .where(OfficialDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def _run_analysis(self, doc: OfficialDocument) -> DocumentAIAnalysis:
        """執行三種分析並持久化"""
        start_ms = time.time()

        subject = doc.subject or ""
        content = doc.content or ""
        sender = doc.sender or ""

        # 依序執行（避免同 session 並發問題）
        summary_result = await self._safe_call(
            self.ai_service.generate_summary, subject, content, sender
        )
        classify_result = await self._safe_call(
            self.ai_service.suggest_classification, subject, content, sender
        )
        keywords_result = await self._safe_call(
            self.ai_service.extract_keywords, subject, content
        )

        elapsed_ms = int((time.time() - start_ms) * 1000)
        text_hash = self.compute_text_hash(subject, content, sender)

        # 判斷狀態
        results = [summary_result, classify_result, keywords_result]
        success_count = sum(1 for r in results if r is not None)
        if success_count == 3:
            status = "completed"
        elif success_count > 0:
            status = "partial"
        else:
            status = "failed"

        # 取得 provider/model 資訊
        llm_provider = None
        llm_model = None
        for r in results:
            if r and r.get("source"):
                llm_provider = r["source"]
                break
        for r in results:
            if r and r.get("model"):
                llm_model = r["model"]
                break

        analysis = await self.repo.upsert(
            document_id=doc.id,
            summary=summary_result.get("summary") if summary_result else None,
            summary_confidence=summary_result.get("confidence") if summary_result else None,
            suggested_doc_type=classify_result.get("doc_type") if classify_result else None,
            doc_type_confidence=classify_result.get("doc_type_confidence") if classify_result else None,
            suggested_category=classify_result.get("category") if classify_result else None,
            category_confidence=classify_result.get("category_confidence") if classify_result else None,
            classification_reasoning=classify_result.get("reasoning") if classify_result else None,
            keywords=keywords_result.get("keywords") if keywords_result else None,
            keywords_confidence=keywords_result.get("confidence") if keywords_result else None,
            llm_provider=llm_provider,
            llm_model=llm_model,
            processing_ms=elapsed_ms,
            source_text_hash=text_hash,
            analysis_version=ANALYSIS_VERSION,
            status=status,
            is_stale=False,
            error_message=None,
            analyzed_at=sa_func.now(),
        )
        await self.db.commit()
        return analysis

    async def _safe_call(self, fn, *args) -> Optional[Dict[str, Any]]:
        """安全呼叫 AI 服務方法，失敗返回 None"""
        try:
            return await fn(*args)
        except Exception as e:
            logger.warning(f"AI 分析呼叫失敗 {fn.__name__}: {e}")
            return None

    async def _attach_ner_counts(
        self, analysis: DocumentAIAnalysis
    ) -> DocumentAIAnalysis:
        """從 document_entities 聚合 NER 計數"""
        from app.extended.models import DocumentEntity, EntityRelation

        entities_result = await self.db.execute(
            select(sa_func.count(DocumentEntity.id))
            .where(DocumentEntity.document_id == analysis.document_id)
        )
        relations_result = await self.db.execute(
            select(sa_func.count(EntityRelation.id))
            .where(EntityRelation.document_id == analysis.document_id)
        )

        # 動態附加（不存入 DB）
        analysis.entities_count = entities_result.scalar() or 0
        analysis.relations_count = relations_result.scalar() or 0
        return analysis

    @staticmethod
    def compute_text_hash(
        subject: Optional[str],
        content: Optional[str],
        sender: Optional[str],
    ) -> str:
        """計算輸入文本的 SHA256（用於過期偵測）"""
        combined = f"{subject or ''}|{content or ''}|{sender or ''}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
