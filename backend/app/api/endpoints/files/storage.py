"""
檔案管理模組 - 儲存資訊端點

包含: /storage-info, /check-network
"""

import os
import asyncio
import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends

from app.extended.models import User
from app.api.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)

from .common import (
    UPLOAD_BASE_DIR, STORAGE_TYPE, ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE, is_network_path, extract_ip_from_path, is_local_ip,
)

router = APIRouter()


@router.post("/storage-info", summary="取得儲存資訊")
async def get_storage_info(
    current_user: User = Depends(get_current_user)
):
    """取得檔案儲存系統資訊"""
    import shutil

    storage_path = Path(UPLOAD_BASE_DIR)

    def _scan_files():
        size, count = 0, 0
        if storage_path.exists():
            for f in storage_path.rglob('*'):
                if f.is_file():
                    size += f.stat().st_size
                    count += 1
        return size, count

    total_size, file_count = await asyncio.to_thread(_scan_files)

    try:
        disk_usage = await asyncio.to_thread(shutil.disk_usage, UPLOAD_BASE_DIR)
        disk_info = {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "usage_percent": round(disk_usage.used / disk_usage.total * 100, 1)
        }
    except Exception as e:
        logger.debug(f"取得磁碟使用量失敗: {e}")
        disk_info = None

    network_ip = extract_ip_from_path(UPLOAD_BASE_DIR)

    return {
        "success": True,
        "storage_path": str(storage_path.absolute()) if storage_path.exists() else UPLOAD_BASE_DIR,
        "storage_type": STORAGE_TYPE,
        "is_network_path": is_network_path(UPLOAD_BASE_DIR),
        "network_ip": network_ip,
        "is_local_ip": is_local_ip(network_ip) if network_ip else None,
        "total_files": file_count,
        "total_size_mb": round(total_size / (1024**2), 2),
        "allowed_extensions": sorted(list(ALLOWED_EXTENSIONS)),
        "max_file_size_mb": MAX_FILE_SIZE / (1024**2),
        "disk_info": disk_info
    }


@router.post("/check-network", summary="檢查網路儲存連線")
async def check_network_storage(
    current_user: User = Depends(get_current_user)
):
    """
    檢查網路儲存路徑的連線狀態

    適用於區域 IP 網路磁碟 (NAS/File Server)
    """
    import socket

    result = {
        "success": True,
        "storage_path": UPLOAD_BASE_DIR,
        "storage_type": STORAGE_TYPE,
        "is_network_path": is_network_path(UPLOAD_BASE_DIR),
        "checks": {}
    }

    path_exists = os.path.exists(UPLOAD_BASE_DIR)
    result["checks"]["path_exists"] = path_exists

    if path_exists:
        try:
            test_file = os.path.join(UPLOAD_BASE_DIR, '.write_test')
            async with aiofiles.open(test_file, 'w') as f:
                await f.write('test')
            await asyncio.to_thread(os.remove, test_file)
            result["checks"]["writable"] = True
        except Exception as e:
            result["checks"]["writable"] = False
            logger.error(f"儲存路徑寫入測試失敗: {e}")
            result["checks"]["write_error"] = "寫入測試失敗"
    else:
        result["checks"]["writable"] = False

    network_ip = extract_ip_from_path(UPLOAD_BASE_DIR)
    if network_ip:
        result["network_ip"] = network_ip
        result["is_local_ip"] = is_local_ip(network_ip)

        def _check_network_ports(ip: str):
            """同步 socket 連線檢測（在背景執行緒執行）"""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            try:
                for port in [445, 139, 80]:
                    try:
                        sock.connect((ip, port))
                        return True, port
                    except Exception:
                        continue
                return False, None
            finally:
                sock.close()

        try:
            reachable, port = await asyncio.to_thread(_check_network_ports, network_ip)
            result["checks"]["network_reachable"] = reachable
            if port is not None:
                result["checks"]["connected_port"] = port
        except Exception as e:
            result["checks"]["network_reachable"] = False
            logger.error(f"網路可達性檢查失敗: {e}")
            result["checks"]["network_error"] = "網路連線失敗"

    result["healthy"] = (
        result["checks"].get("path_exists", False) and
        result["checks"].get("writable", False)
    )

    return result
