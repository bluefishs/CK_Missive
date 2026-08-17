"""填報缺口請求（2026-08-16 owner：「承攬報價案件對應填報人員通報管控」）

置於此處而非端點檔內：`.claude/rules/development-rules.md` §3
明訂 `api/endpoints/` 禁止本地 BaseModel。
"""
from pydantic import BaseModel, Field


class FilingGapRequest(BaseModel):
    # 幾天沒動才算「卡住」。預設 3 天：核銷卡 1-2 天是正常的審核節奏，
    # 卡 3 天以上才是「沒有人記得它」。實測那批卡了 16 天。
    stuck_days: int = Field(3, ge=0, le=60, description="核銷停滯天數門檻")
