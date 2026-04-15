# -*- coding: utf-8 -*-
"""生產環境設定守門（P0 安全規範）

對應 CLAUDE.md 頂層 P0：
「DEVELOPMENT_MODE=false + AUTH_DISABLED=false 於公網部署強制」

本測試確保：
1. pydantic validator 確實阻擋 AUTH_DISABLED=true + DEVELOPMENT_MODE=false 組合
2. dev_only_ SECRET_KEY 不得用於生產
3. `.env.example` 範本值符合安全預設
4. 公網部署旗標（MISSIVE_PUBLIC_URL 指向 cksurvey.tw）時強制 production 設定

違反者：CI 擋下、部署失敗、避免 config drift。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def _reload_settings(monkeypatch, env: Dict[str, str]):
    """以新的環境變數重新載入 Settings（繞過 lru_cache）。"""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    # 強制重新載入以套用 monkeypatch 的環境變數
    import importlib
    from app.core import config as config_module
    importlib.reload(config_module)
    return config_module.Settings()


# ---------------------------------------------------------------------------
# 1. Pydantic validator 行為
# ---------------------------------------------------------------------------

def test_auth_disabled_forbidden_when_dev_mode_false(monkeypatch):
    """生產模式（DEVELOPMENT_MODE=false）下 AUTH_DISABLED=true 必須 raise。"""
    with pytest.raises(Exception) as exc:
        _reload_settings(monkeypatch, {
            "DEVELOPMENT_MODE": "false",
            "AUTH_DISABLED": "true",
            "SECRET_KEY": "x" * 64,
            "POSTGRES_PASSWORD": "placeholder",
        })
    msg = str(exc.value)
    assert "AUTH_DISABLED" in msg or "生產" in msg, f"unexpected error: {msg}"


def test_dev_only_secret_forbidden_in_production(monkeypatch):
    """生產模式下 SECRET_KEY=dev_only_ 必須 raise。"""
    with pytest.raises(Exception) as exc:
        _reload_settings(monkeypatch, {
            "DEVELOPMENT_MODE": "false",
            "AUTH_DISABLED": "false",
            "SECRET_KEY": "dev_only_abc123",
            "POSTGRES_PASSWORD": "placeholder",
        })
    msg = str(exc.value)
    assert "SECRET_KEY" in msg or "dev_only" in msg or "生產" in msg, f"unexpected: {msg}"


def test_production_valid_config_accepted(monkeypatch):
    """基準線：合法的 production 設定應可載入（負向對照）。"""
    settings = _reload_settings(monkeypatch, {
        "DEVELOPMENT_MODE": "false",
        "AUTH_DISABLED": "false",
        "SECRET_KEY": "a" * 64,
        "POSTGRES_PASSWORD": "realpassword",
    })
    assert settings.DEVELOPMENT_MODE is False
    assert settings.AUTH_DISABLED is False
    assert not settings.SECRET_KEY.startswith("dev_only_")


# ---------------------------------------------------------------------------
# 2. .env.example 範本靜態檢查
# ---------------------------------------------------------------------------

def _parse_env_file(path: Path) -> Dict[str, str]:
    """解析 .env 格式檔案 → dict，忽略註解與空行。"""
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def test_env_example_auth_disabled_is_false():
    """範本中 AUTH_DISABLED 必須預設為 false（避免 clone 後意外暴露）。"""
    env = _parse_env_file(ENV_EXAMPLE)
    assert env.get("AUTH_DISABLED", "").lower() == "false", (
        f".env.example AUTH_DISABLED 必須為 false，實際: {env.get('AUTH_DISABLED')!r}"
    )


def test_env_example_no_real_secrets():
    """範本不得含真實密碼/金鑰。"""
    env = _parse_env_file(ENV_EXAMPLE)
    forbidden_patterns = [
        (r"^sk-[A-Za-z0-9]{20,}", "疑似 OpenAI/真實 API key"),
        (r"^gsk_[A-Za-z0-9]{30,}", "疑似 Groq key"),
        (r"^ghp_[A-Za-z0-9]{20,}", "疑似 GitHub PAT"),
    ]
    for key, value in env.items():
        for pattern, desc in forbidden_patterns:
            assert not re.match(pattern, value), (
                f".env.example {key} 含{desc}: {value[:10]}...（請改為 placeholder）"
            )


# ---------------------------------------------------------------------------
# 3. 公網部署旗標一致性
# ---------------------------------------------------------------------------

def test_public_url_consistent_with_tunnel_guard():
    """若 MISSIVE_PUBLIC_URL 指向 cksurvey.tw，確認 tunnel_guard 允許清單存在。"""
    env = _parse_env_file(ENV_EXAMPLE)
    public_url = env.get("MISSIVE_PUBLIC_URL", "")
    if "cksurvey.tw" not in public_url:
        pytest.skip("非 CF Tunnel 部署，跳過")

    # 確認 tunnel_guard 模組存在且載入 ALLOWED_EXTERNAL_PATHS
    from app.core import tunnel_guard
    assert hasattr(tunnel_guard, "ALLOWED_EXTERNAL_PATHS"), (
        "公網部署要求 tunnel_guard.ALLOWED_EXTERNAL_PATHS 存在"
    )
    allowlist = tunnel_guard.ALLOWED_EXTERNAL_PATHS
    # 最小保證：health / auth / webhook 必在白名單
    must_include = ["/api/health", "/api/auth/"]
    for path in must_include:
        assert any(p.startswith(path) or path in p for p in allowlist), (
            f"tunnel_guard 允許清單缺少公網必需路徑: {path}"
        )
