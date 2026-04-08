"""
知識圖譜 Pydantic Schema

Phase 2 正規化實體查詢/管理的 Request/Response Schema。
Phase 3 跨專案聯邦 Federation 的 Contribution/Search Schema。
對應前端型別: frontend/src/api/ai/types.ts (KG* 系列)

Version: 1.1.0
Created: 2026-02-24
Updated: 2026-03-22 — KG Federation schemas
"""
from typing import Any, Dict, List, Optional

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
    source_project: str = "ck-missive"


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
# 時序聚合
# ============================================================================


class KGTimelineAggregateRequest(BaseModel):
    """跨實體時序聚合查詢"""
    relation_type: Optional[str] = Field(None, description="關係類型篩選 (如 correspondence)")
    entity_type: Optional[str] = Field(None, description="實體類型篩選")
    granularity: str = Field("month", description="聚合粒度: month / quarter / year")


class KGTimelineAggregateBucket(BaseModel):
    """時序聚合分桶"""
    period: str
    count: int = 0
    total_weight: float = 0.0
    entity_count: int = 0


class KGTimelineAggregateResponse(BaseModel):
    """時序聚合回應"""
    success: bool = True
    granularity: str = "month"
    buckets: List[KGTimelineAggregateBucket] = []
    total_relationships: int = 0


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


class KGEntityGraphRequest(BaseModel):
    """實體圖譜請求"""
    entity_types: Optional[List[str]] = Field(default=None, description="篩選實體類型")
    min_mentions: int = Field(default=2, ge=1, description="最低提及次數")
    limit: int = Field(default=200, ge=1, le=500, description="最大實體數量")
    year: Optional[int] = Field(default=None, description="民國年篩選（如 114），只含該年度公文相關的實體")
    collapse_agency: bool = Field(default=True, description="是否折疊子機關到上級機關")


class KGEntityGraphResponse(BaseModel):
    """實體圖譜回應"""
    success: bool = True
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class KGGraphStatsResponse(BaseModel):
    """圖譜統計回應"""
    success: bool = True
    total_entities: int = 0
    total_code_entities: int = 0
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


class KGModuleOverviewResponse(BaseModel):
    """模組架構概覽回應"""
    success: bool = True
    layers: Dict[str, Any] = Field(default_factory=dict, description="各架構層模組統計")
    db_tables: List[Dict[str, Any]] = Field(default_factory=list, description="資料表 ERD 摘要")
    summary: Dict[str, Any] = Field(default_factory=dict, description="總計數")


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


# ============================================================================
# 資料庫 Schema 反射
# ============================================================================


class UnifiedGraphSearchRequest(BaseModel):
    """跨圖譜統一搜尋請求 — 7 大圖譜"""
    query: str = Field(..., min_length=2, max_length=200, description="搜尋關鍵字")
    include_kg: bool = Field(True, description="搜尋知識圖譜 (KG-1)")
    include_code: bool = Field(True, description="搜尋代碼圖譜 (KG-3)")
    include_db: bool = Field(True, description="搜尋資料庫圖譜")
    include_erp: bool = Field(True, description="搜尋 ERP 財務圖譜 (KG-7)")
    include_tender: bool = Field(True, description="搜尋標案圖譜 (KG-5)")
    limit_per_graph: int = Field(default=5, ge=1, le=20, description="每個圖譜最大結果數")


class UnifiedGraphResult(BaseModel):
    """統一圖譜搜尋結果項目"""
    source: str = Field(..., description="來源圖譜: kg / code / db / erp / tender")
    entity_type: str = Field(..., description="實體類型")
    name: str = Field(..., description="實體名稱")
    description: str = ""
    relevance: float = 1.0


class UnifiedGraphSearchResponse(BaseModel):
    """跨圖譜統一搜尋回應"""
    success: bool = True
    results: List[UnifiedGraphResult] = []
    total: int = 0
    sources_queried: List[str] = []


# ============================================================================
# 資料庫 Schema 反射
# ============================================================================


class KGDbColumnInfo(BaseModel):
    """資料表欄位資訊"""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False


class KGDbForeignKey(BaseModel):
    """外鍵資訊"""
    constrained_columns: List[str] = []
    referred_table: str = ""
    referred_columns: List[str] = []


class KGDbIndex(BaseModel):
    """索引資訊"""
    name: str = ""
    columns: List[str] = []
    unique: bool = False


class KGDbTableInfo(BaseModel):
    """資料表完整資訊"""
    name: str
    columns: List[KGDbColumnInfo] = []
    primary_key_columns: List[str] = []
    foreign_keys: List[KGDbForeignKey] = []
    indexes: List[KGDbIndex] = []
    unique_constraints: List[KGDbIndex] = []


class KGDbSchemaResponse(BaseModel):
    """資料庫 Schema 反射回應"""
    success: bool = True
    tables: List[KGDbTableInfo] = []
    error: Optional[str] = None


class KGDbGraphNode(BaseModel):
    """DB ER 圖譜節點"""
    id: str
    label: str
    type: str = "db_table"
    category: str = "database"
    status: Optional[str] = None
    mention_count: int = 0


class KGDbGraphEdge(BaseModel):
    """DB ER 圖譜邊"""
    source: str
    target: str
    label: str = ""
    type: str = "foreign_key"
    weight: int = 1


class KGDbGraphResponse(BaseModel):
    """資料庫 ER 圖譜回應"""
    success: bool = True
    nodes: List[KGDbGraphNode] = []
    edges: List[KGDbGraphEdge] = []
    error: Optional[str] = None


# ============================================================================
# 跨專案聯邦 (KG Federation, v1.1.0)
# ============================================================================


