# SSO「今日 OK、明日又壞」反覆回歸 — 元覆盤與跨專案治本指南

> **建立**：2026-07-03
> **適用**：所有採用 CK_Website 為 IdP、子系統為 SSO 消費端的專案（Missive / lvrland / pile / DigitalTunnel…）
> **定位**：CK_Missive 為範本專案。本文把「SSO 反覆回歸」的**根因型態**與**治本設計不變式**萃取出來，供其他專案**仿照與自檢**，避免重蹈同一坑。
> **權威關聯**：`LESSONS_REGISTRY.md#L74` / memory `L74_sso_bootstrap_race_clobber` / fitness step 64 `auth_state_ssot_audit.cjs`

---

## 1. 現象：這不是單一 bug，是「反覆回歸」

2026-05 中至 2026-07-03，約 **7 週內至少 10 次**被宣稱「根治」的 SSO/登入 commit：

| # | commit | 宣稱根治 | 結果 |
|---|---|---|---|
| 1 | `3192c94a` | access token 30→60min（閒置登出）| 局部 |
| 2 | `a66d410b` | 重載後 startup 驗證重試（停在 entry 跳回）| 復發 |
| 3 | `17373757` | 統一 session 解析器（單一權威狀態 sessionStore）| 復發 |
| 4 | `9e229a36` | 宣告式導向（停在 entry 重整才好）| 復發 |
| 5 | `b2b6ae26` | bootstrap 競態 + 破壞性 clearAuth | 復發 |
| 6 | `1dc75776` | auth-state SSOT audit（fitness step 64）| 護欄不足 |
| 7 | `7845748b` | L66 self-heal + L68 CSRF refresh | 復發 |
| 8 | `52053913` | 「閃一下又跳回」已認證單一 401 不清 session | 復發 |
| 9 | `79e36c4d` | **attemptSSOBridge 補存 user_info + 兩 axios 實例 401 守衛** | 本次 |

**owner 的關鍵觀察**：「**今日 OK、明日又無法運作**」。這句話本身就是根因指紋。

---

## 2. 為什麼「今日 OK、明日又壞」？（元根因）

### 2.1 失敗永遠在「帶殘留狀態回來」的復原路徑，不在「乾淨登入」路徑

- **無痕視窗（乾淨狀態）永遠會過** → 乾淨登入的 happy path 一直是好的。
- **明日/重開機/隔夜回來時瀏覽器處於「衰變狀態」**：token 絕對過期（60min，SSO 無 refresh_token）、機器重開機後 cookie/csrf 重新初始化、閒置登出清了一半、localStorage 有 user_info 殘留但 token 已失效……
- 這些**衰變狀態會走到不同的程式分支**（復原/重建 session 的路徑），而每次「修好」的只是**當下重現的那一條**。明日的狀態排列組合走到另一條**還沒修的**路徑 → 又壞。

> **指紋判讀**：「無痕可以、正常不行」「今天好、明天壞」「重整一下就好」＝ bug 一定在**殘留狀態的復原路徑**，不在乾淨登入路徑。驗證若只測乾淨登入，必然漏。

### 2.2 復原路徑有「多重入口」，修一個不等於修全部

SSO 復原邏輯**散在多個入口**，每個入口各自從**部分狀態**做決定：

1. **兩個 axios 實例**各有自己的 401 攔截器：
   - `api/interceptors.ts`（主 client，業務請求）
   - `services/authService.ts` 私有實例（/auth/check、/auth/me、login…）
   - 修了主 client 的 401 守衛，authService 那個仍無條件 `clearAuth + location.href='/login'`。
2. **兩條 SSO bridge 路徑**：
   - `authService.ssoBridge()`（EntryPage 主動）→ **有** `saveAuthData` 寫 user_info。
   - `attemptSSOBridge()`（interceptor 被 401 觸發）→ **只 POST 設 cookie 就 reload、不寫 user_info**。
   - 登出後首次載入是**後者**先被 unread-count 401 觸發 → 每次都 `user_info=NULL`。
3. **破壞性副作用（clearAuth / removeItem user_info / 硬跳 login）散落多處**，各自在不同時機對「部分狀態」下手。

→ 狀態機的節點多、邊多；每次 patch 一個節點，其他節點在別的狀態下仍會引爆。

### 2.3 護欄（fitness step 64）有盲點：只防「新元件造反」，不看「基礎設施內部」

`auth_state_ssot_audit.cjs`（step 64）是 **allowlist** 式：擋「非 auth 基礎設施的元件自行推導登入 + 自行導向」。但它把 `interceptors` / `authService` **列入 allowlist 完全信任** → 今日兩個 bug **都在被信任的基礎設施檔內**，audit 全綠卻仍壞 → **假的安全感**。

### 2.4 驗證偏誤：headless / 無痕只測到 happy path

修法者（含 AI）常在無痕或剛清空的環境驗證 → 一定過 → 宣稱「真活」。但**真正會壞的衰變狀態無法在無痕重現**。這正是 [[adr-anti-half-wired-sop]]「真活 ≠ commit 說真活」在 SSO 上的具體化。

---

## 3. 治本設計不變式（Invariants）— 其他專案照抄

把下列**不變式**寫進 auth 基礎設施，並用 audit 強制（見 §5）：

