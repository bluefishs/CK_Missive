"""
AI 服務相關 Pydantic Schema

Version: 1.2.0
Created: 2026-02-05
Updated: 2026-02-19 - 遷移 AI 端點 Request/Response Schema (SSOT)

功能:
- AI 端點 Request/Response Schema (從 document_ai.py 遷移)
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


class KeywordsValidationResponse(BaseModel):
    """AI 關鍵字提取回應 Schema（用於 _call_ai_with_validation 驗證）"""
    keywords: List[str] = Field(default=[], description="關鍵字列表")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# AI 端點 Request/Response Schema
# ============================================================================


class SummaryRequest(BaseModel):
    """摘要生成請求"""

    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    sender: Optional[str] = Field(None, description="發文機關")
    max_length: int = Field(100, ge=20, le=500, description="摘要最大長度")


class SummaryResponse(BaseModel):
    """摘要生成回應"""

    summary: str
    confidence: float
    source: str


class ClassifyRequest(BaseModel):
    """分類建議請求"""

    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    sender: Optional[str] = Field(None, description="發文機關")


class ClassifyResponse(BaseModel):
    """分類建議回應"""

    doc_type: str
    category: str
    doc_type_confidence: float
    category_confidence: float
    reasoning: Optional[str] = None
    source: str


class KeywordsRequest(BaseModel):
    """關鍵字提取請求"""

    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    max_keywords: int = Field(5, ge=1, le=10, description="最大關鍵字數量")


class KeywordsExtractResponse(BaseModel):
    """關鍵字提取回應"""

    keywords: List[str]
    confidence: float
    source: str


class AgencyCandidate(BaseModel):
    """機關候選項"""

    id: int
    name: str
    short_name: Optional[str] = None


class AgencyMatchRequest(BaseModel):
    """機關匹配請求"""

    agency_name: str = Field(..., description="輸入的機關名稱")
    candidates: Optional[List[AgencyCandidate]] = Field(
        None, description="候選機關列表"
    )


class AgencyMatchResult(BaseModel):
    """匹配結果"""

    id: int
    name: str
    score: float


class AgencyMatchResponse(BaseModel):
    """機關匹配回應"""

    best_match: Optional[AgencyMatchResult] = None
    alternatives: List[AgencyMatchResult] = []
    is_new: bool
    reasoning: Optional[str] = None
    source: str


class HealthResponse(BaseModel):
    """健康檢查回應"""

    groq: Dict[str, Any]
    ollama: Dict[str, Any]


class AIConfigResponse(BaseModel):
    """AI 配置回應"""

    enabled: bool = Field(description="AI 功能是否啟用")
    providers: Dict[str, Any] = Field(description="可用的 AI 提供者")
    rate_limit: Dict[str, int] = Field(description="速率限制設定")
    cache: Dict[str, Any] = Field(description="快取設定")
    features: Dict[str, Dict[str, Any]] = Field(description="各功能的配置")


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
    history_id: Optional[int] = Field(None, description="搜尋歷史 ID（用於回饋）")
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


class SearchFeedbackRequest(BaseModel):
    """搜尋回饋請求"""
    history_id: int = Field(..., description="搜尋歷史 ID")
    score: int = Field(..., ge=-1, le=1, description="回饋分數 (1=有用, -1=無用)")


class SearchFeedbackResponse(BaseModel):
    """搜尋回饋回應"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="訊息")


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
# 搜尋建議 Schema
# ============================================================================

class QuerySuggestionRequest(BaseModel):
    """搜尋建議請求"""
    prefix: str = Field("", max_length=200, description="查詢前綴 (空字串=僅回傳熱門)")
    limit: int = Field(default=8, ge=1, le=20, description="建議數量上限")


class QuerySuggestionItem(BaseModel):
    """單筆搜尋建議"""
    query: str = Field(..., description="建議的查詢文字")
    type: str = Field(..., description="建議類型: popular / history / related")
    count: int = Field(default=0, description="歷史搜尋次數")
    avg_results: float = Field(default=0.0, description="平均結果數")


class QuerySuggestionResponse(BaseModel):
    """搜尋建議回應"""
    suggestions: List[QuerySuggestionItem] = []


# ============================================================================
# 知識圖譜 Schema
# ============================================================================

