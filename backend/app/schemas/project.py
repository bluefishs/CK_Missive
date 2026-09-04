#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
承攬案件相關的Pydantic Schema定義

使用統一回應格式，支援分頁和舊資料相容性
"""

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator

from app.schemas.common import PaginatedResponse, PaginationMeta, SortOrder
from app.schemas._text_utils import normalize_cjk_compat
from app.schemas._text_utils import blank_to_none

class ProjectBase(BaseModel):
    # 2026-08-29（H2）：案號欄位一律去頭尾空白 —— 實測 id=190 的
    # project_code 帶前導空白（` CK2026_01_01_008`），所有以案號 join 的
    # 查詢整批失敗，而 promote 的 btrim 唯一性預檢反而擋得住「正確的」新號。
    # 資料已修，這裡擋住下一筆。
    @field_validator("project_code", "case_code", mode="before", check_fields=False)
    @classmethod
    def _strip_codes(cls, v):
        return v.strip() if isinstance(v, str) else v

    """承攬案件基礎Schema"""
    project_name: str = Field(..., min_length=1, max_length=500, description="案件名稱")
    year: Optional[int] = Field(None, description="年度 (民國或西元)")
    client_agency: Optional[str] = Field(None, max_length=200, description="委託單位")
    contract_doc_number: Optional[str] = Field(None, max_length=100, description="契約文號")
    project_code: Optional[str] = Field(None, max_length=100, description="成案專案編號 (成案後產生)")
    case_code: Optional[str] = Field(None, max_length=50, description="建案案號 (來自 pm_cases，跨模組橋樑)")
    category: Optional[str] = Field(None, max_length=50, description="計畫類別: 01委辦招標, 02承攬報價")
    case_nature: Optional[str] = Field(None, max_length=50, description="作業性質: 01地面測量~11其他類別")
    status: Optional[str] = Field(None, max_length=50, description="執行狀態: 執行中, 已結案")
    contract_amount: Optional[float] = Field(None, ge=0, description="契約金額")
    winning_amount: Optional[float] = Field(None, ge=0, description="得標金額")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    progress: Optional[int] = Field(None, ge=0, le=100, description="完成進度 (0-100)")
    project_path: Optional[str] = Field(None, max_length=500, description="專案路徑")
    notes: Optional[str] = Field(None, description="備註")
    description: Optional[str] = Field(None, description="專案描述")

    # ORM 對齊欄位 (v1.55.0)
    contract_number: Optional[str] = Field(None, max_length=100, description="合約編號")
    contract_type: Optional[str] = Field(None, max_length=50, description="合約類型")
    location: Optional[str] = Field(None, max_length=200, description="專案地點")
    procurement_method: Optional[str] = Field(None, max_length=100, description="採購方式")
    completion_date: Optional[date] = Field(None, description="完工日期")
    acceptance_date: Optional[date] = Field(None, description="驗收日期")
    completion_percentage: Optional[int] = Field(None, ge=0, le=100, description="完成百分比")
    warranty_end_date: Optional[date] = Field(None, description="保固結束日期")
    contact_person: Optional[str] = Field(None, max_length=100, description="聯絡人")
    contact_phone: Optional[str] = Field(None, max_length=50, description="聯絡電話")
    client_agency_id: Optional[int] = Field(None, description="委託機關ID")
    agency_contact_person: Optional[str] = Field(None, max_length=100, description="機關承辦人")
    agency_contact_phone: Optional[str] = Field(None, max_length=50, description="機關承辦電話")
    agency_contact_email: Optional[EmailStr] = Field(None, max_length=100, description="機關承辦Email")
    has_dispatch_management: Optional[bool] = Field(None, description="啟用派工管理功能")
    client_type: Optional[str] = Field(None, max_length=20, description="委託來源: agency=機關 vendor=廠商 other=其他")

    @field_validator('end_date') # 使用 field_validator
    @classmethod
    def validate_end_date(cls, v, info): # info 替代 values
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於起始日期')
        return v

    @field_validator('contract_amount') # 使用 field_validator
    @classmethod
    def validate_contract_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('合約金額不能為負數')
        return v

    # 2026-08-16：只正規化「看不見卻會壞比對」的相容字，**不動全形標點**。
    #
    # 實測 documents.subject 有 1560/2009（78%）帶 CJK 相容漢字
    # （年 U+F98E vs 標準 U+5E74）—— 字形一模一樣、長度一樣、md5 不同，
    # 於是所有以名稱比對的管控靜默失效（含承攬案件防重）。
    #
    # 刻意**不**套完整的 normalize_name：那會把全形括號（）轉半形()，
    # 而公文主旨常用全形括號 —— 那是**看得見的改變**，不該由正規化順手做掉。
    @field_validator('project_name', mode='before')
    @classmethod
    def _normalize_cjk(cls, v):
        return normalize_cjk_compat(v) if isinstance(v, str) else v

class ProjectCreate(ProjectBase):
    """建立承攬案件Schema"""
    pass

class ProjectUpdate(BaseModel):
    """更新承攬案件Schema"""
    # H2 同判準：案號去頭尾空白（見 ProjectBase 的說明）
    @field_validator("project_code", "case_code", mode="before", check_fields=False)
    @classmethod
    def _strip_codes(cls, v):
        return v.strip() if isinstance(v, str) else v

    project_name: Optional[str] = Field(None, min_length=1, max_length=500, description="案件名稱")
    year: Optional[int] = Field(None, description="年度 (民國或西元)")
    client_agency: Optional[str] = Field(None, max_length=200, description="委託單位")
    contract_doc_number: Optional[str] = Field(None, max_length=100, description="契約文號")
    project_code: Optional[str] = Field(None, max_length=100, description="成案專案編號")
    case_code: Optional[str] = Field(None, max_length=50, description="建案案號")
    category: Optional[str] = Field(None, max_length=50, description="計畫類別: 01委辦招標, 02承攬報價")
    case_nature: Optional[str] = Field(None, max_length=50, description="作業性質: 01地面測量~11其他類別")
    status: Optional[str] = Field(None, max_length=50, description="執行狀態: 執行中, 已結案")
    contract_amount: Optional[float] = Field(None, ge=0, description="契約金額")
    winning_amount: Optional[float] = Field(None, ge=0, description="得標金額")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    progress: Optional[int] = Field(None, ge=0, le=100, description="完成進度 (0-100)")
    project_path: Optional[str] = Field(None, max_length=500, description="專案路徑")
    notes: Optional[str] = Field(None, description="備註")
    description: Optional[str] = Field(None, description="專案描述")

    # ORM 對齊欄位 (v1.55.0)
    contract_number: Optional[str] = Field(None, max_length=100, description="合約編號")
    contract_type: Optional[str] = Field(None, max_length=50, description="合約類型")
    location: Optional[str] = Field(None, max_length=200, description="專案地點")
    procurement_method: Optional[str] = Field(None, max_length=100, description="採購方式")
    completion_date: Optional[date] = Field(None, description="完工日期")
    acceptance_date: Optional[date] = Field(None, description="驗收日期")
    completion_percentage: Optional[int] = Field(None, ge=0, le=100, description="完成百分比")
    warranty_end_date: Optional[date] = Field(None, description="保固結束日期")
    contact_person: Optional[str] = Field(None, max_length=100, description="聯絡人")
    contact_phone: Optional[str] = Field(None, max_length=50, description="聯絡電話")
    client_agency_id: Optional[int] = Field(None, description="委託機關ID")
    agency_contact_person: Optional[str] = Field(None, max_length=100, description="機關承辦人")
    agency_contact_phone: Optional[str] = Field(None, max_length=50, description="機關承辦電話")
    agency_contact_email: Optional[EmailStr] = Field(None, max_length=100, description="機關承辦Email")
    has_dispatch_management: Optional[bool] = Field(None, description="啟用派工管理功能")
    client_type: Optional[str] = Field(None, max_length=20, description="委託來源: agency=機關 vendor=廠商 other=其他")

    @field_validator('end_date') # 使用 field_validator
    @classmethod
    def validate_end_date(cls, v, info): # info 替代 values
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於起始日期')
        return v

    @field_validator('contract_amount') # 使用 field_validator
    @classmethod
    def validate_contract_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('合約金額不能為負數')
        return v

    # 空字串 → None：使用者清空選填欄位是正常操作，不該 422
    # （見 `_text_utils.blank_to_none`；2026-08-18 同型共 7 支）
    _blank = field_validator("project_name", "agency_contact_email", mode="before")(
        classmethod(lambda cls, v: blank_to_none(v))
    )

class ProjectResponse(ProjectBase):
    """承攬案件回應Schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    # 2026-07-31 L3 回指：本案由哪個標案而來（tender_records.id）。
    # 原本標案與案件雙向都看不到對方，人工建立的對應關係下次進來就消失。
    source_tender_id: Optional[int] = Field(None, description="來源標案 ID")

    model_config = ConfigDict(from_attributes=True) # 使用 model_config

