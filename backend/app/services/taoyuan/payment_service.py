"""
PaymentService - 契金管控業務邏輯層

處理契金管控的業務邏輯，包括累進計算、控制報表生成等。

@version 1.0.0
@date 2026-01-28
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.repositories.taoyuan import PaymentRepository, DispatchOrderRepository
from app.extended.models import (
    TaoyuanContractPayment,
    TaoyuanDispatchOrder,
    TaoyuanDispatchDocumentLink,
)
from app.schemas.taoyuan.payment import (
    ContractPaymentCreate,
    ContractPaymentUpdate,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    契金管控業務邏輯服務

    職責:
    - 契金記錄 CRUD 操作（透過 Repository）
    - 累進金額計算
    - 控制報表生成
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = PaymentRepository(db)
        self.dispatch_repository = DispatchOrderRepository(db)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_payment(
        self, payment_id: int
    ) -> Optional[TaoyuanContractPayment]:
        """
        取得契金記錄

        Args:
            payment_id: 契金記錄 ID

        Returns:
            契金記錄或 None
        """
        return await self.repository.get_with_dispatch(payment_id)

    async def list_payments(
        self,
        dispatch_order_id: Optional[int] = None,
        contract_project_id: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        查詢契金記錄列表

        Args:
            dispatch_order_id: 派工單 ID
            contract_project_id: 承攬案件 ID
            page: 頁碼
            limit: 每頁筆數

        Returns:
            (契金記錄列表, 總筆數)
        """
        items, total = await self.repository.filter_payments(
            dispatch_order_id=dispatch_order_id,
            contract_project_id=contract_project_id,
            page=page,
            limit=limit,
        )

        # 確保累進金額已計算
        response_items = []
        for item in items:
            payment_dict = await self._to_response_dict(item)
            response_items.append(payment_dict)

        return response_items, total

    async def _to_response_dict(
        self, item: TaoyuanContractPayment
    ) -> Dict[str, Any]:
        """將契金記錄轉換為回應字典"""
        cumulative = item.cumulative_amount
        remaining = item.remaining_amount

        # 如果累進金額為空，計算並更新
        if (cumulative is None or cumulative == 0) and item.dispatch_order:
            cumulative, remaining = await self.repository.calculate_cumulative_payment(
                item.dispatch_order.contract_project_id,
                item.dispatch_order_id,
            )
            # 更新資料庫
            item.cumulative_amount = cumulative
            item.remaining_amount = remaining
            await self.db.commit()

        return {
            'id': item.id,
            'dispatch_order_id': item.dispatch_order_id,
            'work_01_date': item.work_01_date,
            'work_01_amount': item.work_01_amount,
            'work_02_date': item.work_02_date,
            'work_02_amount': item.work_02_amount,
            'work_03_date': item.work_03_date,
            'work_03_amount': item.work_03_amount,
            'work_04_date': item.work_04_date,
            'work_04_amount': item.work_04_amount,
            'work_05_date': item.work_05_date,
            'work_05_amount': item.work_05_amount,
            'work_06_date': item.work_06_date,
            'work_06_amount': item.work_06_amount,
            'work_07_date': item.work_07_date,
            'work_07_amount': item.work_07_amount,
            'current_amount': item.current_amount,
            'cumulative_amount': cumulative,
            'remaining_amount': remaining,
            'acceptance_date': item.acceptance_date,
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'dispatch_no': item.dispatch_order.dispatch_no if item.dispatch_order else None,
            'project_name': item.dispatch_order.project_name if item.dispatch_order else None,
        }

    # =========================================================================
    # CRUD 方法
    # =========================================================================

    async def create_payment(
        self, data: ContractPaymentCreate
    ) -> TaoyuanContractPayment:
        """
        建立契金記錄

        Args:
            data: 契金記錄資料

        Returns:
            新建的契金記錄
        """
        create_data = data.model_dump(exclude_unset=True)

        # 計算當前金額總和
        current_amount = sum([
            float(create_data.get(f'work_{i:02d}_amount') or 0)
            for i in range(1, 8)
        ])
        create_data['current_amount'] = current_amount

        payment = await self.repository.create(create_data)

        # 計算並更新累進金額
        if payment.dispatch_order:
            await self.repository.update_cumulative_amounts(
                payment.dispatch_order.contract_project_id
            )

        return payment

    async def update_payment(
        self, payment_id: int, data: ContractPaymentUpdate
    ) -> Optional[TaoyuanContractPayment]:
        """
        更新契金記錄

        Args:
            payment_id: 契金記錄 ID
            data: 更新資料

        Returns:
            更新後的契金記錄或 None
        """
        update_data = data.model_dump(exclude_unset=True)

        # 重新計算當前金額
        payment = await self.repository.get_with_dispatch(payment_id)
        if not payment:
            return None

        current_amount = 0
        for i in range(1, 8):
            field_name = f'work_{i:02d}_amount'
            if field_name in update_data:
                current_amount += float(update_data[field_name] or 0)
            elif hasattr(payment, field_name):
                current_amount += float(getattr(payment, field_name) or 0)
        update_data['current_amount'] = current_amount

        updated = await self.repository.update(payment_id, update_data)

        # 重新計算累進金額
        if updated and updated.dispatch_order:
            await self.repository.update_cumulative_amounts(
                updated.dispatch_order.contract_project_id
            )

        return updated

    async def delete_payment(self, payment_id: int) -> bool:
        """
        刪除契金記錄

        Args:
            payment_id: 契金記錄 ID

        Returns:
            是否刪除成功
        """
        payment = await self.repository.get_with_dispatch(payment_id)
        contract_project_id = payment.dispatch_order.contract_project_id if payment and payment.dispatch_order else None

        result = await self.repository.delete(payment_id)

        # 重新計算累進金額
        if result and contract_project_id:
            await self.repository.update_cumulative_amounts(contract_project_id)

        return result

    # =========================================================================
    # 控制報表
    # =========================================================================

    async def generate_control_report(
        self, contract_project_id: int
    ) -> Dict[str, Any]:
        """
        生成契金控制報表

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            控制報表資料
        """
        # 取得專案彙總
        summary = await self.repository.get_project_summary(contract_project_id)

        # 取得所有派工單及其契金記錄
        items, _ = await self.dispatch_repository.filter_dispatch_orders(
            contract_project_id=contract_project_id,
            page=1,
            limit=1000,  # 取得所有
        )

        report_items = []
        for dispatch in items:
            payment = await self.repository.get_by_dispatch_order(dispatch.id)

            # 取得關聯公文
            links = await self.dispatch_repository.get_linked_documents(dispatch.id)
            doc_info = self._extract_document_info(links)

            # 提取作業類別代碼
            work_type_code = self._extract_work_type_code(dispatch.work_type)

            report_items.append({
                'dispatch_id': dispatch.id,
                'dispatch_no': dispatch.dispatch_no,
                'project_name': dispatch.project_name,
                'work_type': dispatch.work_type,
                'work_type_code': work_type_code,
                'deadline': dispatch.deadline,
                'case_handler': dispatch.case_handler,
                'agency_doc_number': doc_info.get('agency_doc_number'),
                'company_doc_number': doc_info.get('company_doc_number'),
                'payment': {
                    'current_amount': payment.current_amount if payment else 0,
                    'cumulative_amount': payment.cumulative_amount if payment else 0,
                    'remaining_amount': payment.remaining_amount if payment else summary['total_budget'],
                    'acceptance_date': payment.acceptance_date if payment else None,
                } if payment else None,
            })

        return {
            'summary': summary,
            'items': report_items,
        }

    def _extract_work_type_code(self, work_type: Optional[str]) -> str:
        """
        從作業類別提取代碼

        Args:
            work_type: 作業類別

        Returns:
            代碼字串
        """
        if not work_type:
            return ''

        # 嘗試匹配括號內的代碼
        match = re.search(r'\(([^)]+)\)', work_type)
        if match:
            return match.group(1)

        # 返回前兩個字元作為簡稱
        return work_type[:2] if len(work_type) >= 2 else work_type

    def _extract_document_info(
        self, links: List[TaoyuanDispatchDocumentLink]
    ) -> Dict[str, Optional[str]]:
        """
        從關聯公文中提取資訊

        Args:
            links: 公文關聯列表

        Returns:
            公文資訊字典
        """
        agency_doc_number = None
        company_doc_number = None

        for link in links:
            if link.document:
                # 判斷是機關公文還是公司公文
                if link.link_type == 'agency_doc' or '桃' in (link.document.doc_number or ''):
                    agency_doc_number = link.document.doc_number
                else:
                    company_doc_number = link.document.doc_number

        return {
            'agency_doc_number': agency_doc_number,
            'company_doc_number': company_doc_number,
        }

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

        # 取得總預算
        total_budget = 0
        if contract_project_id:
            summary = await self.repository.get_project_summary(contract_project_id)
            total_budget = summary.get('total_budget', 0)

        result_items = []
        running_total = 0

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
            'total_budget': total_budget,
            'total_dispatched': running_total,
            'total_remaining': total_budget - running_total,
        }

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_project_summary(
        self, contract_project_id: int
    ) -> Dict[str, Any]:
        """
        取得專案契金彙總

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            彙總資料
        """
        return await self.repository.get_project_summary(contract_project_id)
