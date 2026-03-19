"""
AI 實體提取服務

使用 Groq/Ollama LLM 從公文文本中提取命名實體和關係，
豐富知識圖譜的節點和邊。

Version: 1.0.0
Created: 2026-02-24
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.extended.models import OfficialDocument, DocumentEntity, EntityRelation
from app.services.ai.entity_extraction_helpers import (
    VALID_ENTITY_TYPES,
    MIN_CONFIDENCE,
    _PRONOUN_ENTITY_BLACKLIST,
    _extract_json_from_text,
    _normalize_text_nfkc,
    _is_garbled_text,
    _has_corruption_signs,
    _normalize_entity_spacing,
    _is_boilerplate_phrase,
    _validate_entities,
    _validate_relations,
    _parse_extraction_response,
)

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """Output ONLY valid JSON. No markdown, no explanation, no bullet points.

Entity types: org, person, project, location, date
Relation types: issues, receives, manages, located_in, belongs_to, related_to, approves, inspects, deadline

Output this exact JSON structure:
{"entities":[{"name":"實體名","type":"org","confidence":0.9,"context":"出處句"}],"relations":[{"source":"來源","source_type":"org","target":"目標","target_type":"project","relation":"manages","label":"承辦","confidence":0.9}]}

CRITICAL extraction priorities:
1. **project** (工程/案件名稱): Extract FULL official project names (e.g. "桃園區○○路段道路改善工程"). This is the MOST important entity type.
2. **location** (地點): Extract specific addresses, road names, districts, landmarks (e.g. "桃園區中山路", "龍潭區"). NOT generic terms like "工地" or "現場".
3. **org** (機關/公司): Extract full official names (e.g. "桃園市政府工務局"). NOT pronouns like "本府", "貴局".
4. **person** (人名): Only extract real person names, not titles or roles.

DO NOT extract:
- Pronouns/generic terms: 本府, 貴局, 本公司, 承辦人
- Boilerplate phrases: 檢送..., 函送..., 敬請查照
- Document numbers as entities
- Monetary amounts

Rules: extract only explicitly mentioned entities, use full official names, confidence 0.0-1.0.
- 同一個名稱只能有一個最適合的類型（例如「桃園市」應為 location 而非 org）

