# ADR-0024: Calendar 可見性擴充至承攬案件承辦同仁 + Superuser 直通

- **Status**: Accepted
- **Date**: 2026-04-21
- **Deciders**: Aaron (jujuiacc@gmail.com)
- **Related**: ADR-0003 (內網認證繞過), ADR-0013 (統一案號 case_code)
- **Scope**: Calendar 先行，公文 / 派工 v5.9 擴展

---

## Context

### 觸發問題

用戶回報 `https://missive.cksurvey.tw/calendar` 與 `http://192.168.50.210:8001/calendar`
兩者顯示資料不一致。經驗證：
- 兩個 URL 實際上打同一個 FastAPI 後端（:8001）
- 前端依 `detectEnvironment()` 走不同認證路徑
- `/api/calendar/users/calendar-events` 以 `user_id` 為 filter —
  per-user 可見性

### 現行可見性邏輯（events_batch.py）

```python
Event WHERE
  assigned_user_id == user_id
  OR created_by == user_id
  OR (assigned_user_id IS NULL AND created_by IS NULL)  # 公共事件
```

三層可見：被指派 / 自己建 / 完全無歸屬。**缺「同案件承辦同仁」可見。**

### 真實協作場景

- 小花承辦 `CK2024_01_01`，但該案件的交付日事件是老王建的（assigned = 老王）
- 現狀：小花看不到 → **違反「一起承辦」的協作預期**
- 期待：同一承攬案件的 active staff 應共享該案件事件

### 跨 URL 不一致的根因

當同一用戶跨 URL 登入時，若其他用戶建的事件未被 assign 到自己，會缺漏。
當兩 URL 登入的是不同帳號（例：公網 Google SSO vs 內網快速進入），差異更大。

---

## Decision

**擴充 Calendar event 可見性為 4 層 + Superuser 直通：**

### 1. 一般使用者：四層可見

```python
Event WHERE
  assigned_user_id == user_id                        # 被指派
  OR created_by == user_id                           # 自己建
  OR (assigned IS NULL AND created_by IS NULL)       # 公共
  OR EXISTS (                                        # ← 新增：承辦同仁
      SELECT 1 FROM project_user_assignments pua
      JOIN OfficialDocument ON document.contract_project_id = pua.project_id
      WHERE document.id = event.document_id
        AND pua.user_id = request.user_id
        AND pua.status = 'active'
  )
```

### 2. Superuser：直通（不加任何可見性 filter）

```python
if current_user.is_superuser or current_user.role == 'superuser':
    # 不加可見性 filter → 看全部
```

Superuser 判定統一 helper `_is_superuser(user)`：
- `is_superuser` Column（Boolean）為 True
- OR `role` Column 為 `'superuser'`

### 3. 範圍限制（Phase 1）

**僅限 Calendar `/api/calendar/users/calendar-events` 端點。**

公文 List、Dispatch List 現階段**不動**，等 Calendar 跑一週驗證穩定後，
v5.9.0 再評估擴展。

---

## Rationale

### 為什麼這樣做

1. **對齊企業協作本質**：承攬案件是團隊作業，不是個人 todo list
2. **Schema 無需變動**：`project_user_assignments` 關聯表已存在，僅查詢層擴充
3. **最小侵入**：1 處後端 SQL 變動，前端無需改
4. **Superuser 解痛**：主帳號（jujuiacc@gmail.com，role=superuser）跨 URL 看到一致資料

### 為什麼先只改 Calendar

- Calendar 是「協作事件」天然需求（交付日、會議、提醒）
- 公文 / 派工的可見性語意更複雜（涉及審批、權限層、跨機關）
- 先用 Calendar 驗證 `project_user_assignments` 作為可見性來源是否穩健
- 跑一週後擴展：事故低、擴展容易；事故多、止血容易

### 為什麼 Superuser 直通而非 Admin

- `admin` 角色是操作性權限（CRUD / 管理介面）
- `superuser` 是「全公司可見性」角色
- 兩者分離避免權限擴散 — admin 不應等於 全可見

---

## Consequences

### 正面

- 同案件承辦同仁可共享事件資訊
- 跨 URL（公網 / 內網）看到一致資料（以同用戶為前提）
- 不動 Schema，風險可控
- 為公文 / 派工可見性擴展提供 reference implementation

### 負面 / 風險

- **查詢成本**：加一個 EXISTS subquery
  - 緩解：`project_user_assignments` 表預期 <1000 行，有 project_id/user_id index
- **邊界案例**：無 document_id 的 event（例：純手動建的會議）不受益於承辦同仁可見
  - 設計意圖：無 document 即無 case，不是協作範圍
- **Superuser 直通的隱私考量**
  - 緩解：僅 superuser 單一角色（目前 2 人），有審計日誌 `Calendar visibility bypass for superuser ...`

### 測試

- `backend/tests/unit/test_calendar_visibility.py` 6 regression test：
  1. `_is_superuser` via is_superuser flag
  2. `_is_superuser` via role='superuser'
  3. Regular user 判定為 False
  4. Admin 不等於 superuser（避免權限擴散）
  5. 缺 attr graceful handle
  6. Superuser vs regular 分岐行為

---

## Implementation

### 檔案變動

| 檔案 | 變動 |
|---|---|
| `backend/app/api/endpoints/document_calendar/events_batch.py` | 加 `_is_superuser` helper + 重寫 `get_user_calendar_events` visibility 邏輯 |
| `backend/tests/unit/test_calendar_visibility.py` | 新增 6 regression test |
| `docs/adr/0024-calendar-visibility-case-collaborator.md` | 本檔 |

### Migration Path

- **立即上線**：重啟 PM2 ck-backend 即生效
- **向後相容**：API signature 不變，只是可見範圍擴大
- **回滾**：revert events_batch.py 即可，單檔改動

---

## Next Steps (v5.9.0 評估)

- [ ] 公文 List `/api/documents-enhanced/list` 套同邏輯（案件承辦同仁可見）
- [ ] 派工 List `/api/taoyuan/dispatch/list` 評估（可能有機關層權限）
- [ ] 考慮 `case_collaborator` 細粒度 role（per-case ACL）
- [ ] 稽核日誌：記錄 superuser bypass 的存取頻率
