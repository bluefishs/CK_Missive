"""
DispatchOrderService - 派工單業務邏輯層

處理派工單的業務邏輯，包括序號生成、文件匹配、匯入匯出等。

@version 1.0.0
@date 2026-01-28
"""

import io
import re
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import DispatchOrderRepository
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
)
from app.schemas.taoyuan.dispatch import (
    DispatchOrderCreate,
    DispatchOrderUpdate,
    DispatchOrder as DispatchOrderSchema,
    DispatchOrderListQuery,
)
from app.schemas.taoyuan.project import TaoyuanProject as TaoyuanProjectSchema, LinkedProjectItem

logger = logging.getLogger(__name__)


class DispatchOrderService:
    """
    派工單業務邏輯服務

    職責:
    - 派工單 CRUD 操作（透過 Repository）
    - 序號生成邏輯
    - Excel 匯入/匯出
    - 公文歷程匹配
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_dispatch_order(
        self, dispatch_id: int, with_relations: bool = True
    ) -> Optional[TaoyuanDispatchOrder]:
        """
        取得派工單

        Args:
            dispatch_id: 派工單 ID
            with_relations: 是否載入關聯資料

        Returns:
            派工單或 None
        """
        if with_relations:
            return await self.repository.get_with_relations(dispatch_id)
        return await self.repository.get_by_id(dispatch_id)

    async def list_dispatch_orders(
        self, query: DispatchOrderListQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        查詢派工單列表

        Args:
            query: 查詢參數

        Returns:
            (派工單列表, 總筆數)
        """
        items, total = await self.repository.filter_dispatch_orders(
            contract_project_id=query.contract_project_id,
            work_type=query.work_type,
            search=query.search,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            limit=query.limit,
        )

        # 轉換為回應格式
        response_items = []
        for item in items:
            response_items.append(self._to_response_dict(item))

        return response_items, total

    def _to_response_dict(self, item: TaoyuanDispatchOrder) -> Dict[str, Any]:
        """將派工單轉換為回應字典"""
        # TaoyuanProjectSchema 已在模組頂部匯入

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
                }
                for link in item.document_links
            ] if item.document_links else []
        }

    # =========================================================================
    # CRUD 方法
    # =========================================================================

    async def create_dispatch_order(
        self, data: DispatchOrderCreate, auto_generate_no: bool = True
    ) -> TaoyuanDispatchOrder:
        """
        建立派工單

        Args:
            data: 派工單資料
            auto_generate_no: 是否自動生成派工單號

        Returns:
            新建的派工單
        """
        create_data = data.model_dump(exclude_unset=True)

        # 提取關聯工程 ID 列表（非 ORM 欄位）
        linked_project_ids = create_data.pop('linked_project_ids', None)

        if auto_generate_no and not create_data.get('dispatch_no'):
            create_data['dispatch_no'] = await self.get_next_dispatch_no()

        # 建立派工單
        dispatch_order = await self.repository.create(create_data)

        # 建立工程關聯記錄
        if linked_project_ids:
            for project_id in linked_project_ids:
                link = TaoyuanDispatchProjectLink(
                    dispatch_order_id=dispatch_order.id,
                    taoyuan_project_id=project_id
                )
                self.db.add(link)
            await self.db.commit()

        return dispatch_order

    async def update_dispatch_order(
        self, dispatch_id: int, data: DispatchOrderUpdate
    ) -> Optional[TaoyuanDispatchOrder]:
        """
        更新派工單

        Args:
            dispatch_id: 派工單 ID
            data: 更新資料

        Returns:
            更新後的派工單或 None
        """
        update_data = data.model_dump(exclude_unset=True)

        # 提取關聯工程 ID 列表（非 ORM 欄位）
        linked_project_ids = update_data.pop('linked_project_ids', None)

        # 更新派工單基本資料
        dispatch_order = await self.repository.update(dispatch_id, update_data)

        # 如果有指定關聯工程，更新關聯記錄
        if dispatch_order and linked_project_ids is not None:
            # 刪除現有關聯
            await self.db.execute(
                select(TaoyuanDispatchProjectLink).where(
                    TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
                )
            )
            from sqlalchemy import delete
            await self.db.execute(
                delete(TaoyuanDispatchProjectLink).where(
                    TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
                )
            )

            # 建立新關聯
            for project_id in linked_project_ids:
                link = TaoyuanDispatchProjectLink(
                    dispatch_order_id=dispatch_id,
                    taoyuan_project_id=project_id
                )
                self.db.add(link)
            await self.db.commit()

        return dispatch_order

    async def delete_dispatch_order(self, dispatch_id: int) -> bool:
        """
        刪除派工單

        Args:
            dispatch_id: 派工單 ID

        Returns:
            是否刪除成功
        """
        return await self.repository.delete(dispatch_id)

    # =========================================================================
    # 序號生成
    # =========================================================================

    async def get_next_dispatch_no(self, year: Optional[int] = None) -> str:
        """
        取得下一個派工單號

        Args:
            year: 年份（預設為當前年份）

        Returns:
            下一個派工單號
        """
        return await self.repository.get_next_dispatch_no(year)

    # =========================================================================
    # 公文歷程匹配
    # =========================================================================

    async def get_dispatch_with_history(
        self, dispatch_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        取得派工單詳情及公文歷程

        Args:
            dispatch_id: 派工單 ID

        Returns:
            派工單詳情（含公文歷程）或 None
        """
        dispatch = await self.repository.get_with_relations(dispatch_id)
        if not dispatch:
            return None

        result = self._to_response_dict(dispatch)

        # 取得公文歷程
        agency_doc_number = dispatch.agency_doc.doc_number if dispatch.agency_doc else None
        result['document_history'] = await self.repository.get_document_history(
            agency_doc_number=agency_doc_number,
            project_name=dispatch.project_name,
        )

        return result

    async def match_documents(
        self,
        agency_doc_number: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        匹配公文

        Args:
            agency_doc_number: 機關函文號
            project_name: 專案名稱

        Returns:
            匹配的公文列表
        """
        return await self.repository.get_document_history(
            agency_doc_number=agency_doc_number,
            project_name=project_name,
        )

    # =========================================================================
    # Excel 匯入/匯出
    # =========================================================================

    async def import_from_excel(
        self,
        file_content: bytes,
        contract_project_id: int,
    ) -> Dict[str, Any]:
        """
        從 Excel 匯入派工紀錄

        Args:
            file_content: Excel 檔案內容
            contract_project_id: 承攬案件 ID

        Returns:
            匯入結果
        """
        try:
            df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            return {
                'success': False,
                'total': 0,
                'success_count': 0,
                'error_count': 1,
                'errors': [f'Excel 讀取失敗: {str(e)}'],
            }

        # 欄位映射
        column_mapping = {
            '派工單號': 'dispatch_no',
            '機關函文號': 'agency_doc_number_input',
            '工程名稱/派工事項': 'project_name',
            '作業類別': 'work_type',
            '分案名稱/派工備註': 'sub_case_name',
            '履約期限': 'deadline',
            '案件承辦': 'case_handler',
            '查估單位': 'survey_unit',
            '乾坤函文號': 'company_doc_number_input',
            '雲端資料夾': 'cloud_folder',
            '專案資料夾': 'project_folder',
            '聯絡備註': 'contact_note',
        }

        success_count = 0
        errors = []
        total = len(df)

        for idx, row in df.iterrows():
            try:
                record = {}
                for excel_col, db_col in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.notna(value):
                            record[db_col] = str(value).strip() if isinstance(value, str) else value

                # 處理日期
                if 'deadline' in record:
                    deadline_val = record['deadline']
                    if isinstance(deadline_val, (datetime, date)):
                        record['deadline'] = deadline_val.date() if isinstance(deadline_val, datetime) else deadline_val
                    elif isinstance(deadline_val, str):
                        try:
                            record['deadline'] = datetime.strptime(deadline_val, '%Y-%m-%d').date()
                        except ValueError:
                            record.pop('deadline', None)

                # 生成派工單號（如果沒有）
                if not record.get('dispatch_no'):
                    record['dispatch_no'] = await self.get_next_dispatch_no()

                # 設定承攬案件 ID
                record['contract_project_id'] = contract_project_id

                # 移除輸入欄位
                record.pop('agency_doc_number_input', None)
                record.pop('company_doc_number_input', None)

                await self.repository.create(record)
                success_count += 1

            except Exception as e:
                errors.append(f'第 {idx + 2} 行: {str(e)}')

        return {
            'success': True,
            'total': total,
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors,
        }

    def generate_import_template(self) -> bytes:
        """
        生成匯入範本

        Returns:
            Excel 檔案位元組
        """
        template_columns = [
            '派工單號', '機關函文號', '工程名稱/派工事項', '作業類別',
            '分案名稱/派工備註', '履約期限', '案件承辦', '查估單位',
            '乾坤函文號', '雲端資料夾', '專案資料夾', '聯絡備註'
        ]

        sample_data = [{
            '派工單號': 'D-2026-001',
            '機關函文號': '桃工養字第1140001234號',
            '工程名稱/派工事項': '○○路拓寬工程',
            '作業類別': '土地查估',
            '分案名稱/派工備註': '第一標段',
            '履約期限': '2026-06-30',
            '案件承辦': '王○○',
            '查估單位': '第一組',
            '乾坤函文號': '乾字第1140000001號',
            '雲端資料夾': 'https://drive.google.com/...',
            '專案資料夾': 'D:/Projects/2026/001',
            '聯絡備註': '範例資料，請刪除後填入實際資料'
        }]

        df = pd.DataFrame(sample_data, columns=template_columns)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='派工紀錄')
            worksheet = writer.sheets['派工紀錄']
            for idx, col in enumerate(template_columns):
                width = max(len(col) * 2.5, 15)
                col_letter = chr(65 + idx) if idx < 26 else f'A{chr(65 + idx - 26)}'
                worksheet.column_dimensions[col_letter].width = width

        output.seek(0)
        return output.getvalue()

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得派工單統計

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            統計資料
        """
        return await self.repository.get_statistics(contract_project_id)
