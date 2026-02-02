# A01 - 存取控制安全模式

> **OWASP 類別**: A01:2025 – Broken Access Control
> **嚴重性**: Critical
> **適用技術**: FastAPI, React, PostgreSQL

---

## 常見漏洞

| 漏洞類型      | 說明              | 影響           |
| ------------- | ----------------- | -------------- |
| IDOR          | 直接物件參考漏洞  | 可存取他人資料 |
| 權限繞過      | 缺少權限檢查      | 越權操作       |
| URL 篡改      | 修改 URL 參數存取 | 資料洩漏       |
| CORS 錯誤配置 | 允許任意來源      | 跨站請求       |

---

## 安全模式

### 1. 資源擁有權驗證 (IDOR 防護)

```python
# ❌ 錯誤：直接使用用戶傳入的 ID
@router.post("/documents/{doc_id}")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    return await db.get(Document, doc_id)  # 任何人都可存取

# ✅ 正確：驗證資源擁有權
@router.post("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    document = await db.get(Document, doc_id)
    if not document:
        raise HTTPException(404, "Document not found")

    # 驗證擁有權
    if document.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "無權存取此文件")

    return document
```

### 2. 角色權限裝飾器

```python
# backend/app/core/permissions.py
from functools import wraps
from typing import List
from fastapi import HTTPException, status

def require_roles(allowed_roles: List[str]):
    """角色權限檢查裝飾器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user = None, **kwargs):
            if current_user is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登入")

            if current_user.role not in allowed_roles and not current_user.is_admin:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "權限不足")

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# 使用範例
@router.post("/admin/users")
@require_roles(["admin", "superuser"])
async def list_all_users(current_user: User = Depends(get_current_user)):
    ...
```

### 3. 資源層級權限檢查

```python
# backend/app/services/permission_service.py
from enum import Enum
from typing import Optional

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class PermissionService:
    """統一權限檢查服務"""

    @staticmethod
    async def check_document_permission(
        user: User,
        document: Document,
        required_permission: Permission
    ) -> bool:
        # 管理員擁有所有權限
        if user.is_admin:
            return True

        # 擁有者權限
        if document.owner_id == user.id:
            return True

        # 檢查共享權限
        share = await DocumentShare.get_by_user_and_doc(user.id, document.id)
        if share and share.permission_level >= required_permission:
            return True

        return False

# 使用範例
@router.post("/documents/{doc_id}/update")
async def update_document(doc_id: int, data: DocumentUpdate, ...):
    document = await db.get(Document, doc_id)

    if not await PermissionService.check_document_permission(
        current_user, document, Permission.WRITE
    ):
        raise HTTPException(403, "無編輯權限")

    # 執行更新...
```

### 4. 前端路由守衛

```typescript
// src/guards/AuthGuard.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requiredRoles = []
}) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  // 未登入
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 權限不足
  if (requiredRoles.length > 0 && !requiredRoles.includes(user.role)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
};

// 使用範例
<Route
  path="/admin/*"
  element={
    <AuthGuard requiredRoles={['admin']}>
      <AdminLayout />
    </AuthGuard>
  }
/>
```

---

## 檢查清單

- [ ] 所有 API 端點都驗證用戶身份
- [ ] 資源存取前驗證擁有權
- [ ] 使用統一的權限檢查服務
- [ ] 前端路由有對應的守衛
- [ ] CORS 配置只允許信任的來源
- [ ] 敏感操作記錄審計日誌

---

## 相關資源

- [OWASP Access Control Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Access_Control_Cheat_Sheet.html)
- 專案位置: `backend/app/core/permissions.py`
