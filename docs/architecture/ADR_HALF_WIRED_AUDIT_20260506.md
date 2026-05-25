# ADR 半接通風險 Audit 報告

> **執行日期**：2026-05-06
> **觸發事件**：ADR-0025 Identity Unification 13 天 dormant bug 暴露
> **覆盤範圍**：17 個 active ADR（0011 ~ 0033）
> **分析方法**：對每個 ADR 比對「程式接通完整度」+「自動驗證機制」+「觸發邊角」
> **FQID**：`CK_Missive#ADR_HALF_WIRED_AUDIT_20260506`

## 0. 一頁式結論

| 級別 | 數量 | ADR |
|---|--:|---|
| **L1** 文件型不需驗證 | 1 | 0011 |
| **L2** 完整接通（程式碼 + 驗證） | 5 | 0013, 0023, 0028, 0029, 0031 |
| **L3** 半接通風險（程式接通但無自動驗證） | 9 | 0012, 0014, 0015, 0016, 0020, 0025⚠, 0027, 0030, 0032 |
| **L4** 高風險（複雜邊角 + 無/不足驗證） | 2 | 0022, 0033 |

⚠ = 已部分修復（TaskB + Fitness step 17）但仍有殘留範圍。

## 1. 排序建議（按 ROI 補驗證）

| # | ADR | 主題 | 風險核心 | 工時 | 期限 |
|---|---|---|---|---|---|
| 🔴 1 | **0033** | 關閉密碼登入 | 無 SSO 覆蓋率驗證 + 無 IdP outage 監控 + 無回滾 runbook | M (4 hr) | 部署前 |
| 🔴 2 | **0022** | Memory Wiki 自進化 | diary stale ≥2 天無告警 | S (2 hr) | v6.9 |
| 🟠 3 | **0025** | Identity Unification | TaskB 修了 documents/projects；**派工 / ERP / Calendar 範圍待覆驗** | M (4 hr) | 本月內 |
| 🟠 4 | **0032** | Tender 多源識別碼 | URL 轉址 E2E + 9,567 壞資料清理驗證 | M (4 hr) | v5.10 |
| 🟠 5 | **0014** | Hermes 取代 OpenClaw | 5/20 ADR-0030 決策後 LINE canary 驗證 | M (4 hr) | 5/20 後 |
| 🟡 6 | **0027** | Telegram 推播關閉 | LINE 通道單點失效 fallback 缺 | S (2 hr) | v6.9 |
| 🟡 7 | **0012** | 標案檢索模組 | tender 訂閱 → agent auto-case E2E | M (4 hr) | v5.11 |
| 🟡 8 | **0015** | Cloudflare Tunnel | CF Tunnel 宕機演練 | S (1 hr) | v6.10 |
| 🟡 9 | **0016** | 多專案分域 | 跨專案 Hermes skill 隔離 + KG federation | L (1 day) | Phase 2+ |
| 🟡 10 | **0020** | Hermes 終局決策 | 5/20 會議 + sunset tracker | — | 治理 |
| 🟡 11 | **0030** | Hermes GO/NO-GO | dogfooding tracker 持續 | — | 5/20 會議 |

## 2. 兩個 L4 高風險深入分析

### ADR-0033 關閉密碼登入

**為何 L4**：
- 安全決策對；但**外部依賴**（Google + LINE）變單點故障
- **沒驗證**：歷史使用者 SSO 綁定覆蓋率（若 google_id IS NULL 的 user > 0 → 永久鎖在門外）
- **沒監控**：IdP outage 無 fallback 機制
- **沒 runbook**：緊急回滾需手動 git revert + 重新部署

**追加驗證**：
1. 上線前 SQL 檢查：`SELECT COUNT(*) FROM users WHERE google_id IS NULL AND line_id IS NULL AND is_active=TRUE` → 必須 = 0 或所有人都被通知綁定
2. 加 `idp_connectivity_check.py` fitness：每月 GET Google + LINE OAuth discovery doc → 監控 IdP 健康
3. 寫 `docs/runbooks/sso_emergency_rollback.md`：步驟化緊急開啟密碼登入流程（含 ADR-0033 暫時 superseded 標記）

### ADR-0022 Memory Wiki 自進化

**為何 L4**：
- v5.7.1 上線**隔日**就發現 4 層連鎖 silent failure（已修 26 regression test）
- 但**寫入鏈路 dormant** 風險仍在 — diary 連續多天 0 寫入難察覺
- 目前有 `memory_wiki_metrics.py` 7 gauge，但**沒有 alert rule** → silent stale

**追加驗證**：
1. 加 Prometheus alert：`memory_diary_days_total` 在 7 天滑動窗 < 3 天 → warning（與 LINE notify watchdog 同邏輯延伸）
2. 加 fitness step 18：`memory_diary_freshness_check.py` 月跑驗證 diary/patterns/critique 每週寫入 ≥ 1
3. 加 self_diagnosis 端點 `/ai/memory/self-check` 回傳整合健康度（給 owner 體感層用）

## 3-Bis. 新增案例：ADR-0034 Sidebar 4-Layer Stacking（2026-05-07）

新發現另一個典型 dormant 案例 — **不是單純 ADR-0034 半接通，而是 4 個獨立 bug 疊加成
single-symptom（用戶看到不該看的選單）**。

