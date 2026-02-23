"""
AI 實體提取服務

使用 Groq/Ollama LLM 從公文文本中提取命名實體和關係，
豐富知識圖譜的節點和邊。

Version: 1.0.0
Created: 2026-02-24
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.extended.models import OfficialDocument, DocumentEntity, EntityRelation

logger = logging.getLogger(__name__)

# ============================================================================
# 常數
# ============================================================================

VALID_ENTITY_TYPES = {"org", "person", "project", "location", "date", "topic"}
MIN_CONFIDENCE = 0.6  # 最低信心度門檻

EXTRACTION_SYSTEM_PROMPT = """你是一個專業的政府公文實體提取助手。你的任務是從公文資料中提取命名實體和它們之間的關係。

實體類型定義：
- org: 機關或組織名稱（如「桃園市政府工務局」「經濟部」「○○營造有限公司」）
- person: 人名（如「王○明」「陳處長」）
- project: 專案或工程名稱（如「○○道路改善工程」「污水下水道建設計畫」）
- location: 地點（如「桃園市觀音區」「中壢區○○路」）
- date: 重要日期或期限（如「115年3月31日」「本年度第2季」）
- topic: 主題或事項（如「施工許可」「工程驗收」「契約變更」）

關係類型範例：
- issues: 核發/發文
- receives: 受文/收文
- manages: 管理/承辦
- located_in: 位於
- belongs_to: 隸屬/所屬
- related_to: 相關
- approves: 核准
- inspects: 查驗/稽查
- deadline: 期限

回應格式（嚴格 JSON）：
{
  "entities": [
    {"name": "實體名稱", "type": "org", "confidence": 0.95, "context": "出現的上下文"}
  ],
  "relations": [
    {
      "source": "來源實體名稱", "source_type": "org",
      "target": "目標實體名稱", "target_type": "project",
      "relation": "manages", "label": "承辦",
      "confidence": 0.9
    }
  ]
}

注意事項：
1. 只提取明確出現在文本中的實體，不要推測
2. 機關名稱保留完整全稱，不縮寫
3. confidence 範圍 0.0~1.0，根據提取的確定程度評分
4. 一個公文通常可提取 3~15 個實體、1~8 個關係
5. 不要重複提取相同的實體"""


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


def _parse_extraction_response(raw: str) -> Tuple[List[Dict], List[Dict]]:
    """解析 LLM 回傳的 JSON"""
    # 嘗試從 markdown code block 中提取
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        logger.warning(f"實體提取 JSON 解析失敗: {text[:200]}")
        return [], []

    entities = data.get("entities", [])
    relations = data.get("relations", [])

    # 驗證 + 過濾
    valid_entities = []
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
        valid_entities.append({
            "name": name,
            "type": etype,
            "confidence": conf,
            "context": e.get("context", "")[:500],
        })

    valid_relations = []
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
        valid_relations.append({
            "source": src,
            "source_type": r.get("source_type", "org"),
            "target": tgt,
            "target_type": r.get("target_type", "org"),
            "relation": rel,
            "label": r.get("label", rel),
            "confidence": conf,
        })

    return valid_entities, valid_relations


async def extract_entities_for_document(
    db: AsyncSession,
    doc_id: int,
    force: bool = False,
) -> Dict:
    """
    對單筆公文執行實體提取

    Args:
        db: 資料庫 session
        doc_id: 公文 ID
        force: 是否強制重新提取（覆蓋既有結果）

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
        {"role": "user", "content": f"請從以下公文中提取實體和關係：\n\n{text}"},
    ]

    try:
        raw_response = await connector.chat_completion(
            messages=messages,
            temperature=0.1,  # 低溫度確保結構化輸出
            max_tokens=2048,
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

    logger.info(
        f"公文 #{doc_id} 實體提取完成: {len(entities)} 實體, {len(relations)} 關係"
    )

    return {
        "entities_count": len(entities),
        "relations_count": len(relations),
        "skipped": False,
    }


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
