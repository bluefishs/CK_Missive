# -*- coding: utf-8 -*-
"""
TDD: Docker Secrets Loader 測試

RED phase — 驗證：
1. 有 secret 檔案時優先讀取檔案
2. 無 secret 檔案時 fallback 到 env var
3. 檔案內容自動 strip 換行
4. 檔案和 env var 都不存在時回傳 default
5. secret 檔案路徑可自訂 (非僅 /run/secrets/)
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_read_secret_from_file(tmp_path):
    """有 secret 檔案時優先讀取"""
    from app.core.secret_loader import read_secret

    secret_file = tmp_path / "db_password"
    secret_file.write_text("my_super_secret\n")

    result = read_secret(
        "DB_PASSWORD",
        secrets_dir=str(tmp_path),
        secret_name="db_password",
    )
    assert result == "my_super_secret"


def test_read_secret_fallback_to_env(tmp_path):
    """無 secret 檔案時 fallback 到 env var"""
    from app.core.secret_loader import read_secret

    with patch.dict(os.environ, {"DB_PASSWORD": "env_value"}):
        result = read_secret(
            "DB_PASSWORD",
            secrets_dir=str(tmp_path),  # 空目錄，無檔案
            secret_name="db_password",
        )
    assert result == "env_value"


def test_read_secret_strips_whitespace(tmp_path):
    """檔案內容自動 strip 換行和空白"""
    from app.core.secret_loader import read_secret

    secret_file = tmp_path / "jwt_secret"
    secret_file.write_text("  token_value_123  \n\n")

    result = read_secret(
        "JWT_SECRET",
        secrets_dir=str(tmp_path),
        secret_name="jwt_secret",
    )
    assert result == "token_value_123"


def test_read_secret_returns_default_when_missing(tmp_path):
    """檔案和 env var 都不存在時回傳 default"""
    from app.core.secret_loader import read_secret

    # 確保 env var 不存在
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("MISSING_SECRET", None)
        result = read_secret(
            "MISSING_SECRET",
            secrets_dir=str(tmp_path),
            secret_name="missing_secret",
            default="fallback_default",
        )
    assert result == "fallback_default"


def test_read_secret_file_takes_precedence_over_env(tmp_path):
    """檔案優先於 env var"""
    from app.core.secret_loader import read_secret

    secret_file = tmp_path / "db_password"
    secret_file.write_text("from_file")

    with patch.dict(os.environ, {"DB_PASSWORD": "from_env"}):
        result = read_secret(
            "DB_PASSWORD",
            secrets_dir=str(tmp_path),
            secret_name="db_password",
        )
    assert result == "from_file"


def test_read_secret_default_name_from_env_key(tmp_path):
    """未指定 secret_name 時，自動從 env_key 推導（小寫）"""
    from app.core.secret_loader import read_secret

    secret_file = tmp_path / "postgres_password"
    secret_file.write_text("auto_name_value")

    result = read_secret(
        "POSTGRES_PASSWORD",
        secrets_dir=str(tmp_path),
    )
    assert result == "auto_name_value"


def test_read_secret_none_default(tmp_path):
    """default=None 時，找不到回傳 None"""
    from app.core.secret_loader import read_secret

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NOPE", None)
        result = read_secret("NOPE", secrets_dir=str(tmp_path))
    assert result is None
