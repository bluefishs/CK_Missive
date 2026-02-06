"""
統一篩選參數處理模組

提供前後端一致的篩選參數定義與驗證機制
解決以下問題：
1. 日期欄位命名不一致 (date_from vs doc_date_from)
2. 分類欄位值轉換 (send/receive vs 發文/收文)
3. 參數驗證與預設值處理

版本: 1.0.0
日期: 2026-01-08
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Union, Any
from datetime import date, datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CategoryMapping(str, Enum):
    """收發文分類對應"""
    SEND = "send"
    RECEIVE = "receive"

    def to_db_value(self) -> str:
        """轉換為資料庫值"""
        mapping = {
            CategoryMapping.SEND: "發文",
            CategoryMapping.RECEIVE: "收文"
        }
        return mapping[self]

    @classmethod
    def from_db_value(cls, value: str) -> Optional['CategoryMapping']:
        """從資料庫值轉換"""
        reverse_mapping = {
            "發文": cls.SEND,
            "收文": cls.RECEIVE
        }
        return reverse_mapping.get(value)


class DeliveryMethod(str, Enum):
    """發文形式"""
    ELECTRONIC = "電子交換"
    PAPER = "紙本郵寄"
    # 已移除 "電子+紙本" 選項


class UnifiedFilterParams(BaseModel):
    """
    統一篩選參數基礎類別

    統一處理前端傳入的各種篩選參數格式，
    自動轉換為後端服務層可用的標準格式
    """
    # 關鍵字搜尋 (支援多種命名)
    keyword: Optional[str] = Field(None, description="關鍵字搜尋")
    search: Optional[str] = Field(None, description="搜尋 (別名)")
    doc_number: Optional[str] = Field(None, description="公文字號搜尋")

    # 類型篩選
    doc_type: Optional[str] = Field(None, description="公文類型")
    year: Optional[int] = Field(None, description="年度")
    status: Optional[str] = Field(None, description="狀態")
    category: Optional[str] = Field(None, description="收發文分類 (send/receive)")

    # 單位篩選
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    contract_case: Optional[str] = Field(None, description="承攬案件")
    delivery_method: Optional[str] = Field(None, description="發文形式")

    # 日期篩選 (支援多種命名)
    date_from: Optional[str] = Field(None, description="日期起 (通用)")
    date_to: Optional[str] = Field(None, description="日期迄 (通用)")
    doc_date_from: Optional[str] = Field(None, description="公文日期起")
    doc_date_to: Optional[str] = Field(None, description="公文日期迄")

    # 排序
    sort_by: str = Field(default="updated_at", description="排序欄位")
    sort_order: str = Field(default="desc", description="排序方向")

    @field_validator('year', mode='before')
    @classmethod
    def parse_year(cls, v: Any) -> Optional[int]:
        """解析年度參數，支援字串和數字"""
        if v is None or v == '':
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @model_validator(mode='after')
    def normalize_params(self) -> 'UnifiedFilterParams':
        """正規化參數"""
        # 合併關鍵字搜尋
        if not self.keyword:
            self.keyword = self.search or self.doc_number

        # 合併日期參數
        if not self.date_from and self.doc_date_from:
            self.date_from = self.doc_date_from
        if not self.date_to and self.doc_date_to:
            self.date_to = self.doc_date_to

        return self

    def get_effective_keyword(self) -> Optional[str]:
        """取得有效的關鍵字搜尋值"""
        return self.keyword or self.search or self.doc_number

    def get_effective_date_from(self) -> Optional[str]:
        """取得有效的起始日期"""
        return self.date_from or self.doc_date_from

    def get_effective_date_to(self) -> Optional[str]:
        """取得有效的結束日期"""
        return self.date_to or self.doc_date_to

    def get_db_category(self) -> Optional[str]:
        """取得資料庫格式的分類值"""
        if not self.category:
            return None
        mapping = {'send': '發文', 'receive': '收文'}
        return mapping.get(self.category, self.category)

    def parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        將日期字串轉換為 date 物件

        支援格式：
        - YYYY-MM-DD
        - YYYY/MM/DD
        """
        if not date_str:
            return None
        try:
            # 統一處理分隔符
            normalized = date_str.replace('/', '-')
            return datetime.strptime(normalized, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"無法解析日期字串: {date_str}")
            return None


class DocumentFilterParams(UnifiedFilterParams):
    """
    公文篩選參數

    擴展統一篩選參數，加入公文特有的篩選欄位
    """
    assignee: Optional[str] = Field(None, description="承辦人")
    creator: Optional[str] = Field(None, description="建立者")
    doc_word: Optional[str] = Field(None, description="公文字")

    def to_service_filter(self) -> dict:
        """
        轉換為服務層篩選參數格式

        Returns:
            dict: 服務層可用的篩選參數字典
        """
        return {
            'keyword': self.get_effective_keyword(),
            'doc_type': self.doc_type,
            'year': self.year,
            'status': self.status,
            'category': self.get_db_category(),
            'sender': self.sender,
            'receiver': self.receiver,
            'contract_case': self.contract_case,
            'delivery_method': self.delivery_method,
            'date_from': self.get_effective_date_from(),
            'date_to': self.get_effective_date_to(),
            'assignee': self.assignee,
            'creator': self.creator,
            'doc_word': self.doc_word,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
        }


def validate_delivery_method(value: Optional[str]) -> Optional[str]:
    """
    驗證發文形式值

    Args:
        value: 前端傳入的發文形式值

    Returns:
        有效的發文形式值或 None
    """
    valid_methods = ['電子交換', '紙本郵寄']
    if value and value in valid_methods:
        return value
    return None


def validate_sort_field(field: str, allowed_fields: list[str]) -> str:
    """
    驗證排序欄位

    Args:
        field: 前端傳入的排序欄位
        allowed_fields: 允許的排序欄位列表

    Returns:
        有效的排序欄位或預設值
    """
    if field in allowed_fields:
        return field
    return 'updated_at'


# 公文允許的排序欄位
DOCUMENT_SORTABLE_FIELDS = [
    'id', 'doc_number', 'doc_date', 'receive_date', 'send_date',
    'subject', 'sender', 'receiver', 'status', 'category',
    'created_at', 'updated_at', 'auto_serial', 'delivery_method'
]
