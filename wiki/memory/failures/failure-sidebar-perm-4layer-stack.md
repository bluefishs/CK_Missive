---
type: failure
id: sidebar-perm-4layer-stack
detected: 2026-05-07
incident_started: unknown
days_dormant: unknown
severity: high
status: resolved
resolved_at: 2026-05-07
fqid: CK_Missive#failure-sidebar-perm-4layer-stack
related_adr: [0025, 0034]
related_lesson_candidate: [L23, L24, L25]
---

# Failure：Sidebar 權限過濾 4 層連環 dormant bug（P-57 → P-60）

## 一句話摘要

「一般使用者看到不該看的選單」單一現象，背後是 **4 層獨立 bug 疊加**：backend schema /
frontend dev mode / NavTree UX / DB 資料漂移。**任一層沒修都會看到「以為修了仍復現」假象**，
這是教科書級「half-wired anti-pattern stacking」。

## 觸發

User 報告：以 aaronfly1978@gmail.com（role='user' 一般使用者）登入後，側邊欄顯示完整
管理選單。連續 3 次「修了 → 仍可看 → 再修」。

## 4 層連環 root cause

### 層 1（P-57）— Backend schema：JSON-as-TEXT 未 parse

| 元件 | 行為 |
|---|---|
| DB `site_navigation_items.permission_required` | TEXT 欄位，JSON 編碼字串如 `'[]'`、`'["documents:read"]'` |
| Backend `_item_to_dict` / `nav_repo.get_children_recursive` | 直接回傳字串給前端 |
| Frontend `filterNavigationItems` | 期望 `string[]`，用 `length === 0` 判空 |

**症狀**：`'[]'.length === 2` 不等於 0 → 落入 `hasPermission('[]')`（把 JSON 字串當 single
perm key 比對）→ 永遠 false → 全部 nav 被過濾掉 → 落入 fallback。

**Fallback 邏輯本身有 bug**（useNavigationData.tsx 152-156）：
```ts
return !permRequired || !Array.isArray(permRequired) || permRequired.length === 0;
```
JSON 字串 `'[]'` 通過 `!Array.isArray('[]')=true` → **顯示所有項目**！

**修法**：endpoint + repo 兩端對齊新增 `_parse_permission_required` helper，加 19 unit test
鎖定 None / "" / "[]" / JSON list / 已是 list / 損壞 JSON / 異常型別。

### 層 2（P-58）— Frontend dev mode：強制覆蓋真實用戶

| 元件 | 行為 |
|---|---|
| `.env` | `VITE_AUTH_DISABLED=true`（dev 內網方便進入） |
| `usePermissions.fetchUserPermissions()` 第 41-58 行 | 看到 `isAuthDisabled()=true` → **覆寫 user_info** 為 `{role: 'superuser', is_admin: true, permissions: [all]}` |

**症狀**：即使真實用戶（aaronfly1978 role='user'）已登入並寫入 localStorage，
`isAuthDisabled()` 短路會把 user_info 換成 dev mock superuser → `hasPermission` 永遠 true →
所有 nav 顯示。

**修法**：新 helper `shouldUseDevMockUser()` — 只在「dev flag 為 true **且** localStorage 沒
真實 user_info」時才回 true。修 7 處 short-circuit。

### 層 3（P-59）— NavTree UX：cascade 連坐 unsync

NavTreePermissionEditor v1.2 用 antd Tree 預設 cascade 模式。問題：
- 取消父節點 → 連坐子節點 perm 從 draft 移除
- 共享 perm（多 nav 用同一 perm）取消其一 → 該 perm 從 draft 移除 → 其他 nav 視覺也 unchecked

**用戶體驗**：「我只想關一個選單，怎麼好幾個都關了」

**修法**：v1.3 改 `checkStrictly={true}` + per-node toggle handleCheck — 每節點獨立切換。
共享 perm 視覺連動仍存在（perm 才是 SSOT，無法迴避），但父子 cascade 不再連坐。

### 層 4（P-60）— DB 資料漂移：user.permissions vs role 定義脫鉤

