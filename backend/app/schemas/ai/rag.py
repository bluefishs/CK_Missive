"""RAG 問答 + Agent Schema"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Legacy (v0) — 原始格式，保留向下相容
# ---------------------------------------------------------------------------

class AgentQueryRequest(BaseModel):
    """Agentic 問答請求 (v0 legacy 格式)"""
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
    context: Optional[str] = Field(
        None,
        max_length=32,
        pattern=r"^[a-z_]+$",
        description="助理上下文 (doc/dev)，影響 system prompt 選擇",
    )
    channel: Optional[Literal["line", "telegram", "openclaw", "mcp", "web", "discord", "hermes"]] = Field(
        None,
        description="來源頻道標識，用於分析統計（hermes = NousResearch Hermes Agent gateway，ADR-0014）",
    )


class AgentSyncCapabilities(BaseModel):
    """Agent 能力清單（供 Hermes/外部系統探索）"""
    tools: List[str] = Field(default_factory=list, description="可用工具名稱")
    vision: bool = Field(default=True, description="是否支援圖片辨識 (Gemma 4 Vision)")
    voice: bool = Field(default=True, description="是否支援語音轉文字 (Whisper)")
    domains: List[str] = Field(
        default_factory=lambda: [
            "document", "dispatch", "project", "vendor",
            "finance", "tender", "knowledge_graph",
        ],
        description="支援的業務領域",
    )


class AgentSyncMetadata(BaseModel):
    """Agent 回應後設資料（供 Hermes/外部系統使用）"""
    model: str = Field(default="gemma4", description="使用的推理模型")
    latency_ms: int = Field(default=0, description="處理延遲（毫秒）")
    tools_used: List[str] = Field(default_factory=list, description="本次使用的工具")
    source_channel: Optional[str] = Field(None, description="來源頻道")
    agent_version: str = Field(default="5.5.0", description="Agent 版本")


class AgentSyncResponse(BaseModel):
    """Agent 同步問答回應（非串流，v0 legacy 格式 + v0.1 增強欄位）"""
    success: bool = True
    answer: str = ""
    sources: List[Dict[str, Any]] = []
    tools_used: List[str] = []
    latency_ms: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = Field(None, description="結構化錯誤碼 (timeout|auth_failed|internal)")
    capabilities: Optional[AgentSyncCapabilities] = Field(None, description="Agent 能力清單")
    metadata: Optional[AgentSyncMetadata] = Field(None, description="回應後設資料")


# ---------------------------------------------------------------------------
# Schema v1.0 — CK-AaaP 統一通訊格式
# ---------------------------------------------------------------------------

class AgentV1ReasonPayload(BaseModel):
    """Schema v1.0 reason action payload"""
    question: str = Field(..., min_length=1, max_length=32000)
    context: Optional[Dict[str, Any]] = None


class AgentV1Options(BaseModel):
    """Schema v1.0 request options"""
    stream: bool = False
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    priority: Literal["low", "normal", "high"] = "normal"


class AgentV1Request(BaseModel):
    """CK-AaaP Schema v1.0 統一請求格式"""
    agent_id: str = Field(
        ..., pattern=r"^ck_[a-z][a-z0-9_]*$",
        description="發起方代理人 ID",
    )
    action: Literal["reason", "query", "register", "heartbeat", "notify", "health"] = Field(
        ..., description="操作類型",
    )
    payload: Dict[str, Any] = Field(..., description="依 action 不同而異的業務資料")
    options: Optional[AgentV1Options] = None
    session_id: Optional[str] = Field(None, description="對話 session UUID")
    timestamp: str = Field(..., description="ISO-8601 含時區")


class AgentV1ReasonResult(BaseModel):
    """Schema v1.0 reason 成功回應"""
    answer: str = ""
    sources: List[Dict[str, Any]] = []
    tools_used: List[str] = []
    model: str = ""


class AgentV1ErrorObject(BaseModel):
    """Schema v1.0 標準錯誤物件"""
    code: str = Field(..., description="標準錯誤碼")
    message: str = Field(..., description="人類可讀錯誤訊息")
    details: Optional[Dict[str, Any]] = None


class AgentV1Meta(BaseModel):
    """Schema v1.0 回應後設資料"""
    latency_ms: int = 0
    request_id: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    model: str = Field(default="gemma4", description="推理模型")
    source_channel: Optional[str] = Field(None, description="來源頻道")
    agent_version: str = Field(default="5.5.0", description="Agent 版本")


class AgentV1Response(BaseModel):
    """CK-AaaP Schema v1.0 統一回應格式"""
    success: bool
    agent_id: str = Field(..., description="回應方代理人 ID")
    action: str = Field(..., description="與請求 action 對應")
    result: Optional[Union[AgentV1ReasonResult, Dict[str, Any]]] = None
    error: Optional[AgentV1ErrorObject] = None
    meta: Optional[AgentV1Meta] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Dual-format detection helper
# ---------------------------------------------------------------------------

def detect_request_format(data: Dict[str, Any]) -> Literal["v0", "v1"]:
    """偵測請求是 v0 (legacy) 還是 v1 (Schema v1.0) 格式。

    v1 必備: agent_id + action + payload + timestamp
    v0 特徵: question 在頂層
    """
    if (
        "agent_id" in data
        and "action" in data
        and "payload" in data
        and "timestamp" in data
    ):
        return "v1"
    return "v0"


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
