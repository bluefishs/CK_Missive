# SSO「今日 OK、明日又壞」反覆回歸 — 端到端元覆盤與跨專案治本指南（v2）

> **建立**：2026-07-03 ｜ **v2 大改**：2026-07-21（新增「後端 token 生命週期層」＝反覆回歸的底層根因）
> **適用**：所有以 CK_Website 為 IdP、子系統為 SSO 消費端的專案（Missive / lvrland / pile / DigitalTunnel…）
> **定位**：CK_Missive 為範本專案。本文把「SSO 反覆回歸」的**兩層根因型態**與**治本設計不變式**萃取出來，供其他專案仿照與自檢。
> **權威關聯**：`LESSONS_REGISTRY.md#L41/#L44/#L66/#L68/#L74/#L78/#L80` ｜ memory `L74_sso_bootstrap_race_clobber` ｜ fitness step 64 `auth_state_ssot_audit.cjs`（Rule C/D）
> **v2 一句話**：**前一版只治「前端狀態機層（I1–I6）」；但真正讓「明日又壞」的是「後端 token 生命週期層」——SSO 對後端根本沒有可用的透明 refresh 路徑，前端不變式「有 session 可優雅復原」的前提在 SSO 上不成立。兩層必須共同設計。**

---

## 0. TL;DR — 兩層根因模型

SSO 反覆回歸 = **兩層結構性缺口的交集**，任何只修單層的 commit 都會「明日換個衰變狀態又壞」：

| 層 | 本質 | 症狀指紋 | 既有處理 |
|---|---|---|---|
| **Layer 1｜前端狀態機** | 「乾淨登入」與「帶殘留狀態復原」是兩套路徑，後者**多入口 + 散落破壞性副作用 + 多重真相來源** | 「無痕可以、正常不行」「重整才好」「停在 entry / Header 訪客」 | v1 六不變式 I1–I6（**部分落實**，見 §4） |
| **Layer 2｜後端 token 生命週期** | **SSO 沒有可用的透明 refresh 路徑**：token 過期即無法就地復原，唯一出路是會丟失工作的整頁 reload | 「編輯到一半存檔 401 白填」「refresh 一直 401」「併發後全站 401 風暴」 | **v2 首次記錄**；不變式 I7–I11（見 §5），2026-07-21 先止血 |

> **為什麼修了 7 週 10 次還壞**：所有 commit（L44/L66/L74/L78）都在 Layer 1 打轉，把「復原路徑」愈修愈細；但 Layer 2 讓 SSO **根本沒有 session 可優雅復原**——refresh 必 401、rotation 併發互殺、唯一復原是 reload。前端再嚴謹的不變式，也救不了「後端不給你一條無痛續命的路」。

---

## 1. 現象：這不是單一 bug，是「反覆回歸」

2026-05 中至 2026-07-21，**至少 11 次**被宣稱「根治」的 SSO/登入 commit（層級：**FE**=前端狀態機、**BE**=後端 token、**CK**=cookie/跨域、**CS**=CSRF、**M**=元治理）：

| # | 日期 | commit / 資產 | 宣稱根治 | 層 | 結果 |
|---|---|---|---|---|---|
| 1 | 05-21 | ck-sso-py install.sh v1.0 | L41 JWT secret drift silent fail | BE | 局部 |
| 2 | 05-22 | ck-sso-js v2.0 | L44 跨 subdomain session lock 反模式 | FE/CK | 復發 |
| 3 | 06-10 | `useNavigationData.tsx:87` | L66 self-heal gate 漏 cookie-session | FE/CK | 復發 |
| 4 | 06-10 | `csrf.py` EXEMPT + interceptor | L68 CSRF↔refresh 生命週期死結 | CS/CK | 復發 |
| 5 | 06-16 | `b2b6ae26`/`1dc75776` | L74 sessionStore 雙 async 競寫 + 破壞性 clearAuth | FE | 復發 |
| 6 | 07-02 | `52053913` | 已認證單一 401 不清 session（防閃退） | FE | 復發 |
| 7 | 07-03 | `79e36c4d` + audit Rule C/D | L78 元覆盤：多入口 + 兩 axios + bridge 不寫 user_info | M/FE | 局部 |
| 8 | 07-03 | `9b1017e7` | 復原窗口掛起原請求防閃錯 | FE | 局部 |
| 9 | **07-21** | `0062769f` | **L80 SSO 無 refresh 路徑（止血：SSO TTL 8h + replay 寬限）** | **BE** | 止血 |

