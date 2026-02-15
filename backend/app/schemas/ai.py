"""
AI 服務相關 Pydantic Schema

Version: 1.1.0
Created: 2026-02-05
Updated: 2026-02-09 - 新增 related_entity 實體過濾欄位

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
    related_entity: Optional[str] = Field(
        None,
        description="關聯實體類型 (dispatch_order=派工單關聯公文, project=專案關聯公文)"
    )
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


# ============================================================================
# 同義詞管理 Schema (v1.1.0 新增)
# ============================================================================


class AISynonymBase(BaseModel):
    """同義詞群組基礎 Schema"""
    category: str = Field(..., min_length=1, max_length=100, description="分類")
    words: str = Field(..., min_length=1, description="同義詞列表，逗號分隔")
    is_active: bool = Field(default=True, description="是否啟用")


class AISynonymCreate(AISynonymBase):
    """建立同義詞群組請求"""
    pass


class AISynonymUpdate(BaseModel):
    """更新同義詞群組請求"""
    id: int = Field(..., description="同義詞群組 ID")
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="分類")
    words: Optional[str] = Field(None, min_length=1, description="同義詞列表，逗號分隔")
    is_active: Optional[bool] = Field(None, description="是否啟用")


class AISynonymResponse(AISynonymBase):
    """同義詞群組回應"""
    id: int = Field(..., description="同義詞群組 ID")
    created_at: Optional[datetime] = Field(None, description="建立時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    model_config = ConfigDict(from_attributes=True)


class AISynonymListRequest(BaseModel):
    """同義詞列表查詢請求"""
    category: Optional[str] = Field(None, description="分類篩選")
    is_active: Optional[bool] = Field(None, description="啟用狀態篩選")


class AISynonymListResponse(BaseModel):
    """同義詞列表回應"""
    items: List[AISynonymResponse] = Field(default=[], description="同義詞群組列表")
    total: int = Field(default=0, description="總筆數")
    categories: List[str] = Field(default=[], description="所有分類列表")


class AISynonymDeleteRequest(BaseModel):
    """刪除同義詞群組請求"""
    id: int = Field(..., description="同義詞群組 ID")


class AISynonymReloadResponse(BaseModel):
    """重新載入同義詞回應"""
    success: bool = Field(default=True, description="是否成功")
    total_groups: int = Field(default=0, description="載入的同義詞群組數")
    total_words: int = Field(default=0, description="載入的詞彙總數")
    message: str = Field(default="", description="訊息")


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


# ============================================================================
# 搜尋歷史相關 Schema (v1.2.0)
# ============================================================================


class SearchHistoryItem(BaseModel):
    """搜尋歷史項目"""
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    query: str
    parsed_intent: Optional[Dict[str, Any]] = None
    results_count: int = 0
    search_strategy: Optional[str] = None
    source: Optional[str] = None
    synonym_expanded: bool = False
    related_entity: Optional[str] = None
    latency_ms: Optional[int] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SearchHistoryListRequest(BaseModel):
    """搜尋歷史列表請求"""
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    date_from: Optional[str] = Field(None, description="起始日期 YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="結束日期 YYYY-MM-DD")
    search_strategy: Optional[str] = Field(None, description="搜尋策略篩選")
    source: Optional[str] = Field(None, description="來源篩選")
    keyword: Optional[str] = Field(None, max_length=200, description="查詢關鍵字篩選")


class SearchHistoryListResponse(BaseModel):
    """搜尋歷史列表回應"""
    items: List[SearchHistoryItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class DailyTrend(BaseModel):
    """日趨勢項目"""
    date: str
    count: int


class TopQuery(BaseModel):
    """熱門查詢項目"""
    query: str
    count: int
    avg_results: float


class ClearSearchHistoryRequest(BaseModel):
    """清除搜尋歷史請求"""
    before_date: Optional[str] = Field(
        None, description="清除此日期（含）之前的記錄，格式 YYYY-MM-DD。未指定則清除全部。"
    )


class ClearSearchHistoryResponse(BaseModel):
    """清除搜尋歷史回應"""
    success: bool = Field(default=True, description="是否成功")
    deleted_count: int = Field(default=0, description="刪除的記錄數")
    error: Optional[str] = Field(None, description="錯誤訊息")


class SearchStatsResponse(BaseModel):
    """搜尋統計回應"""
    total_searches: int = 0
    today_searches: int = 0
    rule_engine_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    daily_trend: List[DailyTrend] = []
    top_queries: List[TopQuery] = []
    strategy_distribution: Dict[str, int] = {}
    source_distribution: Dict[str, int] = {}
    entity_distribution: Dict[str, int] = {}


# ============================================================================
# Prompt 版本管理 Schema (v2.0.0)
# ============================================================================


class PromptVersionItem(BaseModel):
    """Prompt 版本項目"""
    id: int
    feature: str
    version: int
    system_prompt: str
    user_template: Optional[str] = None
    is_active: bool
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class PromptListRequest(BaseModel):
    """列出 prompt 版本請求"""
    feature: Optional[str] = Field(None, description="按功能名稱篩選")


class PromptListResponse(BaseModel):
    """列出 prompt 版本回應"""
    items: List[PromptVersionItem]
    total: int
    features: List[str] = Field(description="所有可用的功能名稱")


class PromptCreateRequest(BaseModel):
    """新增 prompt 版本請求"""
    feature: str = Field(..., description="功能名稱")
    system_prompt: str = Field(..., min_length=1, description="系統提示詞")
    user_template: Optional[str] = Field(None, description="使用者提示詞模板")
    description: Optional[str] = Field(None, description="版本說明")
    activate: bool = Field(False, description="是否立即啟用")


class PromptCreateResponse(BaseModel):
    """新增 prompt 版本回應"""
    success: bool
    item: PromptVersionItem
    message: str


class PromptActivateRequest(BaseModel):
    """啟用 prompt 版本請求"""
    id: int = Field(..., description="要啟用的版本 ID")


class PromptActivateResponse(BaseModel):
    """啟用 prompt 版本回應"""
    success: bool
    message: str
    activated: PromptVersionItem


class PromptCompareRequest(BaseModel):
    """比較 prompt 版本請求"""
    id_a: int = Field(..., description="版本 A 的 ID")
    id_b: int = Field(..., description="版本 B 的 ID")


class PromptDiff(BaseModel):
    """版本差異"""
    field: str
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    changed: bool


class PromptCompareResponse(BaseModel):
    """比較 prompt 版本回應"""
    version_a: PromptVersionItem
    version_b: PromptVersionItem
    diffs: List[PromptDiff]
