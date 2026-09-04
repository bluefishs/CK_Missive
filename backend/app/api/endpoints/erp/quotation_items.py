"""報價明細 API（POST-only）—— 線上報價單

2026-08-16 owner：「線上報價單機制」。
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth
from app.db.database import get_async_db
from app.extended.models import User
from app.schemas.common import SuccessResponse
# §3 SSOT：型別定義唯一來源是 app/schemas/，端點不得有本地 BaseModel
from app.schemas.erp.quotation import QuotationIdRequest, ReplaceItemsRequest
from app.services.erp.quotation_items import QuotationItemService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/detail", response_model=SuccessResponse)
async def quotation_detail(
    req: QuotationIdRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """線上報價單內容（逐項 + 小計 + 稅 + 總計）。"""
    try:
        data = await QuotationItemService(db).summary(req.quotation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(data=data)


@router.post("/replace", response_model=SuccessResponse)
async def replace_items(
    req: ReplaceItemsRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """整批取代明細，並由小計加總回寫報價總價。

    ⚠️ 明細為空時**不會**把 total_price 歸零 ——
    空明細代表「還沒逐項拆」，不代表「這張報價是 0 元」。
    既有 55 張有總價但沒明細的報價不得被清掉。
    """
    try:
        result = await QuotationItemService(db).replace_items(
            req.quotation_id, [i.model_dump() for i in req.items],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    # 2026-09-04 owner「更新工項，既有報價檔案會同步更新嗎」：此前不會——存進附件的 XLS／PDF 是輸出當下的快照。
    # 現在：這張報價單若已有系統輸出的檔（同名 報價單_<編號>.xlsx／.pdf），改完明細就重新產出並覆蓋。
    # 盡力而為：文件產出失敗不影響明細已儲存的事實，但要在回應裡說（documents_refreshed / documents_error）。
    result["documents_refreshed"] = []
    try:
        from sqlalchemy import select as _select
        from app.extended.models.pm import PMCaseAttachment
        from app.services.erp.quotation_document import QuotationDocumentService
        doc = QuotationDocumentService(db)
        data = await doc.gather(req.quotation_id)
        display_no = data.get("display_no") or f"Q{req.quotation_id}"
        names = {f"報價單_{display_no}.xlsx": "xlsx", f"報價單_{display_no}.pdf": "pdf"}
        existing = (await db.execute(_select(PMCaseAttachment.file_name).where(
            PMCaseAttachment.case_code == data.get("case_code"),
            PMCaseAttachment.file_name.in_(list(names)),
        ))).scalars().all()
        if existing:
            xlsx = doc.render_xlsx(data)
            for fn in existing:
                ext = names[fn]
                content = xlsx if ext == "xlsx" else doc.render_pdf(xlsx)
                await doc.archive(data, content, ext, current_user.id)
                result["documents_refreshed"].append(fn)
    except Exception as e:  # noqa: BLE001 —— 明細已存，文件更新失敗只回報不擋
        logger.warning("工項更新後重新產出報價單文件失敗 qid=%s: %s", req.quotation_id, e)
        result["documents_error"] = str(e)[:200]
    return SuccessResponse(data=result)
