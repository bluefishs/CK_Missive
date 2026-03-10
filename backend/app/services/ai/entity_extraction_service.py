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
import unicodedata
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

# NER 提取支援的實體類型（僅限公文 NER 流程）
# 注意：Code Graph 實體 (py_module, py_class, py_function, db_table) 有獨立入庫路徑
#       (code_graph_service.py)，不經過 NER 驗證，因此不列入此處
VALID_ENTITY_TYPES = {
    "org", "person", "project", "location", "date", "topic",
}
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


def _normalize_text_nfkc(text: str) -> str:
    """NFKC 正規化：康熙部首→標準 CJK、全形→半形、相容字→標準字"""
    return unicodedata.normalize('NFKC', text).strip()


# 簡體字常見字集（繁體系統不應出現）
_SIMPLIFIED_CHARS = set(
    '义组个体与专业严丰临为举么义乐习书买乱争于产亲亿从仅仓付价份众优伤传伦'
    '估体余佣侠侣侦侧侨俩俭债倾偶偿储儿兑党兰关兴养兹冈冲决况冻净凉减凤'
    '几凭击创刘则刚剂剑剧劝办务劳势勋勤区医华协单卖卢卫却厂厅历厉压厌县叁'
    '叶号叹吕吨呐员呜咏咙响哑哟唤啬啸喷嘘嘤嚣团园围坏坚坛坝垄垒垦垫堕塑'
    '壮声壳处备复够头夺奋奖奥妆妇妈姗姜娄娱婴学宁宝实宠审宪宫宽宾寝对寻导'
    '层岁岂岗岛岭岳峡峰崭巩币帅师帐帜帧帮带帻幂广庆庐庄库应废开异弃张弥弹'
    '归录彦彻径徕志忆忧惊惧惩惫惬惭惮惯愤愿慑慨懒戏户执扩扫扬扰抚抢护报担'
    '拟拥择挡挣挤挥损捞据掷搁搜摄摆摇撑撰擞攒敌斋断无旧时旷昼显晓晖暂暴术'
)


def _is_garbled_text(text: str) -> bool:
    """偵測亂碼文字：簡體字混入繁體系統、罕用字元過多、隱私遮蔽符號"""
    if not text:
        return True
    # 含隱私遮蔽符號（○、〇等）→ 不應作為正規化實體
    if '○' in text or '〇' in text:
        return True
    simplified_count = sum(1 for c in text if c in _SIMPLIFIED_CHARS)
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 超過 30% 的 CJK 字元是簡體 → 判定為亂碼
    if cjk_count > 0 and simplified_count / cjk_count > 0.3:
        return True
    return False


# 代名詞/泛稱黑名單 — 這些不是有效的命名實體
_PRONOUN_ENTITY_BLACKLIST = {
    '貴公司', '本公司', '該公司', '貴所', '本所', '該所',
    '貴局', '本局', '該局', '貴府', '本府', '該府',
    '貴會', '本會', '該會', '貴處', '本處', '該處',
    '貴署', '本署', '該署', '貴部', '本部', '該部',
    '貴院', '本院', '該院', '貴市', '本市', '該市',
    '貴機關', '本機關', '該機關', '貴單位', '本單位', '該單位',
    '台端', '臺端',
}

# 公文號正則 — 符合此模式的是公文編號，不應列為 date/topic
_DOC_NUMBER_RE = re.compile(
    r'^(?:[A-Z0-9]*[字函令書]第?\d{5,}號?$|^\d{7,}號$)'
)

# 統一編號前綴正則（8-10 碼英數 + 空格 + 名稱）
_TAX_ID_PREFIX_RE = re.compile(r'^[A-Z0-9]{8,10}\s+')


def _validate_entities(entities: List) -> List[Dict]:
    """驗證並過濾實體列表"""
    valid = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        name = _normalize_text_nfkc(e.get("name", ""))
        etype = e.get("type", "").strip()
        if not name or etype not in VALID_ENTITY_TYPES:
            continue
        if _is_garbled_text(name):
            logger.warning(f"實體名稱疑似亂碼，已過濾: '{name}'")
            continue

        # 代名詞黑名單過濾
        if name in _PRONOUN_ENTITY_BLACKLIST:
            logger.debug(f"代名詞實體已過濾: '{name}'")
            continue

        # 過短實體過濾（<=1 字元，人名除外）
        if len(name) <= 1 and etype != 'person':
            continue

        # 統一編號前綴剝離（EB50819619 乾坤測繪 → 乾坤測繪）
        stripped = _TAX_ID_PREFIX_RE.sub('', name)
        if stripped and stripped != name:
            logger.debug(f"統一編號前綴剝離: '{name}' → '{stripped}'")
            name = stripped

        # 公文號識別：date/topic 但符合公文號模式 → 跳過（公文號不應為圖譜實體）
        if etype in ('date', 'topic') and _DOC_NUMBER_RE.match(name):
            logger.debug(f"公文號誤分類為 {etype}，已跳過: '{name}'")
            continue

        # 金額實體過濾（297萬元整、99萬元整等）
        if re.match(r'^[\d,]+萬?元', name):
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
        src = _normalize_text_nfkc(r.get("source", ""))
        tgt = _normalize_text_nfkc(r.get("target", ""))
        rel = r.get("relation", "").strip()
        if not src or not tgt or not rel:
            continue
        if _is_garbled_text(src) or _is_garbled_text(tgt):
            logger.warning(f"關係實體疑似亂碼，已過濾: '{src}' → '{tgt}'")
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
