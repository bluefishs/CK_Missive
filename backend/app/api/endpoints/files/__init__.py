"""
檔案管理模組

將原始 files.py (713 行) 模組化為：
- common.py     - 共用常數與工具函數
- upload.py     - 上傳端點 (/upload)
- download.py   - 下載端點 (/{file_id}/download)
- management.py - 管理端點 (/{file_id}/delete, /document/{id}, /verify/{id})
- storage.py    - 儲存資訊端點 (/storage-info, /check-network)

@version 2.0.0
@date 2026-01-28
"""

from fastapi import APIRouter

from .upload import router as upload_router
from .download import router as download_router
from .management import router as management_router
from .storage import router as storage_router

router = APIRouter()
router.include_router(upload_router)
router.include_router(download_router)
router.include_router(management_router)
router.include_router(storage_router)
