"""知識圖譜 Schema"""
from typing import List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """圖譜節點"""
    id: str = Field(..., description="節點 ID (如 doc_1, project_2)")
    type: str = Field(..., description="節點類型: document/project/dispatch/agency/org/person/location/date/topic")
    label: str = Field(..., description="顯示文字")
    category: Optional[str] = Field(None, description="收文/發文 等分類")
    doc_number: Optional[str] = Field(None, description="公文字號")
    status: Optional[str] = Field(None, description="狀態")
    mention_count: Optional[int] = Field(None, description="提及次數（實體節點）")


class GraphEdge(BaseModel):
    """圖譜邊"""
    source: str = Field(..., description="起點節點 ID")
    target: str = Field(..., description="終點節點 ID")
    label: str = Field(default="", description="邊標籤")
    type: str = Field(default="relation", description="邊類型")
    weight: Optional[float] = Field(None, description="關係權重")


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
