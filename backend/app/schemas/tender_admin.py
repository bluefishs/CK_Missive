# -*- coding: utf-8 -*-
"""Tender Module Schemas — 標案搜尋/圖譜/訂閱/書籤 API requests.

R8b (v6.9 / 2026-05-09)：從 endpoints/tender_module/{search,graph_case,subscriptions}.py 遷出。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# search.py — 標案搜尋
# ============================================================================

class TenderSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100, description="搜尋關鍵字")
    page: int = Field(1, ge=1, le=100)
    category: Optional[str] = Field(None, description="分類: 工程/勞務/財物")
    search_type: Optional[str] = Field("title", description="搜尋模式: title/org/company")


class TenderDetailRequest(BaseModel):
    unit_id: str = Field(..., description="機關代碼 或 ezbid_id")
    job_number: Optional[str] = Field(None, description="標案案號（ezbid 時可為空）")


class TenderCompanySearchRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100)
    page: int = Field(1, ge=1, le=100)


class TenderRecommendRequest(BaseModel):
    keywords: Optional[List[str]] = Field(None, description="自訂關鍵字 (空=使用預設)")
    page: int = Field(1, ge=1)


# ============================================================================
# graph_case.py — 標案圖譜 + 建案
# ============================================================================

class TenderGraphRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    max_tenders: int = Field(20, ge=1, le=50)


class TenderCreateCaseRequest(BaseModel):
    """從標案建立 PM Case

    2026-07-31（L1 入口斷）：`job_number` 由必填改為選填 ——
    ezbid 來源 37,980 筆（全庫 42.7%）`job_number` 全為 NULL，
    原本必填等於把整個 ezbid 來源擋在鏈路之外。
    無 job_number 時以 `ezbid:{unit_id}` 作為識別碼（見 create-case）。
    """
    unit_id: str = Field(..., description="機關代碼（ezbid 來源為 ezbid_id）")
    job_number: Optional[str] = Field(None, description="標案案號（ezbid 來源無此值）")
    title: str = Field(..., description="標案名稱")
    unit_name: str = Field("", description="招標機關名稱")
    budget: Optional[str] = Field(None, description="預算金額")
    category: Optional[str] = Field(None, description="分類")
    tender_id: Optional[int] = Field(None, description="tender_records.id（供 L3 回指）")


class TenderRelatedCasesRequest(BaseModel):
    """建案前查詢可能相關的既有案件（L2 防重複）"""
    title: str = Field(..., description="標案名稱")
    unit_name: str = Field("", description="招標機關名稱")
    tender_id: Optional[int] = Field(None, description="tender_records.id")


class TenderLinkCaseRequest(BaseModel):
    """把標案關聯到既有案件（L2「關聯既有」而非重複新建）"""
    tender_id: int = Field(..., description="tender_records.id")
    target_type: str = Field(..., description="pm_case | contract_project")
    target_id: int = Field(..., description="目標案件 ID")


# ============================================================================
# subscriptions.py — 訂閱 + 書籤
# ============================================================================

class SubscriptionCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    notify_line: bool = True
    notify_system: bool = True


class SubscriptionUpdateRequest(BaseModel):
    id: int
    keyword: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    notify_line: Optional[bool] = None
    notify_system: Optional[bool] = None


class IdRequest(BaseModel):
    """通用 id 請求（2026-07-20：取代 subscriptions.py 端點內臨時 IdReq 反模式）。"""
    id: int


class BookmarkCreateRequest(BaseModel):
    unit_id: str
    job_number: str
    title: str
    unit_name: Optional[str] = None
    budget: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None


class BookmarkUpdateRequest(BaseModel):
    status: Optional[str] = None
    case_code: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# 標案 enrichment 人工複核（2026-08-17 由端點檔搬入，規範 §3）
# ---------------------------------------------------------------------------
class ListReviewRequest(BaseModel):
    status: str = "pending"  # pending / approved / rejected / all
    limit: int = 50
    offset: int = 0
    min_confidence: Optional[float] = None  # filter by confidence threshold


class ReviewActionRequest(BaseModel):
    review_id: int
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# 推薦關鍵字規則（2026-08-17 由端點檔搬入，規範 §3）
# ---------------------------------------------------------------------------
class KeywordRulesRequest(BaseModel):
    synonyms: list = []      # 同義詞群組 [[主詞, 同義詞...], ...]
    exclusions: list = []    # 負面關鍵字 [str, ...]
