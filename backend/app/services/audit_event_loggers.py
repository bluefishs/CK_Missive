"""
Audit Event Loggers -- specialised audit methods for auth, AI, permissions, users.

Extracted from audit_service.py to keep the core service under 500L.

All methods delegate to AuditService.log_change for actual persistence.

Version: 1.0.0
Created: 2026-04-08
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditEventLoggersMixin:
    """
    Mixin providing domain-specific audit logging methods.

    Designed to be mixed into AuditService so the public API stays unchanged.
    All methods are static and async, delegating to log_change.
    """

    # ============ Auth events ============

    @staticmethod
    async def log_auth_event(
        event_type: str,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> bool:
        """
        Record authentication events.

        Event types:
        - LOGIN_SUCCESS, LOGIN_FAILED, LOGIN_BLOCKED
        - LOGOUT, TOKEN_REFRESH, SESSION_EXPIRED, SESSION_REVOKED
        - ACCOUNT_CREATED, ACCOUNT_ACTIVATED, ACCOUNT_DEACTIVATED
        """
        from app.services.audit_service import AuditService

        changes = {
            "event_type": event_type,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent[:200] if user_agent else None,
            "success": success,
            **(details or {}),
        }

        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"[AUTH_AUDIT] {event_type} | Email: {email} | "
            f"User: {user_id} | IP: {ip_address} | Success: {success}",
        )

        return await AuditService.log_change(
            table_name="auth_events",
            record_id=user_id or 0,
            action=event_type,
            changes=changes,
            user_id=user_id,
            user_name=email,
            source="AUTH",
            ip_address=ip_address,
        )

    # ============ AI events ============

    @staticmethod
    async def log_ai_event(
        event_type: str,
        feature: str,
        input_text: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source_provider: str = "unknown",
        tokens_used: int = 0,
        latency_ms: float = 0,
        success: bool = True,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record AI operation events.

        Event types:
        - AI_SUMMARY_GENERATED, AI_CLASSIFY_SUGGESTED, AI_KEYWORDS_EXTRACTED
        - AI_SEARCH_EXECUTED, AI_INTENT_PARSED, AI_AGENCY_MATCHED
        """
        from app.services.audit_service import AuditService

        changes: Dict[str, Any] = {
            "event_type": event_type,
            "feature": feature,
            "input_text": input_text[:200] if input_text else "",
            "source_provider": source_provider,
            "tokens_used": tokens_used,
            "latency_ms": round(latency_ms, 2),
            "success": success,
        }
        if error:
            changes["error"] = error[:500]
        if details:
            changes.update(details)

        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"[AI_AUDIT] {event_type} | Feature: {feature} | "
            f"Provider: {source_provider} | Tokens: {tokens_used} | "
            f"Latency: {latency_ms:.0f}ms | Success: {success}",
        )

        return await AuditService.log_change(
            table_name="ai_events",
            record_id=user_id or 0,
            action=event_type,
            changes=changes,
            user_id=user_id,
            user_name=user_name,
            source="AI",
        )

    # ============ Permission events ============

    @staticmethod
    async def log_permission_change(
        user_id: int,
        action: str,
        old_permissions: Optional[list] = None,
        new_permissions: Optional[list] = None,
        old_role: Optional[str] = None,
        new_role: Optional[str] = None,
        admin_id: Optional[int] = None,
        admin_name: Optional[str] = None,
    ) -> bool:
        """Record permission change events."""
        from app.services.audit_service import AuditService

        changes: Dict[str, Any] = {}

        if old_permissions is not None or new_permissions is not None:
            changes["permissions"] = {
                "old": old_permissions,
                "new": new_permissions,
            }

        if old_role or new_role:
            changes["role"] = {
                "old": old_role,
                "new": new_role,
            }

        logger.warning(
            f"[PERMISSION_AUDIT] {action} | User: {user_id} | "
            f"Admin: {admin_name}(#{admin_id}) | Changes: {changes}"
        )

        return await AuditService.log_change(
            table_name="user_permissions",
            record_id=user_id,
            action=action,
            changes=changes,
            user_id=admin_id,
            user_name=admin_name,
            source="ADMIN",
        )

    # ============ User data events ============

    @staticmethod
    async def log_user_change(
        user_id: int,
        action: str,
        changes: Dict[str, Any],
        admin_id: Optional[int] = None,
        admin_name: Optional[str] = None,
    ) -> bool:
        """Record user data changes."""
        from app.services.audit_service import AuditService

        return await AuditService.log_change(
            table_name="users",
            record_id=user_id,
            action=action,
            changes=changes,
            user_id=admin_id,
            user_name=admin_name,
            source="ADMIN",
        )
