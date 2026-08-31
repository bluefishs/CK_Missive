"""填報缺口 API（POST-only）

2026-08-16 owner：「承攬報價案件對應填報人員通報管控」。

回答兩個問題：
  · 全公司還有哪些該填沒填的、分別是誰負責（`/list`，管理者看）
  · **我**還有哪些待填報（`/mine`，每個人看自己的）
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth
from app.db.database import get_async_db
from app.extended.models import User
from app.schemas.common import SuccessResponse
# §3 SSOT：型別定義唯一來源是 app/schemas/，端點不得有本地 BaseModel
from app.schemas.erp.filing_gap import FilingGapRequest
from app.services.erp.filing_gap import FilingGapService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/list", response_model=SuccessResponse)
async def list_filing_gaps(
    req: FilingGapRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """全公司填報缺口，依負責人分組。

    **找不到負責人的會單獨列成「（未指派負責人）」**，不會被吞掉 ——
    實測 32 筆無金額的承攬案件裡有 14 筆完全沒有指派人，
    那 14 筆才是最容易永遠躺著的。
    """
    data = await FilingGapService(db).collect(stuck_days=req.stuck_days, no_billing_days=req.no_billing_days)
    return SuccessResponse(data=data)


@router.post("/mine", response_model=SuccessResponse)
async def my_filing_gaps(
    req: FilingGapRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """我的待填報。"""
    data = await FilingGapService(db).for_user(
        current_user.id, stuck_days=req.stuck_days,
        no_billing_days=req.no_billing_days,
    )
    return SuccessResponse(data=data)
