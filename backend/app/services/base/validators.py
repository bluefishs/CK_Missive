# -*- coding: utf-8 -*-
"""
共用驗證器

提供統一的資料驗證規則，確保所有服務使用相同的驗證邏輯。
"""
from typing import Any, Optional, List
from datetime import datetime, date
import re


class DocumentValidators:
    """公文相關驗證器"""

    # 有效的公文類型白名單
    VALID_DOC_TYPES: List[str] = [
        '函',
        '開會通知單',
        '會勘通知單',
        '書函',
        '公告',
        '令',
        '通知'
    ]

    # 有效的類別
    VALID_CATEGORIES: List[str] = ['收文', '發文']

    # 有效的狀態
    VALID_STATUSES: List[str] = ['active', '待處理', '處理中', '已完成', '已歸檔']

    @classmethod
    def validate_doc_type(cls, value: str, auto_fix: bool = True) -> str:
        """
        驗證公文類型

        Args:
            value: 公文類型值
            auto_fix: 是否自動修正無效值為預設值

        Returns:
            驗證後的公文類型

        Raises:
            ValueError: 當 auto_fix=False 且值無效時
        """
        if not value:
            return '函' if auto_fix else ''

        value = str(value).strip()
        if value in cls.VALID_DOC_TYPES:
            return value

        if auto_fix:
            return '函'  # 預設為最常見的類型

        raise ValueError(f"無效的公文類型: {value}，有效值: {cls.VALID_DOC_TYPES}")

    @classmethod
    def validate_category(cls, value: str) -> str:
        """
        驗證公文類別

        Args:
            value: 類別值

        Returns:
            驗證後的類別

        Raises:
            ValueError: 當值無效時
        """
        if not value:
            raise ValueError("類別不可為空")

        value = str(value).strip()
        if value not in cls.VALID_CATEGORIES:
            raise ValueError(f"無效的類別: {value}，有效值: {cls.VALID_CATEGORIES}")

        return value

    @classmethod
    def validate_status(cls, value: str, default: str = 'active') -> str:
        """驗證狀態"""
        if not value:
            return default

        value = str(value).strip()
        if value in cls.VALID_STATUSES:
            return value

        return default


class StringCleaners:
    """字串清理工具"""

    # 無效字串值列表
    INVALID_VALUES = ('none', 'null', 'undefined', 'nan', '')

    @classmethod
    def clean_string(cls, value: Any) -> Optional[str]:
        """
        清理字串值

        避免 None 被轉為 'None' 字串，並去除首尾空白。

        Args:
            value: 任意值

        Returns:
            清理後的字串或 None
        """
        if value is None:
            return None

        text = str(value).strip()

        # 過濾無效值
        if text.lower() in cls.INVALID_VALUES:
            return None

        return text

    @classmethod
    def clean_agency_name(cls, name: str) -> Optional[str]:
        """
        清理機關名稱

        移除代碼後綴，例如 "桃園市政府(10002)" -> "桃園市政府"

        Args:
            name: 機關名稱

        Returns:
            清理後的機關名稱
        """
        if not name:
            return None

        name = cls.clean_string(name)
        if not name:
            return None

        # 移除括號內的代碼
        name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
        # 移除開頭的數字代碼
        name = re.sub(r'^\d+\s*', '', name)

        return name.strip() if name.strip() else None


class DateParsers:
    """日期解析工具"""

    # 支援的日期格式
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y.%m.%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
    ]

    @classmethod
    def parse_date(cls, value: Any) -> Optional[date]:
        """
        解析日期值

        支援多種格式：西元日期、民國日期。

        Args:
            value: 日期值（字串、date、datetime）

        Returns:
            解析後的 date 物件或 None
        """
        if not value:
            return None

        # 如果已經是 date 或 datetime 物件
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        # 字串解析
        value_str = str(value).strip()
        if not value_str or value_str.lower() in ('none', 'null', ''):
            return None

        # 嘗試標準日期格式
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        # 嘗試解析民國日期
        return cls._parse_roc_date(value_str)

    @classmethod
    def _parse_roc_date(cls, value_str: str) -> Optional[date]:
        """解析民國日期格式"""
        # 格式：中華民國114年1月8日 或 民國114年1月8日
        roc_patterns = [
            r'中華民國(\d{2,3})年(\d{1,2})月(\d{1,2})日',
            r'民國(\d{2,3})年(\d{1,2})月(\d{1,2})日',
            r'(\d{2,3})年(\d{1,2})月(\d{1,2})日',
        ]

        for pattern in roc_patterns:
            match = re.search(pattern, value_str)
            if match:
                try:
                    year = int(match.group(1)) + 1911
                    month = int(match.group(2))
                    day = int(match.group(3))
                    return date(year, month, day)
                except ValueError:
                    continue

        return None
