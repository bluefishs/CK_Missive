# ADR-0025: User Identity Unification — canonical_user_id + 權限隔離

- **Status**: Accepted
- **Date**: 2026-04-21
- **Deciders**: Aaron (jujuiacc@gmail.com, superuser)
- **Supersedes / Relates**: ADR-0024（Calendar Visibility，擴充其 alias expand 能力）
- **Scope**: 本 ADR 僅建 Identity 層；Calendar 已套用；公文 / 派工 v5.9 擴

---

## Context

### 痛點

users 表因多登入方式（Google / Email / LINE / Import staff）造成**同一真實人員多筆 User**，導致：

1. `/contract-cases/:id` 承辦同仁下拉列出 **2 個王駿穠**、2 個張雅惠、2 個李昭德
2. 切換登入方式（公網 Google SSO vs 內網 email）成了不同 User → 看不到自己案件
3. `project_user_assignments.user_id` 只能指派單一 User record，其他分身無效

### 現況樣本（合併前）

| 真實人員 | id | 來源 | role |
|---|---|---|---|
| 王駿穠 | 7 | aaronfly@gmail Google | user |
| 王駿穠(fly) | 13 | jujuiacc@gmail Google | **superuser** |
| 張雅惠 | 12 | cks@cksurvey email | admin |
| 張雅惠 | 17 | cyh@gmail Google | admin |
| 李昭德 | 11 | luke@hotmail email（匯入佔位） | staff |
| 李昭德 | 19 | luke@gmail Google | admin |

### 觸發事件

User 在 `/calendar` 頁面於公網與內網看到不一致資料，追根究底發現：
- ADR-0024（Calendar Visibility）已把承辦同仁納入可見範圍
- 但 per-user ID 比對仍無法跨 identity → Identity Unification 必要

---

## Decision

### 方案 D: `canonical_user_id` 自引用（選中）

**Schema 變動最小、Query 邏輯最輕、可逆、漸進遷移。**

```sql
ALTER TABLE users
  ADD COLUMN canonical_user_id INT NULL REFERENCES users(id) ON DELETE SET NULL;
```

- NULL 代表本身即 canonical
- 非 NULL 代表此 user 為別人分身

### 規則 B: 權限隔離（選中）

**合併分身時不動 alias 自身 role**，僅 Identity 層共享：

| 面向 | 共享？ |
|---|---|
| Identity（是哪一個人）| ✅ 共享 |
| 可見性 (visibility) | ✅ 共享 |
| Role / Permission | ❌ **各自保留** |
| Session / last_login | ❌ 各自獨立 |

理由：
- 尊重「主事者刻意用不同 account 做不同事」情境（例：jujuiacc = superuser, aaronfly = 普通業務）
- 若需統一權限，合併 API 提供 `harmonize_role=true` 二次確認

### 拒絕的方案

| 方案 | 拒絕理由 |
|---|---|
| **A. `user_aliases` 新表** | 多一個 JOIN 複雜度，僅 2-3 對分身沒必要重表 |
| **B. 新建 `persons` 主表** | 重構成本高，所有 FK 要重指向，v5.8 做不到 |
| **C. 直接 DELETE alias 合併** | 破壞性、不可逆、歷史 FK 指向 alias 的記錄全毀 |
| **規則 A（激進統一）** | aaronfly 會被升為 superuser，破壞隔離意圖 |
| **規則 C（取較高）** | 同上 |

---

## Implementation

### 元件清單

| 元件 | 檔案 |
|---|---|
| Migration | `alembic/versions/20260421a001_add_canonical_user_id_and_merge_log.py` |
| Model | `app/extended/models/core.py` User.canonical_user_id + self-ref relationships |
| Helper | `app/services/user_alias_service.py`（expand/list_canonical/detect/merge） |
| Calendar 使用 | `app/api/endpoints/document_calendar/events_batch.py` EXISTS 改用 alias set |
| Repo 過濾 | `app/repositories/user_repository.py` canonical_only=True 旗標 |
| Schema 加旗標 | `app/schemas/auth.py` UserSearchParams.canonical_only |
| Admin API | `app/api/endpoints/user_alias_admin.py` 3 端點 |
| Audit 表 | `user_merge_log`（via migration） |
| Regression | `backend/tests/unit/test_user_identity_unification.py` 8 tests |