| 層 | bug | 修法 | 對應 lesson |
|---|---|---|---|
| P-57 | Backend `permission_required` JSON 字串未 parse | `_parse_permission_required` helper 兩端對齊 + 19 tests | L28 |
| P-58 | Frontend `VITE_AUTH_DISABLED=true` 強制覆蓋真實 user | `shouldUseDevMockUser()` opt-in fallback + 4 tests | L27 |
| P-59 | NavTreePermissionEditor cascade 取消連坐 | `checkStrictly={true}` + per-node toggle + 6 tests | — |
| P-60 | DB user.permissions 與 role 定義脫鉤（user 7: 19 vs 5） | 手動 `UPDATE users SET permissions = role_permissions[role]` | — |

**完整事故記錄**：[`wiki/memory/failures/failure-sidebar-perm-4layer-stack.md`](../../wiki/memory/failures/failure-sidebar-perm-4layer-stack.md)

**升級防範**：本檔 §4 SOP 應加入「**多層 bug 疊加偵測**」項目 — 用戶仍復現問題時不要回滾，
假設下一層仍有 bug 繼續挖（L26 穿透式驗證）。

## 3. ADR-0025 殘留範圍盤點

TaskB 修復覆蓋：
- ✅ `documents/{id}/detail` — 已修
- ✅ `documents/list` — 已修（service 層 RLSFilter.apply_document_rls）
- ✅ `documents/{id}/delete` — 已修
- ✅ `projects/{id}` GET / `projects/{id}/update` — 已修
- ✅ `files/can_user_access_document` helper — 已修
- ✅ `events_batch.py` — 早就用 `expand_user_alias`

**待確認**：
- ⚠ **派工 (taoyuan_dispatch)** — endpoint 內未檢查 RLS（目前似乎全公司可見）— 業務確認後再決定
- ⚠ **ERP (erp/*)** — 同派工
- ⚠ **Calendar (document_calendar)** — events.py 內有 `if current_user.is_admin` 判斷，需確認 RLS 過濾邏輯
- ⚠ **行事曆事件** — created_by 對 alias 的歸屬

**建議**：
- 業務面確認「派工 / ERP / Calendar 是否 staff/user 應只看自己關聯專案」
- 若是 → 補 RLS（同 documents 模式）+ 加入 `alias_rls_e2e_check.py` 覆蓋
- 若否（admin 全可見）→ 寫入 ADR 顯式宣告

## 4. 「半接通」防範 SOP（給 owner / 維護者）

每個新 ADR 上線清單：

```
□ 主要程式碼已實作（service / API / UI）
□ DB schema / migration 已執行
□ 至少 1 個 unit test 鎖定核心邏輯
□ 至少 1 個 integration test 涵蓋邊角
□ 列出本 ADR 的「最不容易繞過」用戶身份組合（如 staff + 非 admin + 多帳號）
□ 該組合有對應 fitness function 或 E2E test
□ Owner 切到該身份**實測 1 次** + 寫 wiki diary
□ 上線後 7 天 owner check-in：該身份用戶有沒有 friction
```

**首要原則**：「真活」不是 commit message 寫的，是該身份用戶**實際操作不出 friction** 才算。

## 5. 對應已建立的防線

| 防線 | 落地時間 | 覆蓋範圍 |
|---|---|---|
| Fitness step 17 — `alias_rls_e2e_check.py` | 2026-05-06 | ADR-0025 RLS 雙向展開 |
| Fitness step 16 — `line_notify_heartbeat_check.py` | v6.8 | ADR-0027 體感推送 |
| Fitness step 15 — `integration_liveness_check.py` | v6.8 | 8 接觸面活體 |
| 3 靜態守護 | ADR-0028 | async/SSE/schema lazy load |
| `adr_lifecycle_check.py` | ADR-0029 | active ADR 數量治理 |
| **缺：staff/user 身份體感 SOP** | TODO | 所有 ADR 半接通防範 |

## 6. 後續工作建議（優先序）

### P0（部署前必做）
- TaskB + Fitness step 17 ✅ 已完成
- ADR-0033 SSO 覆蓋率 + IdP runbook（防外部 IdP outage）

### P1（v6.9 補完）
- ADR-0022 Memory Wiki diary freshness alert
- ADR-0025 派工 / ERP / Calendar RLS 範圍確認

### P2（v6.10+）
- ADR-0032 / 0014 / 0015 整合 E2E
- 「半接通防範 SOP」加入 `.claude/rules/`

### P3（戰略）
- 5/20 ADR-0020 Hermes 決策會議
- ADR-0016 Phase 2+ lvrland/PileMgmt 上線時補跨專案隔離測試

---

## 元洞察：為何 ADR 半接通是常態

從 17 個 ADR 觀察，**L3+L4 共 11 個（65%）有半接通風險**。這不是品質差，而是反映：

1. **ADR 強調 decision rationale > implementation detail** — 自然偏重「為什麼做」而非「做完所有層」
2. **Code review 看 PR 不看 ADR** — 整合鏈斷裂在 PR 之間沒人負責
3. **Test 文化偏 unit/regression > integration/E2E** — 邊角組合需要更多 fixture 重型 test
4. **Dev 環境≠ production** — owner 是 admin/superuser，永遠繞過 staff/user RLS

**結論**：ADR 半接通是**結構性問題**，不是個案疏漏。需要**體感層 SOP** + **自動化 fitness function 涵蓋邊角組合**雙管齊下。

> 這份 audit 本身應每季更新 — 新 ADR 上線時加入評估，已修 ADR 升級級別。
