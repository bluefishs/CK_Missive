"""
實體提取驗證/解析輔助模組 — 從 entity_extraction_service.py 提取

包含 JSON 解析、實體驗證、關係驗證等純函數，
供 entity_extraction_service.py 及其他模組使用。

Extracted from entity_extraction_service.py v1.0.0
Version: 1.0.0
"""

import json
import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from app.services.ai.core.ai_config import get_ai_config

logger = logging.getLogger(__name__)

# ============================================================================
# 常數
# ============================================================================

# NER 提取支援的實體類型（僅限公文 NER 流程）
# 注意：Code Graph 實體 (py_module, py_class, py_function, db_table) 有獨立入庫路徑
#       (code_graph_service.py)，不經過 NER 驗證，因此不列入此處
VALID_ENTITY_TYPES = {
    "org", "person", "project", "location", "date",
}
# MIN_CONFIDENCE 改由 AIConfig 統一管理，此處保留 fallback
MIN_CONFIDENCE = get_ai_config().ner_min_confidence


# ============================================================================
# 文本正規化工具
# ============================================================================

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


def _has_corruption_signs(text: str) -> bool:
    """偵測 mojibake / 控制字元 / 亂碼模式

    - U+FFFD 替換字元
    - 不可見控制字元 (U+0000-U+001F, U+007F-U+009F，排除 \\t\\n\\r)
    - 連續 3+ 非 CJK/ASCII 罕用 Unicode 區段字元（Mojibake 典型特徵）
    - 同一字元重複 4+ 次（LLM 幻覺產物）
    """
    # U+FFFD 替換字元 / 遮蔽符號
    if '\ufffd' in text or '■' in text or '□' in text:
        return True
    # 控制字元（排除 tab/newline/carriage return）
    for ch in text:
        cp = ord(ch)
        if (0x00 <= cp <= 0x08) or (0x0B <= cp <= 0x0C) or (0x0E <= cp <= 0x1F) or (0x7F <= cp <= 0x9F):
            return True
    # 同一字元重複 4+ 次（如「哈哈哈哈」「aaaa」）
    if re.search(r'(.)\1{3,}', text):
        return True
    # 連續 3+ 個罕用 Unicode 字元（非 CJK、非 ASCII、非常用標點）
    # 常見 mojibake 會產生 Latin Extended / CJK Compatibility 混合序列
    unusual_count = 0
    for ch in text:
        cp = ord(ch)
        is_common = (
            (0x20 <= cp <= 0x7E)        # ASCII printable
            or (0x4E00 <= cp <= 0x9FFF)  # CJK Unified
            or (0x3400 <= cp <= 0x4DBF)  # CJK Extension A
            or (0x3000 <= cp <= 0x303F)  # CJK Symbols
            or (0xFF00 <= cp <= 0xFFEF)  # Fullwidth Forms
            or (0x2000 <= cp <= 0x206F)  # General Punctuation
            or cp in (0x3001, 0x3002, 0xFF0C, 0xFF0E, 0x300A, 0x300B)  # 常用中文標點
        )
        if not is_common:
            unusual_count += 1
            if unusual_count >= 3:
                return True
        else:
            unusual_count = 0
    return False


def _normalize_entity_spacing(name: str) -> str:
    """正規化實體名稱中的空白與標點

    - 全形標點 → 移除（括號、引號除外）
    - 連續空白 → 單一空白
    - 首尾空白 → 移除
    """
    # 移除無意義全形標點（保留括號 ()（）、引號 「」 等配對符號）
    name = re.sub(r'[，。、；：！？～…‧]', '', name)
    # 連續空白歸一
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


# 公文套語前綴 — 以這些詞開頭的實體名稱通常是公文格式用語，非實質實體
_BOILERPLATE_PREFIXES = (
    '檢送', '函送', '檢附', '檢陳', '函復', '函覆', '函請',
    '敬請', '請查照', '查照', '請照辦', '惠請',
    '敬陳', '敬會', '敬悉', '奉核', '奉悉',
    '依據', '依照', '茲有', '茲將', '茲因', '茲檢',
    '有關', '關於', '為辦理', '為利', '為配合',
    '復貴', '復請',
)


def _is_boilerplate_phrase(name: str) -> bool:
    """檢測公文套語：以常見公文格式用語開頭且長度較長的實體名稱"""
    if len(name) <= 4:
        return False  # 短名稱不判定（避免誤殺「依據」作為 topic 等）
    return any(name.startswith(prefix) for prefix in _BOILERPLATE_PREFIXES)


# 代名詞/泛稱黑名單 — 從 core/name_utils 集中管理
from app.services.ai.core.name_utils import PRONOUN_ENTITY_BLACKLIST

