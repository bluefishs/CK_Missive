"""
AI 實體提取服務

使用 Groq/Ollama LLM 從公文文本中提取命名實體和關係，
豐富知識圖譜的節點和邊。

Version: 1.0.0
Created: 2026-02-24
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.extended.models import OfficialDocument, DocumentEntity, EntityRelation
from app.services.ai.ai_config import get_ai_config

logger = logging.getLogger(__name__)

# ============================================================================
# 常數
# ============================================================================

VALID_ENTITY_TYPES = {"org", "person", "project", "location", "date", "topic"}
# MIN_CONFIDENCE 改由 AIConfig 統一管理，此處保留 fallback
MIN_CONFIDENCE = get_ai_config().ner_min_confidence

EXTRACTION_SYSTEM_PROMPT = """Output ONLY valid JSON. No markdown, no explanation, no bullet points.

Entity types: org, person, project, location, date, topic
Relation types: issues, receives, manages, located_in, belongs_to, related_to, approves, inspects, deadline

Output this exact JSON structure:
{"entities":[{"name":"實體名","type":"org","confidence":0.9,"context":"出處句"}],"relations":[{"source":"來源","source_type":"org","target":"目標","target_type":"project","relation":"manages","label":"承辦","confidence":0.9}]}

Rules: extract only explicitly mentioned entities, use full official names, confidence 0.0-1.0.
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


def _extract_json_from_text(text: str) -> Optional[Dict]:
    """多策略 JSON 提取：純 JSON → code block → 最大 JSON 物件 regex"""
    cleaned = text.strip()

    # 策略 1: 直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 策略 2: markdown code block
    if "```json" in cleaned:
        block = cleaned.split("```json", 1)[1].split("```", 1)[0]
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            pass
    elif "```" in cleaned:
        block = cleaned.split("```", 1)[1].split("```", 1)[0]
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            pass

    # 策略 3: 尋找最大的 {...} JSON 物件
    # 使用 bracket 計數找到完整的 JSON 物件
    best_obj = None
    best_len = 0
    i = 0
    while i < len(cleaned):
        if cleaned[i] == '{':
            depth = 0
            start = i
            in_string = False
            escape_next = False
            for j in range(i, len(cleaned)):
                ch = cleaned[j]
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = cleaned[start:j+1]
                            try:
                                obj = json.loads(candidate)
                                if isinstance(obj, dict) and len(candidate) > best_len:
                                    best_obj = obj
                                    best_len = len(candidate)
                            except json.JSONDecodeError:
                                pass
                            break
            i = start + 1
        else:
            i += 1

    if best_obj and ("entities" in best_obj or "relations" in best_obj):
        return best_obj

    # 策略 4: 從散落的 JSON 物件中收集 entities
    entity_pattern = re.compile(
        r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"type"\s*:\s*"[^"]+"\s*'
        r'(?:,\s*"confidence"\s*:\s*[\d.]+)?'
        r'(?:,\s*"context"\s*:\s*"[^"]*")?\s*\}'
    )
    relation_pattern = re.compile(
        r'\{\s*"source"\s*:\s*"[^"]+"\s*,\s*"source_type"\s*:\s*"[^"]+"\s*'
        r',\s*"target"\s*:\s*"[^"]+"\s*,\s*"target_type"\s*:\s*"[^"]+"\s*'
        r',\s*"relation"\s*:\s*"[^"]+"\s*'
        r'(?:,\s*"label"\s*:\s*"[^"]*")?'
        r'(?:,\s*"confidence"\s*:\s*[\d.]+)?\s*\}'
    )

    entities = []
    for m in entity_pattern.finditer(cleaned):
        try:
            entities.append(json.loads(m.group()))
        except json.JSONDecodeError:
            pass

    relations = []
    for m in relation_pattern.finditer(cleaned):
        try:
            relations.append(json.loads(m.group()))
        except json.JSONDecodeError:
            pass

    if entities or relations:
        logger.info(f"Fallback regex 解析成功: {len(entities)} entities, {len(relations)} relations")
        return {"entities": entities, "relations": relations}

    return None


def _validate_entities(entities: List) -> List[Dict]:
    """驗證並過濾實體列表"""
    valid = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        name = e.get("name", "").strip()
        etype = e.get("type", "").strip()
        if not name or etype not in VALID_ENTITY_TYPES:
            continue
        conf = float(e.get("confidence", 0.8))
        if conf < MIN_CONFIDENCE:
            continue
        valid.append({
            "name": name,
            "type": etype,
            "confidence": conf,
            "context": e.get("context", "")[:500],
        })
    return valid


def _validate_relations(relations: List) -> List[Dict]:
    """驗證並過濾關係列表"""
    valid = []
    for r in relations:
        if not isinstance(r, dict):
            continue
        src = r.get("source", "").strip()
        tgt = r.get("target", "").strip()
        rel = r.get("relation", "").strip()
        if not src or not tgt or not rel:
            continue
        conf = float(r.get("confidence", 0.8))
        if conf < MIN_CONFIDENCE:
            continue
        valid.append({
            "source": src,
            "source_type": r.get("source_type", "org"),
            "target": tgt,
            "target_type": r.get("target_type", "org"),
            "relation": rel,
            "label": r.get("label", rel),
            "confidence": conf,
        })
    return valid


def _parse_extraction_response(raw: str) -> Tuple[List[Dict], List[Dict]]:
    """解析 LLM 回傳的 JSON（含多層 fallback）"""
    data = _extract_json_from_text(raw)
    if data is None:
        logger.warning(f"實體提取所有解析策略均失敗: {raw[:300]}")
        return [], []

    entities = data.get("entities", [])
    relations = data.get("relations", [])

    return _validate_entities(entities), _validate_relations(relations)


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
