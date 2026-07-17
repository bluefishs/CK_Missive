"""
角色權限與系統權限管理 API 端點

拆分自 user_management.py

> 2026-07-17 異質同工收斂（HETEROGENEOUS_WORK_REGISTRY C1）：移除 3 個 verified-dead 端點
>   （roles/{role}/permissions/detail、.../update、roles/list）——前端0+後端0+測試0 呼叫，
>   功能由 role_permissions_admin.py（/admin/role-permissions/*）取代。僅保留仍被
>   adminUsersApi 使用的 /permissions/available。人工+LLM 雙判定為真異質同工。
"""
import logging

from fastapi import APIRouter, Depends

from app.core.dependencies import require_admin
from app.extended.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/permissions/available", summary="取得可用權限列表")
async def get_available_permissions(
    admin_user: User = Depends(require_admin())
):
    """取得系統中所有可用的權限列表 (管理員功能) - POST-only"""
    return {
        "permissions": [
            "documents:read", "documents:create", "documents:edit",
            "documents:delete", "documents:export",
            "projects:read", "projects:create", "projects:edit", "projects:delete",
            "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
            "admin:users", "admin:settings", "admin:database", "admin:site_management",
            "reports:view", "reports:export",
            "calendar:read", "calendar:edit", "notifications:read",
            "operational:read", "operational:write", "operational:approve",
        ],
        "roles": [
            {"name": "unverified", "display_name": "未驗證者", "default_permissions": []},
            {
                "name": "user", "display_name": "一般使用者",
                "default_permissions": [
                    "documents:read", "projects:read", "agencies:read",
                    "vendors:read", "calendar:read", "reports:view",
                    "operational:read",
                ]
            },
            {
                "name": "admin", "display_name": "管理員",
                "default_permissions": [
                    "documents:read", "documents:create", "documents:edit", "documents:delete",
                    "projects:read", "projects:create", "projects:edit", "projects:delete",
                    "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
                    "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
                    "admin:users", "admin:settings", "admin:site_management",
                    "reports:view", "reports:export",
                    "calendar:read", "calendar:edit",
                    "operational:read", "operational:write", "operational:approve",
                ]
            },
            {"name": "superuser", "display_name": "超級管理員", "default_permissions": ["*"]}
        ]
    }
