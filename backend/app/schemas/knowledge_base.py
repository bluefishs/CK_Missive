"""知識庫瀏覽器 API Schema"""

from typing import Any, Dict, List, Literal, Optional

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


class KBEmbedRequest(BaseModel):
    """向量化模式。

    預設 `incremental` —— 只處理新增／異動／已刪除的檔案，
    沒有變動的檔案其向量不會被碰到。
    `force_rebuild` 是全庫砍掉重建，**只在緊急自癒時使用**。
    """
    mode: Literal["incremental", "force_rebuild"] = "incremental"


class KBEmbedResponse(BaseModel):
    """向量化結果。

    ⚠️ 2026-08-30：原本只有下面三個欄位，而 service 在「embedding provider
    不可用而跳過破壞性重建」時會回 `skipped` / `reason` ——
    **Pydantic 預設靜默丟棄多餘欄位** ⇒ 那個「我沒有做事」的訊息
    從來沒有到達呼叫端，畫面上看起來與成功一樣（同 weekly 61 的形狀）。
    故一併宣告出來。
    """
    success: bool
    mode: str = "force_rebuild"

    # 全庫重建
    files_scanned: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0

    # 跳過（provider 不可用）—— 一定要看得見
    skipped: bool = False
    reason: Optional[str] = None

    # 增量同步
    files_total: Optional[int] = None
    unchanged: Optional[int] = None
    updated: Optional[int] = None
    added: Optional[int] = None
    removed: Optional[int] = None
    chunks_written: Optional[int] = None
    skipped_files: Optional[List[Dict[str, Any]]] = None


class KBStatsResponse(BaseModel):
    success: bool
    total_chunks: int
    with_embedding: int
    without_embedding: int
    coverage_percent: float
    files_indexed: int
