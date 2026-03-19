"""
PaymentReportService - 契金管控報表生成服務

從 payment_service.py 拆分，提供契金管控展示資料生成邏輯。

@version 1.0.0
@date 2026-03-19
"""

import re
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import PaymentRepository, DispatchOrderRepository
from app.extended.models import TaoyuanDispatchDocumentLink

logger = logging.getLogger(__name__)


class PaymentReportService:
    """契金管控報表生成服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = PaymentRepository(db)
        self.dispatch_repository = DispatchOrderRepository(db)

    async def get_payment_control_report(
        self,
        contract_project_id: Optional[int] = None,
        page: int = 1,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        取得契金管控展示資料

        Args:
            contract_project_id: 承攬案件 ID
            page: 頁碼
            limit: 每頁筆數

        Returns:
            契金管控展示資料
        """
        from app.schemas.taoyuan.payment import PaymentControlItem

        # 取得派工單列表（含關聯資料）
        items, total = await self.dispatch_repository.filter_dispatch_orders(
            contract_project_id=contract_project_id,
            sort_by='dispatch_no',
            sort_order='asc',
            page=page,
            limit=limit,
        )

        # 取得總預算與合約名稱
        total_budget = 0
        contract_name = None
        if contract_project_id:
            summary = await self.repository.get_project_summary(contract_project_id)
            total_budget = summary.get('total_budget', 0)
            contract_name = summary.get('project_name')

        result_items = []
        running_total = 0
        claimed_total = 0

        for order in items:
            dispatch_date = None
            agency_doc_history = None
            company_doc_history = None

            # 處理公文歷程
            if hasattr(order, 'document_links') and order.document_links:
                agency_docs = [
                    link for link in order.document_links
                    if link.link_type == 'agency_incoming' and link.document
                ]
                company_docs = [
                    link for link in order.document_links
                    if link.link_type == 'company_outgoing' and link.document
                ]

                # 機關公文歷程
                if agency_docs:
                    sorted_agency = sorted(
                        agency_docs,
                        key=lambda x: x.document.doc_date if x.document and x.document.doc_date else '9999-12-31'
                    )
                    if sorted_agency and sorted_agency[0].document and sorted_agency[0].document.doc_date:
                        dispatch_date = sorted_agency[0].document.doc_date
                    history_items = []
                    for link in sorted_agency:
                        if link.document:
                            doc_date_str = link.document.doc_date.strftime('%Y年%m月%d日') if link.document.doc_date else ''
                            doc_number = link.document.doc_number or ''
                            if doc_date_str or doc_number:
                                history_items.append(f"{doc_date_str}_{doc_number}")
                    agency_doc_history = '\n'.join(history_items) if history_items else None

                # 公司公文歷程
                if company_docs:
                    sorted_company = sorted(
                        company_docs,
                        key=lambda x: x.document.doc_date if x.document and x.document.doc_date else '9999-12-31'
                    )
                    history_items = []
                    for link in sorted_company:
                        if link.document:
                            doc_date_str = link.document.doc_date.strftime('%Y年%m月%d日') if link.document.doc_date else ''
                            doc_number = link.document.doc_number or ''
                            if doc_date_str or doc_number:
                                history_items.append(f"{doc_date_str}_{doc_number}")
                    company_doc_history = '\n'.join(history_items) if history_items else None

            # 處理契金資料
            payment = order.payment if hasattr(order, 'payment') else None
            current_amount = 0
            payment_data = {}

            # 解析作業類別代碼
            work_type_codes = set()
            if order.work_type:
                matches = re.findall(r'(\d{2})\.', order.work_type)
                work_type_codes = set(matches)

            if payment:
                current_amount = float(payment.current_amount or 0)
                payment_data = {
                    'payment_id': payment.id,
                    'work_01_date': payment.work_01_date or (dispatch_date if '01' in work_type_codes else None),
                    'work_01_amount': payment.work_01_amount,
                    'work_02_date': payment.work_02_date or (dispatch_date if '02' in work_type_codes else None),
                    'work_02_amount': payment.work_02_amount,
                    'work_03_date': payment.work_03_date or (dispatch_date if '03' in work_type_codes else None),
                    'work_03_amount': payment.work_03_amount,
                    'work_04_date': payment.work_04_date or (dispatch_date if '04' in work_type_codes else None),
                    'work_04_amount': payment.work_04_amount,
                    'work_05_date': payment.work_05_date or (dispatch_date if '05' in work_type_codes else None),
                    'work_05_amount': payment.work_05_amount,
                    'work_06_date': payment.work_06_date or (dispatch_date if '06' in work_type_codes else None),
                    'work_06_amount': payment.work_06_amount,
                    'work_07_date': payment.work_07_date or (dispatch_date if '07' in work_type_codes else None),
                    'work_07_amount': payment.work_07_amount,
                    'current_amount': payment.current_amount,
                    'acceptance_date': payment.acceptance_date,
                }
            else:
                if work_type_codes and dispatch_date:
                    for code in work_type_codes:
                        payment_data[f'work_{code}_date'] = dispatch_date

            running_total += current_amount
            if order.batch_no is not None:
                claimed_total += current_amount
            cumulative_amount = running_total
            remaining_amount = total_budget - running_total

            item = PaymentControlItem(
                dispatch_order_id=order.id,
                dispatch_no=order.dispatch_no,
                project_name=order.project_name,
                work_type=order.work_type,
                sub_case_name=order.sub_case_name,
                case_handler=order.case_handler,
                survey_unit=order.survey_unit,
                cloud_folder=order.cloud_folder,
                project_folder=order.project_folder,
                deadline=order.deadline,
                dispatch_date=dispatch_date,
                agency_doc_history=agency_doc_history,
                company_doc_history=company_doc_history,
                cumulative_amount=cumulative_amount,
                remaining_amount=remaining_amount,
                **payment_data
            )
            result_items.append(item)

        return {
            'items': result_items,
            'total': total,
            'contract_name': contract_name,
            'total_budget': total_budget,
            'total_dispatched': running_total,
            'total_remaining': total_budget - running_total,
            'total_claimed': claimed_total,
        }