```sql
-- role 'user' 定義
SELECT permissions FROM role_permissions WHERE role='user';
-- ["documents:read", "projects:read", "agencies:read", "vendors:read", "calendar:read"]  (5 個)

-- 實際 user 7 (aaronfly1978) 的 user.permissions
SELECT permissions FROM users WHERE id=7;
-- ["documents:read", "documents:create", "documents:edit", "documents:delete",
--  "projects:read", "projects:create", "projects:edit", "projects:delete",
--  "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
--  "reports:view", "reports:export", "calendar:read", "calendar:edit",
--  "vendors:read", ...]  (19+ 個)
```

**為何漂移**：dev 早期 user.permissions 直接寫入完整 perm 集，後來 role 升級為 SSOT
（ADR-0034）但歷史 user 沒同步。staff role 的 6 個用戶 user.permissions=NULL（更糟）。

**修法**：`UPDATE users SET permissions = (SELECT permissions::text FROM role_permissions WHERE role=?)`
手動同步 3 user + 6 staff。長期應用 ADR-0034 sync-users endpoint 自動化。

## 為何 4 層都 dormant 這麼久

### 觸發條件嚴苛
1. **必須以非 admin/superuser role 登入**（dev 機台幾乎全是 admin/superuser）
2. **必須在 dev 內網**（`VITE_AUTH_DISABLED=true` 才觸發 P-58）
3. **必須真實看 sidebar**（admin 通常直接 URL 跳轉不看 sidebar）
4. **必須注意到顯示不對**（admin 視角看一樣，覺得正常）

### Owner 永遠是 admin → 邊角條件視角缺失
與 ADR-0025 13-day dormant 同樣模式：
- 主要 dev/owner 登入用 superuser/admin → P-58 dev mock 把 staff/user 角色變透明
- 沒有「以一般使用者實測 1 次」 的習慣 → 4 層都沒被測到

### 4 層彼此遮蔽
- 修 P-57 schema parse → 仍看到全選單（P-58 dev mock 把所有用戶當 superuser）
- 修 P-58 dev mock → 仍看到全選單（P-60 user 7 本來就有 19 perms）
- 修 P-59 UX → 不影響顯示問題（UX 是另一面向）
- 修 P-60 DB → 才真正讓 user role 對應 5 perms 生效

**Debug 邏輯關鍵**：每修完一層必須**穿透下一層繼續驗證**，不能憑「測一次仍有問題就回滾」誤判。

## 防範

### 1. 立即配套（已執行）
- Frontend `useNavigationData` fallback 改為「只放行真正空陣列」（P-57 雙保險）
- Backend nav endpoint + repo 兩端 helper 對齊（同樣輸入產出相同結果，加 alignment test 鎖定）
- `shouldUseDevMockUser` 4 tests 鎖定 dev mock 對齊「opt-in fallback」原則

### 2. 中期配套（建議）
- **新增 fitness step 21**：「真實 staff/user 角色登入後 sidebar 過濾正確」
  - 建一個 fixture user role='user' permissions=`['documents:read']`
  - 模擬登入後查 nav menuItems，斷言只看到 `documents:*` 那批
  - 月跑 + 任何認證/權限/sidebar 改動觸發
- **新增 ADR-0034 sync-users 排程**：role_permissions 變更後自動 invalidate 相關 user
  user.permissions（避免再度漂移 6 個月）
- **建立「身份矩陣 dogfooding 表」**：每週 owner 切換 5 種 role 各登入 1 次，
  截圖記錄 sidebar 內容；自動化前先用人工跑 4 週

### 3. 長期配套（願景）
- 移除 `VITE_AUTH_DISABLED` dev 短路機制本身，改成：dev 內網直接給 6 個固定 quick-login
  按鈕（superuser / admin / staff / user / unverified / 訪客），每按一次寫入該角色的 fake
  user_info 走真實 permission flow。徹底消除 dev mode override trap。

## 連結

- ADR-0034 動態 Role Permissions
- ADR-0025 Identity Unification（同模式 13 天 dormant）
- `.claude/rules/adr-anti-half-wired-sop.md`
- LESSON L23 / L24 / L25 候選（待 registry 評估）