**CRITICAL OUTPUT FORMAT**:
- Output ONLY valid JSON, no markdown, no explanation.
- Do NOT wrap in ```json``` code blocks.
- Expected format:
{"entities": [{"name": "...", "type": "org|person|project|location|date", "confidence": 0.9}], "relations": [{"source": "...", "target": "...", "relation_type": "...", "confidence": 0.8}]}
IMPORTANT: Your entire response must be parseable by json.loads(). No other text."""


def _build_extraction_text(doc: OfficialDocument) -> str:
    """組合公文文本供提取"""
    parts = []
    if doc.subject:
        parts.append(f"主旨：{doc.subject}")
    if doc.doc_number:
        parts.append(f"文號：{doc.doc_number}")
    if doc.sender:
        parts.append(f"發文單位：{doc.sender}")
    if doc.receiver:
        parts.append(f"受文單位：{doc.receiver}")
    if doc.category:
        parts.append(f"分類：{doc.category}")
    if doc.doc_type:
        parts.append(f"類型：{doc.doc_type}")
    if hasattr(doc, "content") and doc.content:
        # 截斷超長內容
        content = doc.content[:2000] if len(doc.content) > 2000 else doc.content
        parts.append(f"內容：{content}")
    if hasattr(doc, "notes") and doc.notes:
        parts.append(f"備註：{doc.notes[:500]}")
    return "\n".join(parts)


async def get_extracted_document_ids(db: AsyncSession) -> set:
    """取得所有已提取實體的公文 ID（單次查詢，避免 N+1）

    批次處理時可先呼叫此函式取得已完成的 ID 集合，
    再用 ``doc_id in extracted_ids`` 快速跳過，
    避免對每筆公文各發一次 COUNT 查詢。

    Args:
        db: 資料庫 session

    Returns:
        已存在 DocumentEntity 記錄的 document_id 集合
    """
    result = await db.execute(
        select(func.distinct(DocumentEntity.document_id))
    )
    return {row[0] for row in result.all()}


async def extract_entities_for_document(
    db: AsyncSession,
    doc_id: int,
    force: bool = False,
    commit: bool = False,
) -> Dict:
    """
    對單筆公文執行實體提取

    Args:
        db: 資料庫 session
        doc_id: 公文 ID
        force: 是否強制重新提取（覆蓋既有結果）
        commit: 是否在完成後自動 commit（端點呼叫時為 True）

    Returns:
        {"entities_count": int, "relations_count": int, "skipped": bool}
    """
    # 取得公文
    result = await db.execute(
        select(OfficialDocument).where(OfficialDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return {"entities_count": 0, "relations_count": 0, "skipped": True, "reason": "公文不存在"}

    # 檢查是否已提取
    if not force:
        existing = await db.execute(
            select(func.count(DocumentEntity.id))
            .where(DocumentEntity.document_id == doc_id)
        )
        if (existing.scalar() or 0) > 0:
            return {"entities_count": 0, "relations_count": 0, "skipped": True, "reason": "已有提取結果"}

    # 組合文本
    text = _build_extraction_text(doc)
    if not text.strip():
        return {"entities_count": 0, "relations_count": 0, "skipped": True, "reason": "無可提取文本"}

    # 呼叫 LLM
    connector = get_ai_connector()
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract entities and relations from this document. Reply with JSON only.\n\n{text}"},
    ]

    try:
        raw_response = await connector.chat_completion(
            messages=messages,
            temperature=0.1,  # 低溫度確保結構化輸出
            max_tokens=2048,
            prefer_local=True,  # NER 使用 Ollama-first（本地無限量）
            task_type="ner",
            response_format={"type": "json_object"},  # Ollama format=json 強制 JSON 輸出
        )
    except Exception as e:
        logger.error(f"公文 #{doc_id} 實體提取 LLM 呼叫失敗: {e}")
        return {"entities_count": 0, "relations_count": 0, "skipped": False, "error": str(e)}

    # 解析結果
    entities, relations = _parse_extraction_response(raw_response)

    # 若 force 模式，先刪除舊資料
    if force:
        await db.execute(
            delete(EntityRelation).where(EntityRelation.document_id == doc_id)
        )
        await db.execute(
            delete(DocumentEntity).where(DocumentEntity.document_id == doc_id)
        )

    # 寫入 entities
    for e in entities:
        db.add(DocumentEntity(
            document_id=doc_id,
            entity_name=e["name"],
            entity_type=e["type"],
            confidence=e["confidence"],
            context=e["context"],
        ))

    # 寫入 relations
    for r in relations:
        db.add(EntityRelation(
            source_entity_name=r["source"],
            source_entity_type=r["source_type"],
            target_entity_name=r["target"],
            target_entity_type=r["target_type"],
            relation_type=r["relation"],
            relation_label=r["label"],
            document_id=doc_id,
            confidence=r["confidence"],
        ))

    await db.flush()
    if commit:
        await db.commit()

    logger.info(
        f"公文 #{doc_id} 實體提取完成: {len(entities)} 實體, {len(relations)} 關係"
    )

    return {
        "entities_count": len(entities),
        "relations_count": len(relations),
        "skipped": False,
    }


async def get_pending_extraction_count(db: AsyncSession, force: bool = False) -> int:
    """取得待實體提取的公文數量"""
    if force:
        count_result = await db.execute(
            select(func.count(OfficialDocument.id))
        )
    else:
        extracted_subq = (
            select(func.distinct(DocumentEntity.document_id))
            .scalar_subquery()
        )
        count_result = await db.execute(
            select(func.count(OfficialDocument.id))
            .where(OfficialDocument.id.notin_(extracted_subq))
        )
    return count_result.scalar() or 0


async def get_entity_stats(db: AsyncSession) -> Dict:
    """取得實體提取覆蓋率統計"""
    # 總公文數
    total_result = await db.execute(
        select(func.count(OfficialDocument.id))
    )
    total = total_result.scalar() or 0

    # 已提取實體的公文數（distinct document_id）
    extracted_result = await db.execute(
        select(func.count(func.distinct(DocumentEntity.document_id)))
    )
    extracted = extracted_result.scalar() or 0

    # 總實體數
    entity_count_result = await db.execute(
        select(func.count(DocumentEntity.id))
    )
    entity_count = entity_count_result.scalar() or 0

    # 總關係數
    relation_count_result = await db.execute(
        select(func.count(EntityRelation.id))
    )
    relation_count = relation_count_result.scalar() or 0

    # 各類型實體統計
    type_stats_result = await db.execute(
        select(DocumentEntity.entity_type, func.count(DocumentEntity.id))
        .group_by(DocumentEntity.entity_type)
    )
    type_stats = {row[0]: row[1] for row in type_stats_result.all()}

    coverage = (extracted / total * 100) if total > 0 else 0.0

    return {
        "total_documents": total,
        "extracted_documents": extracted,
        "without_extraction": total - extracted,
        "coverage_percent": round(coverage, 2),
        "total_entities": entity_count,
        "total_relations": relation_count,
        "entity_type_stats": type_stats,
    }
