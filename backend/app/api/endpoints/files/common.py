"""
檔案管理模組 - 共用常數與工具函數

包含：儲存路徑、白名單、大小限制、校驗、結構化路徑生成、權限檢查
"""

import os
import re
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import DocumentAttachment, User, OfficialDocument
from app.core.config import settings
from app.core.rls_filter import RLSFilter

# ============================================================================
# 設定常數
# ============================================================================

UPLOAD_BASE_DIR = getattr(settings, 'ATTACHMENT_STORAGE_PATH', None) or os.getenv(
    'ATTACHMENT_STORAGE_PATH',
    'uploads'
)

LOCAL_IP_PATTERN = re.compile(
    r'^(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|'
    r'192\.168\.\d{1,3}\.\d{1,3}|'
    r'127\.\d{1,3}\.\d{1,3}\.\d{1,3})$'
)

ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    '.zip', '.rar', '.7z',
    '.txt', '.csv', '.xml', '.json',
    '.dwg', '.dxf',
    '.shp', '.kml', '.kmz',
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# ============================================================================
# 網路路徑處理函數
# ============================================================================


def is_network_path(path: str) -> bool:
    """檢測是否為網路路徑"""
    if not path:
        return False
    if path.startswith('\\\\') or path.startswith('//'):
        return True
    if path.startswith('/mnt/') or path.startswith('/media/'):
        return True
    return False


def is_local_ip(ip: str) -> bool:
    """檢測是否為區域 IP 地址"""
    return bool(LOCAL_IP_PATTERN.match(ip))


def extract_ip_from_path(path: str) -> Optional[str]:
    """從路徑中提取 IP 地址"""
    unc_match = re.match(r'^[\\\/]{2}(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\\\/]', path)
    if unc_match:
        return unc_match.group(1)
    mnt_match = re.match(r'^/(?:mnt|media)/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/', path)
    if mnt_match:
        return mnt_match.group(1)
    return None


def get_storage_type(path: str) -> str:
    """根據路徑判斷儲存類型: 'local', 'network', 'nas'"""
    if not is_network_path(path):
        return 'local'
    ip = extract_ip_from_path(path)
    if ip and is_local_ip(ip):
        return 'network'
    if path.startswith('\\\\') or path.startswith('//'):
        return 'nas'
    return 'network'


def normalize_path(path: str) -> str:
    """正規化路徑，確保跨平台相容"""
    if not path:
        return path
    if path.startswith('\\\\'):
        return path.replace('/', '\\')
    return os.path.normpath(path)


# 正規化並確保根目錄存在
UPLOAD_BASE_DIR = normalize_path(UPLOAD_BASE_DIR)
STORAGE_TYPE = get_storage_type(UPLOAD_BASE_DIR)

try:
    os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)
except OSError as e:
    logging.warning(f"無法建立儲存目錄 {UPLOAD_BASE_DIR}: {e}")


# ============================================================================
# 工具函數
# ============================================================================


def get_structured_path(document_id: Optional[int], filename: str) -> tuple[str, str]:
    """
    生成結構化儲存路徑

    格式: {base}/{year}/{month}/doc_{document_id}/{uuid}_{original_name}
    Returns: (完整檔案路徑, 相對路徑)
    """
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    file_uuid = str(uuid.uuid4())[:8]

    safe_filename = "".join(c for c in filename if c.isalnum() or c in '._-').strip()
    if not safe_filename:
        safe_filename = 'unnamed'

    unique_filename = f"{file_uuid}_{safe_filename}"

    if document_id:
        relative_dir = os.path.join(year, month, f"doc_{document_id}")
    else:
        relative_dir = os.path.join(year, month, "temp")

    full_dir = os.path.join(UPLOAD_BASE_DIR, relative_dir)
    os.makedirs(full_dir, exist_ok=True)

    relative_path = os.path.join(relative_dir, unique_filename)
    full_path = os.path.join(UPLOAD_BASE_DIR, relative_path)

    return full_path, relative_path


def calculate_checksum(content: bytes) -> str:
    """計算 SHA256 校驗碼"""
    return hashlib.sha256(content).hexdigest()


def validate_file_extension(filename: str) -> bool:
    """驗證檔案副檔名是否在白名單中"""
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """取得檔案副檔名"""
    return os.path.splitext(filename or '')[1].lower()


async def check_document_access(
    db: AsyncSession,
    document_id: int,
    current_user: User
) -> bool:
    """
    檢查使用者是否有權限存取指定公文 - 使用統一 RLSFilter
    """
    if current_user.is_admin or current_user.is_superuser:
        return True

    doc_result = await db.execute(
        select(OfficialDocument.contract_project_id)
        .where(OfficialDocument.id == document_id)
    )
    project_id = doc_result.scalar_one_or_none()

    if not project_id:
        return True

    return await RLSFilter.check_user_project_access(db, current_user.id, project_id)
