"""
資料庫備份管理 API 端點
提供備份、還原、列表與管理功能

@version 1.0.0
@date 2026-01-11
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.endpoints.auth import get_current_user
from app.services.backup_service import backup_service

# 統一從 schemas 匯入型別定義
from app.schemas.backup import (
    CreateBackupRequest,
    DeleteBackupRequest,
    RestoreBackupRequest,
)

router = APIRouter()


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
    if current_user.role not in ["admin", "super_admin"]:
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
    if current_user.role not in ["admin", "super_admin"]:
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
    if current_user.role not in ["admin", "super_admin"]:
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
    if current_user.role != "super_admin":
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
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="僅管理員可查看備份設定")

    return await backup_service.get_backup_config()


@router.post("/status", summary="取得備份狀態")
async def get_backup_status(current_user=Depends(get_current_user)):
    """
    取得備份系統狀態

    包含最近備份時間、下次排程時間等
    """
    if current_user.role not in ["admin", "super_admin"]:
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