| # | 不變式 | 反例（會反覆回歸）|
|---|---|---|
| **I1** | **單一權威登入狀態**：`is-authenticated` 只有一個真相（如 `sessionStore.status: resolving\|authenticated\|anonymous`）。所有守衛只**讀**，不各自推導。| 5+ 元件各讀 localStorage/cookie 各自 redirect |
| **I2** | **破壞性清除只在 `anonymous` 執行**：任何 401 handler 的 `clearAuth`／清 user_info／跳 login，**必須先確認權威狀態 === anonymous**；`resolving`/`authenticated` 一律只 reject，交由啟動解析器（bootstrap）依權威狀態決定。| 任一 401 就 clearAuth + 硬跳 → 瞬態 race 清掉剛建立的 session |
| **I3** | **所有 session 建立路徑都必須持久化 user_info**：不論 EntryPage 主動或 interceptor 被動的 SSO bridge，200 後**都要寫 user_info（前端唯一「我登入了」訊號）**才能 reload。| interceptor bridge 只設 cookie 就 reload → 重載後 user_info=NULL → anonymous |
| **I4** | **破壞性副作用收歸唯一決策點**：清除/降級的決策集中在 bootstrap（或等價單一處），不埋在被動驗證函式或多個攔截器裡。| clearAuth 埋在 validateTokenOnStartup、又埋在兩個攔截器 |
| **I5** | **明確事件優先於被動檢查**：`markAuthenticated`（登入/SSO 成功）優先於「舊 token 被動驗證」的遲到結果（last-writer-wins 競態防護）。| ssoBridge 先贏設 authenticated，遲到的 validate 又覆寫回 anonymous |
| **I6** | **多實例一致**：專案內**每一個** axios/fetch 實例的 401 處理必須套同一組 I2/I3 守衛。修一個實例不算修完。| 修了 client 攔截器，authService 私有實例仍無守衛 |

---

## 4. 驗證協定（防「只測 happy path」）

宣稱 SSO 修好前，**必須**覆蓋下列衰變狀態（不能只無痕測乾淨登入）：

- [ ] **乾淨登入**（無痕）：www 登入 → 子系統直接進 dashboard、Header 顯示姓名。
- [ ] **隔夜/ token 過期回來**：token 絕對壽命過後（或手動改系統時間 / 縮短 TTL 重現）reload → 不停登入頁。
- [ ] **機器重開機後**：cookie/csrf 重新初始化的首個 /auth/check race → 不清 session。
- [ ] **localStorage 殘留但 token 失效**：手動保留 user_info、使 token 失效 → reload 能自我修復或乾淨降級，不 ping-pong。
- [ ] **登出後立即重新登入**：unread-count 等高頻輪詢先 401（走 interceptor bridge 路徑）→ user_info 有被寫、直接進 dashboard。
- [ ] **F12 檢查**：`localStorage.user_info` 有值、Header 非「訪客」、Network 無殘留 401 迴圈。

> 這些狀態多數 headless/無痕無法代行 → **owner 真人複驗是必要關卡**，但上述清單讓復驗有明確標的（非「感覺一下」）。

---

## 5. 結構性防護（fitness audit 強化）

`auth_state_ssot_audit.cjs`（step 64）已擴充，**不再無條件信任 auth 基礎設施內部**，新增兩條規則直掃 interceptor/authService：

- **Rule C（I2）**：偵測 401 handler 內的破壞性動作（`clearAuth(` / `removeItem('user_info')` / `location.href|replace('/login')`）而**同檔未引用 session 狀態守衛**（`getSessionStatus` / `useSessionStore` / `status ===|!==`）→ RED。
- **Rule D（I3）**：偵測有 POST `sso-bridge` 的檔案而**未持久化 user_info**（`setItem('user_info'` / `saveAuthData` / `setUserInfo`）→ RED。

> 這兩條**若在 2026-07-03 之前就存在，會直接 RED 標出**今日兩個 bug（interceptor bridge 沒寫 user_info、authService 401 無守衛）。

---

## 6. 其他專案（lvrland / pile / DigitalTunnel）落地步驟

1. **盤點入口**：列出專案內**所有** axios/fetch 實例 + **所有** SSO/login 成功路徑（grep `sso-bridge` / `create(` / `interceptors.response`）。
2. **對照 §3 六不變式**逐條檢查；特別確認 I3（每條 bridge 都寫 user_info）、I6（每個實例都有 I2 守衛）。
3. **移植 audit**：把強化後的 `auth_state_ssot_audit.cjs` 納入該專案 fitness（`install-template-to.sh` 已可跨 repo 部署）。
4. **採 §4 驗證協定**，尤其「隔夜/重開機/登出後立即重登」三個衰變狀態。
5. **禁止**在無痕/headless 通過就宣稱真活（[[adr-anti-half-wired-sop]]）。

---

## 7. 一句話總結

> **SSO 反覆回歸的本質＝「乾淨登入」與「帶殘留狀態復原」是兩套路徑，後者有多入口且散落破壞性副作用；每次只修當下重現的那一條、又只在無痕驗過 happy path，於是明日換個衰變狀態就走到另一條沒修的路。治本＝六不變式（單一權威狀態 / 破壞性清除只在 anonymous / 每條 bridge 都寫 user_info / 副作用收歸唯一決策點 / 明確事件優先 / 多實例一致）＋ 直掃基礎設施內部的 audit ＋ 覆蓋衰變狀態的真人驗證協定。**
