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

## 2.6 Phase 1 續（2026-07-22 稍後）— 阻斷已解、lvrland bridge 完成

**✅ 前端 build-tooling 阻斷已解決（vendored-in-context 模式，比照後端 vendored-wheel）**：
- shared-modules/sso-js＝canonical，`sync.sh` 同步進 repo `frontend/.shared-sso`（in-context）、Dockerfile 於 npm install 前 `COPY .shared-sso`；`sync.sh --check` 守護 drift。
- **關鍵**：vendored 進 `frontend/` 子目錄 → 其 react import 往上解析到 `frontend/node_modules`（不像 `../../shared-modules` 在外），順帶解 host tsc react 問題。
- **lvrland isolated build ✓（18950 modules）→ 部署 → 公網 200 → 瀏覽器 LoginPage `useSSOBridge` 正確 fallback（console 無錯）→ 真 rename 100%（byte-identical 確證）**。commit lvrland `1f4b3323e`。

**🔍 執行揭發精確事實（修正 agent 的「4 repo bridge copy」）**：
- **只有 lvrland 真正 import 使用 `ck-sso-js` lib** → 已收斂。
- **pile 用自己 inline `attemptSSOBridge`（api/client.ts）**、且刻意移除 useSSOBridge（security-aware manual-trigger 設計）；**DT 用自己 `ckSsoHandler`（bearer/XOR）** → 兩者的 `src/lib/ck-sso-js/` 是**死碼**、live bridge 是 **divergent 行為敏感實作**。
- Missive 用 `authService.ssoBridge()`（原始源，3 touchpoint）。

**∴ 修正結論**：bridge「單一源」對 lvrland 已達成（+ 證實 build-tooling 機制）；pile/DT/Missive 的 live bridge 收斂**與狀態機同屬行為敏感 Tier2 staged 工作**（不可簡單 import repoint，須逐一保真遷移）。下一步最高 ROI＝把 pile inline / DT ckSsoHandler / Missive authService.ssoBridge 逐一遷 `@ck-shared/sso`（用 lvrland 已驗證的 vendored 機制），每 repo isolated build + 公網 200 + 瀏覽器驗證。

## 2.7 auth 狀態機收斂（2026-07-23）— lvrland + pile 完成、Missive/DT paradigm 差異

**✅ 2-state authStore 收斂完成（lvrland + pile，皆 live 驗證）**：
- canonical `createAuthStore(config)` 於 @ck-shared/sso（保真基準＝lvrland，含 **I2 非破壞性 checkAuth**）；per-repo 差異 config 注入（persistKey/checkAuthUrl/logger/onLoginSuccess）。
- **lvrland**（`3238b1630`）：behavior-preserving；tsc0→isolated build✓18951→公網200→瀏覽器 login+guard+console 乾淨。
- **pile**（`9bae9a6bd`）：**行為改善**（原 destructive checkAuth → I2 修「第一次失敗重刷才好」）；**順修 latent 破損**（pile theme `@ck-shared/tokens` 在 context 外無法 build、6/17 起從未部署 → 比照 vendored-in-context 修好+交付 radius6）；tsc0→isolated build✓14744→公網200→瀏覽器 dashboard+console 乾淨；ratchet 測試同步（fetch budget 10→8、zustand 偵測認 createAuthStore）。
- **關鍵基礎設施**：`@ck-shared/tokens` 亦有 context 外問題（pile 揭發），已用同 vendored-in-context 修；lvrland tokens 恰因 antdTheme 被 tree-shake 而僥倖 build 過（實為死引用）。

## 2.8 auth 狀態機收斂完成（2026-07-23）— Missive tri-state 收斂 + DT 結論

**✅ Missive sessionStore 收斂完成（tri-state，live 驗證）**（`missive c8fc6e66` + canonical `f98a87d`）：
- 建 tri-state `createSessionStore(config)` canonical（保真基準＝Missive 原版，含 L74/L78 markAuthenticated 競態防護）；per-repo 差異注入（getUserInfo/validateTokenOnStartup/clearAuthData/computeBypass/logger）。
- Missive host build（vite，file: 直用、不受 Docker context 限制）：host tsc0 → **build-to-test✓9221（不觸 live dist）** → build live✓9220 → 公網200 → 瀏覽器 entry+SessionGate bootstrap 解析+console 乾淨。
- drift GREEN（lvrland/pile .shared-sso 同步含 createSessionStore、對 2-state 消費者 tree-shake 無害）。

**✅ DT 結論：正確地維持獨立 bearer paradigm（非「未完成」）**：
- DT 用 `TokenManager`（bearer/XOR localStorage）+ `ckSsoHandler`、**無 zustand store** → 與 cookie-based createAuthStore/createSessionStore 根本不同 paradigm。
- 強行收斂需 bearer-adapter 設計 + 風險（DT 曾 outage、有「sub=email 無限登入迴圈」史）+ 屬過度標準化（L58「只共享真一致且穩定者」）。→ **DT 維持獨立＝正確架構（異質 auth model），非缺口**。

**收斂總結**：3/4 repo（凡 zustand-store paradigm 者）全收斂＝lvrland(bridge+authStore 2-state) + pile(authStore 2-state) + Missive(sessionStore tri-state)，皆 live 驗證；DT 為正確的 bearer paradigm 例外。canonical 並存 createAuthStore(2-state) + createSessionStore(tri-state)，tri-state 為未來升級目標（lvrland/pile 可升）。

---
（以下為收斂前的 paradigm 差異記錄，供覆盤）

**⏳ Missive + DT 為不同 paradigm、不適用當前 2-state canonical**：
- **Missive** 用 `sessionStore` **tri-state**（resolving|authenticated|anonymous，L74/L78 最 hardened）→ 遷 2-state canonical 會**降級**（失去 resolving race-guard）。
- **DT** 用 `TokenManager`（bearer/XOR）+ `ckSsoHandler`，**無 zustand authStore** → 無對應可遷。
- **∴ 收 Missive/DT 需把 canonical 升級為 tri-state + 3 adapter（Storage/Csrf/UserNormalizer）+ tokenMode**（agent 完整設計，見 README）＝更大 Tier2，須逐一保真、DT 最後。當前 2-state 收斂對 lvrland/pile 已達成且 live，Missive/DT 維持各自 hardened 版待升級式收斂。

## 3. 一句話總結

> **本次已把 SSO 最底層（JWT verify）Tier1 化；最高 ROI 的下一步是把 SSO 認證中間層（前端 `ck-sso-js`→`@ck-shared/sso`、後端 sso_bridge+csrf→`ck_auth`、四種 auth 狀態機→單一契約）一併收斂——這直接根治 L74/L78/L80 反覆 SSO bug。其餘 base_repository/errorBus/WebSocket 是零風險速贏。全程用 import＋版本閘＋conformance，並殺死沒人用的死模組。**
