"""
DispatchResponseFormatter - 派工單回應格式化共用模組

從 dispatch_order_service.py 提取，供 dispatch_match_service.py 共用，
消除兩者之間的循環依賴。

@version 1.0.0
@date 2026-03-10
"""

from datetime import date
from typing import Any, Dict, List, Optional

from app.schemas.taoyuan.project import TaoyuanProject as TaoyuanProjectSchema


# work_category → 中文標籤
STAGE_LABELS = {
    'dispatch_notice': '派工通知',
    'work_result': '作業成果',
    'meeting_notice': '會議通知',
    'meeting_record': '會議紀錄',
    'survey_notice': '會勘通知',
    'survey_record': '會勘紀錄',
    'other': '其他',
}


def _is_meaningful_record(record, parent_ids: set) -> bool:
    """判斷作業紀錄是否有實質內容（與前端 filterBlankRecords 對齊）

    排除「空白紀錄」：無關聯公文、無描述、且未被其他紀錄引用為 parent 者。
    避免空白紀錄的預設 status 影響整體進度計算。
    """
    if getattr(record, 'document_id', None):
        return True
    if getattr(record, 'incoming_doc_id', None):
        return True
    if getattr(record, 'outgoing_doc_id', None):
        return True
    if getattr(record, 'description', None):
        return True
    if record.id in parent_ids:
        return True
    return False


def compute_work_progress(work_records) -> Optional[Dict[str, Any]]:
    """從作業紀錄計算進度摘要"""
    if not work_records:
        return None

    # 過濾空白紀錄（與前端 filterBlankRecords 邏輯一致）
    parent_ids = {
        r.parent_record_id
        for r in work_records
        if getattr(r, 'parent_record_id', None)
    }
    records = [r for r in work_records if _is_meaningful_record(r, parent_ids)]

    if not records:
        return None

    total = len(records)
    completed = sum(1 for r in records if r.status == 'completed')
    in_progress = sum(1 for r in records if r.status == 'in_progress')
    overdue = sum(1 for r in records if r.status == 'overdue')

    # 整體狀態
    if total > 0 and total == completed:
        overall_status = 'completed'
    elif overdue > 0:
        overall_status = 'overdue'
    elif in_progress > 0:
        overall_status = 'in_progress'
    else:
        overall_status = 'pending'

    # 最新階段（從有效紀錄中取）
    sorted_records = sorted(
        records,
        key=lambda r: (r.sort_order or 0, r.record_date or date.min),
        reverse=True,
    )
    latest = sorted_records[0]
    stage_key = latest.work_category or latest.milestone_type or 'other'
    current_stage = STAGE_LABELS.get(stage_key, stage_key)

    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'overdue': overdue,
        'current_stage': current_stage,
        'status': overall_status,
    }


def dispatch_to_response_dict(
    item,
    doc_dispatch_counts: Optional[Dict[int, int]] = None,
) -> Dict[str, Any]:
    """將派工單 ORM 物件轉換為回應字典

    Args:
        item: TaoyuanDispatchOrder ORM 實例（需預載關聯）
        doc_dispatch_counts: {document_id: 被幾個派工單引用}，可選

    Returns:
        標準化的派工單回應字典
    """
    return {
        'id': item.id,
        'dispatch_no': item.dispatch_no,
        'contract_project_id': item.contract_project_id,
        'agency_doc_id': item.agency_doc_id,
        'company_doc_id': item.company_doc_id,
        'project_name': item.project_name,
        'work_type': item.work_type,
        'sub_case_name': item.sub_case_name,
        'deadline': item.deadline,
        'case_handler': item.case_handler,
        'survey_unit': item.survey_unit,
        'cloud_folder': item.cloud_folder,
        'project_folder': item.project_folder,
        'contact_note': item.contact_note,
        'batch_no': item.batch_no,
        'batch_label': item.batch_label,
        'created_at': item.created_at,
        'updated_at': item.updated_at,
        'agency_doc_number': item.agency_doc.doc_number if item.agency_doc else None,
        'company_doc_number': item.company_doc.doc_number if item.company_doc else None,
        'attachment_count': len(item.attachments) if item.attachments else 0,
        'linked_projects': [
            {
                **TaoyuanProjectSchema.model_validate(link.project).model_dump(),
                'link_id': link.id,
                'project_id': link.taoyuan_project_id,
            }
            for link in item.project_links if link.project
        ] if item.project_links else [],
        'linked_documents': [
            {
                'link_id': link.id,
                'link_type': link.link_type,
                'dispatch_order_id': link.dispatch_order_id,
                'document_id': link.document_id,
                'doc_number': link.document.doc_number if link.document else None,
                'subject': link.document.subject if link.document else None,
                'doc_date': link.document.doc_date.isoformat() if link.document and link.document.doc_date else None,
                'created_at': link.created_at.isoformat() if link.created_at else None,
                'linked_dispatch_count': (
                    doc_dispatch_counts.get(link.document_id, 1)
                    if doc_dispatch_counts else None
                ),
            }
            for link in item.document_links
        ] if item.document_links else [],
        'work_type_items': [
            {
                'id': wt.id,
                'work_type': wt.work_type,
                'sort_order': wt.sort_order,
            }
            for wt in sorted(item.work_type_links, key=lambda x: x.sort_order)
        ] if item.work_type_links else [],
        'work_progress': compute_work_progress(
            item.work_records if hasattr(item, 'work_records') and item.work_records else []
        ),
    }
