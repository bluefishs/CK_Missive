"""坤哥記憶（日記／提案／結晶）端點請求
（2026-08-17 由 `api/endpoints/ai/memory.py` 搬入）

依 `.claude/rules/development-rules.md` §3。

⚠️ 這幾個名稱很通用（`ListReq`／`ApproveReq`）—— 它們原本躲在端點檔裡不會撞名，
搬進共用模組後就得靠模組路徑區分。匯入時請保留
`from app.schemas.ai.memory import ...` 的完整路徑，不要再 re-export 到
`schemas/__init__.py`，否則下一個 `ListReq` 就會覆蓋它。
"""
from typing import Optional

from pydantic import BaseModel, Field



class DiaryQueryReq(BaseModel):
    date: Optional[str] = Field(None, description="YYYY-MM-DD；None 為今日")


class ListReq(BaseModel):
    limit: int = 50
    offset: int = 0


class ApproveReq(BaseModel):
    proposal_id: str
    approved_by: str = "admin"


class RejectReq(BaseModel):
    proposal_id: str
    reason: str = ""
    rejected_by: str = "admin"


class RollbackReq(BaseModel):
    crystal_id: str


class NebulaReq(BaseModel):
    days: int = 30


# ────────── Helpers ──────────


class AutoApplyModeReq(BaseModel):
    mode: str = Field(..., description="dry-run | live")
    confirmed_by: str = Field("admin", description="切換人")


class MemoryDigestRequest(BaseModel):
    """`POST /api/ai/memory/digest` 的請求 —— 欄位與舊 GET 的 query 參數一一對應。

    2026-08-26：規範 §24 要求所有 endpoint 用 POST，而這一條是 weekly 66
    盤點出的 5 條真違反裡唯一沒改的（消費端在 CK_Hermes 的 skill 包）。
    過渡期兩個方法並存，`_pending` 清掉之前 GET 仍在。
    """
    since: Optional[str] = Field(None, description="YYYY-MM-DD（預設近 7 日）")
    limit: int = Field(7, ge=1, le=30, description="各清單上限")
