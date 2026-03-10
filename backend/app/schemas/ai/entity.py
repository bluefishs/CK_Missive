"""實體提取 Schema"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    limit: int = Field(default=200, ge=1, le=1000, description="批次處理筆數上限")
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