class GraphNode(BaseModel):
    """圖譜節點"""
    id: str = Field(..., description="節點 ID (如 doc_1, project_2)")
    type: str = Field(..., description="節點類型: document/project/dispatch/agency/org/person/location/date/topic")
    label: str = Field(..., description="顯示文字")
    category: Optional[str] = Field(None, description="收文/發文 等分類")
    doc_number: Optional[str] = Field(None, description="公文字號")
    status: Optional[str] = Field(None, description="狀態")


class GraphEdge(BaseModel):
    """圖譜邊"""
    source: str = Field(..., description="起點節點 ID")
    target: str = Field(..., description="終點節點 ID")
    label: str = Field(default="", description="邊標籤")
    type: str = Field(default="relation", description="邊類型")


class SemanticSimilarRequest(BaseModel):
    """語意相似公文請求"""
    document_id: int = Field(..., description="來源公文 ID")
    limit: int = Field(default=5, ge=1, le=20, description="推薦筆數")


class SemanticSimilarItem(BaseModel):
    """語意相似公文項目"""
    id: int
    doc_number: Optional[str] = None
    subject: Optional[str] = None
    category: Optional[str] = None
    sender: Optional[str] = None
    doc_date: Optional[str] = None
    similarity: float = 0.0


class SemanticSimilarResponse(BaseModel):
    """語意相似公文回應"""
    source_id: int
    similar_documents: List[SemanticSimilarItem] = []


class EmbeddingStatsResponse(BaseModel):
    """Embedding 覆蓋率統計"""
    total_documents: int = 0
    with_embedding: int = 0
    without_embedding: int = 0
    coverage_percent: float = 0.0
    pgvector_enabled: bool = False


class EmbeddingBatchRequest(BaseModel):
    """Embedding 批次管線請求"""
    limit: int = Field(default=100, ge=1, le=5000, description="批次處理筆數上限")
    batch_size: int = Field(default=50, ge=10, le=200, description="每批 commit 大小")


class EmbeddingBatchResponse(BaseModel):
    """Embedding 批次管線回應"""
    success: bool = True
    message: str = ""
    success_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    elapsed_seconds: float = 0.0


class RelationGraphRequest(BaseModel):
    """關聯圖譜請求"""
    document_ids: List[int] = Field(default_factory=list, max_length=50, description="公文 ID 列表（空值=自動載入最近公文）")


class RelationGraphResponse(BaseModel):
    """關聯圖譜回應"""
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


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


# ============================================================================
# 實體提取 Schema (v1.0.0)
# ============================================================================


class EntityItem(BaseModel):
    """提取的實體"""
    id: int
    document_id: int
    entity_name: str
    entity_type: str = Field(description="org/person/project/location/date/topic")
    confidence: float
    context: Optional[str] = None
    extracted_at: Optional[str] = None


class EntityRelationItem(BaseModel):
    """實體關聯"""
    id: int
    source_entity_name: str
    source_entity_type: str
    target_entity_name: str
    target_entity_type: str
    relation_type: str
    relation_label: Optional[str] = None
    document_id: int
    confidence: float


class EntityExtractRequest(BaseModel):
    """單筆實體提取請求"""
    document_id: int = Field(..., description="公文 ID")
    force: bool = Field(False, description="是否強制重新提取")


class EntityExtractResponse(BaseModel):
    """單筆實體提取回應"""
    success: bool = True
    document_id: int
    entities_count: int = 0
    relations_count: int = 0
    skipped: bool = False
    reason: Optional[str] = None
    error: Optional[str] = None


class EntityBatchRequest(BaseModel):
    """批次實體提取請求"""
    limit: int = Field(default=50, ge=1, le=500, description="批次處理筆數上限")
    force: bool = Field(False, description="是否強制重新提取已有結果的公文")


class EntityBatchResponse(BaseModel):
    """批次實體提取回應"""
    success: bool = True
    message: str = ""
    total_processed: int = 0
    success_count: int = 0
    skip_count: int = 0
    error_count: int = 0


class EntityStatsResponse(BaseModel):
    """實體提取統計"""
    total_documents: int = 0
    extracted_documents: int = 0
    without_extraction: int = 0
    coverage_percent: float = 0.0
    total_entities: int = 0
    total_relations: int = 0
    entity_type_stats: Dict[str, int] = Field(default_factory=dict)
