"""
安全性工具模組

提供專案共用的安全性驗證和工具函數

@version 1.0.0
@date 2026-02-02

安全性功能:
- SQL 識別符驗證
- 檔案上傳驗證
- 輸入消毒
"""

import re
import os
import logging
from pathlib import Path
from typing import Set, Optional
from fastapi import UploadFile
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)

# =========================================================================
# SQL 安全性
# =========================================================================

def validate_sql_identifier(identifier: str) -> bool:
    """
    驗證 SQL 識別符（表格名、欄位名）是否安全

    規則:
    - 只允許字母、數字、底線
    - 必須以字母或底線開頭
    - 長度限制 1-63 字元 (PostgreSQL 限制)

    Args:
        identifier: 要驗證的識別符

    Returns:
        bool: 是否為有效的識別符
    """
    if not identifier or len(identifier) > 63:
        return False
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier))


def sanitize_sql_identifier(identifier: str) -> Optional[str]:
    """
    消毒 SQL 識別符，移除危險字元

    Args:
        identifier: 原始識別符

    Returns:
        Optional[str]: 消毒後的識別符，如果無法消毒則返回 None
    """
    if not identifier:
        return None

    # 移除非法字元
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)

    # 確保以字母或底線開頭
    if sanitized and not re.match(r'^[a-zA-Z_]', sanitized):
        sanitized = '_' + sanitized

    # 長度限制
    sanitized = sanitized[:63]

    return sanitized if sanitized else None


# =========================================================================
# 檔案上傳安全性
# =========================================================================

# 允許的檔案副檔名
ALLOWED_EXTENSIONS: Set[str] = {
    '.pdf', '.xlsx', '.xls', '.doc', '.docx',
    '.jpg', '.jpeg', '.png', '.gif',
    '.txt', '.csv', '.json', '.xml'
}

# 危險的檔案副檔名（絕對禁止）
DANGEROUS_EXTENSIONS: Set[str] = {
    '.exe', '.dll', '.bat', '.cmd', '.ps1', '.sh',
    '.py', '.js', '.php', '.asp', '.aspx', '.jsp',
    '.msi', '.scr', '.com', '.pif', '.vbs', '.wsf'
}

# 最大檔案大小 (50MB)
MAX_FILE_SIZE: int = 50 * 1024 * 1024


async def validate_upload_file(
    file: UploadFile,
    allowed_extensions: Optional[Set[str]] = None,
    max_size: Optional[int] = None
) -> None:
    """
    驗證上傳的檔案

    Args:
        file: 上傳的檔案
        allowed_extensions: 允許的副檔名（預設使用 ALLOWED_EXTENSIONS）
        max_size: 最大檔案大小（預設使用 MAX_FILE_SIZE）

    Raises:
        ValidationException: 驗證失敗時拋出
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS
    if max_size is None:
        max_size = MAX_FILE_SIZE

    if not file.filename:
        raise ValidationException("檔案名稱不能為空")

    # 取得副檔名
    ext = Path(file.filename).suffix.lower()

    # 檢查危險副檔名
    if ext in DANGEROUS_EXTENSIONS:
        logger.warning(f"嘗試上傳危險檔案類型: {file.filename}")
        raise ValidationException(f"不允許上傳此類型的檔案: {ext}")

    # 檢查允許的副檔名
    if ext not in allowed_extensions:
        raise ValidationException(f"不支援的檔案格式: {ext}，允許的格式: {', '.join(allowed_extensions)}")

    # 檢查檔案大小
    content = await file.read()
    await file.seek(0)  # 重置讀取位置

    if len(content) > max_size:
        size_mb = max_size // (1024 * 1024)
        raise ValidationException(f"檔案大小超過限制 ({size_mb}MB)")

    # 檢查檔案內容類型（可選的額外驗證）
    # 這裡可以加入 magic number 驗證來確認檔案內容與副檔名匹配


def sanitize_filename(filename: str) -> str:
    """
    消毒檔案名稱，移除路徑遍歷和危險字元

    Args:
        filename: 原始檔案名稱

    Returns:
        str: 安全的檔案名稱
    """
    if not filename:
        return "unnamed_file"

    # 取得基本檔名（移除路徑）
    basename = os.path.basename(filename)

    # 移除危險字元，保留中文、字母、數字、點、底線、連字號
    # 使用 Unicode 類別來保留中文字元
    sanitized = re.sub(r'[^\w\u4e00-\u9fff\.\-]', '_', basename)

    # 移除連續的點（防止 .. 路徑遍歷）
    sanitized = re.sub(r'\.{2,}', '.', sanitized)

    # 移除開頭的點（防止隱藏檔案）
    sanitized = sanitized.lstrip('.')

    # 確保有檔名
    if not sanitized or sanitized == '.':
        sanitized = "unnamed_file"

    return sanitized


# =========================================================================
# 輸入消毒
# =========================================================================

def sanitize_html(text: str) -> str:
    """
    消毒 HTML 內容，防止 XSS 攻擊

    Args:
        text: 原始文字

    Returns:
        str: 消毒後的文字
    """
    if not text:
        return ""

    # HTML 實體編碼
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }

    for char, entity in replacements.items():
        text = text.replace(char, entity)

    return text


def validate_email(email: str) -> bool:
    """
    驗證電子郵件格式

    Args:
        email: 電子郵件地址

    Returns:
        bool: 是否為有效的電子郵件格式
    """
    if not email:
        return False

    # 基本格式驗證
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
