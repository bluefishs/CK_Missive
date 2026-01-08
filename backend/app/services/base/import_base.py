# -*- coding: utf-8 -*-
"""
匯入服務基礎類別

提供匯入服務的共用邏輯，包括：
- 資料驗證
- 字串清理
- 日期解析
- 流水號生成
- 智慧關聯匹配
"""
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import date
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.extended.models import OfficialDocument
from app.services.base.validators import DocumentValidators, StringCleaners, DateParsers
from app.services.base.response import ImportRowResult, ImportResult
from app.services.strategies.agency_matcher import AgencyMatcher, ProjectMatcher

logger = logging.getLogger(__name__)


class ImportBaseService(ABC):
    """匯入服務基礎類別"""

    def __init__(self, db: AsyncSession):
        """
        初始化匯入服務

        Args:
            db: 資料庫連線
        """
        self.db = db

        # 流水號計數器（批次匯入時避免重複）
        self._serial_counters: Dict[str, int] = {'R': 0, 'S': 0}

        # 智慧關聯匹配器
        self._agency_matcher = AgencyMatcher(db)
        self._project_matcher = ProjectMatcher(db)

        # 驗證器與工具
        self.validators = DocumentValidators
        self.cleaners = StringCleaners
        self.date_parser = DateParsers

    # ========== 共用方法 ==========

    def clean_string(self, value: Any) -> Optional[str]:
        """清理字串值"""
        return self.cleaners.clean_string(value)

    def clean_agency_name(self, name: str) -> Optional[str]:
        """清理機關名稱"""
        return self.cleaners.clean_agency_name(name)

    def parse_date(self, value: Any) -> Optional[date]:
        """解析日期"""
        return self.date_parser.parse_date(value)

    def validate_doc_type(self, value: str, auto_fix: bool = True) -> str:
        """驗證公文類型"""
        return self.validators.validate_doc_type(value, auto_fix)

    def validate_category(self, value: str) -> str:
        """驗證類別"""
        return self.validators.validate_category(value)

    # ========== 流水號生成 ==========

    async def generate_auto_serial(self, category: str) -> str:
        """
        生成流水號

        使用記憶體計數器追蹤已生成的流水號，避免批次匯入時重複。

        Args:
            category: 類別（收文/發文）

        Returns:
            流水號（格式：R0001 或 S0001）
        """
        prefix = 'S' if category == '發文' else 'R'

        # 如果計數器尚未初始化，從資料庫取得最大值
        if self._serial_counters[prefix] == 0:
            query = select(func.max(OfficialDocument.auto_serial)).where(
                OfficialDocument.auto_serial.like(f'{prefix}%')
            )
            result = await self.db.execute(query)
            max_serial = result.scalar()

            if max_serial:
                # 提取數字部分
                num_match = re.search(r'\d+', max_serial)
                if num_match:
                    self._serial_counters[prefix] = int(num_match.group())

        # 遞增計數器並生成新流水號
        self._serial_counters[prefix] += 1
        return f"{prefix}{self._serial_counters[prefix]:04d}"

    def reset_serial_counters(self):
        """重置流水號計數器（用於新的匯入批次）"""
        self._serial_counters = {'R': 0, 'S': 0}

    # ========== 智慧關聯 ==========

    async def match_agency(self, name: str) -> Optional[int]:
        """
        智慧匹配機關

        Args:
            name: 機關名稱

        Returns:
            機關 ID 或 None
        """
        clean_name = self.clean_agency_name(name)
        if not clean_name:
            return None
        return await self._agency_matcher.match_or_create(clean_name)

    async def match_project(self, name: str) -> Optional[int]:
        """
        智慧匹配專案

        Args:
            name: 專案名稱

        Returns:
            專案 ID 或 None
        """
        clean_name = self.clean_string(name)
        if not clean_name:
            return None
        return await self._project_matcher.match_or_create(clean_name)

    # ========== 重複檢查 ==========

    async def check_duplicate_by_doc_number(self, doc_number: str) -> Optional[OfficialDocument]:
        """
        檢查公文字號是否已存在

        Args:
            doc_number: 公文字號

        Returns:
            存在的公文物件或 None
        """
        if not doc_number:
            return None

        query = select(OfficialDocument).where(
            OfficialDocument.doc_number == doc_number
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_duplicate_by_id(self, doc_id: int) -> Optional[OfficialDocument]:
        """
        根據 ID 查詢公文

        Args:
            doc_id: 公文 ID

        Returns:
            公文物件或 None
        """
        if not doc_id:
            return None

        query = select(OfficialDocument).where(OfficialDocument.id == doc_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ========== 必填欄位驗證 ==========

    def validate_required_fields(
        self,
        row_data: Dict[str, Any],
        required_fields: List[str]
    ) -> Optional[str]:
        """
        驗證必填欄位

        Args:
            row_data: 列資料
            required_fields: 必填欄位列表

        Returns:
            錯誤訊息或 None
        """
        for field in required_fields:
            value = row_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                return f"缺少必填欄位: {field}"
        return None

    # ========== 抽象方法（子類必須實作） ==========

    @abstractmethod
    async def import_from_file(
        self,
        file_content: bytes,
        filename: str
    ) -> ImportResult:
        """
        從檔案匯入資料

        Args:
            file_content: 檔案內容
            filename: 檔案名稱

        Returns:
            匯入結果
        """
        pass

    @abstractmethod
    async def process_row(
        self,
        row_num: int,
        row_data: Dict[str, Any]
    ) -> ImportRowResult:
        """
        處理單列資料

        Args:
            row_num: 列號
            row_data: 列資料

        Returns:
            處理結果
        """
        pass