**owner 的關鍵觀察**：「**今日 OK、明日又無法運作**」「多次修復仍有問題」——這兩句本身就是**跨層根因指紋**：Layer 1 的復原路徑衰變狀態排列組合 × Layer 2 根本無法復原。

---

## 2. Layer 1｜前端狀態機層（v1 精華 + 現況校準）

### 2.1 失敗永遠在「帶殘留狀態回來」的復原路徑

- 無痕視窗（乾淨狀態）永遠會過 → happy path 一直好。
- 明日/重開機/隔夜回來時瀏覽器處於**衰變狀態**：token 絕對過期、cookie/csrf 重新初始化、閒置登出清了一半、localStorage 有 user_info 殘留但 token 已失效……
- 這些衰變狀態走到**不同的復原分支**，每次「修好」只修當下重現那一條 → 明日換個組合走到還沒修的那條 → 又壞。

> **指紋判讀**：「無痕可以、正常不行 / 今天好明天壞 / 重整就好」＝ bug 一定在**殘留狀態的復原路徑**。只測乾淨登入必漏。

### 2.2 復原路徑「多入口」（2026-07-21 實測現況）

| 入口 | 位置 | 401 有 refresh | 401 有 session 守衛 | 破壞性清除 |
|---|---|:-:|:-:|:-:|
| 主 axios（apiClient） | `api/interceptors.ts:181` | ✅（+重試原請求） | ✅ `status!=='anonymous'` | 散裝 removeItem ×2 分支 |
| authService axios | `services/authService.ts:100` | ❌ | ✅ `status==='anonymous'` | `clearAuth()` |
| 裸 axios（bridge/refresh/csrf 補打） | interceptors 內 | — | ❌（刻意防遞迴） | — |
| raw fetch（digitalTwin / ai / xlsx 匯出入） | 多檔 | ❌ | ❌ | — |

→ **兩個已配置攔截器的 axios 實例各寫一份 401 邏輯**（語意一致但程式碼未收單點）；raw fetch 客戶端完全不參與一致性。

### 2.3 `is-authenticated` 仍有 5 個真相來源（違 I1）

`sessionStore.status`（意圖 SSOT）之外，仍被當登入判據使用的：① `authService.isAuthenticated()`（idle timeout / checkAuth / EntryPage fallback）② `localStorage.user_info` ③ `csrf_token` cookie（useNavigationData self-heal）④ `access_token` localStorage。

### 2.4 護欄盲點與驗證偏誤

- **fitness step 64 曾 allowlist 完全信任 auth 基礎設施內部** → 07-03 兩個 bug 都在被信任檔內、audit 全綠卻壞（已補 Rule C/D 直掃 interceptors/authService）。
- **headless / 無痕只測 happy path** → 真正會壞的衰變狀態無法在無痕重現 → 「真活 ≠ commit 說真活」（[[adr-anti-half-wired-sop]]）。

---

## 3. Layer 2｜後端 token 生命週期層（v2 新增，反覆回歸的底層）

### 3.1 端到端契約現況（2026-07-21 實測）

| 元件 | key | httponly | samesite | path | TTL | 簽發者 |
|---|---|:-:|:-:|---|---|---|
| IdP SSO cookie | `ck_employee`(HS256)/`ck_employee_rs`(RS256) | ✅ | **Lax** | `/` | **4h** | CK_Website `callback.ts`，Domain=**`.cksurvey.tw`** |
| Missive access | `access_token` | ✅ | Lax | `/` | local **60min** / SSO **8h**（07-21 起） | Missive `set_auth_cookies` |
| Missive refresh | `refresh_token` | ✅ | **strict** | **`/api/auth/refresh`** | cookie 7 天，**但 DB session.expires_at 綁 access TTL** | 同上 |
| CSRF | `csrf_token` | ❌ | Lax | `/` | **1h** | 同上（`/auth/refresh` 已 EXEMPT，L68） |

