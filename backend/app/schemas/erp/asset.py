"""資產管理 Schema"""
from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar, Optional, List
from pydantic import BaseModel, Field, ConfigDict


# --- Request ---
class AssetCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_code: Optional[str] = Field(None, max_length=50, description="資產編號 (空值時自動生成)")
    name: str = Field(..., max_length=200)
    category: str = Field(default="equipment", pattern=r"^(equipment|vehicle|instrument|furniture|other)$")
    brand: Optional[str] = None
    asset_model: Optional[str] = Field(None, description="型號")
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_amount: Decimal = Decimal("0")
    current_value: Optional[Decimal] = None
    depreciation_rate: Decimal = Decimal("0")
    expense_invoice_id: Optional[int] = None
    case_code: Optional[str] = None
    status: str = Field(default="in_use", pattern=r"^(in_use|maintenance|idle|disposed|lost)$")
    location: Optional[str] = None
    custodian: Optional[str] = None
    notes: Optional[str] = None


class AssetUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    asset_model: Optional[str] = Field(None, description="型號")
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_amount: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    depreciation_rate: Optional[Decimal] = None
    expense_invoice_id: Optional[int] = None
    case_code: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    custodian: Optional[str] = None
    photo_path: Optional[str] = None
    notes: Optional[str] = None


class AssetListRequest(BaseModel):
    """資產列表查詢。**統計端點（/stats）吃同一份**（2026-09-09 weekly 133）：卡片是列表的分母，
    篩選條件只宣告一次，`AssetRepository.filters()` 把它翻成 SQL，列表與統計共用。"""
    category: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None
    case_code: Optional[str] = None
    skip: int = 0
    limit: int = 50

    #: weekly 133：統計卡不收的欄位與理由。資產頁的卡片本身就是「各狀態的計數」——
    #: 點「使用中」篩列表時，卡片不能跟著只剩使用中（§2.6 ②）。
    STATS_EXEMPT: ClassVar[dict[str, str]] = {"status": "卡片本身是各狀態計數，不隨自己的篩選歸零"}


class AssetBatchInventoryRequest(BaseModel):
    """批次盤點請求"""
    asset_ids: List[int] = Field(..., min_length=1)
    operator: str = Field(..., max_length=100)
    notes: Optional[str] = None


class AssetLogCreateRequest(BaseModel):
    asset_id: int
    action: str = Field(..., pattern=r"^(purchase|repair|maintain|transfer|dispose|inspect|other)$")
    action_date: date
    description: Optional[str] = None
    cost: Decimal = Decimal("0")
    expense_invoice_id: Optional[int] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    operator: Optional[str] = None
    notes: Optional[str] = None


class AssetLogListRequest(BaseModel):
    asset_id: int
    action: Optional[str] = None
    skip: int = 0
    limit: int = 50


# --- Response ---
class AssetResponse(BaseModel):
    id: int
    asset_code: str
    name: str
    category: str
    brand: Optional[str] = None
    asset_model: Optional[str] = Field(None, validation_alias="model", description="型號")
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_amount: Decimal = Decimal("0")
    current_value: Optional[Decimal] = None
    depreciation_rate: Decimal = Decimal("0")
    expense_invoice_id: Optional[int] = None
    case_code: Optional[str] = None
    status: str = "in_use"
    location: Optional[str] = None
    custodian: Optional[str] = None
    photo_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AssetLogResponse(BaseModel):
    id: int
    asset_id: int
    action: str
    action_date: date
    description: Optional[str] = None
    cost: Decimal = Decimal("0")
    expense_invoice_id: Optional[int] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    operator: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AssetStatsResponse(BaseModel):
    total_count: int = 0
    in_use: int = 0
    maintenance: int = 0
    idle: int = 0
    disposed: int = 0
    total_value: Decimal = Decimal("0")
    by_category: dict = {}
