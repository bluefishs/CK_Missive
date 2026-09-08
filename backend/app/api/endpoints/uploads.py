# -*- coding: utf-8 -*-
"""`/uploads/{path}` —— 上傳檔案的**附件層級**存取（A116，2026-09-08）。

## 歷史

* 09-08 之前：`app.mount("/uploads", StaticFiles(...))`。1,642 個附件公網未登入 200（L148）。
* 09-08 上午：改成帶 `require_auth()` 的路由——登入即可讀任何附件。
* 09-08 晚（本檔）：**誰能讀哪一類**。附件的權限比 metadata 敏感（owner D6）。

## 規則（依路徑前綴；不認得的前綴＝只有管理員）

| 前綴 | 誰能讀 | 為什麼 |
|---|---|---|
| `certifications/user_<id>/…` | 本人、管理員、或持有 `/staff` 頁權限者 | 證照掃描是個資 |
| `YYYY/MM/doc_<id>/…` | `check_document_access`（與 `/files/{id}/download` 同一份 RLS） | 公文附件跟著公文的專案 RLS 走 |
| `YYYY/MM/dispatch_<id>/…` | 持有 `/taoyuan/dispatch` 頁權限者 | 派工單附件跟頁面走 |
| `pm_attachments/…` | `/pm/cases` | 報價單／邀標附件 |
| `receipts/…` | `/erp/expenses` 或 `/erp/einvoice-sync` | 收據 |
| `asset_photos/…` | `/erp/assets` | 資產照片 |
| 其他 | 管理員 | 拒絕優先 |

頁面權限從選單表讀（收斂 B：`app/core/capabilities`），所以改選單表就改了附件的門，零部署。

⚠️ 大部分附件其實**不走這裡**：公文附件走 `/api/files/{id}/download`、派工附件走
`/api/taoyuan-dispatch/dispatch/attachments/{id}/download`，兩者各自有守衛。直接用 `/uploads/…`
連結的是證照（`StaffDetailPage`／`useCertificationAttachment`）與收據（`einvoice_sync`）。
本路由是**底線**，不是主要通道。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import permissions_for_page
from app.core.config import settings
from app.core.dependencies import is_admin_user, require_auth
from app.db.database import get_async_db

router = APIRouter()

UPLOADS_DIR = Path(getattr(settings, "ATTACHMENT_STORAGE_PATH", None)
                   or os.getenv("ATTACHMENT_STORAGE_PATH", "uploads")).resolve()
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

_CERT = re.compile(r"^certifications/user_(\d+)/")
_DOC = re.compile(r"^\d{4}/\d{2}/doc_(\d+)/")
_DISPATCH = re.compile(r"^\d{4}/\d{2}/dispatch_(\d+)/")
_PAGE_PREFIX = {
    "pm_attachments/": ("/pm/cases",),
    "receipts/": ("/erp/expenses", "/erp/einvoice-sync"),
    "asset_photos/": ("/erp/assets",),
}


def _has_all(user, codes: list[str]) -> bool:
    mine = set(getattr(user, "permissions", None) or [])
    return all(c in mine for c in codes)


async def _page_ok(user, pages: tuple[str, ...]) -> bool:
    """任一頁的宣告權限全部持有即可；頁面沒宣告（[]）視為登入即可。"""
    for p in pages:
        if _has_all(user, await permissions_for_page(p)):
            return True
    return False


async def _allowed(rel: str, user, db: AsyncSession) -> bool:
    if is_admin_user(user):
        return True
    m = _CERT.match(rel)
    if m:
        return int(m.group(1)) == int(getattr(user, "id", -1)) or await _page_ok(user, ("/staff",))
    m = _DOC.match(rel)
    if m:
        from app.api.endpoints.files.common import check_document_access
        return bool(await check_document_access(db, int(m.group(1)), user))
    if _DISPATCH.match(rel):
        return await _page_ok(user, ("/taoyuan/dispatch",))
    for prefix, pages in _PAGE_PREFIX.items():
        if rel.startswith(prefix):
            return await _page_ok(user, pages)
    return False  # 不認得的前綴：拒絕優先


@router.get("/uploads/{path:path}", include_in_schema=False)
async def serve_upload(
    path: str,
    user=Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    target = (UPLOADS_DIR / path).resolve()
    if UPLOADS_DIR not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="檔案不存在")
    rel = target.relative_to(UPLOADS_DIR).as_posix()
    if not await _allowed(rel, user, db):
        # 403 不 404：讓「有這個檔但你不能看」與「沒有這個檔」在稽核上分得開
        raise HTTPException(status_code=403, detail="沒有這份附件的檢視權限")
    # 沒有這個標頭，Cloudflare 會依副檔名把 PDF 快取在邊緣：登入者抓一次，之後任何人未登入都拿得到
    return FileResponse(str(target), headers={"Cache-Control": "private, no-store"})