### 3.2 為什麼 SSO **沒有可用的透明 refresh 路徑**（四重疊加）

1. **access token 與 session.expires_at 都綁同一 TTL**（原 60min）→ 名目上 7 天的 refresh cookie，被 60min 就過期的 DB session 廢掉：**過 TTL 後 refresh 對誰都必 401**。
2. **業務請求是 stateful，不是無狀態 JWT**：`get_current_user_from_token` 每個請求都查 `user_sessions WHERE jti AND is_active AND expires_at>now`。→ **rotation 一撤舊 session（is_active=False），舊 access token 即使 JWT 未過期也立刻失效**。
3. **refresh rotation × 併發 × 雙 axios 實例**：token 過期時多請求同時 401，各自 refresh；`isRefreshing` 鎖是**每個 axios 實例各一把**，兩實例可同時 rotate 互殺；舊 refresh_token 二次使用觸發 **replay → 撤銷該用戶全部 session → 401 風暴**。
4. **唯一復原 = sso-bridge，但它 `location.replace('/dashboard')` 整頁跳轉** → 進行中的編輯/存檔丟失；且前端 `believedAuthed` 分支（防閃退）直接 `throw` 該 401、不重試 → 使用者白填。

### 3.3 跨 repo「session 存活期」無單一 SSOT

**IdP cookie 4h ≠ Missive SSO session 8h ≠ 前端 idle 60min** — 三個「一次 session 能活多久」的值散在三個 repo/層，無 audit 對齊（同 `cross-file-ssot-governance` 家族）。後果：
- Missive 8h token 比 IdP cookie（唯一 re-bridge 憑證）4h 還長 → 4h–8h 之間 Missive 有效但 IdP 已失效（安全/一致性缺口）。
- 「有時收不到 SSO cookie」= ck_employee 4h 過期 / 內網 HTTP 不帶 Secure cookie / 背景 fetch 的 SameSite=Lax 情境。

---

## 4. Layer 1 不變式 I1–I6（其他專案照抄）+ Missive 現況

| # | 不變式 | Missive 現況（07-21） |
|---|---|---|
| **I1** | 單一權威登入狀態（`is-authenticated` 只有一個真相，守衛只讀不推導） | **半符合** — status 主導，但 `isAuthenticated()`/user_info/csrf/access_token 仍 4 個殘留來源 |
| **I2** | 破壞性清除（clearAuth/清 user_info/跳 login）**只在權威 `anonymous` 執行** | **行為符合、實作分散** — 兩 axios + bootstrap 各有守衛 |
| **I3** | 所有 session 建立路徑都持久化 user_info（前端唯一「我登入了」訊號） | **符合** — 9 條成功路徑全寫（含 07-03 補的 interceptor bridge） |
| **I4** | 破壞性副作用收歸唯一決策點（單一 teardown） | **違反** — 清除 3 份、redirect 多份，未收單點 |
| **I5** | 明確事件（markAuthenticated）優先於被動舊 token 檢查（防 last-writer-wins 競寫） | **符合**（有測試鎖定） |
| **I6** | 多實例一致：每個 axios/fetch 的 401 都套同一組守衛 | **半符合** — 實例 B 無 refresh/重試、raw fetch 完全不參與 |

---

## 5. Layer 2 不變式 I7–I11（v2 新增，後端/生命週期層）

| # | 不變式 | 反例（會反覆回歸） |
|---|---|---|
| **I7** | **SSO session 必須有「無痛續命」路徑**：access token 過期時，能在**不整頁 reload、不丟失進行中請求**下取得新 token（refresh 對 SSO 回退重鑄，或 in-place re-bridge + 重試原請求） | 唯一復原是 `location.replace` → 編輯白填 |
| **I8** | **stateful session 檢查對「剛 rotation 的 jti」須有寬限**：rotation 撤舊發新的瞬間，在途請求用舊 jti 不應立即 401（grace window） | 每次 refresh 讓所有在途舊 token 請求 401 |
| **I9** | **refresh rotation 對併發須冪等/寬限**：近 N 秒內剛撤銷的 refresh_token 二次使用判「併發誤觸」而非 replay，**不撤全 session** | 雙 axios/多請求併發 → replay → 全 session 撤銷 → 401 風暴 |
| **I10** | **「一次 session 能活多久」跨 repo 單一 SSOT**：IdP cookie TTL = 消費端 session TTL = idle timeout 基準，三者對齊並有 audit | IdP 4h / Missive 8h / idle 60min 各自為政 |
| **I11** | **session 存活期不得被更短的相依值 silent 廢掉**：DB session.expires_at 應對齊「可續命窗口」（refresh 壽命），不可綁更短的 access TTL 而讓長效 cookie 形同虛設 | 7 天 refresh cookie 被 60min session.expires_at 廢掉 |