### Admin API

- `POST /admin/users/alias-candidates` — 偵測潛在分身（full_name 重複）
- `POST /admin/users/merge-alias` — 合併（需 admin）
- `POST /admin/users/merge-history` — 稽核歷史

### 可見性展開（expand_user_alias）

```python
async def expand_user_alias(db, user_id) -> Set[int]:
    """
    - canonical_id = user.canonical_user_id or user.id
    - 回 SELECT id WHERE id = canonical_id OR canonical_user_id = canonical_id
    """
```

Calendar EXISTS 從 `pua.user_id == :user_id` 改為 `pua.user_id.in_(alias_id_list)`。

### 合併流程

1. Admin 打開 `/admin/user-management` alias 警示卡片
2. 選 canonical（建議「能實際登入」者；UI 顯示各 role 供對照）
3. 確認 merge，`harmonize_role=false`（規則 B）
4. Backend：
   - `UPDATE users SET canonical_user_id = :canonical_id WHERE id = :alias_id`
   - `INSERT INTO user_merge_log ...`
   - 不動 alias.role（除非 harmonize_role=true）

---

## Consequences

### 正面

- 跨 URL 身份一致（合併後 aaronfly/jujuiacc 看到同一組案件）
- 承辦同仁下拉只顯示 canonical，不重複
- 可逆：`UPDATE users SET canonical_user_id = NULL` 即可還原
- 為公文 / 派工 visibility 擴展提供 reference

### 負面 / 風險

- **每次 visibility 查詢多 1 次 DB 取 alias set**
  - 緩解：alias_ids 通常 1-3 個，有 canonical_user_id index，成本微小
- **權限隔離可能讓用戶疑惑**：「我是同一人為何 aaronfly 不能看後台？」
  - 緩解：UI 警示 + 文件說明「權限由 role 管，不是 identity」
- **alias_candidates 偵測以 full_name exact match**，「王駿穠」vs「王駿穠(fly)」不會自動配對
  - 設計：保守偵測避免誤配，此類情況由 admin 手動以 merge API 合併

### 遷移路徑

| 步驟 | 狀態 |
|---|---|
| 1. Migration 上線 | ✅ 已執行 |
| 2. 合併 3 對已知分身（王駿穠/張雅惠/李昭德） | ✅ 已執行 |
| 3. Admin UI 分身警示卡片 | ⏳ Phase 2（本週內） |
| 4. 公文 list 可見性套 alias | ⏳ v5.9 評估 |
| 5. 派工 list 可見性套 alias | ⏳ v5.9 評估 |

---

## Initial Cleanup（2026-04-21）

| canonical | alias | 真實人員 | 合併方向 |
|---|---|---|---|
| 13 jujuiacc (superuser) | 7 aaronfly (user) | 王駿穠 | ✅ 合併（權限隔離）|
| 17 cyh@gmail (admin) | 12 cks@cksurvey (admin) | 張雅惠 | ✅ 合併 |
| 19 luke@gmail (admin) | 11 staff_李昭德 (staff) | 李昭德 | ✅ 合併（權限隔離） |

`user_merge_log` 3 筆稽核記錄，`role_harmonized=false` 全部保留原 role。

---

## Next Steps（非本 ADR 範圍）

- [ ] UserManagementPage 前端：「分身偵測」卡片 + 合併按鈕
- [ ] UI：合併前警示框（顯示 role 差異 + 決定是否 harmonize）
- [ ] 公文 list / 派工 list 套 alias expand（v5.9）
- [ ] LINE Login 綁定 流程考慮自動 detect 潛在分身
