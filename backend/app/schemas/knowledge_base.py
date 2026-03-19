"""知識庫瀏覽器 API Schema"""

from pydantic import BaseModel, Field


class FileRequest(BaseModel):
    path: str


class FileInfo(BaseModel):
    name: str
    path: str


class SectionInfo(BaseModel):
    name: str
    path: str
    files: list[FileInfo]


class TreeResponse(BaseModel):
    success: bool
    sections: list[SectionInfo]


class FileContentResponse(BaseModel):
    success: bool
    content: str
    filename: str


class AdrInfo(BaseModel):
    number: str
    title: str
    status: str
    date: str
    path: str


class AdrListResponse(BaseModel):
    success: bool
    items: list[AdrInfo]


class DiagramInfo(BaseModel):
    name: str
    path: str
    title: str


class DiagramListResponse(BaseModel):
    success: bool
    items: list[DiagramInfo]


class KBSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)


class KBSearchResult(BaseModel):
    file_path: str
    filename: str
    excerpt: str
    line_number: int
    relevance_score: float = 1.0


class KBSearchResponse(BaseModel):
    success: bool
    results: list[KBSearchResult]
    total: int
    search_mode: str = "text"  # "vector" | "text"


class KBEmbedResponse(BaseModel):
    success: bool
    files_scanned: int
    chunks_created: int
    embeddings_generated: int


class KBStatsResponse(BaseModel):
    success: bool
    total_chunks: int
    with_embedding: int
    without_embedding: int
    coverage_percent: float
    files_indexed: int
