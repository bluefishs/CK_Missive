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
    # 2026-08-13：ADR 的「誰在強制它」。一條決策若沒有任何機制強制，
    # 它就只是一段文字 —— 而文字不會在有人違反時出聲（L01 家族）。
    # 這個欄位由 ADR 檔行首的 `<!--enforced-by: …-->` / `<!--not-enforceable: …-->`
    # 解析而來（宣告制，weekly step 51 的閘門擋新增未表態者）。
    # 放進 ADR 分頁而不是另開一頁：人看 ADR 的地方就該看得到它有沒有牙齒。
    enforced_by: str = ""
    not_enforceable_reason: str = ""


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
