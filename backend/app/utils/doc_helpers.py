# -*- coding: utf-8 -*-
"""
公文方向判定工具 (Single Source of Truth)

規則：公文字號以「乾坤」開頭 → 公司發文 (company_outgoing)
     其他 → 機關來函 (agency_incoming)

前端對應：frontend/src/components/taoyuan/workflow/chainUtils.ts → isOutgoingDocNumber()
"""
from typing import Optional

OUTGOING_DOC_PREFIX = "乾坤"


def is_outgoing_doc_number(doc_number: Optional[str]) -> bool:
    """判斷公文字號是否為公司發文（「乾坤」開頭）"""
    return bool(doc_number and doc_number.startswith(OUTGOING_DOC_PREFIX))
