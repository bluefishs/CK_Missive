"""
收發文單位正規化服務

將 documents.sender/receiver 欄位中的多種格式變體正規化：
- 去除統編前綴 (如 "EB50819619 乾坤測繪科技有限公司" → "乾坤測繪科技有限公司")
- 去除機關代碼括號 (如 "380110000G (桃園市政府工務局)" → "桃園市政府工務局")
- 拆分管道分隔的多受文者 (如 "A|B|C" → primary="A", cc=["B","C"])
- 處理換行符 (如 "EB50819619\\n乾坤測繪科技有限公司" → "乾坤測繪科技有限公司")
- 去除代表人後綴 (如 "乾坤測繪科技有限公司(張坤樹)" → "乾坤測繪科技有限公司")
- 去除協力廠商資訊 (如 "...（協力廠商:大有國際...）" → 主要公司名)

Version: 1.0.0
Created: 2026-03-13
"""

import json
import re
import unicodedata
from dataclasses import dataclass


@dataclass
class NormalizedResult:
    """正規化結果"""
    primary: str          # 主要單位名稱
    cc_list: list[str]    # 副本/附加受文單位
    tax_id: str | None    # 擷取的統編（如有）
    agency_code: str | None  # 擷取的機關代碼（如有）


# 統編前綴模式: "EB50819619 名稱" 或 "EB50819619\n名稱"
_TAX_ID_PREFIX = re.compile(r'^([A-Z]{1,3}\d{7,10})\s*[\s\n]\s*(.+)$', re.DOTALL)

# 機關代碼括號模式: "380110000G (桃園市政府工務局)" 或 "380110000G\n(名稱)"
_AGENCY_CODE_PAREN = re.compile(
    r'^([A-Z0-9]{8,20})\s*[\s\n]*[（(]\s*(.+?)\s*[）)]\s*$', re.DOTALL,
)

# 代表人後綴: "公司名(張坤樹)" — 注意不能匹配到 "(協力廠商:...)"
_REPRESENTATIVE_SUFFIX = re.compile(r'[（(]([^）)]{1,10})[）)]$')

# 協力/合作廠商資訊: "（協力廠商:大有國際...）" 或 "（合作廠商:...）"
_SUBCONTRACTOR_SUFFIX = re.compile(r'[（(](?:協力|合作)廠商[:：].+?[）)]$')

# 多受文者分隔符: 管道 "|", 分號 ";/；" (NFKC 正規化後為半形)
_MULTI_DELIMITER = re.compile(r'\s*[\|;]\s*')


def normalize_unit(raw: str | None) -> NormalizedResult:
    """
    正規化單一收/發文單位欄位。

    處理流程:
    1. 空值/空白 → 空結果
    2. 全形→半形正規化
    3. 拆分管道分隔的多受文者
    4. 對每個子項去除統編/機關代碼/代表人/協力廠商
    5. 第一個為 primary，其餘為 cc_list
    """
    if not raw or not raw.strip():
        return NormalizedResult(primary='', cc_list=[], tax_id=None, agency_code=None)

    # NFKC 正規化 + strip
    text = unicodedata.normalize('NFKC', raw).strip()

    # 拆分管道分隔的多受文者
    parts = _MULTI_DELIMITER.split(text)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return NormalizedResult(primary='', cc_list=[], tax_id=None, agency_code=None)

    # 正規化每個子項
    normalized_parts: list[str] = []
    first_tax_id: str | None = None
    first_agency_code: str | None = None

    for i, part in enumerate(parts):
        name, tax_id, agency_code = _normalize_single(part)
        if name:
            normalized_parts.append(name)
        if i == 0:
            first_tax_id = tax_id
            first_agency_code = agency_code

    if not normalized_parts:
        return NormalizedResult(primary='', cc_list=[], tax_id=None, agency_code=None)

    # 去重（同一單位可能重複出現）
    seen: set[str] = set()
    unique_parts: list[str] = []
    for p in normalized_parts:
        if p not in seen:
            seen.add(p)
            unique_parts.append(p)

    return NormalizedResult(
        primary=unique_parts[0],
        cc_list=unique_parts[1:],
        tax_id=first_tax_id,
        agency_code=first_agency_code,
    )


def _normalize_single(text: str) -> tuple[str, str | None, str | None]:
    """
    正規化單一單位名稱，回傳 (名稱, 統編, 機關代碼)。
    """
    text = text.strip()
    tax_id: str | None = None
    agency_code: str | None = None

    # 處理換行 → 空格
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text).strip()

    # 1. 統編前綴
    m = _TAX_ID_PREFIX.match(text)
    if m:
        tax_id = m.group(1)
        text = m.group(2).strip()

    # 2. 機關代碼括號
    m = _AGENCY_CODE_PAREN.match(text)
    if m:
        agency_code = m.group(1)
        text = m.group(2).strip()

    # 3. 協力廠商後綴（先於代表人，避免誤刪）
    text = _SUBCONTRACTOR_SUFFIX.sub('', text).strip()

    # 4. 代表人後綴（僅短名字，排除含 "廠商" "公司" 等）
    m = _REPRESENTATIVE_SUFFIX.search(text)
    if m:
        suffix_content = m.group(1)
        # 只移除看起來是人名的（不含「廠商」「公司」等關鍵字）
        if not any(kw in suffix_content for kw in ('廠商', '公司', '事務所', '工程')):
            text = text[:m.start()].strip()

    # 5. 純代表人名（如「張坤樹代表」）→ 無法正規化為機關，保留原值
    # 但標記為空以便上層服務決定是否用 is_self 公司替代

    return text, tax_id, agency_code


def cc_list_to_json(cc: list[str]) -> str | None:
    """將 cc_list 轉為 JSON 字串，空列表回傳 None"""
    if not cc:
        return None
    return json.dumps(cc, ensure_ascii=False)


# ============================================================================
# 文號前綴 → 實際發文機關名稱 對照表
# 用於修正 sender='桃園市政府' 但實際由工務局發文的情況
# ============================================================================
_DOC_PREFIX_TO_AGENCY: dict[str, str] = {
    '府工用字第': '桃園市政府工務局',
    '府工字第': '桃園市政府工務局',
    '桃工用字第': '桃園市政府工務局',
    '桃工採字第': '桃園市政府工務局',
}


def infer_agency_from_doc_number(doc_number: str | None) -> str | None:
    """
    根據公文字號前綴推斷實際發文機關。

    例如 '府工用字第1140331294號' → '桃園市政府工務局'
    找不到對照回傳 None。
    """
    if not doc_number:
        return None
    for prefix, agency_name in _DOC_PREFIX_TO_AGENCY.items():
        if doc_number.startswith(prefix):
            return agency_name
    return None
