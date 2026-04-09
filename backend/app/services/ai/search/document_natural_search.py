"""
自然語言公文搜尋服務

從 document_ai_service.py 提取，處理自然語言搜尋流程:
1. 意圖解析 (含超時保護)
2. 知識圖譜實體擴展
3. QueryBuilder 查詢建構
4. 並行附件/專案取得
5. 結果組裝 + 搜尋歷史寫入

Version: 1.0.0
Created: 2026-03-24
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.ai_config import get_ai_config
from app.services.ai.synonym_expander import SynonymExpander
from app.services.ai.document_search_helpers import resolve_search_entities
from app.schemas.ai.search import (
    AttachmentInfo,
    DocumentSearchResult,
    MatchedEntity,
    NaturalSearchRequest,
    NaturalSearchResponse,
)

logger = logging.getLogger(__name__)


async def execute_natural_search(
    service: Any,
    db: AsyncSession,
    request: NaturalSearchRequest,
    current_user: Optional[Any] = None,
) -> NaturalSearchResponse:
    """
    執行自然語言公文搜尋（含韌性降級）。

    Args:
        service: DocumentAIService 實例 (提供 parse_search_intent, connector)
        db: 資料庫 session
        request: 搜尋請求
        current_user: 當前使用者 (可選，用於 RLS)
    """
    from app.extended.models import DocumentAttachment, ContractProject
    from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder

    start_time = time.monotonic()

    # 1. 解析搜尋意圖（含超時保護和降級）
    parsed_intent, source = await _parse_intent_safe(service, request.query, db)

    # 1.5 知識圖譜實體擴展
    entity_expanded, expanded_keywords_list, search_keywords = await _expand_entities(
        db, parsed_intent.keywords
    )
    if not entity_expanded:
        search_keywords = parsed_intent.keywords

    # 2. QueryBuilder 建構查詢
    qb = _build_query(
        db, parsed_intent, search_keywords, current_user, request,
    )

    # 排序策略
    query_embedding = await _resolve_embedding(
        service, parsed_intent, request.query, qb
    )

    if request.offset > 0:
        qb = qb.offset(request.offset)
    qb = qb.limit(request.max_results)

    # 3. 執行查詢（超時保護）
    try:
        documents, total_count = await asyncio.wait_for(
            qb.execute_with_count(),
            timeout=get_ai_config().search_query_timeout,
        )
    except asyncio.TimeoutError:
        logger.error(f"搜尋查詢超時 (>20s): {request.query}")
        return NaturalSearchResponse(
            success=False, query=request.query, parsed_intent=parsed_intent,
            results=[], total=0, source=source, search_strategy="keyword",
            synonym_expanded=False,
            error="搜尋查詢超時，請縮小搜尋範圍或使用更具體的關鍵字",
        )

    # 4. 附件與專案
    doc_ids = [doc.id for doc in documents]
    project_ids = list({doc.contract_project_id for doc in documents if doc.contract_project_id})
    attachment_map = await _fetch_attachments(db, doc_ids, request.include_attachments)
    project_map = await _fetch_projects(db, project_ids)

    # 5. 組裝結果
    search_results = _assemble_results(documents, attachment_map, project_map)

    search_strategy = "keyword"
    if parsed_intent.keywords and parsed_intent.confidence > 0:
        search_strategy = "hybrid" if query_embedding else "similarity"

    synonym_expanded = bool(
        parsed_intent.keywords and len(parsed_intent.keywords) > 0
        and SynonymExpander.get_lookup()
    )

    # 6. 正規化實體解析
    matched_entities: List[MatchedEntity] = []
    try:
        matched_entities = await resolve_search_entities(db, parsed_intent, search_results)
    except Exception as e:
        logger.debug(f"正規化實體解析跳過: {e}")

    # 7. 搜尋歷史寫入
    history_id = await _write_search_history(
        db, request, parsed_intent, total_count, search_strategy,
        source, synonym_expanded, query_embedding, current_user, start_time,
    )

    return NaturalSearchResponse(
        success=True, query=request.query, parsed_intent=parsed_intent,
        results=search_results, total=total_count, source=source,
        search_strategy=search_strategy, synonym_expanded=synonym_expanded,
        entity_expanded=entity_expanded, expanded_keywords=expanded_keywords_list,
        history_id=history_id, matched_entities=matched_entities,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _parse_intent_safe(service: Any, query: str, db: AsyncSession):
    """解析搜尋意圖（含超時 + 降級）"""
    try:
        return await asyncio.wait_for(
            service.parse_search_intent(query, db=db), timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.warning(f"意圖解析超時 (>10s)，降級為關鍵字搜尋: {query}")
    except Exception as e:
        logger.warning(f"意圖解析失敗，降級為關鍵字搜尋: {e}")

    from app.schemas.ai.search import ParsedSearchIntent as PSI
    return PSI(keywords=[query], confidence=0.3), "rule_engine"


async def _expand_entities(db: AsyncSession, keywords: Optional[List[str]]):
    """知識圖譜實體擴展（非阻塞）"""
    if not keywords:
        return False, None, keywords or []

    try:
        from app.services.ai.search_entity_expander import expand_search_terms, flatten_expansions
        expansions = await expand_search_terms(db, keywords)
        flattened = flatten_expansions(expansions)
        if len(flattened) > len(keywords):
            logger.info(f"實體擴展: {keywords} → {flattened}")
            return True, flattened, flattened
    except Exception as e:
        logger.debug(f"實體擴展跳過: {e}")

    return False, None, keywords


def _build_query(
    db: AsyncSession,
    parsed_intent: Any,
    search_keywords: List[str],
    current_user: Optional[Any],
    request: NaturalSearchRequest,
):
    """建構 QueryBuilder 查詢"""
    from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder

    qb = DocumentQueryBuilder(db)

    if search_keywords:
        qb = qb.with_keywords_full(search_keywords)
        logger.debug(f"AI 搜尋關鍵字: {search_keywords}")
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

    return qb


async def _resolve_embedding(service: Any, parsed_intent: Any, query: str, qb: Any):
    """解析查詢 embedding 並設定排序"""
    query_embedding = None
    if parsed_intent.keywords:
        relevance_text = " ".join(parsed_intent.keywords)
        try:
            from app.services.ai.embedding_manager import EmbeddingManager
            query_embedding = await EmbeddingManager.get_embedding(query, service.connector)
        except Exception as e:
            logger.warning(f"查詢 embedding 生成失敗，降級為 trigram 搜尋: {e}")

        if query_embedding:
            qb = qb.with_relevance_order(relevance_text)
            qb = qb.with_semantic_search(query_embedding, weight=get_ai_config().hybrid_semantic_weight)
        else:
            qb = qb.with_relevance_order(relevance_text)
    else:
        qb = qb.order_by("updated_at", descending=True)

    return query_embedding


async def _fetch_attachments(
    db: AsyncSession, doc_ids: List[int], include: bool,
) -> Dict[int, list]:
    """取得文件附件"""
    from app.extended.models import DocumentAttachment

    att_map: Dict[int, list] = {doc_id: [] for doc_id in doc_ids}
    if not (include and doc_ids):
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


async def _fetch_projects(db: AsyncSession, project_ids: List[int]) -> Dict[int, str]:
    """取得專案名稱"""
    from app.extended.models import ContractProject

    proj_map: Dict[int, str] = {}
    if not project_ids:
        return proj_map

    proj_query = select(ContractProject).where(ContractProject.id.in_(project_ids))
    proj_result = await db.execute(proj_query)
    for proj in proj_result.scalars().all():
        proj_map[proj.id] = proj.project_name
    return proj_map


def _assemble_results(documents, attachment_map, project_map) -> List[DocumentSearchResult]:
    """組裝搜尋結果"""
    results = []
    for doc in documents:
        doc_attachments = attachment_map.get(doc.id, [])
        results.append(DocumentSearchResult(
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
    return results


async def _write_search_history(
    db: AsyncSession,
    request: NaturalSearchRequest,
    parsed_intent: Any,
    total_count: int,
    search_strategy: str,
    source: str,
    synonym_expanded: bool,
    query_embedding: Optional[list],
    current_user: Optional[Any],
    start_time: float,
) -> Optional[int]:
    """非阻塞寫入搜尋歷史"""
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
        await asyncio.wait_for(db.commit(), timeout=5.0)
        await db.refresh(history)
        return history.id
    except asyncio.TimeoutError:
        logger.warning("搜尋歷史寫入超時 (>5s)，跳過")
        try:
            await db.rollback()
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"搜尋歷史寫入失敗: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
    return None
