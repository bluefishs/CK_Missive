# RETRO v6.11 — Audit Consolidation Week（2026-05-19 ~ 2026-05-27）

> **版本**：v1.0 / 2026-05-27
> **覆蓋期間**：v6.10 → v6.11 過渡（9 天連續推進）
> **觸發**：跨 session /loop 連續優化 + 三 repo 治理協同
> **結論**：8 大根因 audit 自動化 7/7 完成 + 跨檔 SSOT family 7 案集齊 + 治理範本擴散

---

## 0. 一句話總結

> **從「事故事後反應」（L41 6 天 dormant / L43 10h dormant）演進到「audit 跑出即知」（< 1 秒偵測）。**
> 7 個自動化 audit + 1 個 owner-only SOP 完整覆蓋 next_session_resume 8 大不穩定根因。

---

## 1. 9 天時程線

| Day | 主軸 | 關鍵交付 |
|---|---|---|
| 5/19 | 策略級體檢 v1.2 | 4 平行代理 + 7 缺陷自我檢視 + v6.11 路線圖 |
| 5/20 | v6.10.2 慢性 bug 大掃除 | L39 queryKey drift 12→0 + Calendar 90% NULL owner |
| 5/21 上 | L41 SSO 治理立基 | ck-sso-py v2.0 + ADR-0043 三件套 + network_audit |
| 5/21 下 | L43 災難級恢復 | volume drift 4h Plan A + step 38 + /health business_data |
| 5/22 | L44/L45 同型修法 | ck-sso-js v2.0 移除 session lock + frontend healthcheck align |
| **5/25** | **15-commit 治理整合** | **546 dirty → 0 + step 39→42 + PM2 SOP + B-plan hooks** |
| **5/25-26** | **L41-L45 family closure** | **cross-file-ssot-governance 立法 + 跨 repo location.replace 修法** |
| **5/26** | **step 43-44 audit** | **db_schema_drift + container_lifecycle**（揭發 ck-tunnel:latest）|
| **5/27** | **step 45-46 audit + 範本擴散** | **subdomain_registry + sso_autoload_completeness + 跨 repo PileMgmt typo 修法 + toolkit/AaaP 範本擴散** |

---

## 2. 8 大根因 audit 完成度（per next_session_resume_20260521）

| # | 議題 | Audit Script | Step | 狀態 |
|---|---|---|---|---|
| 1 | DB Schema / ORM drift | db_schema_drift_audit.py | 43 | ✅ |
| 2 | JWT secret 跨 repo drift | cross_repo_secret_audit.py | 41 | ✅ |
| 3 | dashboard subdomain typo | subdomain_registry_audit.py | 45 | ✅ |
| 4 | cloudflared latest tag | container_lifecycle_audit.py | 44 | ✅ |
| **5** | **PM2 + docker 混合架構** | **pm2-deprecation-sop.md（owner-only）** | — | **⏳ SOP done, owner action 待** |
| 6 | docker network label drift | network_audit.py | 37 | ✅ |
| 7 | frontend SSO autoload | sso_autoload_completeness_audit.py | 46 | ✅ |
| 8 | sessionStorage chronic | cross_repo_auth_state_audit.py | 42 | ✅ |

**自動化 7/7 完成。**剩 #5 是純執行性工作（無 audit 可代替）。

---

## 3. 跨檔 SSOT family（L41-L48 8 案）

> 共通模式：「同一資源在多個檔分別宣告，沒 audit enforce 一致」→ silent dormant

| Lesson | 失效層 | Audit | 觸發 dormant |
|---|---|---|---|
| L41 jwt secret drift | step 41 | 6 days |
| L43 volume mount drift | step 38 | 10 hours |
| L44 sso state lock | step 42 | < 1 day |
| L45 healthcheck override | step 40 | 18 minutes |
| L46（隱式）image tag SSOT | step 44 | (preventive) |
| L47（隱式）subdomain typo | step 45 | (preventive) |
| L48（隱式）frontend autoload completeness | step 46 | (preventive) |

**規範**：`.claude/rules/cross-file-ssot-governance.md`（5 規則）
- 規則 1：每個跨檔資源指定 SSOT 位置
- 規則 2：每個資源類型有 fitness audit script
- 規則 3：Runtime healthcheck 驗證業務量
- 規則 4：Dual-write atomic 或 dual-validation
- 規則 5：跨 repo 必走 ADR + Registry + Audit 三件套

---

## 4. 真實揭發（owner 應 review）

### 4.1 已修
- ✅ `CK_PileMgmt` 4 處 `pile.cksurvey.tw` typo（misconfigured）→ `7db531cbd`
- ✅ `CK_lvrland_Webmap` config + env.example → `bb94ad407` + `fa31b11ca`
- ✅ `CK_lvrland_Webmap` + `CK_PileMgmt` 5 處 `location.href` → `location.replace`
- ✅ frontend healthcheck align（L45 5/22 修法）
- ✅ shadow_logger / circuit_breaker / memory subsystem 完整 commit

### 4.2 P0 owner action 待
- ⏳ `ck-tunnel-cloudflared:latest` → `:2026.5.0`（5 min，命令已備）
- ⏳ Owner SSO E2E 3 subdomain（5 min，walkthrough 已備）
- ⏳ PM2 廢除 4 階段（3-4h，SOP 已備）

