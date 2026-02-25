"""
DispatchImportService - 派工單 Excel 匯入/匯出服務

處理派工單的 Excel 匯入解析和範本生成。

從 dispatch_order_service.py 拆分而來。

@version 1.0.0
@date 2026-02-25
"""

import io
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import DispatchOrderRepository

logger = logging.getLogger(__name__)


class DispatchImportService:
    """
    派工單 Excel 匯入/匯出服務

    職責:
    - Excel 檔案解析與匯入
    - 匯入範本生成
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)

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
                    record['dispatch_no'] = await self.repository.get_next_dispatch_no()

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

        roc_year = datetime.now().year - 1911
        sample_data = [{
            '派工單號': f'{roc_year}年_派工單號001',
            '機關函文號': '桃工養字第1140001234號',
            '工程名稱/派工事項': '○○路拓寬工程',
            '作業類別': '02.土地協議市價查估作業',
            '分案名稱/派工備註': '第一標段',
            '履約期限': f'{roc_year}年06月30日前檢送成果',
            '案件承辦': '王○○',
            '查估單位': '○○不動產估價師事務所',
            '乾坤函文號': '乾字第1140000001號',
            '雲端資料夾': 'https://reurl.cc/xxxxx',
            '專案資料夾': 'Z:\\03.專案管控專區\\...',
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