---

## 6. 目標態設計 + 根治路線圖（holistic recommendation）

> **原則**：Layer 1 與 Layer 2 **共同設計**；先止血降頻率，再根治補「無痛續命」路徑，最後收斂前端單點與跨專案。

### ✅ P0 止血（2026-07-21 已交付 `0062769f`）
- SSO access token / session TTL 60min→**8h**（`SSO_ACCESS_TOKEN_EXPIRE_MINUTES`，僅 sso-bridge、local login 不弱化）→ 大幅降低編輯途中過期。
- refresh replay **5s 併發寬限**（`REFRESH_REPLAY_GRACE_SECONDS`）→ 不再誤殺全 session（I9 部分）。
- regression 6/6 + 既有 auth 51 全綠；兩參數 config 可逆。

### 🔷 P1 後端根治「無痛續命」（推薦，最小前端動）— 落實 I7/I8/I11
1. **`/api/auth/refresh` 對 SSO 回退重鑄**：refresh_token 失效但**帶有效 `ck_employee` SSO cookie** 時，伺服端等同 sso-bridge 重鑄 token 回 200 → **沿用既有 interceptor「refresh 成功→重試原請求」線路**，無 reload、無資料丟失。
2. **stateful 檢查對剛 rotation 的 jti 加 grace**（I8）：`get_current_user_from_token` 對「revoked_at 在 N 秒內」的 jti 仍放行，讓在途請求不被 rotation 秒殺。
3. **session.expires_at 對齊續命窗口**（I11）：SSO session 存活期 = 可 re-bridge 窗口，不再綁 access TTL。

### 🔷 P2 跨 repo TTL SSOT（I10）
- 對齊 IdP `ck_employee`（現 4h）、Missive SSO session（現 8h）、idle timeout（現 60min 活動制）為一致策略值，寫入 `cross-file-ssot-governance.md` + 新增 audit（同 volume/network SSOT 三件套）。**選一個值**：建議 IdP cookie 與消費端 session 同為 8h（IdP 端 `callback.ts` Max-Age 4h→對齊），idle 維持活動制。

### 🔷 P3 前端單點收斂（完成 I1/I4/I6）
- 移除 `authService.isAuthenticated()` 第二套真相，全部改讀 `sessionStore.status`。
- 破壞性清除 3 份 + redirect 多份 → 收歸**單一 `teardown()`**（I4）。
- 實例 B（authService）與 raw fetch → 共用主攔截器或統一 401 handler（I6）。
- interceptor `believedAuthed` refresh 失敗分支 → **in-place re-bridge（不 reload）+ 重試原請求**（I7 前端側），mutation 不再白填。

### 🔷 P4 跨專案落地（見 §9）
- pile 補 I2+I3（最高風險）、lvrland 補 client.ts Rule C；audit step 64 + Rule C/D 移植兩專案。

---

## 7. 驗證協定（防「只測 happy path」）— 兩層衰變狀態

宣稱 SSO 修好前**必須**覆蓋（不能只無痕測乾淨登入）：

**Layer 1（前端狀態）**
- [ ] 乾淨登入（無痕）→ 直接進 dashboard、Header 顯示姓名。
- [ ] 機器重開機後首個 `/auth/check` race → 不清 session。
- [ ] localStorage 殘留 user_info 但 token 失效 → reload 自我修復或乾淨降級，不 ping-pong。
- [ ] 登出後立即重登：unread-count 高頻輪詢先 401（走 interceptor bridge）→ user_info 有寫、直接進 dashboard。

