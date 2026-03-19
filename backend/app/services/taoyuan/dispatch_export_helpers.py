"""
dispatch_export_helpers - 派工單匯出輔助函數

從 dispatch_export_service.py 拆分，提供公文配對演算法。

@version 1.0.0
@date 2026-03-19
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

from app.extended.models import TaoyuanWorkRecord
from app.utils.doc_helpers import is_outgoing_doc_number

logger = logging.getLogger(__name__)


def _fmt_date(value: Any) -> str:
    """Format a date/datetime to YYYY-MM-DD string."""
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    return str(value)


def pair_documents_for_dispatch(
    records: List[TaoyuanWorkRecord],
    doc_links: list,
) -> List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]:
    """3 階段公文配對演算法 (與前端 buildCorrespondenceMatrix 一致)

    Phase 1: parent_record_id chain pairing
    Phase 2: date proximity greedy pairing (assigned + unassigned)
    Phase 3: remaining standalone rows

    Args:
        records: 該派工單的作業紀錄列表
        doc_links: 該派工單的公文關聯列表

    Returns:
        List of (incoming_dict | None, outgoing_dict | None) tuples
    """
    # --- 分離作業紀錄中的來文/覆文 ---
    assigned_in: List[Dict[str, Any]] = []
    assigned_out: List[Dict[str, Any]] = []
    record_doc_ids: set = set()  # 已出現在 work records 的 document IDs

    for r in records:
        # Old format: incoming_doc / outgoing_doc
        if r.incoming_doc:
            doc = r.incoming_doc
            assigned_in.append({
                'record_id': r.id,
                'parent_record_id': getattr(r, 'parent_record_id', None),
                'doc_number': doc.doc_number or '',
                'doc_date': _fmt_date(doc.doc_date),
                'subject': r.description or (doc.subject or ''),
            })
            if doc.id:
                record_doc_ids.add(doc.id)
        if r.outgoing_doc:
            doc = r.outgoing_doc
            assigned_out.append({
                'record_id': r.id,
                'parent_record_id': getattr(r, 'parent_record_id', None),
                'doc_number': doc.doc_number or '',
                'doc_date': _fmt_date(doc.doc_date),
                'subject': r.description or (doc.subject or ''),
            })
            if doc.id:
                record_doc_ids.add(doc.id)
        # New format: document (判斷方向)
        if r.document and not r.incoming_doc and not r.outgoing_doc:
            doc = r.document
            doc_number = doc.doc_number or ''
            item = {
                'record_id': r.id,
                'parent_record_id': getattr(r, 'parent_record_id', None),
                'doc_number': doc_number,
                'doc_date': _fmt_date(doc.doc_date),
                'subject': r.description or (doc.subject or ''),
            }
            if is_outgoing_doc_number(doc_number):
                assigned_out.append(item)
            else:
                assigned_in.append(item)
            if doc.id:
                record_doc_ids.add(doc.id)

    # --- 收集未指派到 work record 的公文 (unassigned) ---
    unassigned_in: List[Dict[str, Any]] = []
    unassigned_out: List[Dict[str, Any]] = []
    for lk in doc_links:
        doc = lk.document
        if not doc or doc.id in record_doc_ids:
            continue
        item = {
            'doc_number': doc.doc_number or '',
            'doc_date': _fmt_date(doc.doc_date),
            'subject': doc.subject or '',
        }
        if lk.link_type == 'company_outgoing':
            unassigned_out.append(item)
        else:
            unassigned_in.append(item)

    # --- Phase 1: parent_record_id chain pairing ---
    result: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
    used_in_ids: set = set()
    used_out_ids: set = set()

    for out_item in assigned_out:
        pid = out_item.get('parent_record_id')
        if not pid:
            continue
        for in_item in assigned_in:
            if in_item['record_id'] == pid and in_item['record_id'] not in used_in_ids:
                result.append((in_item, out_item))
                used_in_ids.add(in_item['record_id'])
                used_out_ids.add(out_item['record_id'])
                break

    # --- Phase 2: date proximity greedy pairing ---
    remain_in = [
        x for x in assigned_in if x.get('record_id') not in used_in_ids
    ]
    remain_out = [
        x for x in assigned_out if x.get('record_id') not in used_out_ids
    ]

    all_in = sorted(remain_in + unassigned_in, key=lambda x: x.get('doc_date', ''))
    all_out = sorted(remain_out + unassigned_out, key=lambda x: x.get('doc_date', ''))

    used_out_idx: set = set()
    date_matched: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []

    for in_item in all_in:
        best_idx = -1
        best_date = ''
        in_date = in_item.get('doc_date', '')

        for j, out_item in enumerate(all_out):
            if j in used_out_idx:
                continue
            out_date = out_item.get('doc_date', '')
            if out_date >= in_date:
                if best_idx == -1 or out_date < best_date:
                    best_idx = j
                    best_date = out_date

        if best_idx >= 0:
            date_matched.append((in_item, all_out[best_idx]))
            used_out_idx.add(best_idx)
        else:
            date_matched.append((in_item, None))

    # --- Phase 3: remaining outgoing standalone ---
    for j, out_item in enumerate(all_out):
        if j not in used_out_idx:
            date_matched.append((None, out_item))

    result.extend(date_matched)

    # --- 按最早日期排序 ---
    result.sort(key=lambda pair: (
        pair[0].get('doc_date', '') if pair[0] else (pair[1].get('doc_date', '') if pair[1] else '')
    ))

    return result
