"""Service-to-service authentication via X-Service-Token header.

Used by NemoClaw and other internal service integrations.
Supports dual-token rotation for zero-downtime token changes (S-3).
"""

import hmac
import os
from typing import Any

import structlog
from fastapi import Header, HTTPException, Request, status

log = structlog.get_logger(__name__)


async def verify_service_token(
    request: Request,
    x_service_token: str | None = Header(None),
) -> dict[str, Any]:
    """Verify X-Service-Token header for service-to-service authentication.

    Supports dual-token rotation: accepts both MCP_SERVICE_TOKEN (current)
    and MCP_SERVICE_TOKEN_PREV (previous) for zero-downtime token rotation.

    Returns a claims dict with service metadata for audit logging.
    Raises HTTPException on auth failure (401/403).
    """
    current_token = os.getenv("MCP_SERVICE_TOKEN", "")
    prev_token = os.getenv("MCP_SERVICE_TOKEN_PREV", "")

    if not current_token:
        is_dev = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        client_host = request.client.host if request.client else ""
        if is_dev and (
            client_host in ("127.0.0.1", "::1")
            or client_host.startswith("172.16.")
            or client_host.startswith("172.17.")
            or client_host.startswith("172.18.")
            or client_host.startswith("172.24.")
            or client_host.startswith("192.168.")
            or client_host.startswith("10.")
        ):
            log.warning(
                "service_token_dev_bypass",
                client_host=client_host,
            )
            return {"service_id": "local-dev", "request_source": client_host}
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service token required",
        )

    if not x_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )

    token_bytes = x_service_token.encode("utf-8")
    match_current = hmac.compare_digest(token_bytes, current_token.encode("utf-8"))
    match_prev = (
        hmac.compare_digest(token_bytes, prev_token.encode("utf-8"))
        if prev_token
        else False
    )
    if not match_current and not match_prev:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )

    return {
        "service_id": "service-token-auth",
        "request_source": request.client.host if request.client else "unknown",
        "token_generation": "prev" if not match_current and match_prev else "current",
    }
