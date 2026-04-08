# -*- coding: utf-8 -*-
"""
ERP Graph 共用資料類別

ErpEntity / ErpRelation — ERP 圖譜入圖的中間表示。
與 Code Graph 同模式：定義 entity_type + relation_type 常數集合。

Version: 1.0.0
Created: 2026-04-08
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Set


@dataclass
class ErpEntity:
    """ERP 圖譜實體中間表示"""
    canonical_name: str
    entity_type: str  # erp_quotation | erp_invoice | erp_billing | erp_expense | erp_asset | erp_ledger
    description: Dict[str, Any] = field(default_factory=dict)
    external_id: str = ""  # case_code / invoice_number / asset_code


@dataclass
class ErpRelation:
    """ERP 圖譜關係中間表示"""
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relation_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Entity categories
# ---------------------------------------------------------------------------

ERP_ENTITY_TYPES: Set[str] = {
    "erp_quotation",     # 報價/案件
    "erp_invoice",       # 開票
    "erp_billing",       # 請款
    "erp_expense",       # 費用報銷
    "erp_asset",         # 資產
    "erp_ledger",        # 帳本科目
    "erp_vendor",        # 廠商 (應付)
    "erp_client",        # 委託單位 (應收)
}

ERP_ENTITY_CATEGORIES: Dict[str, Set[str]] = {
    "financial": {"erp_quotation", "erp_invoice", "erp_billing", "erp_expense", "erp_ledger"},
    "asset": {"erp_asset"},
    "party": {"erp_vendor", "erp_client"},
}

# ---------------------------------------------------------------------------
# Relation categories
# ---------------------------------------------------------------------------

ERP_RELATION_TYPES: Set[str] = {
    # 案件流程鏈
    "quoted_for",        # quotation → project (案件報價)
    "invoiced_from",     # invoice → quotation (開票來源)
    "billed_from",       # billing → quotation (請款來源)
    "paid_to",           # vendor_payable → vendor (付款對象)
    "received_from",     # client_receivable → client (收款來源)
    # 費用
    "expensed_for",      # expense → project (費用歸屬)
    "recorded_in",       # expense/invoice/billing → ledger (入帳)
    # 資產
    "asset_of",          # asset → project (資產歸屬)
    # 跨域橋接
    "case_link",         # ERP entity → PM case / tender (case_code 橋接)
    "doc_link",          # ERP entity → official_document (公文關聯)
    "supplies_to",       # vendor → quotation (供應關係)
}

ERP_RELATION_CATEGORIES: Dict[str, Set[str]] = {
    "flow": {"quoted_for", "invoiced_from", "billed_from", "recorded_in"},
    "party": {"paid_to", "received_from", "supplies_to"},
    "attribution": {"expensed_for", "asset_of"},
    "cross_domain": {"case_link", "doc_link"},
}
