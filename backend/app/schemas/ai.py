"""
AI 服務相關 Pydantic Schema

Version: 1.0.0
Created: 2026-02-05

功能:
- 自然語言公文搜尋請求/回應
- 搜尋意圖解析結果
- 公文搜尋結果 (含附件)
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 自然語言搜尋相關 Schema
# ============================================================================


class ParsedSearchIntent(BaseModel):
    """
    AI 解析的搜尋意圖

    由 AI 從自然語言查詢中提取的結構化搜尋條件
    """
    keywords: Optional[List[str]] = Field(None, description="關鍵字陣列")
    doc_type: Optional[str] = Field(None, description="公文類型 (函/開會通知單/會勘通知單)")
    category: Optional[str] = Field(None, description="收發類別 (收文/發文)")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    date_from: Optional[str] = Field(None, description="日期起 (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="日期迄 (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="處理狀態 (待處理/已完成)")
    has_deadline: Optional[bool] = Field(None, description="是否有截止日期要求")
    contract_case: Optional[str] = Field(None, description="承攬案件名稱")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="解析信心度")

    model_config = ConfigDict(from_attributes=True)


class ParseIntentRequest(BaseModel):
    """意圖解析請求（僅解析，不執行搜尋）"""
    query: str = Field(..., min_length=1, max_length=500, description="自然語言查詢")


class ParseIntentResponse(BaseModel):
    """意圖解析回應"""
    success: bool = Field(default=True, description="是否成功")
    query: str = Field(..., description="原始查詢")
    parsed_intent: ParsedSearchIntent = Field(..., description="AI 解析的搜尋意圖")
    source: str = Field(default="ai", description="資料來源")
    error: Optional[str] = Field(None, description="錯誤訊息")


class NaturalSearchRequest(BaseModel):
    """自然語言搜尋請求"""
    query: str = Field(..., min_length=1, max_length=500, description="自然語言查詢")
    max_results: int = Field(default=20, ge=1, le=100, description="最大結果數")
    offset: int = Field(default=0, ge=0, description="偏移量（分頁用）")
    include_attachments: bool = Field(default=True, description="是否包含附件資訊")


class AttachmentInfo(BaseModel):
    """附件簡要資訊"""
    id: int = Field(..., description="附件 ID")
    file_name: str = Field(..., description="儲存檔案名稱")
    original_name: Optional[str] = Field(None, description="原始檔案名稱")
    file_size: Optional[int] = Field(None, description="檔案大小 (bytes)")
    mime_type: Optional[str] = Field(None, description="MIME 類型")
    created_at: Optional[datetime] = Field(None, description="上傳時間")

    model_config = ConfigDict(from_attributes=True)


class DocumentSearchResult(BaseModel):
    """公文搜尋結果項目"""
    id: int = Field(..., description="公文 ID")
    auto_serial: Optional[str] = Field(None, description="流水序號")
    doc_number: str = Field(..., description="公文字號")
    subject: str = Field(..., description="主旨")
    doc_type: Optional[str] = Field(None, description="公文類型")
    category: Optional[str] = Field(None, description="收發類別")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date: Optional[date] = Field(None, description="公文日期")
    status: Optional[str] = Field(None, description="處理狀態")
    contract_project_name: Optional[str] = Field(None, description="承攬案件名稱")
    ck_note: Optional[str] = Field(None, description="乾坤備註")

    # 附件資訊
    attachment_count: int = Field(default=0, description="附件數量")
    attachments: List[AttachmentInfo] = Field(default=[], description="附件列表")

    # 時間戳
    created_at: Optional[datetime] = Field(None, description="建立時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    model_config = ConfigDict(from_attributes=True)


class ClassificationResponse(BaseModel):
    """AI 分類建議回應 Schema（用於 _call_ai_with_validation 驗證）"""
    doc_type: Optional[str] = Field(None, description="公文類型")
    category: Optional[str] = Field(None, description="收發類別 (收文/發文)")
    doc_type_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="類型信心度")
    category_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="類別信心度")
    reasoning: Optional[str] = Field(None, description="判斷理由")

    model_config = ConfigDict(from_attributes=True)


class KeywordsResponse(BaseModel):
    """AI 關鍵字提取回應 Schema（用於 _call_ai_with_validation 驗證）"""
    keywords: List[str] = Field(default=[], description="關鍵字列表")

    model_config = ConfigDict(from_attributes=True)


class NaturalSearchResponse(BaseModel):
    """自然語言搜尋回應"""
    success: bool = Field(default=True, description="是否成功")
    query: str = Field(..., description="原始查詢")
    parsed_intent: ParsedSearchIntent = Field(..., description="AI 解析的搜尋意圖")
    results: List[DocumentSearchResult] = Field(default=[], description="搜尋結果")
    total: int = Field(default=0, description="總筆數")
    source: str = Field(default="ai", description="資料來源 (ai/fallback/rate_limited)")
    search_strategy: str = Field(
        default="keyword",
        description="搜尋策略 (keyword/similarity/hybrid/semantic)"
    )
    synonym_expanded: bool = Field(
        default=False,
        description="是否經過同義詞擴展"
    )
    error: Optional[str] = Field(None, description="錯誤訊息")

    model_config = ConfigDict(from_attributes=True)