### 4.3 informational（治理債，無 runtime risk）
- DB schema 117 added indexes / 14 type widening / 177 dead tables（step 43 YELLOW）
- nginx + postgres 跨 repo 版本 drift（step 44 YELLOW，dev-only）
- 9 處跨 repo `pile.cksurvey.tw` 引用（CK_AaaP scripts × 2 / CK_Hermes plan docs × 3 / lvrland tests × 2 + comment × 1）

---

## 5. 跨 repo 範本擴散（5/27）

| 範本 | 來源 | 目標 |
|---|---|---|
| 7 audit scripts | `CK_Missive/scripts/checks/` | `shared-modules/ck-modular-toolkit/checks/` |
| `cross-file-ssot-governance.md` | `CK_Missive/.claude/rules/` | `CK_AaaP/runbooks/` |
| `subdomain-registry.yaml` SSOT | `CK_Missive/configs/` | （CK_AaaP 待補 cross-repo 集中版）|

**未來 repo 採用**：`bash shared-modules/ck-modular-toolkit/install.sh --target=<repo>` 一鍵部署 audit 套件。

---

## 6. 中斷症狀根因 + 修法（5/25 揭發）

**問題**：每次 Edit/Write 觸發 `PostToolUse hook stopped continuation` × 4

**根因**：`.claude/settings.json` 4 個 `type: "prompt"` hooks 用判斷句但無條件注入，Claude Code runtime 解讀為阻擋。

**A 方案** 移除（commit `5cf400b5`，止血）
**B 方案** 補回 PowerShell command hook（commit `f310da93`）— 4 個 hooks 真實做路徑判斷後才注入

---

## 7. v7.0 baseline 進度（unchanged from v6.10）

| 指標 | 5/19 baseline | 5/27 現況 | target | gap |
|---|---|---|---|---|
| `v7_channel_diversity` | 1 | 1 | ≥4 | -3 |
| `v7_reference_density_diary_pct` | 1.1% | 1.1%（無增） | ≥50% | -48.9% |
| `v7_reference_density_critique_pct` | 100% | 100% | ≥80% | ✓ |
| `v7_soul_drift_lines` | 57 | 待跑 | ≤5 | ? |
| `v7_provider_fidelity_gap_pct` | 待跑 | 待跑 | ≤10% | ? |

**v7.0 baseline 進度本週無增**（治理債優先），下週 v6.12 應推進。

---

## 8. v6.12 路線圖建議（2026-06-17 起）

### 8.1 P0 必修
- 完成 PM2 廢除（owner-only，3-4h，本週可做）
- ck-tunnel-cloudflared pin（owner-only，5 min）
- owner SSO E2E（owner-only，5 min）

### 8.2 P1 整合
- 4 層分網路（折衷 2 層版本，1.5-2h，依 `network-refactor-roi-analysis.md`）
- v7.0 baseline 推進：
  - channel_diversity 1→4（補 Telegram + Discord push）
  - diary_density 1.1%→50%（autobiography 寫入鏈活體確認）
  - soul_drift 跨 repo 同步
  - provider_gap 跑 soul-fidelity-eval.py

### 8.3 P2 範本治理擴散
- step 41-46 audit suite 引入 CK_AaaP / CK_Hermes / CK_lvrland_Webmap / CK_PileMgmt 自己的 fitness
- `cross-file-ssot-governance.md` 各 repo `_meta/standards-consumed.yml` 宣告
- 9 處跨 repo `pile.cksurvey.tw` 修法（30 min）

### 8.4 P3 未來 audit 候補（新 step 47+）
- container startup race（postgres ready 前 backend 啟）
- DB connection pool exhaustion silent
- cloudflared metric scraping 404
- frontend bundle size drift
- 4 PostToolUse PowerShell hook 1 週觀察期 → 確認無 stopped continuation 復發

---

## 9. 治理觀察 — 過去 9 天學到的 4 件事

1. **跨檔 SSOT family 是大宗失效模式** — 從 L41 觸發到識別 L46/L47/L48 共 8 案，全是同型。立法 + audit 化是唯一根治。
2. **事故驅動 vs 治理債的決策法** — DEFER 4 層分網路是正解（沒事故 + 觀測棧未就緒 + 真實 ROI 小），同預算做 PM2 廢除 / step 42 修法 ROI 高 3-10 倍。
3. **Hook 設計反模式立刻識別** — `type: "prompt"` 用判斷句 = 必然 stopped continuation 觸發。Command + 真實判斷才是正解。
4. **大規模 commit 治理 single session 可行** — 546 dirty → 0 在 2h 內完成，前提是 owner 對 batch 範圍點頭 + conventional commit lowercase subject 過 commitlint。

---

## 10. 未來反思題

- v6.12 結束時，audit 套件擴散到幾個 repo？目標 ≥3。
- 8 大根因會不會有第 9 個出現？
- v7.0 baseline 從 1 → 4 需要多少 channel 工作？
- PM2 廢除後 cloudflared 命中 docker 是否真活？

---

> **核心精神**：**Audit 自動化的價值不在 GREEN，在於把 dormant 從 days 縮到 seconds。**
> 8 大根因從事故反應演進到 audit 偵測 — 這是 v6.11 真正的勝利。
