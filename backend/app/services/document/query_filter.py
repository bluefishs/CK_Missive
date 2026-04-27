"""
公文查詢篩選服務

將複雜的篩選邏輯從 DocumentService 分離出來，
提高可測試性和可維護性。

@version 1.0.0
@date 2026-01-19
"""

import re
import logging
from datetime import datetime, date
from typing import Optional, List, Any

from sqlalchemy import or_, and_, extract
from sqlalchemy.sql import Select

from app.schemas.document import DocumentFilter
from app.extended.models import OfficialDocument as Document

logger = logging.getLogger(__name__)


class DocumentQueryFilterService:
    """
    公文查詢篩選服務

    職責：
    - 套用各種篩選條件到查詢
    - 日期字串解析
    - 機關名稱提取

    使用方式：
    ```python
    filter_service = DocumentQueryFilterService()
    query = filter_service.apply_filters(base_query, filters)
    ```
    """

    def __init__(self):
        """初始化篩選服務"""
        pass

    def parse_date_string(self, date_str: str) -> Optional[date]:
        """
        解析日期字串

        支援格式:
        - YYYY-MM-DD
        - YYYY/MM/DD

        Args:
            date_str: 日期字串

        Returns:
            解析後的 date 物件，失敗返回 None
        """
        if not date_str:
            return None

        # 嘗試不同格式
        formats = ['%Y-%m-%d', '%Y/%m/%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"無法解析日期字串: {date_str}")
        return None

    def extract_agency_names(self, agency_value: str) -> List[str]:
        """
        從下拉選項值中提取機關名稱

        處理情況:
        1. 純名稱: "台北市政府" -> ["台北市政府"]
        2. 帶統計: "台北市政府 (5筆)" -> ["台北市政府"]
        3. 代碼+名稱: "A01 台北市政府" -> ["台北市政府"]
        4. 多個值: "台北市政府,新北市政府" -> ["台北市政府", "新北市政府"]

        Args:
            agency_value: 下拉選項原始值

        Returns:
            提取出的機關名稱列表
        """
        if not agency_value:
            return []

        names = []

        # 先移除括號內的統計數據
        clean_value = re.sub(r'\s*\([^)]*筆[^)]*\)', '', agency_value).strip()

        # 檢查是否有多個值（逗號分隔）
        parts = clean_value.split(',')

        for part in parts:
            part = part.strip()
            if part:
                # 嘗試移除前面的代碼（如 A01, B02 等）
                cleaned = re.sub(r'^[A-Z0-9]+\s*', '', part, flags=re.IGNORECASE)
                if cleaned:
                    names.append(cleaned.strip())
                else:
                    # 如果全都被移除了，就用原值
                    names.append(part)

        return names

    def apply_filters(self, query: Select, filters: DocumentFilter) -> Select:
        """
        套用篩選條件到查詢

        使用 DocumentFilter 的輔助方法取得有效值，
        支援多種參數命名慣例

        Args:
            query: SQLAlchemy 查詢物件
            filters: 篩選條件

        Returns:
            套用篩選後的查詢物件
        """
        # 取得有效的篩選值
        effective_keyword = self._get_effective_keyword(filters)
        effective_date_from = self._get_effective_date_from(filters)
        effective_date_to = self._get_effective_date_to(filters)
        doc_number_filter = getattr(filters, 'doc_number', None)

        # 調試日誌
        logger.info(
            f"[篩選] 有效條件: keyword={effective_keyword}, doc_number={doc_number_filter}, "
            f"doc_type={filters.doc_type}, year={filters.year}, "
            f"sender={filters.sender}, receiver={filters.receiver}, "
            f"delivery_method={filters.delivery_method}, "
            f"date_from={effective_date_from}, date_to={effective_date_to}, "
            f"contract_case={filters.contract_case}, category={filters.category}"
        )

        # 公文類型篩選
        if filters.doc_type:
            query = query.where(Document.doc_type == filters.doc_type)

        # 年度篩選
        if filters.year:
            query = query.where(extract('year', Document.doc_date) == filters.year)

        # 公文字號專用篩選
        if doc_number_filter:
            doc_num_kw = f"%{doc_number_filter}%"
            logger.debug(f"[篩選] 套用 doc_number 專用篩選: {doc_number_filter}")
            query = query.where(Document.doc_number.ilike(doc_num_kw))

        # 關鍵字搜尋（主旨、說明、備註 - 不包含 doc_number）
        if effective_keyword:
            kw = f"%{effective_keyword}%"
            query = query.where(or_(
                Document.subject.ilike(kw),
                Document.content.ilike(kw),
                Document.notes.ilike(kw)
            ))

        # 收發文分類篩選
        if filters.category:
            logger.debug(f"[篩選] 套用 category: {filters.category}")
            query = query.where(Document.category == filters.category)

        # 發文形式篩選
        if filters.delivery_method:
            valid_methods = ['電子交換', '紙本郵寄']
            if filters.delivery_method in valid_methods:
                logger.debug(f"[篩選] 套用 delivery_method: {filters.delivery_method}")
                query = query.where(Document.delivery_method == filters.delivery_method)
            else:
                logger.warning(f"[篩選] 無效的 delivery_method: {filters.delivery_method}")

        # 發文單位篩選
        if filters.sender:
            sender_names = self.extract_agency_names(filters.sender)
            logger.debug(f"[篩選] 套用 sender: {filters.sender} -> 提取名稱: {sender_names}")
            if sender_names:
                sender_conditions = [Document.sender.ilike(f"%{name}%") for name in sender_names]
                query = query.where(or_(*sender_conditions))

        # 受文單位篩選
        if filters.receiver:
            receiver_names = self.extract_agency_names(filters.receiver)
            logger.debug(f"[篩選] 套用 receiver: {filters.receiver} -> 提取名稱: {receiver_names}")
            if receiver_names:
                receiver_conditions = [Document.receiver.ilike(f"%{name}%") for name in receiver_names]
                query = query.where(or_(*receiver_conditions))

        # 公文日期範圍篩選
        if effective_date_from:
            date_from_val = (
                self.parse_date_string(effective_date_from)
                if isinstance(effective_date_from, str)
                else effective_date_from
            )
            if date_from_val:
                logger.debug(f"[篩選] 套用 date_from: {date_from_val}")
                query = query.where(Document.doc_date >= date_from_val)

        if effective_date_to:
            date_to_val = (
                self.parse_date_string(effective_date_to)
                if isinstance(effective_date_to, str)
                else effective_date_to
            )
            if date_to_val:
                logger.debug(f"[篩選] 套用 date_to: {date_to_val}")
                query = query.where(Document.doc_date <= date_to_val)

        # 承攬案件篩選 (支援 ID 和名稱)
        if filters.contract_case:
            query = self._apply_contract_case_filter(query, filters.contract_case)

        return query

    def _get_effective_keyword(self, filters: DocumentFilter) -> Optional[str]:
        """取得有效的關鍵字值"""
        if hasattr(filters, 'get_effective_keyword'):
            return filters.get_effective_keyword()
        return filters.keyword or getattr(filters, 'search', None)

    def _get_effective_date_from(self, filters: DocumentFilter) -> Optional[Any]:
        """取得有效的起始日期"""
        if hasattr(filters, 'get_effective_date_from'):
            return filters.get_effective_date_from()
        return filters.date_from or getattr(filters, 'doc_date_from', None)

    def _get_effective_date_to(self, filters: DocumentFilter) -> Optional[Any]:
        """取得有效的結束日期"""
        if hasattr(filters, 'get_effective_date_to'):
            return filters.get_effective_date_to()
        return filters.date_to or getattr(filters, 'doc_date_to', None)

    def _apply_contract_case_filter(self, query: Select, contract_case: str) -> Select:
        """
        套用承攬案件篩選

        支援:
        - 數字 ID
        - 案件名稱
        """
        from app.extended.models import ContractProject

        try:
            project_id = int(contract_case)
            logger.debug(f"[篩選] 套用 contract_case ID: {project_id}")
            query = query.where(Document.contract_project_id == project_id)
        except ValueError:
            # 名稱匹配
            logger.debug(f"[篩選] 套用 contract_case 名稱: {contract_case}")
            query = query.join(
                ContractProject,
                Document.contract_project_id == ContractProject.id
            ).where(ContractProject.project_name.ilike(f"%{contract_case}%"))

        return query
