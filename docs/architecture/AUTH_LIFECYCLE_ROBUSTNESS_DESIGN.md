# Auth 生命週期 Robustness 設計（SSO + 各系統直登皆正常運作）

> **建立**：2026-07-25（owner：「整體 SSO 與各系統自行登入皆要能正常運作」；拒絕「改走 SSO」workaround）
> **觸發 live 事證**：2026-07-27 15:11 owner 直登 Missive `/taoyuan/dispatch`「安全憑證已過期」。
> **性質**：**設計文件（零程式碼、對齊方向用）**。實作待 owner 審核後另啟（TDD + owner 瀏覽器實測 + revert-on-fail）。
> **對應教訓**：L74/L78/**L80**（SSO 反覆回歸底層＝後端 token 生命週期層；前端單點補丁反覆失敗、須兩層共同設計）+ L68/L69（CSRF 死結/併發 race）。

---

## 1. 目標（驗收定義）

**兩條登入路徑 × 全 4 系統，token 過期恢復必須無縫**：使用者閒置逾 access TTL 後回來操作，只要底層 session/SSO-cookie 仍有效，**背景自動恢復、不彈任何錯誤**；只有 session 真的失效才提示重新登入。

- **路徑 A（SSO）**：www.cksurvey.tw 簽發 ck_employee cookie → sso-bridge → 各系統 session。
- **路徑 B（直登）**：各系統自身 Google OAuth → 各系統 session。

### ⭐ owner 決策（2026-07-25）：access TTL 全系統統一 60min
現況分歧（Missive 直登 60 / lvrland·pile 直登 30 / Missive SSO 480）→ **統一為 60min**（直登 + SSO 同值）。
依據：本設計讓 token 過期恢復**無縫**後，SSO 的 8h（480min）止血 band-aid（L74/L78「編輯途中過期」）**變得不必要**——真正的解是「過期即無痛恢復」，非「拉長 TTL 拖延過期」。
> ⚠️ **關鍵排序（不可顛倒）**：**先實作並證實無縫恢復（§2 不變式）＋ owner 瀏覽器實測通過，才可把 SSO 480→60**。否則 SSO 使用者拿到 60min 卻無 robust 恢復 = 直接回歸 L74/L78。**TTL 統一是恢復修法的「果」，非「因」。**

---

## 2. 通用不變式（Invariants — 全系統必守；違反即 bug）

| # | 不變式 | 說明 |
|---|---|---|
| **I1** | **恢復透明性** | access token 過期但底層仍可恢復（有 refresh_token / 有 SSO cookie）時，恢復期間**不得**對使用者彈可見錯誤 |
| **I2** | **恢復單飛** | 併發請求觸發的恢復動作（401→refresh、CSRF 失效→重取）必須**單飛**（一次進行、其餘等待共用結果），禁併發連鑄競態 |
| **I3** | **可恢復失敗先重試** | 可恢復的 auth 失敗（401 過期、403-CSRF 過期/不匹配）必須先**靜默恢復並單次重試**，僅重試仍失敗才彈錯 |
| **I4** | **CSRF 生命週期跟隨 access** | refresh / session 續命時必須**重發 CSRF**（cookie 或 Redis），使 CSRF 不獨立於 access 過期 |
| **I5** | **只在真失效才提示** | 唯有底層 session/SSO 真的失效（refresh 失敗且 SSO fallback 失敗）才顯示「請重新登入」 |

---

## 3. 各系統現況矩陣（2026-07-25 初版；**2026-07-29 讀碼複核修正**；⚠️=違反不變式）

| 面向 | Missive | lvrland | pile | DigitalTunnel |
|---|---|---|---|---|
| access TTL（prod 直登）現況 | 60min | **30min** | **30min** | 24h |
| access TTL（SSO）現況 | 480min(8h) | **同直登 30min**（無獨立 SSO TTL 設定） | **同直登 30min**（同左） | — |
| **access TTL 目標（owner 決策）** | **60min** | **60min** | **60min** | 保留 24h(bearer) |
| CSRF 模型 | double-submit **cookie**（無狀態，max_age 3600；FE 讀 cookie） | **Redis stateful** + **FE 存記憶體**（authStore，`csrfToken` **不持久化**；僅由 auth 回應 header 補水） | 同 lvrland | bearer/XOR（無 cookie-CSRF） |
| 後端 refresh 重發 CSRF（I4） | ✅（`set_auth_cookies`→`generate_csrf_token`） | ✅（`auth.py:174` 共用 helper，login/refresh/sso 皆走） | ✅（`auth.py:178`/`:758`） | N/A |
| FE 401 refresh 單飛（I2） | ✅（`isRefreshing`+subscribers） | ✅ **有**（`inFlightRefresh` module-level 共用 promise，P161 2026-04-18）<br>⚠️**原矩陣記「無」係誤判**（grep `isRefreshing` 未命中其命名，L25 關鍵字陷阱） | ✅（`isRefreshing`+queue） | 待查（低優先） |
| FE CSRF 自癒單飛（I2） | **✅ 已修**（`5bff56d5` FE-1） | **N/A — 無獨立 csrf 端點可補打**（僅能靠 refresh 回應 header 補水）→ 修法異於 Missive，見 §5.2 | 同 lvrland | N/A |
| FE CSRF-403 可恢復重試（I3） | **✅ 已修**（`5bff56d5` FE-2） | **❌ 無**（403 直接 `apiErrorBus.emit('權限不足，請重新登入')`） | **❌ 無**（403 僅顯示後端 detail，不重試） | N/A |
| SSO refresh fallback（I5） | ✅（`try_mint_session_from_sso_cookie`） | 待查 | ✅（401 時嘗試 bridge，`client.ts:101` 註明「對齊 Missive」） | 待查（低優先） |

> **關鍵觀察（07-29 修正版）**：三系統**後端 I4 皆已正確**（refresh 都重發 CSRF）、**401 單飛三系統皆有**。真正共通缺口只有一個——**I3「CSRF-403 視為可恢復」全 portfolio 只有 Missive 修了**。
> 另 lvrland/pile 因 `csrfToken` **不持久化**，頁面重載後記憶體空 → 首個 mutating 請求不帶 header → 403 且無恢復，是同一缺口的第二觸發路徑。
> ⇒ **propagate 工作量比原估小**（不需補 401 單飛），但**修法形狀與 Missive 不同**（無 csrf 端點可單飛補打）。

---

## 4. Live 失效重現（Missive 直登，2026-07-27 15:11 實證）

1. owner 直登（路徑 B）→ 60min token（iat 14:08:13 → exp 15:08:13）。
2. 閒置逾 1h、15:11:40 回來 → token 過期 3.5 分。dispatch 頁併發多個 POST（morning-status / list …）。
3. access + csrf cookie（同 max_age 3600）皆已過期 → 前端 `!csrfToken` → 併發各自補打 → **7ms 內連鑄 2 個 csrf**（違 I2）。
4. `dispatch/list` header(舊 token) ≠ cookie(新 token) → **403 CSRF 不匹配**；未重試直接彈「安全憑證已過期」（違 I3）。
5. `morning-status` → 401（token 過期）→ 401 單飛 refresh 恢復中——但 CSRF 403 已先彈錯（違 I1）。

→ **後端恢復其實正確（refresh 重發 csrf + SSO fallback 都在）；壞在前端於恢復窗口把 CSRF race 洩漏成嚇人錯誤。**

---

## 5. 修法設計（依 CSRF 模型分兩類）

### 5.1 Missive（double-submit 無狀態）— 前端為主，後端已正確
- **FE-1（I2）**：CSRF 自癒**單飛**——比照同檔已驗證的 401 單飛（`isRefreshing`/subscribers）：一次 in-flight `csrf-token` fetch，併發 caller 等待共用結果、統一在其後讀 cookie → header 必等於 cookie。
- **FE-2（I3）**：CSRF-403 視為**可恢復**——回應攔截器攔 403 且 detail 含 csrf → 單飛重取 csrf + 單次重試 `originalRequest`；僅重試仍 403 才進 GlobalApiErrorNotifier。
- 後端：**無需改**（refresh 已重發 csrf、SSO fallback 已在）。

### 5.2 lvrland / pile（Redis stateful + FE 記憶體 csrf）— **07-29 複核後修正：純前端、範圍比原估小**
> 原版誤判「lvrland 缺 401 單飛」「需補 CSRF 自癒單飛」「後端 I4 待確認」——**三點皆已核實不成立**（見 §3 修正矩陣）。

- **後端：無需改**。`auth.py` 共用 auth-response helper 已在 login/refresh/sso 全路徑重發 CSRF（I4 ✅）。
- **FE（唯一缺口 I3）**：回應攔截器攔 **403 且屬 CSRF 類**（依後端 detail 判別）→ **不直接彈錯**，改：
  1. 觸發**已存在的單飛 refresh**（`inFlightRefresh` / `isRefreshing`）取得新 CSRF（由回應 header 自動寫回 authStore）；
  2. 單次重試原請求；
  3. 僅重試仍 403 才進 `apiErrorBus` / 顯示 detail。
  → 形狀是「**403 → 借用既有 refresh 通道補水 → 重試**」，**非** Missive 的「單飛補打 csrf 端點」（兩系統無此端點）。
- **順帶治第二觸發路徑**：`csrfToken` 不持久化 → 重載後首個 mutating 請求無 header 即 403；上述 I3 修法**同時覆蓋此情境**（403→refresh 補水→重試），故**不需**改為持久化 csrf（持久化會削弱 stateful 模型的安全性，不採）。
- **TTL 統一 60min（owner 決策）**：lvrland `ACCESS_TOKEN_EXPIRE_MINUTES` 30→60（注意其寫法為 `30 if prod else 480`）、pile 30→60；需 backend 重啟 + L76 公網 200 複驗。

### 5.3 DigitalTunnel（bearer/XOR，24h）
- 無 cookie-CSRF、24h TTL → 本問題基本不適用；僅需確認 bearer 過期恢復路徑符合 I1/I5。**最低優先。**

---

## 6. Rollout 計畫

1. **✅ Missive 先做（proving ground）— 2026-07-25 完成部署（commit `5bff56d5`）**：FE-1（csrf 單飛）+ FE-2（csrf-403 可恢復重試）+ regression 4/4 + tsc 0 + build + dist served + 公網 200。後端未動（refresh 已重發 csrf、SSO fallback 已在）。
2. **⏳ owner 瀏覽器實測（headless 無法代行）＝ propagate 前硬 gate**：直登 Missive 閒置逾 1h 回來操作 dispatch 頁 + SSO 登入 → 確認不再彈「安全憑證已過期」、背景無縫恢復。**通過後才進 step 3/4。**
3. **通過後 propagate**：lvrland → pile（Redis 模型，需後端 I4 + FE 補齊），DT 最後（低優先）。每系統 isolated + 登入實測 + revert-on-fail。
4. **TTL 統一 60min（恢復證實後才做）**：lvrland/pile 直登 30→60；Missive SSO 480→60（**必須在該系統無縫恢復已證實後**，否則 SSO 回歸 L74/L78）。config env + backend 重啟 + L76 公網 200 複驗。
5. **立通用護欄**：fitness audit 檢查各系統 FE 具備「401 單飛 + CSRF 單飛 + CSRF-403 可恢復重試」+ access TTL=60min 對齊（防未來某系統又缺一角 / TTL 又漂移）。

---

## 7. 反面守則（L80）
- ❌ 不做單層、單系統、單症狀的急補（那是 7 週 ~10 次失敗的模式）。
- ❌ 不用「改走 SSO」當 workaround（owner 明確要求兩路徑都要通）。
- ✅ 對齊本文不變式（§2），各系統按其 CSRF 模型實作，Missive 先證後推。
- ✅ 破壞性驗證：owner 真瀏覽器測「帶殘留狀態回來」的恢復路徑（happy-path 永遠過＝假象，L78）。

---

## 8. 待確認清單（**2026-07-29 讀碼複核：多數已結案**）

| 項目 | 狀態 | 結論 |
|---|---|---|
| lvrland/pile SSO access TTL | ✅ 已確認 | 無獨立 SSO TTL 設定 → 與直登同值 **30min** |
| lvrland/pile refresh 是否重發 CSRF（I4） | ✅ 已確認 | **兩者皆有**（共用 auth-response helper），後端不需改 |
| lvrland/pile FE CSRF-403 是否重試（I3） | ✅ 已確認 | **兩者皆無** ← 唯一真缺口，修法見 §5.2 |
| lvrland FE 401 單飛（I2） | ✅ 已確認 | **有**（`inFlightRefresh`）；原矩陣「無」為誤判，已更正 |
| lvrland SSO fallback（I5） | ⏳ 未查 | pile 已確認有（對齊 Missive）；lvrland 待實作時一併讀 |
| DT bearer 過期恢復路徑 | ⏳ 未查 | 24h TTL + 無 cookie-CSRF，本問題基本不適用，維持最低優先 |
| SSO TTL 與 IdP `ck_employee` TTL 對齊（I10/L80） | ⏳ owner 決策 | IdP 4h vs Missive SSO 8h 仍 drift；TTL 統一 60min 時一併處理（IdP `callback.ts` 屬 CK_Website，需 CF Pages 部署） |

---

## 9. 相關
- `SSO_RECURRING_REGRESSION_RETROSPECTIVE.md`（L78 六不變式 + 衰變狀態驗證協定）
- `TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md`（§1.1 async/sync、§1.5 session TTL 屬刻意；但**恢復機制不一致是真 drift、非刻意**，屬本文修法範圍）
- memory `L80_sso_backend_token_lifecycle_layer` / `L74_sso_bootstrap_race_clobber`
- `interceptors.ts`（Missive FE，401 單飛範本在此）
