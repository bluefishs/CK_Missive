# 模組化下一步候選 — 跨 4 repo 重複熱點評估與 ROI 收斂路線圖

> 日期：2026-07-22 | 依據：前後端各一 Explore agent 逐行 diff 實證（CK_Missive / lvrland / PileMgmt / DigitalTunnel）
> 承接：本次 SSO/模組化馬拉松（`ck_auth` 後端 JWT verify 已 Tier1 化、`@ck-shared/tokens` 前端設計系統已採用）
> 方法論：`MODULARIZATION_CROSS_PROJECT_STRATEGY.md`（Tier1 import+版本閘 / Tier2 契約+conformance / Tier3 per-repo）+ L58 粒度紀律

---

## 0. 元洞察（決定策略方向，先讀）

**問題不是「缺共享模組」，是「用 copy 式建了一堆死模組」**：
- `shared-modules/` 已有 **20+ 模組**（ai-connector / auth-module / data-backup-module / observability / gis-platform-module …），但前端只有 **4 個**（tokens / core / ui-components / site-management-module）真被 `import`，後端只有 `ck_auth` 真被消費。
- **observability 模組存在、卻沒人用**——各 repo 繼續帶自己的 diverged 副本（L30 環節不連通＝浪費、L31 ROI＝entities×usage_rate 的活教材）。
- **`ck-sso-js` / `ck-sso-py` 是「vendored 手動複製」而非 import**：一份邏輯散成 3–4 份，bug 修一次要手動同步四次 = **反覆 SSO bug 的結構根因**。

**∴ 收斂原則（全部候選共用）**：
1. **只正式化「已證明近乎逐字相同」的重複**（非投機建模組）
2. **import 式 + 版本閘**（`ck_auth` 模式），不再 copy vendoring
3. **同概念但合理分歧者走 Tier2 契約 + conformance**（`DT jose` 前例），不強壓單一實作
4. **殺死死模組**（沒人 import 的 shared-modules 模組降級或刪除）

---

## 1. 分層歸類 + ROI 排序

### ⭐ Phase 1（最高 ROI，直接續本次工作）— SSO 認證層完成收斂

本次已把**最底層 JWT verify** 收斂為 `ck_auth`；但**上面兩層仍是 4× copy**，正是反覆 bug 源：

| 層 | 現況 | 目標 | 證據 |
|---|---|---|---|
| 後端 sso_bridge | 4 repo copy-derived（同註解語彙 L41/I7/L80）| 併入 `ck_auth`（Tier1）| 4 份手動同步、pile↔lvrland csrf **僅差 2 行** |
| 後端 csrf | pile↔lvrland 差 2 行、Missive/DT 分歧 | pile+lvrland 立即併、Missive/DT 走契約 | 實質同一檔 |
| 前端 sso-bridge | **`ck-sso-js` vendored 3 repo**、`useSSOBridge.ts` **三方逐字相同**、`sso-bridge.ts` lvrland↔pile 差 1 行 | 正式化 **`@ck-shared/sso`**（Tier1 npm workspace）| diff≈0 |
| 前端 auth 狀態機 | 4 種平行（Missive `sessionStore`/`SessionGate`、lvrland/pile `authStore`、DT `ckSsoHandler`）| 契約化單一 SSO 狀態機（Tier2）| 同概念四命名＝bug 根因（L74/L78） |

**行動**：①後端 `ck_auth` 擴入 sso_bridge+csrf（bump 0.2.0→0.3.0、版本閘沿用 step 70）②前端 `ck-sso-js`→`@ck-shared/sso`（`file:` workspace）③authStore/authService/sessionStore 收斂為單一狀態機（Tier2 契約，因 Missive 版較複雜）。**這直接根治 L74/L78/L80。**

### Phase 2（低成本速贏）— 近乎逐字相同、零/低風險立即併

| 候選 | repo | 分歧 | Tier |
|---|---|---|---|
| 後端 `base_repository` | pile↔lvrland | **8 行** | Tier1 → `ck-core-py` |
| 後端 `db_query_metrics` | Missive↔pile | **5 行** | 併入既有 `shared-modules/observability`（改為真被 import）|
| 前端 `apiErrorHandler` + `errorBus` | lvrland↔pile | **~4%（18 行）** | Tier1 → `@ck-shared/error-bus` |
| 前端 WebSocket context/hook | lvrland↔pile | **~7%（77 行）** | Tier1 → `@ck-shared/ws`（僅 2 repo 但近複製）|
| 前端 queryClient 設定 | lvrland↔pile | **~13%（70 行）** | Tier1 → `@ck-shared/query-config`（順帶 pile `.js→.ts`）|

