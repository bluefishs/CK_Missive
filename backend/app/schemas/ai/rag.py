"""RAG 問答 + Agent Schema"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    """Agentic 問答請求"""
    question: str = Field(..., min_length=1, max_length=500, description="自然語言問題")
    history: Optional[List[Dict[str, str]]] = Field(
        None, description="對話歷史 [{role, content}, ...]"
    )
    session_id: Optional[str] = Field(
        None,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="對話 session ID（伺服器端記憶），與 history 二擇一",
    )


class AgentSyncResponse(BaseModel):
    """Agent 同步問答回應（非串流）"""
    success: bool = True
    answer: str = ""
    sources: List[Dict[str, Any]] = []
    tools_used: List[str] = []
    latency_ms: int = 0
    error: Optional[str] = None


class RAGQueryRequest(BaseModel):
    """RAG 問答請求"""
    question: str = Field(..., min_length=2, max_length=500, description="自然語言問題")
    top_k: int = Field(default=5, ge=1, le=20, description="檢索文件數")
    similarity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="最低相似度門檻"
    )


class RAGStreamRequest(BaseModel):
    """RAG 串流問答請求（含對話歷史）"""
    question: str = Field(..., min_length=2, max_length=500, description="自然語言問題")
    top_k: int = Field(default=5, ge=1, le=20, description="檢索文件數")
    similarity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="最低相似度門檻"
    )
    history: Optional[List[Dict[str, str]]] = Field(
        None, description="對話歷史 [{role, content}, ...]"
    )
    session_id: Optional[str] = Field(
        None, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$",
        description="對話 session ID（伺服器端記憶），與 history 二擇一",
    )


class RAGSourceItem(BaseModel):
    """RAG 來源文件"""
    document_id: int = Field(..., description="公文 ID")
    doc_number: str = Field(default="", description="公文字號")
    subject: str = Field(default="", description="主旨")
    doc_type: str = Field(default="", description="公文類型")
    category: str = Field(default="", description="收發類別")
    sender: str = Field(default="", description="發文單位")
    receiver: str = Field(default="", description="受文單位")
    doc_date: str = Field(default="", description="公文日期")
    similarity: float = Field(default=0.0, description="相似度分數")


class RAGQueryResponse(BaseModel):
    """RAG 問答回應"""
    success: bool = Field(default=True, description="是否成功")
    answer: str = Field(default="", description="AI 生成的回答")
    sources: List[RAGSourceItem] = Field(default=[], description="來源文件列表")
    retrieval_count: int = Field(default=0, description="檢索到的文件數")
    latency_ms: int = Field(default=0, description="總處理時間 (毫秒)")
    model: str = Field(default="", description="使用的模型")
