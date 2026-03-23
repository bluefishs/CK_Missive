"""
公文篩選服務 - 查詢條件套用邏輯

v1.0.0 - 2026-03-23
- 從 DocumentService 拆分篩選相關方法
- parse_date_string, extract_agency_names, expand_agency_filter, apply_filters

職責：
- 日期字串解析
- 機關名稱提取與同義詞擴展
- 查詢篩選條件套用
"""
import logging
import re
from typing import List, Optional, Any
from datetime import datetime, date

from sqlalchemy import or_, extract

from app.extended.models import (
    OfficialDocument as Document,
    ContractProject,
)
from app.schemas.document import DocumentFilter

logger = logging.getLogger(__name__)


class DocumentFilterService:
    """
    公文篩選服務（靜態方法集合）

    所有方法皆為靜態或類別方法，不需要 DB session。
    從 DocumentService 拆分，負責查詢條件的解析與套用。
    """

    @staticmethod
    def parse_date_string(date_str: str) -> Optional[date]:
        """
        解析日期字串為 date 物件

        支援格式：YYYY-MM-DD, YYYY/MM/DD

        Args:
            date_str: 日期字串

        Returns:
            date 物件或 None
        """
        if not date_str:
            return None
        try:
            normalized = date_str.replace('/', '-')
            return datetime.strptime(normalized, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"[篩選] 無效的日期格式: {date_str}")
            return None

    @staticmethod
    def extract_agency_names(agency_value: str) -> List[str]:
        """
        從下拉選項值中提取機關名稱

        支援格式：
        - 純名稱: "桃園市政府"
        - 代碼+名稱: "380110000G (桃園市政府工務局)"
        - 多機關: "376480000A (南投縣政府) | A01020100G (內政部國土管理署城鄉發展分署)"
        - 換行格式: "380110000G\\n(桃園市政府工務局)"

        Args:
            agency_value: 下拉選項值

        Returns:
            提取出的機關名稱列表
        """
        if not agency_value:
            return []

        names = []

        # 先按 | 分割多個機關
        parts = agency_value.split('|')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 處理換行格式: "380110000G\n(桃園市政府工務局)"
            part = part.replace('\n', ' ').replace('\r', ' ')

            # 嘗試提取括號內的名稱: "380110000G (桃園市政府工務局)" -> "桃園市政府工務局"
            match = re.search(r'\(([^)]+)\)', part)
            if match:
                names.append(match.group(1).strip())
            else:
                # 嘗試移除代碼前綴: "380110000G 桃園市政府工務局" -> "桃園市政府工務局"
                # 代碼格式通常是 字母+數字 組合
                cleaned = re.sub(r'^[A-Z0-9]+\s*', '', part, flags=re.IGNORECASE)
                if cleaned:
                    names.append(cleaned.strip())
                else:
                    # 如果全都被移除了，就用原值（可能本身就是純名稱）
                    names.append(part)

        return names

    @staticmethod
    def expand_agency_filter(agency_value: str) -> List[str]:
        """
        機關篩選值擴展：名稱提取 + 同義詞擴展

        1. 先用 extract_agency_names 提取純名稱
        2. 再用 SynonymExpander 擴展同義詞（DB SSOT）

        例：輸入「桃園市工務局」-> 擴展出 [「桃園市工務局」,「桃園市政府工務局」,「工務局」,「工務處」]
        """
        from app.services.ai.synonym_expander import SynonymExpander

        extracted = DocumentFilterService.extract_agency_names(agency_value)
        if not extracted:
            return []

        expanded = SynonymExpander.expand_keywords(extracted)
        if len(expanded) > len(extracted):
            logger.info(f"[篩選] 機關同義詞擴展: {extracted} -> {expanded}")
        return expanded

    @staticmethod
    def apply_filters(query: Any, filters: DocumentFilter) -> Any:
        """
        套用篩選條件到查詢

        使用 DocumentFilter 的輔助方法取得有效值，
        支援多種參數命名慣例 (如 date_from 和 doc_date_from)

        Args:
            query: SQLAlchemy 查詢物件
            filters: 篩選條件

        Returns:
            套用篩選後的查詢物件
        """
        # 取得有效的篩選值 (使用 DocumentFilter 的輔助方法)
        effective_keyword = filters.get_effective_keyword() if hasattr(filters, 'get_effective_keyword') else (filters.keyword or getattr(filters, 'search', None))
        effective_date_from = filters.get_effective_date_from() if hasattr(filters, 'get_effective_date_from') else (filters.date_from or getattr(filters, 'doc_date_from', None))
        effective_date_to = filters.get_effective_date_to() if hasattr(filters, 'get_effective_date_to') else (filters.date_to or getattr(filters, 'doc_date_to', None))

        # 取得 doc_number 篩選值（專用公文字號搜尋）
        doc_number_filter = getattr(filters, 'doc_number', None)

        # 調試日誌
        logger.info(f"[篩選] 有效條件: keyword={effective_keyword}, doc_number={doc_number_filter}, "
                   f"doc_type={filters.doc_type}, year={filters.year}, "
                   f"sender={filters.sender}, receiver={filters.receiver}, "
                   f"delivery_method={filters.delivery_method}, "
                   f"date_from={effective_date_from}, date_to={effective_date_to}, "
                   f"contract_case={filters.contract_case}, category={filters.category}")

        # 公文類型篩選
        if filters.doc_type:
            query = query.where(Document.doc_type == filters.doc_type)

        # 年度篩選
        if filters.year:
            query = query.where(extract('year', Document.doc_date) == filters.year)

        # 公文字號專用篩選（僅搜尋 doc_number 欄位）
        if doc_number_filter:
            doc_num_kw = f"%{doc_number_filter}%"
            logger.debug(f"[篩選] 套用 doc_number 專用篩選: {doc_number_filter}")
            query = query.where(Document.doc_number.ilike(doc_num_kw))

        # 關鍵字搜尋（公文字號、主旨、說明、備註、簡要說明、發文/受文單位）
        if effective_keyword:
            kw = f"%{effective_keyword}%"
            query = query.where(or_(
                Document.doc_number.ilike(kw),
                Document.subject.ilike(kw),
                Document.content.ilike(kw),
                Document.notes.ilike(kw),
                Document.ck_note.ilike(kw),
                Document.sender.ilike(kw),
                Document.receiver.ilike(kw),
            ))

        # 收發文分類篩選
        if filters.category:
            logger.debug(f"[篩選] 套用 category: {filters.category}")
            query = query.where(Document.category == filters.category)

        # 發文形式篩選 (驗證有效值)
        if filters.delivery_method:
            valid_methods = ['電子交換', '紙本郵寄']
            if filters.delivery_method in valid_methods:
                logger.debug(f"[篩選] 套用 delivery_method: {filters.delivery_method}")
                query = query.where(Document.delivery_method == filters.delivery_method)
            else:
                logger.warning(f"[篩選] 無效的 delivery_method: {filters.delivery_method}")

        # 發文單位篩選 (名稱提取 + 同義詞擴展 + 模糊匹配)
        if filters.sender:
            sender_names = DocumentFilterService.expand_agency_filter(filters.sender)
            logger.debug(f"[篩選] 套用 sender: {filters.sender} -> 擴展: {sender_names}")
            if sender_names:
                sender_conditions = [Document.sender.ilike(f"%{name}%") for name in sender_names]
                query = query.where(or_(*sender_conditions))

        # 受文單位篩選 (名稱提取 + 同義詞擴展 + 模糊匹配)
        if filters.receiver:
            receiver_names = DocumentFilterService.expand_agency_filter(filters.receiver)
            logger.debug(f"[篩選] 套用 receiver: {filters.receiver} -> 擴展: {receiver_names}")
            if receiver_names:
                receiver_conditions = [Document.receiver.ilike(f"%{name}%") for name in receiver_names]
                query = query.where(or_(*receiver_conditions))

        # 公文日期範圍篩選
        if effective_date_from:
            date_from_val = DocumentFilterService.parse_date_string(effective_date_from) if isinstance(effective_date_from, str) else effective_date_from
            if date_from_val:
                logger.debug(f"[篩選] 套用 date_from: {date_from_val}")
                query = query.where(Document.doc_date >= date_from_val)

        if effective_date_to:
            date_to_val = DocumentFilterService.parse_date_string(effective_date_to) if isinstance(effective_date_to, str) else effective_date_to
            if date_to_val:
                logger.debug(f"[篩選] 套用 date_to: {date_to_val}")
                query = query.where(Document.doc_date <= date_to_val)

        # 承攬案件篩選 (案件名稱或編號模糊匹配)
        if filters.contract_case:
            logger.debug(f"[篩選] 套用 contract_case: {filters.contract_case}")
            query = query.outerjoin(ContractProject, Document.contract_project_id == ContractProject.id)
            query = query.where(or_(
                ContractProject.project_name.ilike(f"%{filters.contract_case}%"),
                ContractProject.project_code.ilike(f"%{filters.contract_case}%")
            ))

        # 承辦人篩選
        if hasattr(filters, 'assignee') and filters.assignee:
            logger.debug(f"[篩選] 套用 assignee: {filters.assignee}")
            query = query.where(Document.assignee.ilike(f"%{filters.assignee}%"))

        return query