class EntityContribution(BaseModel):
    """單一實體貢獻（由外部專案提交）"""
    entity_type: str = Field(..., min_length=1, max_length=50, description="實體類型")
    canonical_name: str = Field(..., min_length=1, max_length=300, description="正規化名稱")
    external_id: str = Field(..., min_length=1, max_length=255, description="來源專案原始 ID")
    description: Optional[str] = Field(None, max_length=500, description="實體描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元資料 (座標/嚴重度/etc)")
    aliases: List[str] = Field(default_factory=list, description="別名列表")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        from app.core.constants import CROSS_PROJECT_ENTITY_TYPES
        if v not in CROSS_PROJECT_ENTITY_TYPES:
            raise ValueError(
                f"無效的實體類型: '{v}', 允許: {sorted(CROSS_PROJECT_ENTITY_TYPES)}"
            )
        return v

    model_config = {"extra": "ignore"}


class RelationContribution(BaseModel):
    """單一關係貢獻（由外部專案提交）"""
    source_external_id: str = Field(..., description="來源實體的 external_id")
    source_type: str = Field(..., description="來源實體類型")
    target_external_id: str = Field(..., description="目標實體的 external_id")
    target_type: str = Field(..., description="目標實體類型")
    relation_type: str = Field(..., max_length=100, description="關係類型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="關係元資料")

    @field_validator("source_type", "target_type")
    @classmethod
    def validate_entity_types(cls, v: str) -> str:
        from app.core.constants import CROSS_PROJECT_ENTITY_TYPES
        if v not in CROSS_PROJECT_ENTITY_TYPES:
            raise ValueError(
                f"無效的實體類型: '{v}', 允許: {sorted(CROSS_PROJECT_ENTITY_TYPES)}"
            )
        return v

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: str) -> str:
        from app.core.constants import CROSS_PROJECT_RELATION_TYPES
        if v not in CROSS_PROJECT_RELATION_TYPES:
            raise ValueError(
                f"無效的關係類型: '{v}', 允許: {sorted(CROSS_PROJECT_RELATION_TYPES)}"
            )
        return v

    model_config = {"extra": "ignore"}


class FederatedContributionRequest(BaseModel):
    """跨專案聯邦貢獻請求"""
    source_project: str = Field(..., description="來源專案: ck-lvrland | ck-tunnel")
    contributions: List[EntityContribution] = Field(..., min_length=1, max_length=500)
    relations: List[RelationContribution] = Field(default_factory=list, max_length=500)
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="冪等鍵 — 相同 key 在 TTL 內重複提交將回傳快取結果",
    )

    @field_validator("source_project")
    @classmethod
    def validate_source_project(cls, v: str) -> str:
        from app.core.constants import KG_SOURCE_PROJECTS
        if v not in KG_SOURCE_PROJECTS:
            raise ValueError(
                f"未知的來源專案: '{v}', 允許: {sorted(KG_SOURCE_PROJECTS)}"
            )
        return v

    model_config = {"extra": "ignore"}


class ResolvedEntity(BaseModel):
    """單一實體解析結果"""
    external_id: str
    hub_entity_id: int
    resolution: str = Field(description="exact_match | fuzzy_match | semantic_match | created")
    canonical_name: str


class FederatedContributionResponse(BaseModel):
    """跨專案聯邦貢獻回應"""
    success: bool = True
    resolved: List[ResolvedEntity] = []
    relations_created: int = 0
    processing_ms: int = 0
    message: Optional[str] = None


class FederatedSearchRequest(BaseModel):
    """跨專案聯邦搜尋請求"""
    query: str = Field(..., min_length=1, max_length=200, description="搜尋關鍵字")
    entity_types: Optional[List[str]] = Field(None, description="實體類型篩選")
    source_projects: Optional[List[str]] = Field(None, description="來源專案篩選")
    max_hops: int = Field(default=1, ge=1, le=4, description="鄰居展開跳數 (目前僅支援 1-hop)")
    limit: int = Field(default=50, ge=1, le=200, description="最大結果數")


class FederatedGraphNode(BaseModel):
    """跨專案圖譜節點（含來源標記）"""
    id: int
    name: str
    type: str
    source_project: str = "ck-missive"
    mention_count: int = 0
    external_id: Optional[str] = None
    hop: int = 0


class FederatedSearchResponse(BaseModel):
    """跨專案聯邦搜尋回應"""
    success: bool = True
    nodes: List[FederatedGraphNode] = []
    edges: List[KGGraphEdge] = []
    total: int = 0
    source_projects_found: List[str] = []


# ============================================================================
# 跨專案路徑查詢 (KG-4, v1.1.0)
# ============================================================================


class CrossDomainPathRequest(BaseModel):
    """跨專案路徑查詢請求"""
    source_id: int = Field(..., description="起始實體 ID")
    target_id: int = Field(..., description="目標實體 ID")
    max_hops: int = Field(default=6, ge=1, le=8, description="最大跳數")


class CrossDomainPathNode(BaseModel):
    """跨專案路徑節點（含來源專案標記）"""
    id: int
    name: str
    type: str
    source_project: str = "ck-missive"


class CrossDomainPathResponse(BaseModel):
    """跨專案路徑查詢回應"""
    success: bool = True
    found: bool = False
    depth: int = 0
    path: List[CrossDomainPathNode] = []
    relations: List[str] = []
    source_projects_traversed: List[str] = Field(
        default_factory=list,
        description="路徑中涉及的來源專案列表",
    )
    is_cross_project: bool = Field(
        default=False,
        description="路徑是否跨越專案邊界",
    )