**Layer 2（token 生命週期）— v2 新增**
- [ ] **編輯表單途中 token 過期 → 存檔仍成功**（無痛續命，不整頁跳轉、不白填）。← 本次核心
- [ ] 隔夜/token 絕對過期回來 reload → 不停登入頁、無殘留 401 迴圈。
- [ ] 併發多請求同時撞 401（開多分頁/快速操作）→ 不觸發全 session 撤銷（無 401 風暴）。
- [ ] IdP cookie（4h）過期後回來 → 明確導去 www 重登，非卡死。
- [ ] F12：`localStorage.user_info` 有值、Header 非「訪客」、Network 無殘留 401 迴圈。

> 多數衰變狀態 headless/無痕無法代行 → **owner 真人複驗是必要關卡**（本清單提供明確標的，非「感覺一下」）。

---

## 8. 結構性防護（fitness audit）

**現有（step 64 `auth_state_ssot_audit.cjs`，2026-07-03）**
- **Rule C（I2）**：401 handler 內破壞性動作而同檔未引用 session 狀態守衛 → RED。
- **Rule D（I3）**：有 POST `sso-bridge` 卻未持久化 user_info → RED。

**建議新增（Layer 2 / P1-P3 落實後）**
- **Rule E（I10/I11）**：跨檔掃 IdP cookie TTL / 消費端 session TTL / idle timeout 三值一致（drift → RED）。
- **Rule F（I6）**：偵測未經統一 401 handler 的 raw fetch/裸 axios 對業務端點（無 session 守衛）→ YELLOW。

---

## 9. 跨專案落地現況與待辦（lvrland / pile / DigitalTunnel）

| 面向 | Missive（治本後） | lvrland | pile |
|---|---|---|---|
| SSO bridge | interceptors + sessionStore | vendored ck-sso-js v2.0 ✅ | **自寫 inline（未用 lib）**⚠ |
| I1 單一權威狀態（sessionStore SSOT） | 半 | ✗（authStore） | ✗（authStore） |
| I2 破壞性清除須 anonymous 守衛（Rule C） | ● | 部分（authStore 有、client.ts 無）⚠ | **✗ 多處無守衛** ❌ |
| I3 bridge 成功持久化 user_info（Rule D） | ● | ●（LoginPage onSuccess 寫）✅ | **✗ reload 前不寫、靠 probe 兜底** ❌ |
| SessionGate / useAuthGuard | ● | ✗ | ✗ |
| step 64 + Rule C/D fitness | ● | ✗ | ✗ |
| I2 傳態非破壞（checkAuth） | ● | ●（明確標 Missive L74）✅ | 部分（僅 useAuthSync）⚠ |

**落地步驟（照 §6 P4）**
1. **pile 最高同型風險**（同 Missive 07-03 復發前）：補 I2（401 加 anonymous 守衛）+ I3（bridge 持久化 user_info），建議改用 vendored ck-sso-js 消除自寫分歧。
2. **lvrland**：只差把 `client.ts` 401 收攏到 Rule C 守衛（bridge/I3 已合規）。
3. 兩專案移植 `auth_state_ssot_audit.cjs` step 64（`install-template-to.sh` 可跨 repo 部署）。
4. 採 §7 兩層驗證協定，尤其 Layer 2「編輯途中 token 過期存檔」。
5. **禁止**無痕/headless 通過就宣稱真活。

---

## 10. 一句話總結（v2）

> **SSO 反覆回歸 ＝ 兩層結構性缺口的交集：Layer 1「乾淨登入 vs 帶殘留復原」是兩套路徑、後者多入口且散落破壞性副作用；Layer 2「SSO 對後端根本沒有無痛續命路徑」（stateful session + rotation 併發互殺 + 唯一復原是整頁 reload + 跨 repo TTL 無 SSOT）。歷次只修 Layer 1 的某一條復原分支、又只在無痕驗 happy path，於是明日換個衰變狀態就走到另一條沒修的路。治本 ＝ 兩層共同設計：前端六不變式（I1–I6）＋ 後端五不變式（I7–I11：無痛續命 / rotation 併發寬限 / 跨 repo session TTL 單一 SSOT）＋ 直掃基礎設施內部的 audit ＋ 覆蓋兩層衰變狀態的真人驗證協定。**
