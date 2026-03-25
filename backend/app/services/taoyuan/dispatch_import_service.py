"""
DispatchImportService - 派工單 Excel 匯入/匯出服務

處理派工單的 Excel 匯入解析、自動公文關聯、批次重新關聯和範本生成。

從 dispatch_order_service.py 拆分而來。

@version 2.0.0
@date 2026-03-04
"""

import io
import re
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import ContractProject, OfficialDocument, TaoyuanDispatchOrder
from app.repositories.taoyuan import DispatchOrderRepository, DispatchDocLinkRepository
from app.utils.doc_number_parser import parse_doc_numbers
from app.utils.doc_helpers import is_outgoing_doc_number
from app.services.taoyuan.dispatch_link_resolver import is_generic_admin_doc

logger = logging.getLogger(__name__)


class DispatchImportService:
    """
    派工單 Excel 匯入/匯出服務

    職責:
    - Excel 檔案解析與匯入
    - 匯入時自動建立公文關聯
    - 批次重新關聯（公文後匯入時使用）
    - 匯入範本生成
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)
        self.doc_link_repo = DispatchDocLinkRepository(db)

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
            匯入結果（含公文關聯統計）
        """
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

        # 智慧偵測正確的工作表（自動跳過日誌/說明 sheet）
        required_columns = {'派工單號', '工程名稱/派工事項', '作業類別'}
        try:
            xls = pd.ExcelFile(io.BytesIO(file_content))
            target_sheet = None
            for sheet_name in xls.sheet_names:
                df_check = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
                if required_columns.issubset(set(df_check.columns)):
                    target_sheet = sheet_name
                    break

            if target_sheet is None:
                # 找不到完全匹配 → 嘗試欄位部分匹配（至少 3 個映射欄位命中）
                for sheet_name in xls.sheet_names:
                    df_check = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
                    matched = set(column_mapping.keys()) & set(df_check.columns)
                    if len(matched) >= 3:
                        target_sheet = sheet_name
                        break

            if target_sheet is None:
                return {
                    'success': False,
                    'total': 0,
                    'success_count': 0,
                    'error_count': 1,
                    'errors': [
                        f'Excel 中未找到包含必要欄位的工作表。'
                        f'需要欄位: {", ".join(required_columns)}。'
                        f'找到的工作表: {", ".join(xls.sheet_names)}'
                    ],
                }

            logger.info(f"匯入使用工作表: {target_sheet} (共 {len(xls.sheet_names)} 個 sheet)")
            df = pd.read_excel(xls, sheet_name=target_sheet)
        except Exception as e:
            return {
                'success': False,
                'total': 0,
                'success_count': 0,
                'error_count': 1,
                'errors': [f'Excel 讀取失敗: {type(e).__name__}'],
            }

        # 驗證欄位匹配度
        matched_columns = set(column_mapping.keys()) & set(df.columns)
        if len(matched_columns) < 3:
            return {
                'success': False,
                'total': 0,
                'success_count': 0,
                'error_count': 1,
                'errors': [
                    f'Excel 欄位不符。找到欄位: {list(df.columns)[:5]}..., '
                    f'需要欄位: {list(column_mapping.keys())[:5]}...'
                ],
            }

        # 從承攬案件名稱解析民國年（用於自動生成派工單號）
        dispatch_year = await self._resolve_roc_year(contract_project_id)

        # 預載該案件所有公文的 {doc_number: (id, doc_number)} map（避免 N+1）
        doc_number_map = await self._build_doc_number_map(contract_project_id)

        success_count = 0
        errors = []
        warnings: List[str] = []
        total = len(df)
        link_stats = {'linked': 0, 'not_found': []}

        for idx, row in df.iterrows():
            try:
                record = {}
                for excel_col, db_col in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.notna(value):
                            record[db_col] = str(value).strip() if isinstance(value, str) else value

                # 處理履約期限（DB 為 String(200)，保留原始文字）
                if 'deadline' in record:
                    deadline_val = record['deadline']
                    if isinstance(deadline_val, (datetime, date)):
                        # Excel 日期格式 → 轉為民國年字串
                        d = deadline_val.date() if isinstance(deadline_val, datetime) else deadline_val
                        roc_year = d.year - 1911
                        record['deadline'] = f"{roc_year}年{d.month:02d}月{d.day:02d}日"
                    else:
                        # 字串直接保留（如 "115年03月20日前函送成果"）
                        record['deadline'] = str(deadline_val).strip()

                # 生成派工單號（如果沒有）— 使用承攬案件的民國年
                if not record.get('dispatch_no'):
                    record['dispatch_no'] = await self.repository.get_next_dispatch_no(year=dispatch_year)

                # 設定承攬案件 ID
                record['contract_project_id'] = contract_project_id

                # 提取並保留原始文號（不再丟棄）
                agency_raw = record.pop('agency_doc_number_input', None)
                company_raw = record.pop('company_doc_number_input', None)
                if agency_raw is not None:
                    record['agency_doc_number_raw'] = str(agency_raw).strip()[:500]
                if company_raw is not None:
                    record['company_doc_number_raw'] = str(company_raw).strip()[:500]

                dispatch_order = await self.repository.create(record, auto_commit=False)
                success_count += 1

                # 嘗試自動關聯公文（不阻斷匯入）
                try:
                    link_result = await self._link_documents_by_number(
                        dispatch_id=dispatch_order.id,
                        agency_raw=str(agency_raw) if agency_raw is not None else None,
                        company_raw=str(company_raw) if company_raw is not None else None,
                        doc_number_map=doc_number_map,
                    )
                    link_stats['linked'] += link_result['linked_count']
                    link_stats['not_found'].extend(link_result['not_found'])
                except Exception as e:
                    warnings.append(f'第 {idx + 2} 行: 公文關聯失敗: {type(e).__name__}')
                    logger.warning("公文關聯失敗 row=%d: %s", idx + 2, e)

            except Exception as e:
                logger.error(f"第 {idx + 2} 行匯入失敗: {e}")
                errors.append(f'第 {idx + 2} 行: 匯入失敗')

        await self.db.commit()

        return {
            'success': True,
            'total': total,
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors,
            'doc_link_stats': link_stats,
            'warnings': warnings,
        }

    async def _link_documents_by_number(
        self,
        dispatch_id: int,
        agency_raw: Optional[str],
        company_raw: Optional[str],
        doc_number_map: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        根據文號建立派工-公文關聯

        Args:
            dispatch_id: 派工單 ID
            agency_raw: 機關函文號原始值
            company_raw: 乾坤函文號原始值
            doc_number_map: 預載的 {doc_number: doc_id} 映射

        Returns:
            {linked_count, not_found, agency_doc_id, company_doc_id}
        """
        linked_count = 0
        already_linked = 0
        not_found: List[str] = []
        agency_doc_id = None
        company_doc_id = None

        # 處理機關函文號（跳過通用行政文件）
        if agency_raw:
            numbers = parse_doc_numbers(agency_raw)
            for i, doc_num in enumerate(numbers):
                doc_id = doc_number_map.get(doc_num)
                if doc_id:
                    link = await self.doc_link_repo.link_dispatch_to_document(
                        dispatch_id, doc_id,
                        link_type="agency_incoming",
                        auto_commit=False,
                    )
                    if link is not None:
                        linked_count += 1
                    else:
                        already_linked += 1
                    if i == 0:
                        agency_doc_id = doc_id
                else:
                    not_found.append(doc_num)

        # 處理乾坤函文號
        if company_raw:
            numbers = parse_doc_numbers(company_raw)
            for i, doc_num in enumerate(numbers):
                doc_id = doc_number_map.get(doc_num)
                if doc_id:
                    link_type = "company_outgoing" if is_outgoing_doc_number(doc_num) else "agency_incoming"
                    link = await self.doc_link_repo.link_dispatch_to_document(
                        dispatch_id, doc_id,
                        link_type=link_type,
                        auto_commit=False,
                    )
                    if link is not None:
                        linked_count += 1
                    else:
                        already_linked += 1
                    if i == 0:
                        company_doc_id = doc_id
                else:
                    not_found.append(doc_num)

        # 更新向下相容的 FK 欄位
        if agency_doc_id or company_doc_id:
            dispatch = await self.db.get(TaoyuanDispatchOrder, dispatch_id)
            if dispatch:
                if agency_doc_id and not dispatch.agency_doc_id:
                    dispatch.agency_doc_id = agency_doc_id
                if company_doc_id and not dispatch.company_doc_id:
                    dispatch.company_doc_id = company_doc_id

        return {
            'linked_count': linked_count,
            'already_linked': already_linked,
            'not_found': not_found,
            'agency_doc_id': agency_doc_id,
            'company_doc_id': company_doc_id,
        }

    async def batch_relink_by_project(
        self,
        contract_project_id: int,
    ) -> Dict[str, Any]:
        """
        批次重新關聯：掃描該案件所有有原始文號的派工單，嘗試匹配公文

        適用場景：派工單先匯入（文號已存），公文後建檔，需補建關聯。

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            {total_scanned, newly_linked, already_linked, not_found}
        """
        # 查詢有原始文號的派工單 — 委派至 Repository
        dispatch_orders = await self.repository.get_with_doc_numbers_by_project(
            contract_project_id
        )

        if not dispatch_orders:
            return {
                'total_scanned': 0,
                'newly_linked': 0,
                'already_linked': 0,
                'not_found': [],
            }

        # 預載公文 map
        doc_number_map = await self._build_doc_number_map(contract_project_id)
        logger.info(
            "批次重新關聯: project=%d, 派工單=%d, 公文map=%d",
            contract_project_id, len(dispatch_orders), len(doc_number_map),
        )

        total_scanned = len(dispatch_orders)
        newly_linked = 0
        already_linked = 0
        not_found_list: List[Dict[str, str]] = []

        for dispatch in dispatch_orders:
            link_result = await self._link_documents_by_number(
                dispatch_id=dispatch.id,
                agency_raw=dispatch.agency_doc_number_raw,
                company_raw=dispatch.company_doc_number_raw,
                doc_number_map=doc_number_map,
            )
            newly_linked += link_result['linked_count']
            already_linked += link_result.get('already_linked', 0)
            for doc_num in link_result['not_found']:
                not_found_list.append({
                    'dispatch_no': dispatch.dispatch_no,
                    'doc_number': doc_num,
                })

        await self.db.commit()

        # Post-relink: 標記通用行政文件（不自動刪除，僅記錄警告）
        generic_warnings: List[str] = []
        for dispatch in dispatch_orders:
            linked_docs = await self.doc_link_repo.get_linked_doc_details(dispatch.id)
            for doc_id, subject, ck_note in linked_docs:
                if is_generic_admin_doc(subject or '', ck_note or ''):
                    generic_warnings.append(
                        f"dispatch#{dispatch.id}({dispatch.dispatch_no}) 關聯了通用行政文件 doc#{doc_id}"
                    )

        return {
            'total_scanned': total_scanned,
            'newly_linked': newly_linked,
            'already_linked': already_linked,
            'not_found': not_found_list,
            'doc_map_size': len(doc_number_map),
            'generic_doc_warnings': generic_warnings[:20],
        }

    async def _build_doc_number_map(
        self,
        contract_project_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        建立 {doc_number: doc_id} 映射

        優先載入該案件關聯的公文，若無則載入所有公文。

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            {doc_number: document_id} 字典
        """
        # 載入所有公文（派工單的文號可能跨案件）— 委派至 Repository
        from app.repositories.document_repository import DocumentRepository
        doc_repo = DocumentRepository(self.db)
        return await doc_repo.build_doc_number_map()

    async def _resolve_roc_year(self, contract_project_id: int) -> int:
        """
        從承攬案件名稱解析民國年（取起始年）

        支援格式：
        - "115年度..." → 115
        - "112至113年度..." → 112
        """
        from app.repositories import ProjectRepository
        project_repo = ProjectRepository(self.db)
        project = await project_repo.get_by_id(contract_project_id)
        project_name = project.project_name if project else None
        if project_name:
            year_match = re.search(r'(\d{2,3})(?:[-~～至]\d{2,3})?年', project_name)
            if year_match:
                return int(year_match.group(1))
        return datetime.now().year - 1911

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
