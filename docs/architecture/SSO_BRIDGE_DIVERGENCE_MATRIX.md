# SSO Bridge 跨 repo 分歧矩陣（刻意差異 vs 意外 drift）

> **建立**：2026-07-25（Tier2 auth 收斂複查產出）
> **觸發**：模組化收斂欲把 4 repo `sso_bridge.py` 強抽成單一 async/sync 共用 flow；複查揭露**連 sync 雙胞胎 pile/lvrland 都有 141 行差 + auto-provision 安全政策分歧**。
> **決策**：**不強抽 orchestration**（過度抽象 auth = blast radius 最大）。安全核心已共享（`ck_auth.sso`）；orchestration 的差異多為**刻意 per-repo policy**，本文件登記之，供未來稽核區分「刻意分歧」與「意外 drift」。
> **元教訓對應**：v6.26（07-20）「驗證優先於收斂 — HH-2 結構相異非重複，強抽＝過度抽象」的 auth 版教科書案例。

---

## 1. 已共享的安全核心（單一源，勿重新實作）

| 元件 | 單一源 | 說明 |
|---|---|---|
| JWT/JWKS 驗證 | `ck_auth.sso.verify_ck_sso_jwt_auto`（RS256 優先 / HS256 fallback） | 4 repo 原 copy → Tier1 wheel。改驗證邏輯＝改 `shared-modules/ck-auth-py/src/ck_auth/sso.py` 一處 + bump + 換 wheel |
| 系統權限檢查 | `ck_auth.sso.has_system_permission(employee, system_name)` | JWT `systems` claim 比對 |
| Employee 模型 | `ck_auth.sso.CKSSOEmployee` | — |

> **鐵律**：任何 `sso_bridge.py` 變體**禁止**重新實作 JWT 驗證或權限檢查，必須 `from <repo>.core.ck_sso import ...`（該檔已是 `ck_auth.sso` re-export shim）。conformance audit（`scripts/checks/sso_bridge_conformance_audit.py`）強制之。

---

## 2. 共享的安全契約（所有變體必須一致 — 守衛順序 + 狀態碼）

所有 sso_bridge 變體**必須**維持相同的守衛順序與 HTTP 狀態碼語意：

| 序 | 守衛 | 失敗狀態碼 | 語意 |
|---|---|---|---|
| 1 | `CK_SSO_ENABLED` flag | **503** | 功能未啟用 |
| 2 | `CK_SSO_JWT_SECRET` 存在 | **503** | 設定不完整 |
| 3 | cookie（ck_employee / ck_employee_rs）存在 | **401** | 缺少 SSO cookie |
| 4 | JWT 驗證（`verify_ck_sso_jwt_auto`） | **401** | 憑證無效/過期 |
| 5 | 系統權限（`has_system_permission`） | **403** | 無此系統權限 |
| 6 | User 存在 | **404 或 403**（見 §3 policy） | 帳號不存在 |
| 7 | `user.is_active` | **403** | 停用/待啟用 |

> 這是**意外 drift 的防線**：若某 repo 把守衛順序打亂或狀態碼改掉（如把 401 弄成 200），conformance audit 應標紅。

---

## 3. 刻意 per-repo policy 分歧（**不是 drift，勿強行對齊**）

以下差異為各平台**刻意**決定，強抽成單一 flow 需把它們參數化——參數化 auth 安全政策 = 高風險過度抽象，故保留各檔獨立。

| 面向 | Missive（async 主產品） | lvrland（sync） | pile（sync） | 分歧性質 |
|---|---|---|---|---|
| User-not-found 行為 | **404**（須先 Google 登入過，不 auto-provision） | **404**（同 Missive） | **auto-provision pending 帳號**（2026-06-02 incident 修：SSO 員工幾乎全 404 無法登入） | 安全政策 |
| 稽核服務 | `AuditService` | `LoginHistoryService`（`log_event`） | `AuditService`（try/except non-blocking） | 基礎設施差異 |
| email domain 檢查 | （於 User 存在前不檢查） | 無 | 有（`_check_email_domain_allowed`，fail-open） | 政策 |
| Session TTL | `SSO_ACCESS_TOKEN_EXPIRE_MINUTES`（8h，L74/L78 止血） | 預設 | 預設 | 產品差異（主產品編輯途中過期止血） |
| set_auth_cookies 簽名 | `AuthService.set_auth_cookies(response, tr, request=request)` | module fn | module fn `set_auth_cookies(response, tr, user.id)`（2026-06-02 P1-A 修：原 hasattr 永 False → cookie 從未設） | 實作差異 |
| refresh-SSO-fallback | `try_mint_session_from_sso_cookie`（async） | 同（sync） | 同（sync） | 已對齊（L80） |
| Session 模型 | `AsyncSession` + `await` | `Session`（sync） | `Session`（sync） | 執行模型（async/sync 分裂根源） |

---

## 4. 為何不強抽 orchestration

1. **安全核心已共享**（§1）——收斂最高價值部分已完成。
2. **剩餘差異多為刻意安全政策**（§3 auto-provision matrix）——強抽需把「是否 auto-provision」「哪個稽核服務」參數化，任一失誤 = 4 系統 auth 回歸（如誤讓員工繞過 admin 啟用）。
3. **async/sync 分裂**——單一函式無法同時 async/sync，需雙殼；雙殼 + policy 參數化 = 比「兩個清楚的獨立檔」更複雜難稽核。
4. **L58 治理範本污染教訓**：共享契約（§1/§2），勿共享整檔實作（§3 的 glue）。

**結論**：sso_bridge 維持各 repo 獨立，用 **conformance audit** 守 §1/§2 安全契約（防意外 drift），用**本矩陣**登記 §3 刻意分歧（防誤判）。這比強抽更安全、更可稽核。

---

## 5. 相關

- 收斂策略：`MODULARIZATION_CROSS_PROJECT_STRATEGY.md`（缺口 C/D、L58）
- 候選路線圖：`MODULARIZATION_NEXT_CANDIDATES_20260722.md`
- conformance audit：`scripts/checks/sso_bridge_conformance_audit.py`（fitness 追加步）
- 已收斂的真乾淨重複對照：csrf_service（pile↔lvrland 189 行僅差 1 行 redis import）＝ HH-1，該收斂