class ProjectListResponse(PaginatedResponse):
    """
    承攬案件列表回應 Schema（統一分頁格式）

    回應格式：
    {
        "success": true,
        "items": [...],
        "pagination": { "total": 100, "page": 1, "limit": 20, ... }
    }
    """
    items: List[ProjectResponse] = Field(default=[], description="專案列表")


class ProjectOption(BaseModel):
    """承攬案件選項Schema (用於下拉選單)"""
    id: int
    project_name: str
    project_code: Optional[str] = None
    case_code: Optional[str] = None
    year: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class ProjectListQuery(BaseModel):
    """專案列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    # 2026-09-01 owner 裁示「先擴充限制比數，避免業務無法運作」：100 → 1000。
    # 承攬案件已 226 筆，而下拉需要一次拿完（Select 的搜尋是在拿到的那些上做的）。
    # 上限不是拿掉、是放到目前資料量的數倍 —— 完全不設限會讓誤傳的大 limit 拖垮查詢。
    limit: int = Field(default=20, ge=1, le=1000, description="每頁筆數")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    year: Optional[int] = Field(None, description="年度篩選")
    category: Optional[str] = Field(None, description="類別篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")


class ProjectStatisticsRequest(BaseModel):
    """承攬案件統計卡的範圍（2026-09-04 owner：統計卡要跟篩選條件動態調整）。

    year／category／search 決定分母（總計、狀態分組、合約總額都在這個範圍內算）；
    status 只套在合約總額——狀態卡本身就是互動篩選，點了某一張其他卡不能歸零（§2.6 ②）。
    """
    year: Optional[int] = Field(None, description="西元年度")
    category: Optional[str] = None
    status: Optional[str] = Field(None, description="只影響 total_contract_amount")
    search: Optional[str] = None
