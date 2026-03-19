# -*- coding: utf-8 -*-
"""
Excel 匯入驗證器

從 excel_import_service.py 提取的驗證與資料準備邏輯。

函數：
- validate_preview_row: 驗證預覽列資料
- prepare_document_data: 準備公文匯入資料（含智慧關聯匹配）
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def validate_preview_row(
    row_num: int,
    row_data: Dict,
    doc_numbers_seen: set,
    existing_doc_numbers: set,
    result: Dict,
    validators: Any,
    required_fields: list,
) -> Dict:
    """
    驗證預覽列

    Args:
        row_num: 行號
        row_data: 該行資料
        doc_numbers_seen: 已出現的公文字號集合（會被修改）
        existing_doc_numbers: 資料庫中已存在的公文字號集合
        result: 整體預覽結果字典（會被修改）
        validators: 驗證器物件（需有 VALID_CATEGORIES, VALID_DOC_TYPES 屬性）
        required_fields: 必填欄位列表

    Returns:
        驗證狀態字典
    """
    validation_status = {
        "row": row_num,
        "data": row_data,
        "status": "valid",
        "issues": [],
        "action": "insert"
    }

    # 檢查公文ID判斷新增/更新
    doc_id = row_data.get('公文ID')
    if doc_id and str(doc_id).strip():
        validation_status["action"] = "update"
        result["validation"]["will_update"] += 1
    else:
        result["validation"]["will_insert"] += 1

    # 檢查類別
    category = str(row_data.get('類別', '')).strip()
    if category and category not in validators.VALID_CATEGORIES:
        validation_status["issues"].append(f"無效類別: {category}")
        result["validation"]["invalid_categories"].append(row_num)

    # 檢查公文類型
    doc_type = str(row_data.get('公文類型', '')).strip()
    if doc_type and doc_type not in validators.VALID_DOC_TYPES:
        validation_status["issues"].append(f"無效公文類型: {doc_type}")
        result["validation"]["invalid_doc_types"].append(row_num)

    # 檢查重複公文字號
    doc_number = str(row_data.get('公文字號', '')).strip()
    if doc_number:
        if doc_number in doc_numbers_seen:
            validation_status["issues"].append("檔案內重複公文字號")
            result["validation"]["duplicate_doc_numbers"].append(row_num)
        doc_numbers_seen.add(doc_number)

        if doc_number in existing_doc_numbers and validation_status["action"] == "insert":
            validation_status["issues"].append("資料庫已存在此公文字號")
            result["validation"]["existing_in_db"].append(row_num)

    # 缺少必填欄位
    for field in required_fields:
        value = row_data.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            validation_status["issues"].append(f"缺少必填欄位: {field}")
            validation_status["status"] = "warning"

    if validation_status["issues"]:
        validation_status["status"] = "warning"

    return validation_status


async def prepare_document_data(
    row_data: Dict[str, Any],
    category: str,
    doc_type: str,
    clean_string,
    match_agency,
    match_project,
    parse_date,
) -> Dict[str, Any]:
    """
    準備公文資料

    Args:
        row_data: Excel 列資料
        category: 已驗證的類別
        doc_type: 已驗證的公文類型
        clean_string: 字串清理函數 (from ImportBaseService)
        match_agency: 機關匹配函數 (async, from ImportBaseService)
        match_project: 專案匹配函數 (async, from ImportBaseService)
        parse_date: 日期解析函數 (from ImportBaseService)

    Returns:
        公文資料字典
    """
    sender_name = clean_string(row_data.get('發文單位'))
    receiver_name = clean_string(row_data.get('受文單位'))
    contract_name = clean_string(row_data.get('承攬案件'))

    # 智慧關聯匹配
    sender_agency_id = await match_agency(sender_name) if sender_name else None
    receiver_agency_id = await match_agency(receiver_name) if receiver_name else None
    contract_project_id = await match_project(contract_name) if contract_name else None

    # 正規化收發文單位
    from app.services.receiver_normalizer import (
        normalize_unit, cc_list_to_json, infer_agency_from_doc_number,
    )
    s_norm = normalize_unit(sender_name)
    r_norm = normalize_unit(receiver_name)

    # 根據公文字號前綴修正發文機關（如「府工用字第」→桃園市政府工務局）
    doc_number = clean_string(row_data.get('公文字號')) or ''
    inferred_agency = infer_agency_from_doc_number(doc_number)
    if inferred_agency and s_norm.primary != inferred_agency:
        s_norm = normalize_unit(inferred_agency)  # 重新正規化
        corrected_id = await match_agency(inferred_agency)
        if corrected_id:
            sender_agency_id = corrected_id

    data = {
        'category': category,
        'doc_type': doc_type or '函',
        'doc_number': doc_number,
        'subject': clean_string(row_data.get('主旨')) or '',
        'content': clean_string(row_data.get('說明')),
        'sender': sender_name,
        'receiver': receiver_name,
        'normalized_sender': s_norm.primary or None,
        'normalized_receiver': r_norm.primary or None,
        'cc_receivers': cc_list_to_json(r_norm.cc_list),
        'sender_agency_id': sender_agency_id,
        'receiver_agency_id': receiver_agency_id,
        'contract_project_id': contract_project_id,
        'delivery_method': clean_string(row_data.get('發文形式')) or '紙本郵寄',
        'notes': clean_string(row_data.get('備註')),
        'ck_note': clean_string(row_data.get('簡要說明(乾坤備註)')),
        'status': clean_string(row_data.get('狀態')) or 'active',
    }

    # 處理日期欄位
    data['doc_date'] = parse_date(row_data.get('公文日期'))
    data['receive_date'] = parse_date(row_data.get('收文日期'))
    data['send_date'] = parse_date(row_data.get('發文日期'))

    return data
