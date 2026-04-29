"""
Token 用量報告 API — Token Economics 領域

從 ai_stats.py 抽出（領域驅動分治）。
跟 cost / budget / provider 經濟學相關，獨立於 stats。

端點:
- POST /ai/stats/token-usage — Token 用量報告（按 provider/日/月 + 預算使用率）
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.dependencies import optional_auth

router = APIRouter()


@router.post("/stats/token-usage", summary="Token 用量報告")
async def get_token_usage_report(
    date: str = None,
    _user=Depends(optional_auth),
):
    """
    Token 用量報告 — 按 provider/日/月統計，含預算使用率。

    Args:
        date: 查詢日期 (YYYY-MM-DD)，預設今天
    """
    from app.services.ai.core.token_usage_tracker import get_token_tracker

    tracker = get_token_tracker()
    report = await tracker.get_usage_report(date)
    return JSONResponse(
        {"success": True, "data": report},
        media_type="application/json; charset=utf-8",
    )