### Phase 3（中，需先設計/統一路線）

| 候選 | 障礙 | Tier |
|---|---|---|
| 前端 API client interceptors（401/CSRF/throttler）| **axios（3 repo）vs fetch（DT）路線分裂**，需先統一；Missive `interceptors.ts` 最完整可作 reference | Tier2 契約（401/CSRF/throttle 行為）|
| 後端 session 管理 | 4 種實作（session_repository / blacklist / session_service）無共同祖本 | Tier2 契約 + conformance |
| 前端 `env.ts` / `isAuthDisabled` | 分歧且分散（部分 repo 未集中化）| Tier2 → 以 Missive `env.ts` 為藍本 `@ck-shared/env` |
| 後端 `secret_loader` | Missive 獨有成熟版 | Tier1 反向補給其他 3 repo |
| 後端 middleware 三件套（security_headers/rate_limit/api_version）| 4/4 漂移，需先統一**註冊順序**（pile `middleware_order.py` 可作藍本）| Tier2 契約 |

### Phase 4（延後 / 低優先）

- 後端 backup 服務（Missive↔pile 同源漂移，中度；lvrland 走 Celery 不同命名）
- observability 全面採用（先做 Phase 2 的 db_query_metrics 試點證明可行再擴）

### Tier 3（明訂 per-repo，不標準化，避免 L58 污染）

- 業務邏輯、GIS 圖層（lvrland/pile domain）、domain models、各 repo 專屬 UI

---

## 2. 執行紀律（每個 Phase 通用）

- **先寫 conformance test 證行為等價，再切換**（`DT jose↔ck_auth.sso` 前例：改一處 + bump 版本 + 換 wheel/workspace）
- **每個 Tier1 套件配版本閘 audit**（沿用 `tier1_shared_package_audit.py` step 70 模式）
- **L76：後端 rebuild 完整跑完 + isolated `docker run --rm` 測 image 才 recreate**（本次 DT outage 教訓）
- **殺死死模組**：Phase 完成後，把被取代的 vendored copy（`ck-sso-js` 舊複製、各 repo diverged observability）刪除或降為 shim，並標記 shared-modules 中無人 import 的模組
- **粒度紀律（L58）**：只收斂「已證明近乎逐字相同」者；同概念但合理分歧走契約不強壓

---

## 2.5 Phase 1 執行實況（2026-07-22，owner 選「連狀態機一起收斂」後啟動）

**已完成（安全）**：
- 建 `@ck-shared/sso` 種子套件（bridge 單一源，copy 自 lvrland canonical + react peerDep + host tsc 型別自帶）
- 狀態機契約設計（agent 深度分析）：`createAuthStore(config)` + 3 adapter（Storage/Csrf/UserNormalizer）+ tokenMode 分支；**保真鐵律＝繼承 hardened 版**（lvrland I2 + Missive race-guard），不繼承 pile/DT 未修 bug；DT 最硬最後收斂

**🔴 揭發真正阻斷（cutover 前置，isolated build 實測，未 deploy 零連鎖）**：
- lvrland frontend Docker `context: ./frontend`，shared-modules 在外 → `@ck-shared/sso` **Rollup 無法 resolve**（`✗ failed to resolve import "@ck-shared/sso"`）。tokens（純 TS）能過、sso（新套件+react）不能。
- **前置任務＝前端 Docker 共享套件 build tooling**（三選一：build context 改 repo root / pre-build staging + vite alias / 發佈真 npm package）——**影響 4 repo compose+Dockerfile，屬基礎設施變更**，須 focused session deliberate 執行，勿尾端 trial-and-error（＝反覆修測+連鎖風險）。
- lvrland 已完整還原乾淨（tsc EXIT=0、running 系統全程未受影響）。

**修正結論**：SSO 根治的**真正第一阻斷不是程式碼**（bridge 已 identical、狀態機已設計），**而是 monorepo 前端共享套件的 Docker build tooling**。此前置解決後，bridge→狀態機 cutover 才可逐 repo 安全進行。→ 確認為 focused-session 基礎設施專案。詳見 `shared-modules/sso-js/README.md`。

## 3. 一句話總結

> **本次已把 SSO 最底層（JWT verify）Tier1 化；最高 ROI 的下一步是把 SSO 認證中間層（前端 `ck-sso-js`→`@ck-shared/sso`、後端 sso_bridge+csrf→`ck_auth`、四種 auth 狀態機→單一契約）一併收斂——這直接根治 L74/L78/L80 反覆 SSO bug。其餘 base_repository/errorBus/WebSocket 是零風險速贏。全程用 import＋版本閘＋conformance，並殺死沒人用的死模組。**
