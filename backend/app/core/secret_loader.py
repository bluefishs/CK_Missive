# -*- coding: utf-8 -*-
"""
Docker Secrets Loader

優先從 Docker Secrets 掛載檔案讀取敏感資訊，
fallback 到環境變數，最後使用預設值。

Docker Secrets 掛載路徑預設: /run/secrets/ (Linux)
Windows 開發環境可透過 secrets_dir 參數自訂。

Usage:
    from app.core.secret_loader import read_secret

    db_password = read_secret("POSTGRES_PASSWORD")
    # 1. 讀取 /run/secrets/postgres_password
    # 2. fallback: os.environ["POSTGRES_PASSWORD"]
    # 3. fallback: None
"""
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SECRETS_DIR = "/run/secrets"


def read_secret(
    env_key: str,
    *,
    secrets_dir: str = DEFAULT_SECRETS_DIR,
    secret_name: Optional[str] = None,
    default: Optional[str] = None,
) -> Optional[str]:
    """從 Docker Secrets 檔案或環境變數讀取敏感設定。

    Args:
        env_key: 環境變數名稱 (e.g. "POSTGRES_PASSWORD")
        secrets_dir: Docker Secrets 掛載目錄
        secret_name: 檔案名稱，預設為 env_key 小寫
        default: 都找不到時的預設值

    Returns:
        讀取到的值，或 default
    """
    name = secret_name or env_key.lower()
    secret_path = Path(secrets_dir) / name

    # 1. 嘗試從 Docker Secrets 檔案讀取
    if secret_path.is_file():
        try:
            value = secret_path.read_text(encoding="utf-8").strip()
            if value:
                logger.debug("Secret '%s' loaded from file: %s", env_key, secret_path)
                return value
        except Exception as e:
            logger.warning("Failed to read secret file %s: %s", secret_path, e)

    # 2. Fallback 到環境變數
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value

    # 3. 使用預設值
    return default
