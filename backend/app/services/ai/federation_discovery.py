"""
Federation Discovery -- 服務發現模組 (拆分自 federation_client.py)

負責 NemoClaw Registry 動態服務發現與靜態回退邏輯。

Version: 1.0.0
Created: 2026-04-08
"""

import logging
import os
import time
from typing import Any, Dict

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# 本系統 ID — 從 Registry 發現時排除自身
_SELF_PLUGIN_ID = "ck-missive"

# NemoClaw Registry 端點
_REGISTRY_URL = os.getenv(
    "NEMOCLAW_REGISTRY_URL", "http://nemoclaw_tower:9000/api/registry"
)
_REGISTRY_TIMEOUT = 5.0  # Registry 查詢超時（秒）
_REGISTRY_REFRESH_TTL = 60  # 自動重新整理間隔（秒）

# 靜態回退表 — 僅在 Registry 不可達時使用
_FALLBACK_REGISTRY: Dict[str, Dict[str, str]] = {
    "openclaw": {
        "name": "CK_OpenClaw",
        "description": "多頻道 AI 管道系統 (via NemoClaw Gateway)",
        "url_env": "NEMOCLAW_GATEWAY_URL",
        "token_env": "MCP_SERVICE_TOKEN",
        "endpoint": "/api/gateway/reason",
        "default_url": "http://nemoclaw_tower:9000",
    },
    "lvrland": {
        "name": "CK_lvrland_Webmap",
        "description": "地圖測繪引擎",
        "url_env": "LVRLAND_URL",
        "token_env": "MCP_SERVICE_TOKEN",
        "endpoint": "/api/map/query",
        "default_url": "http://ck-lvrland:8000",
    },
    "tunnel": {
        "name": "CK_DigitalTunnel",
        "description": "隧道監控引擎",
        "url_env": "TUNNEL_URL",
        "token_env": "MCP_SERVICE_TOKEN",
        "endpoint": "/api/tunnel/query",
        "default_url": "http://ck-tunnel:8000",
    },
}


def load_configs(
    configs: Dict[str, Dict[str, str]],
    system_meta: Dict[str, Dict[str, Any]],
) -> str:
    """從 NemoClaw Registry 動態載入，失敗時回退至環境變數。

    Args:
        configs: 要填充的配置字典 (會被 clear)
        system_meta: 要填充的元資料字典 (會被 clear)

    Returns:
        discovery source: "registry" or "fallback"
    """
    if _try_load_from_registry(configs, system_meta):
        return "registry"
    else:
        _load_from_fallback(configs, system_meta)
        return "fallback"


def maybe_refresh(
    last_refresh: float,
    configs: Dict[str, Dict[str, str]],
    system_meta: Dict[str, Dict[str, Any]],
) -> tuple:
    """TTL 到期時 lazy refresh Registry.

    Returns:
        (new_last_refresh, new_discovery_source) or (last_refresh, None) if no refresh
    """
    if time.monotonic() - last_refresh > _REGISTRY_REFRESH_TTL:
        source = load_configs(configs, system_meta)
        return time.monotonic(), source
    return last_refresh, None


def _try_load_from_registry(
    configs: Dict[str, Dict[str, str]],
    system_meta: Dict[str, Dict[str, Any]],
) -> bool:
    """同步查詢 NemoClaw Registry API"""
    if httpx is None:
        return False

    token = os.getenv("MCP_SERVICE_TOKEN", "")
    headers: Dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        with httpx.Client(timeout=_REGISTRY_TIMEOUT) as client:
            resp = client.get(_REGISTRY_URL, headers=headers)
            if resp.status_code != 200:
                logger.warning(
                    "NemoClaw Registry returned HTTP %d", resp.status_code
                )
                return False

            data = resp.json()
            _parse_registry_response(data, configs, system_meta)
            logger.info(
                "Federation loaded %d systems from NemoClaw Registry",
                len(configs),
            )
            return True

    except Exception as e:
        logger.warning("NemoClaw Registry unreachable: %s", e)
        return False


def _parse_registry_response(
    data: Dict[str, Any],
    configs: Dict[str, Dict[str, str]],
    system_meta: Dict[str, Dict[str, Any]],
) -> None:
    """解析 Registry JSON 並建構 configs + system_meta"""
    configs.clear()
    system_meta.clear()

    token = os.getenv("MCP_SERVICE_TOKEN", "")

    # Engine (OpenClaw) — 透過 NemoClaw Gateway scheduler 調度
    engine: Dict[str, Any] = data.get("engine") or {}
    engine_url: str = str(engine.get("url", ""))
    engine_status: str = str(engine.get("status", ""))
    if engine_url and engine_status in ("active", "degraded"):
        engine_name: str = str(engine.get("name", "openclaw"))
        gateway_url = os.getenv(
            "NEMOCLAW_GATEWAY_URL",
            _REGISTRY_URL.rsplit("/api/registry", 1)[0],
        )
        configs[engine_name] = {
            "url": gateway_url.rstrip("/"),
            "token": token,
            "endpoint": "/api/gateway/reason",
        }
        fallback_name = (_FALLBACK_REGISTRY.get(engine_name) or {}).get("name")
        system_meta[engine_name] = {
            "name": fallback_name or f"CK_{engine_name.title()}",
            "description": "多頻道 AI 管道系統",
            "status": engine_status,
        }

    # Plugins（排除自身）
    for plugin in data.get("plugins") or []:
        plugin_id: str = plugin.get("id", "")
        if not plugin_id or plugin_id == _SELF_PLUGIN_ID:
            continue
        if not plugin.get("enabled"):
            continue

        system_id = plugin_id.removeprefix("ck-")
        url = plugin.get("url", "")
        api_path = plugin.get("api_path", "")

        if not url:
            continue

        configs[system_id] = {
            "url": url.rstrip("/"),
            "token": token,
            "endpoint": api_path or "/health",
        }
        system_meta[system_id] = {
            "name": plugin_id,
            "description": plugin.get("description", ""),
            "status": plugin.get("status", "unknown"),
            "capabilities": plugin.get("capabilities", []),
        }


def _load_from_fallback(
    configs: Dict[str, Dict[str, str]],
    system_meta: Dict[str, Dict[str, Any]],
) -> None:
    """從環境變數 + 靜態回退表載入（Registry 不可達時）"""
    configs.clear()
    system_meta.clear()
    token = os.getenv("MCP_SERVICE_TOKEN", "")

    for system_id, registry in _FALLBACK_REGISTRY.items():
        url = os.getenv(registry["url_env"], "") or registry.get("default_url", "")
        if url:
            configs[system_id] = {
                "url": url.rstrip("/"),
                "token": token,
                "endpoint": registry["endpoint"],
            }
            system_meta[system_id] = {
                "name": registry["name"],
                "description": registry["description"],
                "status": "unknown",
            }
            source = "env" if os.getenv(registry["url_env"], "") else "default"
            logger.info(
                "Federation fallback '%s': %s (%s)",
                system_id,
                url,
                source,
            )
