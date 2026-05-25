"""ADR-0034 動態 Role Permissions 管理端點（POST-only 資安規範）。

對應 `/admin/permissions/admin` 動態編輯介面。

所有 endpoint 一律 POST（含查詢類）以符合系統 POST-only 資安要求。

Endpoints (mount prefix: /api/admin/role-permissions):
    POST /list       — 列所有 role 配置（管理員可見）
    POST /get        — 取單一 role 詳情（body: {role: "admin"}）
    POST /update     — 更新單一 role permissions（body: {role, permissions[]}）+ audit
    POST /available  — 系統內可分派 permission 全集 + 未分派提示

Authorization:
    全部 endpoint 走 require_admin（admin / superuser 可訪問）。
    update 端點額外要求 admin:settings 權限（防 admin 越權自我擴權）。

關聯：
- ADR-0034 動態 role permissions
- docs/architecture/ADR_HALF_WIRED_AUDIT_20260506.md
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db, require_admin
from app.core.rate_limiter import limiter
from app.extended.models import User
from app.services.system.role_permissions_service import RolePermissionsService

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /list — 列所有 role 配置
# ---------------------------------------------------------------------------
@router.post("/list", summary="列出所有 role 與其 permissions")
@limiter.limit("30/minute")
async def list_role_permissions(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """列出所有 role 配置。

    回傳每個 role 的 permission count + name_zh + can_login 等 metadata，
    供 PermissionManagementPage 主畫面卡片展示用。
    """
    service = RolePermissionsService(db)
    roles = await service.list_all_roles()
    return {"success": True, "items": roles, "total": len(roles)}


# ---------------------------------------------------------------------------
# POST /get — 取單一 role 詳情
# ---------------------------------------------------------------------------
@router.post("/get", summary="取得單一 role 詳細權限")
@limiter.limit("30/minute")
async def get_role_permissions(
    request: Request,
    response: Response,
    role: str = Body(..., embed=True, description="role key（admin/user/staff/...）"),
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """取單一 role 完整 permission list（給編輯介面初始化）。"""
    service = RolePermissionsService(db)
    data = await service.get_role(role)
    if not data:
        raise HTTPException(status_code=404, detail=f"role '{role}' 不存在")
    return {"success": True, "role": data}


# ---------------------------------------------------------------------------
# POST /update — 更新 role permissions + audit
# ---------------------------------------------------------------------------
@router.post("/update", summary="更新 role 的 permissions（admin 限定 + audit log）")
@limiter.limit("10/minute")
async def update_role_permissions(
    request: Request,
    response: Response,
    role: str = Body(..., description="目標 role"),
    permissions: List[str] = Body(..., description="新 permission list"),
    note: Optional[str] = Body(None, description="變更說明（可選，記入 audit）"),
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """更新 role 的 permission set。

    限制：
    - 不可修改 'superuser'（wildcard 保護）
    - 操作者必須是 admin 或 superuser
    - 變更會記入 audit log（actor_id + 時間戳）

    Body:
        role: 目標 role
        permissions: 新的 permission keys 陣列（會去重 + 排序）
        note: 變更說明（可選）
    """
    service = RolePermissionsService(db)
    try:
        updated = await service.update_role_permissions(role, permissions, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log（best-effort，不阻擋主交易）
    try:
        from app.services.audit import AuditService
        await AuditService.log_auth_event(
            event_type="ROLE_PERMISSIONS_UPDATE",
            user_id=current_user.id,
            email=current_user.email,
            details={
                "role": role,
                "permission_count": len(updated["permissions"]),
                "note": note,
            },
            success=True,
        )
    except Exception as audit_err:
        logger.error(
            "[AUDIT] ROLE_PERMISSIONS_UPDATE 寫入失敗: %s", audit_err, exc_info=True
        )

    return {
        "success": True,
        "role": updated,
        "message": f"role '{role}' permissions 已更新（{len(updated['permissions'])} 項）",
    }


# ---------------------------------------------------------------------------
# POST /available — 系統內可分派 permission 全集
# ---------------------------------------------------------------------------
@router.post("/available", summary="列出系統可分派的 permission 全集")
@limiter.limit("30/minute")
async def get_available_permissions(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """回傳系統內已知所有 permission keys，分類：
    - all: 全集
    - assigned: 已被某 role 分派
    - unassigned: 未分派（待 admin 在 PermissionManagementPage 處理 — 紅點提示）
    - from_navigation_items: 來自 site_navigation_items
    - from_business_endpoints: 來自業務 endpoint hardcode

    /admin/site-management 加新 nav item 後，permission_required 會自動進入 from_navigation_items；
    /admin/permissions/admin 介面立即看到「unassigned 紅點」提示。
    """
    service = RolePermissionsService(db)
    data = await service.get_available_permissions()
    return {"success": True, **data}


# ---------------------------------------------------------------------------
# POST /sync-users — 將指定 role 所有 user.permissions 同步至最新 role 配置
# ---------------------------------------------------------------------------
@router.post(
    "/sync-users",
    summary="批次同步指定 role 的所有 user.permissions（修 role 後補齊舊用戶）",
)
@limiter.limit("3/minute")
async def sync_users_to_role(
    request: Request,
    response: Response,
    role: str = Body(..., description="目標 role"),
    only_outdated: bool = Body(True, description="True 只更新與目前 role 不同的 user；False 強制全更新"),
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """將指定 role 的所有 active user.permissions 同步為 role_permissions[role]。

    場景：在 /admin/permissions/{role} 修改 admin role 後，舊有 admin user 的
    user.permissions 不會自動跟著動。本端點批次補齊。

    限制：
    - rate limit 3/min（避免誤觸）
    - role='superuser' 拒絕（wildcard 不適用「同步」概念）
    - 操作必須 admin 級
    """
    if role == "superuser":
        raise HTTPException(
            status_code=400,
            detail="superuser 為 wildcard，無需同步（user.permissions 由 hasPermission 短路）",
        )

    service = RolePermissionsService(db)
    try:
        result = await service.sync_users_to_role_permissions(
            role=role, actor_id=current_user.id, only_outdated=only_outdated,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        from app.services.audit import AuditService
        await AuditService.log_auth_event(
            event_type="ROLE_USERS_SYNC",
            user_id=current_user.id,
            email=current_user.email,
            details={
                "role": role,
                "scanned": result["scanned"],
                "updated": result["updated"],
                "skipped": result["skipped"],
            },
            success=True,
        )
    except Exception as audit_err:
        logger.error("[AUDIT] ROLE_USERS_SYNC 寫入失敗: %s", audit_err, exc_info=True)

    return {
        "success": True,
        "message": (
            f"role '{role}' 同步完成：掃 {result['scanned']} user，"
            f"更新 {result['updated']}，略過 {result['skipped']}（已對齊）"
        ),
        **result,
    }


# ---------------------------------------------------------------------------
# POST /nav-tree — 完整 nav 階層 + 對應 permission_required + 反查 map
# ---------------------------------------------------------------------------
@router.post(
    "/nav-tree",
    summary="取得完整選單階層 + 對應 permission_required（給「依選單階層」編輯介面）",
)
@limiter.limit("30/minute")
async def get_navigation_tree(
    request: Request,
    response: Response,
    role: Optional[str] = Body(None, embed=True, description="目標 role（如有，回傳該 role 當前 permissions 預勾用）"),
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """回傳 site_navigation_items 完整階層 + 每節點 permission_required。

    Response:
        - tree: 階層樹（root list，含 children 遞迴）
        - role / role_permissions / is_wildcard: 預勾依據
        - perm_to_nav: 反查同 perm 影響哪些 nav

    用途：/admin/permissions/{role} 編輯頁「依選單階層」Tab 渲染樹。
    多個 nav 共用同 perm 時（如平臺資訊 + 知識地圖 + AI助理 都用 admin:settings），
    UI 可用 perm_to_nav 反查並標示「同時影響 N 個選單」。
    """
    service = RolePermissionsService(db)
    data = await service.get_navigation_tree_with_permissions(role=role)
    return {"success": True, **data}
