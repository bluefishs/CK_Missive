"""坤哥快照（2026-08-17 由 `api/endpoints/ai/kunge.py` 搬入）

依 `.claude/rules/development-rules.md` §3：
`api/endpoints/` 禁止本地 BaseModel，型別唯一來源是 `app/schemas/`。
"""
from typing import Any, Dict, List

from pydantic import BaseModel, Field



class KungeSnapshotReq(BaseModel):
    window_days: int = Field(7, ge=1, le=90, description="統計窗口天數")
    include_pending_proposals: bool = True


class KungeSnapshotResp(BaseModel):
    success: bool
    timestamp: str
    window_days: int
    counts: Dict[str, int]
    recent: Dict[str, List[str]]
    pending_proposals: List[Dict[str, Any]]
    db_stats: Dict[str, int]
    health_signals: Dict[str, Any]
