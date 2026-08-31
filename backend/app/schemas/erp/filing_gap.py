"""填報缺口請求（2026-08-16 owner：「承攬報價案件對應填報人員通報管控」）

置於此處而非端點檔內：`.claude/rules/development-rules.md` §3
明訂 `api/endpoints/` 禁止本地 BaseModel。
"""
from pydantic import BaseModel, Field


class FilingGapRequest(BaseModel):
    # 幾天沒動才算「卡住」。預設 3 天：核銷卡 1-2 天是正常的審核節奏，
    # 卡 3 天以上才是「沒有人記得它」。實測那批卡了 16 天。
    stuck_days: int = Field(3, ge=0, le=60, description="核銷停滯天數門檻")
    # 開工幾天還沒開過任何請款單才算「該請款未開單」。
    #
    # 預設 365 是**用公司自己的資料校準的**：實際第一張請款單距開工的
    # 中位數是 205 天、30 天內無人請款，所以 90 天那種直覺門檻會把
    # 正常節奏叫成缺口（實測會多報 40 件）。365 ≈ 中位數的 1.7 倍。
    #
    # ⚠️ 做成參數而不是寫死：那個 205 天是**今天的**中位數，資料會變。
    no_billing_days: int = Field(365, ge=30, le=1095, description="未開請款單天數門檻")
