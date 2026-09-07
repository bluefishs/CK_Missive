#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依賴注入模組

提供統一的依賴注入機制，用於 FastAPI 端點。

依賴注入模式說明
================

工廠模式（所有服務統一使用）
-------------------------------------
Service 在建構時接收 db session，方法簽名更簡潔。

    def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
        def _get_service(db: AsyncSession = Depends(get_async_db)) -> T:
            return service_class(db)
        return _get_service

    @router.get("/items")
    async def list_items(
        item_service: ItemService = Depends(get_service(ItemService))
    ):
        return await item_service.get_items()  # 無需傳遞 db

遷移計劃
========
新開發的 Service 應使用模式 2（工廠模式）。
現有 Service 將逐步遷移，遷移順序：
1. 新服務 → 直接使用工廠模式
2. 獨立服務 → 修改 __init__ 接受 db 參數
3. 核心服務 → 保持向後相容直到大版本更新
"""

from typing import Type, TypeVar, Callable, Any
from functools import wraps
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db

# 泛型類型變數
T = TypeVar('T')


# ============================================================================
# Service 工廠函數
# ============================================================================

def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
    """
    建立 Service 依賴注入工廠函數

    使用方式:
        from app.core.dependencies import get_service
        from app.services.vendor.core import VendorService

        @router.get("/vendors")
        async def list_vendors(
            vendor_service: VendorService = Depends(get_service(VendorService))
        ):
            return await vendor_service.get_list()

    Args:
        service_class: Service 類別

    Returns:
        依賴注入函數
    """
    def _get_service(db: AsyncSession = Depends(get_async_db)) -> T:
        # 建立 Service 實例並傳入 db session
        return service_class(db)
    return _get_service


# 別名：向後相容
get_service_with_db = get_service


def get_project_service(db: AsyncSession = Depends(get_async_db)):
    """ProjectService 工廠函數"""
    from app.services.contract.core import ProjectService
    return ProjectService(db)


def get_agency_service(db: AsyncSession = Depends(get_async_db)):
    """AgencyService 工廠函數"""
    from app.services.agency.core import AgencyService
    return AgencyService(db)


# ============================================================================
# 分頁參數依賴
# ============================================================================

from app.schemas.common import PaginationParams, BaseQueryParams


async def get_pagination(
    page: int = 1,
    limit: int = 20
) -> PaginationParams:
    """
    分頁參數依賴注入

    使用方式:
        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(get_pagination)
        ):
            skip = pagination.skip
            limit = pagination.limit
    """
    return PaginationParams(page=page, limit=limit)


async def get_query_params(
    page: int = 1,
    limit: int = 20,
    search: str = None,
    sort_by: str = "id",
    sort_order: str = "desc"
) -> BaseQueryParams:
    """
    通用查詢參數依賴注入

    包含分頁、搜尋和排序參數。
    """
    from app.schemas.common import SortOrder
    return BaseQueryParams(
        page=page,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=SortOrder(sort_order) if sort_order in ['asc', 'desc'] else SortOrder.DESC
    )


# ============================================================================
# 認證與權限依賴
# ============================================================================

from app.extended.models import User
from app.api.endpoints.auth import get_current_user


def require_auth() -> Callable:
    """
    需要認證的依賴

    使用方式:
        @router.get("/protected")
        async def protected_endpoint(
            current_user: User = Depends(require_auth())
        ):
            return {"user": current_user.username}
    """
    return get_current_user


def optional_auth() -> Callable:
    """
    可選認證的依賴

    若有 token 則驗證並返回用戶，無 token 則返回 None。
    使用 Depends(get_async_db) 共享端點的 DB session（避免重複建立連線）。

    使用方式:
        @router.get("/public-or-private")
        async def endpoint(
            current_user: Optional[User] = Depends(optional_auth())
        ):
            if current_user:
                return {"user": current_user.username}
            return {"message": "Anonymous access"}
    """
    from typing import Optional
    from fastapi import Request

    async def _get_current_user_optional(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
    ) -> Optional[User]:
        """可選的用戶認證 — 支援 Bearer header + httpOnly cookie"""
        from app.core.config import settings
        if settings.AUTH_DISABLED:
            return None

        # 1. Authorization header (Bearer token)
        token = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # 2. httpOnly cookie fallback
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            return None

        try:
            from app.core.auth_service import AuthService
            return await AuthService.get_current_user_from_token(db, token)
        except Exception:
            return None

    return _get_current_user_optional


# 管理員判定的**唯一實作**（2026-08-10 收斂）。
#
# 這條規則原本散在四個地方且各不相同：
#   · dependencies.require_admin  → flag OR role（正確，且註解寫明「防止雙軌不一致」）
#   · auth/login_history.py       → flag OR role（正確）
#   · api/endpoints/backup.py     → **只看 flag**（10 個端點）
#   · auth_service.check_admin_permission → 只看 flag（零生產呼叫者）
#
# 後果是真的發生了：員工 `洪慶忠` 的 role='admin' 但 is_admin=false，
# 於是他在選單看得到「備份管理」（前端 usePermissions 併看 role），
# 點進去每一個動作都回 403 —— 看得到而用不了，最難自行診斷的一種。
#
# 為什麼是併看而不是二選一：兩個欄位都存在且都被寫入，任一為真就是管理員；
# 只認其中一個，等於讓另一個欄位的資料靜靜失效。
def is_admin_user(user) -> bool:
    """是否為管理員 —— **只看角色**。

    ⭐ 2026-09-07 權限收斂：此前是「旗標 OR 角色」，於是 `is_admin` 旗標是
    凌駕權限清單的第三份宣告 —— 賴秀玲的角色與權限清單都是財務，旗標卻讓她
    仍能進使用者管理、備份、部署、資料庫，而權限管理頁上完全看不出來。
    ⇒ 角色是唯一來源；`is_admin` 欄位改為**由角色推導的鏡像**（寫入時同步、讀取時不看）。
    """
    if user is None:
        return False
    return getattr(user, "role", "") in ("admin", "superuser")


def is_superuser_user(user) -> bool:
    """是否為超級使用者 —— 同樣併看 role。

    與 `is_admin_user` 分開，因為語意不同：superuser 是更窄的一群，
    用在「擁有所有權限」的直通、與「不得刪除／停用」的保護。
    這兩個方向都偏好併看 role —— 保護性檢查若漏看，就會**保護不到**。
    """
    if user is None:
        return False
    # 2026-09-07 權限收斂：只看角色（旗標改為由角色推導的鏡像，見 is_admin_user）
    return getattr(user, "role", "") == "superuser"


def require_admin():
    """
    需要管理員權限的依賴

    使用方式:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_admin())
        ):
            return {"message": "Admin access granted"}
    """
    async def _require_admin(
        current_user: User = Depends(get_current_user)
    ) -> User:
        from app.core.exceptions import ForbiddenException
        if not is_admin_user(current_user):
            raise ForbiddenException("需要管理員權限")
        return current_user
    return _require_admin


def require_permission(permission: str):
    """
    需要特定權限的依賴

    使用方式:
        @router.delete("/items/{id}")
        async def delete_item(
            id: int,
            current_user: User = Depends(require_permission("items:delete"))
        ):
            pass

    Args:
        permission: 需要的權限名稱
    """
    async def _require_permission(
        current_user: User = Depends(get_current_user)
    ) -> User:
        from app.core.exceptions import ForbiddenException
        from app.core.auth_service import AuthService

        # 超級管理員擁有所有權限
        if is_superuser_user(current_user):
            return current_user

        # 檢查特定權限
        if not AuthService.check_permission(current_user, permission):
            raise ForbiddenException(f"需要 '{permission}' 權限")

        return current_user
    return _require_permission


def require_any_permission(*permissions: str):
    """**任一**權限即可通過。

    ⚠️ 2026-09-07 owner：「ERP 仍無法獨立區分選取」。
    ERP 底下 6 個頁面共用 `reports:erp:view` 一個碼 ⇒ 在權限管理頁勾任何一個
    等於把 6 個全部打開（粒度是碼的數量，不是頁面的數量）。

    要獨立勾選就得一頁一碼；但只把 API 換成新碼，**既有持有 `reports:erp:view`
    的人會當場被擋**（角色層與使用者層都要同步，任一沒跟上就是 403 —— 09-07
    拆委託／協力帳款時已經因此讓管理員看不到那兩頁）。

    ⇒ 每支 ERP 子路由改成「**該頁自己的碼 或 `reports:erp:view`**」：
      · 只給新碼的人 → 只進得去那一頁（真正的獨立）
      · 既有 `reports:erp:view` 的人 → 全部照舊，零回歸
      · 日後要收緊，把 `reports:erp:view` 從角色移除即可，不必再動程式碼

    superuser 一律短路（與 `require_permission` 相同）。
    """
    async def _require_any(
        current_user: User = Depends(get_current_user)
    ) -> User:
        from app.core.exceptions import ForbiddenException
        from app.core.auth_service import AuthService

        if is_superuser_user(current_user):
            return current_user
        if any(AuthService.check_permission(current_user, p) for p in permissions):
            return current_user
        raise ForbiddenException(f"需要 {' 或 '.join(permissions)} 其中之一的權限")
    return _require_any


# ============================================================================
# 快取相關依賴（預留）
# ============================================================================

# async def get_cache_manager():
#     """取得快取管理器"""
#     from app.core.cache_manager import cache_manager
#     return cache_manager


