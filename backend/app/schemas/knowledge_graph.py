"""
知識圖譜 Pydantic Schema

Phase 2 正規化實體查詢/管理的 Request/Response Schema。
對應前端型別: frontend/src/api/ai/types.ts (KG* 系列)

Version: 1.0.0
Created: 2026-02-24
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# 實體搜尋
# ============================================================================


class KGEntitySearchRequest(BaseModel):
    """搜尋正規化實體"""
    query: str = Field(..., min_length=1, max_length=200, description="搜尋關鍵字")
    entity_type: Optional[str] = Field(None, description="實體類型篩選")
    limit: int = Field(default=20, ge=1, le=100, description="最大結果數")


class KGEntityItem(BaseModel):
    """正規化實體項目"""
    id: int
    canonical_name: str
    entity_type: str
    mention_count: int = 0
    alias_count: int = 0
    description: Optional[str] = None
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None


class KGEntitySearchResponse(BaseModel):
    """搜尋正規化實體回應"""
    success: bool = True
    results: List[KGEntityItem] = []
    total: int = 0


# ============================================================================
# 實體鄰居
# ============================================================================


class KGNeighborsRequest(BaseModel):
    """K 跳鄰居查詢"""
    entity_id: int = Field(..., description="實體 ID")
    max_hops: int = Field(default=2, ge=1, le=4, description="最大跳數")
    limit: int = Field(default=50, ge=1, le=200, description="最大鄰居數")


class KGGraphNode(BaseModel):
    """圖譜鄰居節點"""
    id: int
    name: str
    type: str
    mention_count: int = 0
    hop: int = 0


class KGGraphEdge(BaseModel):
    """圖譜鄰居邊"""
    source_id: int
    target_id: int
    relation_type: str
    relation_label: Optional[str] = None
    weight: float = 1.0


class KGNeighborsResponse(BaseModel):
    """K 跳鄰居回應"""
    success: bool = True
    nodes: List[KGGraphNode] = []
    edges: List[KGGraphEdge] = []


# ============================================================================
# 最短路徑
# ============================================================================


class KGShortestPathRequest(BaseModel):
    """最短路徑查詢"""
    source_id: int = Field(..., description="起始實體 ID")
    target_id: int = Field(..., description="目標實體 ID")
    max_hops: int = Field(default=5, ge=1, le=6, description="最大跳數")


class KGPathNode(BaseModel):
    """路徑上的節點"""
    id: int
    name: str
    type: str


class KGShortestPathResponse(BaseModel):
    """最短路徑回應"""
    success: bool = True
    found: bool = False
    depth: int = 0
    path: List[KGPathNode] = []
    relations: List[str] = []


# ============================================================================
# 實體詳情
# ============================================================================


class KGEntityDetailRequest(BaseModel):
    """實體詳情查詢"""
    entity_id: int = Field(..., description="實體 ID")


class KGEntityDocument(BaseModel):
    """實體關聯的公文"""
    document_id: int
    mention_text: str
    confidence: float = 0.0
    subject: Optional[str] = None
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None


class KGEntityRelationship(BaseModel):
    """實體關係"""
    id: int
    direction: str = Field(description="outgoing/incoming")
    relation_type: str
    relation_label: Optional[str] = None
    target_name: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    weight: float = 1.0
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    document_count: int = 0


class KGEntityDetailResponse(BaseModel):
    """實體詳情回應"""
    success: bool = True
    id: int
    canonical_name: str
    entity_type: str
    description: Optional[str] = None
    alias_count: int = 0
    mention_count: int = 0
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    aliases: List[str] = []
    documents: List[KGEntityDocument] = []
    relationships: List[KGEntityRelationship] = []


# ============================================================================
# 時間軸
# ============================================================================


class KGTimelineRequest(BaseModel):
    """實體時間軸查詢"""
    entity_id: int = Field(..., description="實體 ID")


class KGTimelineItem(BaseModel):
    """時間軸關係項目"""
    id: int
    direction: str
    relation_type: str
    relation_label: Optional[str] = None
    other_name: str
    other_type: str
    weight: float = 1.0
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    invalidated_at: Optional[str] = None
    document_count: int = 0


class KGTimelineResponse(BaseModel):
    """實體時間軸回應"""
    success: bool = True
    entity_id: int
    timeline: List[KGTimelineItem] = []


# ============================================================================
# 高頻實體
# ============================================================================


class KGTopEntitiesRequest(BaseModel):
    """高頻實體排名"""
    entity_type: Optional[str] = Field(None, description="實體類型篩選")
    sort_by: str = Field(default="mention_count", description="排序欄位")
    limit: int = Field(default=20, ge=1, le=100, description="最大結果數")


class KGTopEntitiesResponse(BaseModel):
    """高頻實體排名回應"""
    success: bool = True
    entities: List[KGEntityItem] = []


# ============================================================================
# 入圖管線
# ============================================================================


class KGIngestRequest(BaseModel):
    """入圖管線請求"""
    document_id: Optional[int] = Field(None, description="指定公文 ID（空值=批次入圖）")
    limit: int = Field(default=50, ge=1, le=200, description="批次處理筆數上限")
    force: bool = Field(False, description="是否強制重新入圖")


class KGIngestResponse(BaseModel):
    """入圖管線回應"""
    success: bool = True
    status: str = ""
    document_id: Optional[int] = None
    entities_found: Optional[int] = None
    entities_new: Optional[int] = None
    entities_merged: Optional[int] = None
    relations_found: Optional[int] = None
    processing_ms: Optional[int] = None
    total_processed: Optional[int] = None
    success_count: Optional[int] = None
    skip_count: Optional[int] = None
    error_count: Optional[int] = None
    message: Optional[str] = None


# ============================================================================
# 圖譜統計
# ============================================================================


class KGGraphStatsResponse(BaseModel):
    """圖譜統計回應"""
    success: bool = True
    total_entities: int = 0
    total_aliases: int = 0
    total_mentions: int = 0
    total_relationships: int = 0
    total_ingestion_events: int = 0
    entity_type_distribution: Dict[str, int] = Field(default_factory=dict)


# ============================================================================
# 實體合併
# ============================================================================


class KGMergeEntitiesRequest(BaseModel):
    """合併實體請求"""
    keep_id: int = Field(..., description="保留的實體 ID")
    merge_id: int = Field(..., description="被合併的實體 ID")


class KGMergeEntitiesResponse(BaseModel):
    """合併實體回應"""
    success: bool = True
    message: str = ""
    entity_id: int = 0


# ============================================================================
# Code Wiki 代碼圖譜
# ============================================================================


VALID_CODE_ENTITY_TYPES = {"py_module", "py_class", "py_function", "db_table"}


class KGCodeWikiRequest(BaseModel):
    """Code Wiki 圖譜請求"""
    entity_types: List[str] = Field(
        default=["py_module"],
        description="要顯示的代碼實體類型: py_module/py_class/py_function/db_table",
    )
    module_prefix: Optional[str] = Field(
        None,
        description="模組路徑前綴篩選 (如 'app.services')",
    )
    limit: int = Field(default=500, ge=1, le=2000, description="最大節點數")

    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v: List[str]) -> List[str]:
        invalid = [t for t in v if t not in VALID_CODE_ENTITY_TYPES]
        if invalid:
            raise ValueError(
                f"無效的實體類型: {invalid}。允許值: {sorted(VALID_CODE_ENTITY_TYPES)}"
            )
        return v


class KGCodeWikiResponse(BaseModel):
    """Code Wiki 圖譜回應"""
    success: bool = True
    nodes: List[Dict] = Field(default_factory=list)
    edges: List[Dict] = Field(default_factory=list)


class KGCodeGraphIngestRequest(BaseModel):
    """Code Graph 入圖觸發請求"""
    clean: bool = Field(default=False, description="是否先清除舊資料再重建")
    include_schema: bool = Field(default=True, description="是否包含 DB Schema 反射")
    include_frontend: bool = Field(default=True, description="是否包含前端 TypeScript/React 分析")
    incremental: bool = Field(default=True, description="增量模式：跳過未變更的檔案")


class KGCodeGraphIngestResponse(BaseModel):
    """Code Graph 入圖觸發回應"""
    success: bool = True
    message: str = ""
    modules: int = 0
    classes: int = 0
    functions: int = 0
    tables: int = 0
    ts_modules: int = 0
    ts_components: int = 0
    ts_hooks: int = 0
    relations: int = 0
    errors: int = 0
    skipped: int = 0
    elapsed_seconds: float = 0.0


class KGCycleDetectionResponse(BaseModel):
    """循環依賴偵測回應"""
    success: bool = True
    total_modules: int = 0
    total_import_edges: int = 0
    cycles_found: int = 0
    cycles: List[List[str]] = Field(default_factory=list)


class KGArchitectureAnalysisResponse(BaseModel):
    """架構分析回應"""
    success: bool = True
    complexity_hotspots: List[Dict] = Field(default_factory=list, description="高耦合模組（出向依賴最多）")
    hub_modules: List[Dict] = Field(default_factory=list, description="樞紐模組（被匯入最多）")
    large_modules: List[Dict] = Field(default_factory=list, description="大型模組（行數最多）")
    orphan_modules: List[str] = Field(default_factory=list, description="孤立模組（無入向匯入）")
    god_classes: List[Dict] = Field(default_factory=list, description="巨型類別（方法數最多）")
    summary: Dict = Field(default_factory=dict, description="概要統計")


class KGJsonImportRequest(BaseModel):
    """JSON 圖譜匯入請求 — 讀取本地 GitNexus 產生的 knowledge_graph.json"""
    file_path: str = Field(
        default="knowledge_graph.json",
        description="相對於專案根目錄的 JSON 檔案路徑",
    )
    clean: bool = Field(default=True, description="匯入前是否先清除既有 code_graph 資料")


class KGJsonImportResponse(BaseModel):
    """JSON 圖譜匯入回應"""
    success: bool = True
    message: str = ""
    nodes_imported: int = 0
    edges_imported: int = 0
    elapsed_seconds: float = 0.0