# 向後相容別名
_PRONOUN_ENTITY_BLACKLIST = PRONOUN_ENTITY_BLACKLIST

# 公文號正則 — 符合此模式的是公文編號，不應列為實體
# 覆蓋：桃工用字第1140045160號、第1140045160號、1140045160號 等
_DOC_NUMBER_RE = re.compile(
    r'(?:^[A-Z0-9]*[字函令書]第?\d{5,}號?$|^\d{7,}號$|字第\d{5,}號)'
)

# 統一編號前綴正則（8-10 碼英數 + 空格 + 名稱）
_TAX_ID_PREFIX_RE = re.compile(r'^[A-Z0-9]{8,10}\s+')


# ============================================================================
# JSON 提取
# ============================================================================

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


# ============================================================================
# 驗證函數
# ============================================================================

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

        # 空白/標點正規化
        name = _normalize_entity_spacing(name)
        if not name:
            continue

        if _is_garbled_text(name):
            logger.warning(f"實體名稱疑似亂碼，已過濾: '{name}'")
            continue

        # Mojibake / 控制字元偵測
        if _has_corruption_signs(name):
            logger.warning(f"實體名稱含損壞字元，已過濾: '{name}'")
            continue

        # 代名詞黑名單過濾（精確匹配）
        if name in _PRONOUN_ENTITY_BLACKLIST:
            logger.debug(f"代名詞/套語實體已過濾: '{name}'")
            continue

        # 公文套語前綴過濾（「檢送…」「函復…」等開頭的實體名稱）
        if _is_boilerplate_phrase(name):
            logger.debug(f"公文套語實體已過濾: '{name}'")
            continue

        # location 降級：建築物內部位置（會議室、研討室等）對圖譜關聯性低，過濾掉
        # 1. 含「N樓...室/廳/間」模式（7樓研討室、2樓會議室）
        # 2. 直接含「會議室」「研討室」「辦公室」等室內場所關鍵字
        if etype == 'location' and (
            re.search(r'(?:[B]?\d+[F樓]|地下\d)', name) and re.search(r'[室廳間]', name)
            or re.search(r'(?:會議室|研討室|辦公室|會議廳|簡報室|視聽室|教室|禮堂)', name)
        ):
            logger.debug(f"建築內部位置實體已過濾: '{name}'")
            continue

        # 過短實體過濾（<=1 字元，人名除外）
        if len(name) <= 1 and etype != 'person':
            continue

        # 純代碼字串（機關代碼等，非實體名稱）
        if re.match(r'^[A-Z0-9]{6,}$', name, re.IGNORECASE):
            logger.debug(f"純代碼字串已過濾: '{name}'")
            continue

        # 統一編號前綴剝離（EB50819619 乾坤測繪 → 乾坤測繪）
        stripped = _TAX_ID_PREFIX_RE.sub('', name)
        if stripped and stripped != name:
            logger.debug(f"統一編號前綴剝離: '{name}' → '{stripped}'")
            name = stripped

        # 公文號識別：任何類型若符合公文號模式 → 跳過（公文號不是實體）
        if _DOC_NUMBER_RE.search(name):
            logger.debug(f"公文號誤分類為 {etype}，已跳過: '{name}'")
            continue

        # 金額實體過濾（297萬元整、99萬元整等）
        if re.match(r'^[\d,]+萬?元', name):
            continue

        # person 敬稱後綴剝離（「君」「先生」「小姐」「女士」「代表」）
        if etype == 'person':
            name = re.sub(r'(君|先生|小姐|女士|代表)$', '', name)
            if len(name) <= 1:  # 剝離後過短
                continue

        # project 類型品質過濾
        if etype == 'project':
            # 純專案代碼（如 PULI-11502）→ 不是有效名稱
            if re.match(r'^[A-Z]+-?\d+$', name, re.IGNORECASE):
                logger.debug(f"專案代碼非名稱，已跳過: '{name}'")
                continue
            # 會議/課程/活動 → 不是工程專案
            if re.search(r'(會議|課程|茶會|聯誼|工作會報|說明會)$', name):
                logger.debug(f"會議/活動誤分類為 project，已跳過: '{name}'")
                continue
            # 文件名稱（計畫書/修正版/工作計畫）→ 不是專案
            if re.search(r'(計畫書|修正版|修正本|工作計畫|報告書)[\(（]?[^)）]*[\)）]?$', name):
                logger.debug(f"文件名稱誤分類為 project，已跳過: '{name}'")
                continue

        # date 類型降級：日期實體對圖譜關聯性低，僅保留高信心度的
        if etype == 'date':
            conf = float(e.get("confidence", 0.8))
            if conf < 0.9:  # date 需 >= 0.9 才入圖
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
