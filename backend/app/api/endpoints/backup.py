"""
資料庫備份管理 API 端點
提供備份、還原、列表與管理功能
支援異地備份設定與備份日誌查詢

@version 1.1.0
@date 2026-01-29
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.endpoints.auth import get_current_user
from app.services.backup_service import backup_service
from app.services.backup_scheduler import (
    get_backup_scheduler_status,
    start_backup_scheduler,
    stop_backup_scheduler,
)

# 統一從 schemas 匯入型別定義
from app.schemas.backup import (
    CreateBackupRequest,
    DeleteBackupRequest,
    RestoreBackupRequest,
    RemoteBackupConfigRequest,
    BackupLogListRequest,
)

router = APIRouter()


# ============================================================================
# 權限檢查輔助函數
# ============================================================================

def _is_admin(user) -> bool:
    """檢查是否為管理員 (admin 或 superuser)"""
    return user.is_admin or user.is_superuser


def _is_superuser(user) -> bool:
    """檢查是否為超級管理員"""
    return user.is_superuser


# ============================================================================
# API 端點 (POST-only 安全模式)
# ============================================================================

@router.post("/create", summary="建立備份")
async def create_backup(
    request: CreateBackupRequest,
    current_user=Depends(get_current_user)
):
    """
    建立資料庫和/或附件備份

    - **include_database**: 是否備份資料庫 (預設: true)
    - **include_attachments**: 是否備份附件 (預設: true)
    - **retention_days**: 備份保留天數 (預設: 7)
    """
    # 檢查權限 (僅管理員可操作)
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可執行備份操作")

    result = await backup_service.create_backup(
        include_database=request.include_database,
        include_attachments=request.include_attachments,
        retention_days=request.retention_days
    )

    return result


@router.post("/list", summary="列出備份")
async def list_backups(current_user=Depends(get_current_user)):
    """
    列出所有可用備份

    回傳資料庫備份和附件備份的詳細列表
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可查看備份列表")

    return await backup_service.list_backups()


@router.post("/delete", summary="刪除備份")
async def delete_backup(
    request: DeleteBackupRequest,
    current_user=Depends(get_current_user)
):
    """
    刪除指定備份

    - **backup_name**: 備份名稱
    - **backup_type**: database 或 attachments
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可刪除備份")

    result = await backup_service.delete_backup(
        backup_name=request.backup_name,
        backup_type=request.backup_type
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "刪除失敗"))

    return result


@router.post("/restore", summary="還原資料庫")
async def restore_database(
    request: RestoreBackupRequest,
    current_user=Depends(get_current_user)
):
    """
    從備份還原資料庫

    **警告**: 此操作會覆蓋現有資料，請謹慎使用
    """
    if not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="僅超級管理員可執行還原操作")

    result = await backup_service.restore_database(request.backup_name)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "還原失敗"))

    return result


@router.post("/config", summary="取得備份設定")
async def get_backup_config(current_user=Depends(get_current_user)):
    """
    取得目前備份設定資訊

    包含備份目錄、資料庫設定等
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可查看備份設定")

    return await backup_service.get_backup_config()


@router.post("/status", summary="取得備份狀態")
async def get_backup_status(current_user=Depends(get_current_user)):
    """
    取得備份系統狀態

    包含最近備份時間、下次排程時間等
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可查看備份狀態")

    # 取得備份列表以獲取最近備份資訊
    backups = await backup_service.list_backups()
    config = await backup_service.get_backup_config()

    # 取得最近的備份
    latest_db_backup = None
    latest_att_backup = None

    if backups["database_backups"]:
        latest_db_backup = backups["database_backups"][0]

    if backups["attachment_backups"]:
        latest_att_backup = backups["attachment_backups"][0]

    return {
        "status": "active",
        "config": config,
        "latest_database_backup": latest_db_backup,
        "latest_attachment_backup": latest_att_backup,
        "statistics": backups["statistics"]
    }


# ============================================================================
# 異地備份設定 API
# ============================================================================

@router.post("/remote-config", summary="取得異地備份設定")
async def get_remote_backup_config(current_user=Depends(get_current_user)):
    """
    取得異地備份路徑設定

    包含異地路徑、同步狀態、最後同步時間等
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可查看異地備份設定")

    return await backup_service.get_remote_config()


@router.post("/remote-config/update", summary="更新異地備份設定")
async def update_remote_backup_config(
    request: RemoteBackupConfigRequest,
    current_user=Depends(get_current_user)
):
    """
    更新異地備份路徑設定

    - **remote_path**: 異地備份路徑 (本地或網路路徑)
    - **sync_enabled**: 是否啟用自動同步
    - **sync_interval_hours**: 同步間隔 (小時)
    """
    if not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="僅超級管理員可修改異地備份設定")

    result = await backup_service.update_remote_config(
        remote_path=request.remote_path,
        sync_enabled=request.sync_enabled,
        sync_interval_hours=request.sync_interval_hours
    )

    return result


@router.post("/remote-sync", summary="手動觸發異地同步")
async def trigger_remote_sync(current_user=Depends(get_current_user)):
    """
    手動觸發異地備份同步

    將本地備份同步到設定的異地路徑
    """
    if not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="僅超級管理員可觸發異地同步")

    result = await backup_service.sync_to_remote()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "同步失敗"))

    return result


# ============================================================================
# 備份日誌 API
# ============================================================================

@router.post("/logs", summary="查詢備份日誌")
async def get_backup_logs(
    request: BackupLogListRequest,
    current_user=Depends(get_current_user)
):
    """
    查詢備份操作日誌

    支援分頁、操作類型篩選、狀態篩選、日期範圍篩選
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可查看備份日誌")

    return await backup_service.get_backup_logs(
        page=request.page,
        page_size=request.page_size,
        action_filter=request.action_filter,
        status_filter=request.status_filter,
        date_from=request.date_from,
        date_to=request.date_to
    )


# ============================================================================
# 排程器控制 API
# ============================================================================

@router.post("/scheduler/status", summary="取得排程器狀態")
async def get_scheduler_status(current_user=Depends(get_current_user)):
    """
    取得備份排程器狀態

    包含運行狀態、備份時間、下次執行時間、統計資訊等
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="僅管理員可查看排程器狀態")

    return get_backup_scheduler_status()


@router.post("/scheduler/start", summary="啟動排程器")
async def start_scheduler(current_user=Depends(get_current_user)):
    """
    啟動備份排程器

    開始自動備份排程
    """
    if not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="僅超級管理員可啟動排程器")

    await start_backup_scheduler()
    return {"success": True, "message": "排程器已啟動"}


@router.post("/scheduler/stop", summary="停止排程器")
async def stop_scheduler(current_user=Depends(get_current_user)):
    """
    停止備份排程器

    停止自動備份排程
    """
    if not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="僅超級管理員可停止排程器")

    await stop_backup_scheduler()
    return {"success": True, "message": "排程器已停止"}
