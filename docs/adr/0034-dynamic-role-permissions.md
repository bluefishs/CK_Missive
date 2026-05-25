# ADR-0034：動態 Role Permissions（DB 為 SSOT）

> **狀態**：accepted
> **建立日期**：2026-05-06
> **觸發事件**：李昭德 admin role 側邊欄只 3 項；前端 `roleNavigationMap` 與 DB navigation_items 命名不一致；前端把 `is_admin → true` 短路導致 admin 等同 superuser
> **關聯**：
> - failure-adr-0025-rls-half-wired.md（同類雙軌不同步事故）
> - failure-generic-admin-regex-overmatch.md
> - .claude/rules/adr-anti-half-wired-sop.md

---

## Context（事故脈絡）

5/06 用戶報「李昭德 admin role 但側邊欄只看到 3 項」。盤點發現 3 條斷裂：

1. **前端 `roleNavigationMap['admin']`** 寫死 42 keys（`documents-menu`/`erp-menu`...）vs **DB site_navigation_items** 用 `documents`/`ERP` 等不同命名 → 只有 24 keys 交集
2. **前端 `USER_ROLES.admin.default_permissions`** 寫死 15 個 vs **後端 `get_default_permissions(admin)`** 寫死 28 個 → 兩端不一致
3. **PermissionManagementPage** 唯讀展示 `USER_ROLES`，沒有實際編輯介面 → 無法動態改 admin role 權限
4. **前端 `usePermissions:hasPermission`**：`is_admin → return true` 短路，admin 等同 superuser

導致 owner 在 `/admin/site-management` 加新 nav item 後，需手動改前端 `USER_ROLES.admin.default_permissions` 並 redeploy code，**不能透過 `/admin/permissions/admin` 動態同步**。

## Decision

**以 DB `role_permissions` 表為 Single Source of Truth**，與 `site_navigation_items` 動態對應。

### Schema

```sql
CREATE TABLE role_permissions (
    role           VARCHAR(20) PRIMARY KEY,
    permissions    JSONB NOT NULL DEFAULT '[]',  -- ['*'] 表 wildcard
    can_login      BOOLEAN DEFAULT TRUE,
    name_zh        VARCHAR(50),
    description_zh TEXT,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW(),
    updated_by     INT REFERENCES users(id)
);
CREATE INDEX ix_role_permissions_permissions_gin ON role_permissions USING gin(permissions);
```

種子：`unverified / user / staff / admin / superuser`（superuser 用 wildcard `*`）。

### API（POST-only 資安規範）

- `POST /api/admin/role-permissions/list` — 列所有 role
- `POST /api/admin/role-permissions/get` — 取單一 role 詳情
- `POST /api/admin/role-permissions/update` — 更新 role permissions（含 audit log）
- `POST /api/admin/role-permissions/available` — 系統可分派 permission 全集 + 未分派紅點

### 業務邏輯

`available_permissions` 來源（union）：
1. `site_navigation_items.permission_required`（`/admin/site-management` 編輯）
2. 業務 endpoint hardcoded set（含 `documents:*` / `admin:*` 等）
3. 任一 role 已分派的 permissions（追溯既有配置）

未分派警報（紅點）：
- `unassigned = (1) ∪ (2) − (3)` — 已被 nav 配置但無任何 role 帶有，進 PermissionManagementPage Alert 提示

### 用戶建立流程

```python
# auth/oauth.py:create_oauth_user
user.permissions = await get_default_permissions_from_db(db, user.role)
# fallback: get_default_permissions(role) hardcoded（DB 不可達時）
```

### 前端 admin ≠ superuser

修 `usePermissions.ts`：
- `is_admin → return true` 短路移除
- 僅 `role === 'superuser'` 短路 hasPermission
- `roleNavigationMap['admin']` 改為 `'all'` 進 permission filter（取代硬編碼 42 keys）

## 動態對應流程

```
/admin/site-management 加新 nav item (permission_required=["xxx:yyy"])
    ↓
POST /api/admin/role-permissions/available
    ↓ unassigned 包含 xxx:yyy
/admin/permissions/admin Alert 紅點顯示「xxx:yyy 待分派」
    ↓ owner 開 Drawer 勾選
POST /api/admin/role-permissions/update {role:"admin", permissions:[..., "xxx:yyy"]}
    ↓
新建 admin user → get_default_permissions_from_db 自動帶 xxx:yyy
舊 admin user → 由 owner 在「使用者管理」頁同步（或全 admin 自動 sync 後續排程任務）
```

## Consequences

### 優點
- 單一真實來源（DB role_permissions）
- 加新 nav item 後，admin 立即收到「待分派」紅點提示
- PermissionManagementPage 可實際編輯（Drawer + checkbox + 分類）
- POST-only 全套 API 符合資安規範
- audit log（updated_by + 時間戳）追蹤誰何時改

### 風險
- DB 不可達時 fallback hardcoded — 兩個版本可能短期不同步（已記入 fallback 行為註解）
- `_BUSINESS_PERMISSIONS` set 仍 hardcoded — 未來改為「啟動時 scan FastAPI routes 找 require_permission」自動產出
- 既有 user.permissions 不會自動隨 role_permissions 更新 — 需在使用者管理頁手動 sync 或建排程任務

### 後續工作
- [ ] 自動掃描 require_permission decorator 產出 _BUSINESS_PERMISSIONS（取代 hardcode）
- [ ] 「全 admin user 同步權限」按鈕（PermissionManagementPage 加 action）
- [ ] Fitness step 20：`role_permissions_consistency_check.py` 月驗證 navigation_items vs role_permissions 一致性
- [ ] LESSON L26：DB-driven 配置取代 hardcoded role 白名單（雙軌不同步典範）

## 命令參考

```bash
# 跑 migration
cd backend && alembic upgrade head

# 驗證 API
curl -s -X POST http://localhost:8001/api/admin/role-permissions/list -d '{}' -H "Content-Type: application/json"

# 查 DB
SELECT role, jsonb_array_length(permissions) AS n FROM role_permissions ORDER BY role;
```

## 測試覆蓋

- 單元：`tests/unit/test_role_permissions_repository.py`（SSOT 查詢 / fallback 行為）
- 整合：`tests/integration/test_role_permissions_admin_api.py`（4 endpoints + audit）
- E2E：`tests/e2e/test_admin_permissions_dynamic.py`（PermissionManagementPage 編輯 → user.permissions 對齊）
- Fitness：`scripts/checks/role_permissions_consistency_check.py`（規劃中）
