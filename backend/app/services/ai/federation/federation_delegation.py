"""
Federation Delegation -- 跨域委派模組 (拆分自 federation_client.py)

負責跨域任務委派與模式共享邏輯。

Version: 1.0.0
Created: 2026-04-08
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# 本系統 Agent ID
_SELF_AGENT_ID = "ck_missive"

# NemoClaw Registry 端點 (用於推算 Gateway URL)
_REGISTRY_URL = os.getenv(
    "NEMOCLAW_REGISTRY_URL", "http://nemoclaw_tower:9000/api/registry"
)


async def delegate(
    target_agent_id: str,
    intent: str,
    context: Optional[Dict[str, Any]] = None,
    forward_action: str = "reason",
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    透過 NemoClaw Gateway 將任務委派至其他插件

    Args:
        target_agent_id: 目標插件 ID（如 "ck-tunnel"）或 "auto" 自動匹配
        intent: 委派意圖描述（自然語言）
        context: 跨域上下文（可選）
        forward_action: 轉發至目標的 action 類型（reason/query）
        timeout: 請求超時秒數

    Returns:
        { system, success, target_agent_id, delegated, target_response,
          routing_reason, latency_ms, error }
    """
    gateway_url = os.getenv(
        "NEMOCLAW_GATEWAY_URL",
        _REGISTRY_URL.rsplit("/api/registry", 1)[0],
    )
    url = f"{gateway_url.rstrip('/')}/api/gateway/delegate"
    token = os.getenv("MCP_SERVICE_TOKEN", "")

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    payload: Dict[str, Any] = {
        "agent_id": _SELF_AGENT_ID,
        "action": "delegate",
        "payload": {
            "target_agent_id": target_agent_id,
            "intent": intent,
            "forward_action": forward_action,
            "context": context or {},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    start = time.monotonic()

    try:
        if httpx is None:
            raise ImportError("httpx not installed")

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            data = resp.json()
            success = data.get("success", False)
            result = data.get("result") or {}
            error_obj = data.get("error") or {}
            meta = data.get("meta") or {}

            return {
                "system": target_agent_id,
                "success": success,
                "target_agent_id": result.get("target_agent_id", target_agent_id) if isinstance(result, dict) else target_agent_id,
                "delegated": result.get("delegated", False) if isinstance(result, dict) else False,
                "target_response": result.get("target_response") if isinstance(result, dict) else None,
                "routing_reason": result.get("routing_reason", "") if isinstance(result, dict) else "",
                "latency_ms": meta.get("latency_ms", elapsed_ms) if isinstance(meta, dict) else elapsed_ms,
                "error": error_obj.get("message") if isinstance(error_obj, dict) and not success else None,
            }

    except ImportError:
        logger.error("httpx not installed; delegate unavailable")
        return delegate_error(target_agent_id, "httpx 未安裝")
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Delegate to %s failed: %s", target_agent_id, e)
        return delegate_error(
            target_agent_id,
            f"連線失敗: {type(e).__name__}: {e}",
            elapsed_ms,
        )


async def delegate_with_patterns(
    query: str,
    context: str = "",
    max_patterns: int = 5,
) -> Dict[str, Any]:
    """Delegate query to external agent WITH learned patterns.

    Includes top successful patterns from local agent to aid external.
    Accepts contributed_patterns back from external agent.
    """
    # 1. Gather top local patterns
    local_patterns = await get_top_patterns(max_patterns)

    # 2. Build enhanced payload
    enhanced_context: Dict[str, Any] = {
        "original_context": context,
        "source_agent": _SELF_AGENT_ID,
        "learned_patterns": local_patterns,
    }

    # 3. Delegate via existing mechanism
    result = await delegate(
        target_agent_id="auto",
        intent=query,
        context=enhanced_context,
    )

    # 4. If response includes contributed_patterns, merge locally
    target_resp = result.get("target_response") or {}
    contributed = (
        target_resp.get("contributed_patterns", [])
        if isinstance(target_resp, dict)
        else []
    )
    if contributed:
        merged = await merge_external_patterns(contributed)
        result["patterns_merged"] = merged

    return result


async def delegate_auto(
    intent: str,
    context: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    自動路由委派 — 由 NemoClaw Gateway 依 capabilities 匹配最佳插件
    """
    return await delegate("auto", intent, context, timeout=timeout)


async def get_top_patterns(limit: int = 5) -> List[Dict[str, Any]]:
    """Get top graduated patterns for sharing."""
    try:
        from app.core.redis_client import get_redis

        redis = await get_redis()
        if not redis:
            return []
        patterns = await redis.zrevrange(
            "agent:patterns:index", 0, limit - 1, withscores=True
        )
        result: List[Dict[str, Any]] = []
        for key, score in patterns:
            if isinstance(key, bytes):
                key = key.decode()
            detail = await redis.hgetall(f"agent:patterns:detail:{key}")
            if detail:
                tool_seq = detail.get(b"tool_sequence", detail.get("tool_sequence", b""))
                query_tpl = detail.get(b"query_template", detail.get("query_template", b""))
                if isinstance(tool_seq, bytes):
                    tool_seq = tool_seq.decode()
                if isinstance(query_tpl, bytes):
                    query_tpl = query_tpl.decode()
                result.append({
                    "pattern_key": key,
                    "score": score,
                    "tool_sequence": tool_seq,
                    "query_template": query_tpl,
                })
        return result
    except Exception:
        return []


async def merge_external_patterns(patterns: List[Dict[str, Any]]) -> int:
    """Merge externally contributed patterns into local store."""
    merged = 0
    try:
        from app.core.redis_client import get_redis

        redis = await get_redis()
        if not redis:
            return 0
        for p in patterns[:10]:
            raw_key = p.get("pattern_key", "")
            if not raw_key:
                continue
            key = f"ext:{raw_key}"
            await redis.zadd("agent:patterns:index", {key: 0.5})
            await redis.hset(
                f"agent:patterns:detail:{key}",
                mapping={
                    "tool_sequence": p.get("tool_sequence", ""),
                    "query_template": p.get("query_template", ""),
                    "source_agent": p.get("source_agent", "external"),
                    "imported_at": str(datetime.now(timezone.utc)),
                },
            )
            merged += 1
    except Exception as e:
        logger.debug("Failed to merge external patterns: %s", e)
    return merged


def delegate_error(
    target: str, error: str, latency_ms: int = 0
) -> Dict[str, Any]:
    """Create a delegation error result."""
    return {
        "system": target,
        "success": False,
        "target_agent_id": target,
        "delegated": False,
        "target_response": None,
        "routing_reason": "",
        "latency_ms": latency_ms,
        "error": error,
    }
