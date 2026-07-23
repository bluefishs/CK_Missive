# 模組化與標準化落地策略 — 為何一直無法落實 + 治本路線

> **建立**：2026-07-21
> **緣起**：owner「模組化與標準化是本專案另一核心目標（作為其他專案範本，含設計架構/服務/前端 UI），但一直無法落實 → 後續專案分歧、相同功能也無法移植」
> **觸發實證**：2026-07-21 同一個 SSO refresh 白填修法，被迫**手動搬 4 個 repo**（Missive/lvrland/pile/digitaltwin）——這就是「無法同步修正」的活教材。
> **定位**：不是新增第 6 份標準文件（已有 STANDARD_REFERENCE / MODULARIZATION_STANDARDS_v1 / MODULAR_INVENTORY / CONVENTIONS / REGISTRY），而是回答「**為何有這麼多標準卻一直不落實**」並給可執行的機制治本。

---

## 1. 一句話診斷

> **標準化一直失敗，不是「不會做模組」或「缺文件」，而是三個結構性缺口：機制分裂（前端 import 式／後端 copy 式）＋ 執行不強制（規範是 advisory、drift audit 只偵測不阻擋）＋ 標準化粒度過廣（複製整檔實作而非共享穩定契約，觸發 L58 範本污染被下游拒絕）。**

「文件夠多、落地夠少」本身就是最強證據：問題在**機制與強制**，不在知識。

---

## 2. 現況實證盤點（2026-07-21）

| 面向 | 現況 | 判定 |
|---|---|---|
| **前端共享** | `shared-modules/` = `@ck-surveying/shared-modules` **npm workspace**；各 repo 前端 `"@ck-shared/core": "file:../../shared-modules/core"` **import 式** | ✅ **機制正確**、但採用局部（僅 core/ui-components/site-management 幾個） |
| **後端共享** | `ck-sso-py`/`ck-auth` = **copy 式 vendoring**（`.template` + `install.sh` + `drift audit`） | ❌ **機制錯誤**：改範本不自動傳播、每 repo 各自漂移 |
| **標準文件** | 5 份（STANDARD_REFERENCE/MODULARIZATION_STANDARDS/MODULAR_INVENTORY/CONVENTIONS/REGISTRY）| 🟡 齊全但**advisory**，未 block PR |
| **漂移治理** | `toolkit_sync_audit`/`manifest_drift_audit`/`repository_coverage_audit` 等 | 🟡 **偵測 ≠ 阻擋**（L54「apply ≠ 落實」、ADR-0028「假基線」同族）|
| **前端 UI 一致性** | DetailPageLayout/createTabItem 等規約 + ui-components 套件 | 🟡 規約在、但無 design-token 單一源、無視覺一致性 gate |

**兩個 shared-modules 系統並存**（`D:\CKProject\shared-modules` npm workspace vs `CK_Missive/shared-modules/ck-*` copy 範本）本身就是標準化方法的分歧。

---

## 3. 根因診斷（為何「一直無法落實」）

### 缺口 A — 機制分裂：copy 式無法同步（後端），import 式未擴（前端）
- **copy 式（vendoring）結構上就不可能保持同步**：任何 repo 一改本地副本即漂移；drift audit 偵測到也只是「事後告警」，修正仍要人工逐 repo。本次 4-repo 手動搬 = 直接後果。
- **import 式（npm workspace `file:`）才是對的模型**：改一次套件、所有 repo `import` 立即取得。前端已證可行，但後端完全沒用、前端也只用了幾個模組。

### 缺口 B — 執行不強制：advisory 規範 + detect-not-block audit
- 標準是「草案期 advisory」、drift audit「偵測不阻擋」→ 分歧在 PR 時**零阻力**進 main（ADR-0028 假基線 13 天、L54 apply≠落實同族）。
- **沒有「版本偏移即 CI 失敗」的硬 gate** → 標準化靠人工紀律，紀律必然衰變。

### 缺口 C — 粒度過廣：複製整檔實作而非共享契約（L58 範本污染）
- 過去「強推 132 檔、57% 為本專案特定」→ 下游收到一堆不適用的東西 → **整批拒絕或分岔**（L58/L61 下游反治理）。
- **標準化錯了層**：複製**實作**（脆、耦合各 repo model）而非共享**契約/介面 + 薄套件**（穩、各 repo 實作 adapter）。

### 缺口 D — 最深耦合未解：per-repo AuthService（async/sync 分裂）
- session/token/rotation 綁死各 repo User model + DB session（async vs sync）→ 連「共享」sso_bridge 都得分兩範本。這是「一次修全同步」的最後障礙（詳見 `SSO_RECURRING_REGRESSION_RETROSPECTIVE.md` §11）。

---

## 4. 重新框定目標（改變一切的關鍵）

**不要用「複製實作 + 稽核漂移」追求標準化。** 改為三層：

| 層 | 內容 | 機制 | 例 |
|---|---|---|---|
| **Tier 1 真共享（import 式套件、釘版本）** | 跨 repo 一致且穩定的橫切能力 | **path dependency**（前端 `file:` npm workspace／後端 `pip install -e` 或 uv path dep），**版本釘選 + CI gate** | JWT 驗證、auth/session、API error 契約、design tokens、少數 UI primitives、observability client |
| **Tier 2 契約 + adapter** | 概念一致但耦合各 repo model | **共享介面/schema（federation-contracts）**，各 repo 實作 adapter；用 **conformance test** 驗證符合，不比對檔案 diff | RLS port、repository pattern、morning-report 契約 |
| **Tier 3 明訂 per-repo（不標準化）** | 各域業務邏輯 | 明白**不共享**、audit 不管 | 業務 model、domain service、各域 UI 頁面 |

**核心轉念**：標準化的是**契約（what）+ 薄共享庫（how 的最小集）**，不是整檔實作。over-standardize 是 L58 的病根。

---

## 5. 治本路線圖（漸進、零成本、可逆）

> 原則：**先在一條高價值鏈證明 import 式端到端，再擴**。不做大爆炸重寫。solo/免費 tier 友善（用 path dep，不需私有 registry）。

### Phase 0 — 統一機制決策（本文 = 提案）
- 決定「Tier 1 一律 import 式 path dependency」；後端比照前端 `file:` 模式改 `pip install -e ../shared-modules/<pkg>`（或 uv path dep）。
- 廢止「copy 式 vendoring 作為長期方案」（`.template`/`install.sh` 僅過渡）。

### Phase 1 — ck-auth 端到端證明（高價值，痛點剛驗證）
- 把 `ck-auth`（memory 記 87% portable）+ `ck-sso-py` 合為**單一可安裝 Python 套件**，暴露 **async + sync 兩個 adapter**（解缺口 D），核心 rotation/session/refresh-SSO-fallback **只一份實作**。
- 2 個 repo（Missive async + lvrland sync）改 `import`，跑各自測試證行為不變。
- **成功指標**：下次 auth 修法只改**套件一處** + 各 repo 版本 bump，不再手搬 4 repo。

### Phase 2 — 執行 gate（把 advisory 變 blocking）
- CI/pre-push 新增 **版本偏移檢查**：consumer 釘的 Tier-1 版本落後 registry → **FAIL**（非 warn）。
- **conformance test suite**：每個 consumer 跑「我符合契約」測試（取代檔案 diff drift audit）→ Tier 2 也可驗。
- 對齊既有紀律：ADR-0028「假基線」教訓 = gate 必須真的 block。

### Phase 3 — 前端 UI 標準化（設計一致性）
- 抽 **design tokens 單一源**（色/間距/字級/圓角）成 `@ck-shared/tokens`，各 repo import；建立 3–5 個真 primitive（DetailPageLayout/StatCard/DataTable）。
- 視覺一致性 gate：新頁面未用 tokens/primitives → lint 警示（漸進 block）。

### Phase 4 — 擴展 + 明訂 per-repo zone
- 逐一把 Tier 1 候選（observability client、API error 契約）轉 import 式。
- **明文列 Tier 3 per-repo zone**（各域業務），audit 不再對其告警 → 消 L58 污染、下游不再反治理。

---

## 6. 落地機制細節（務實、零成本）

- **不需私有 registry**：repo 皆 `D:\CKProject` 兄弟目錄 → 前端 `file:` / 後端 `pip install -e ../..`（editable path）即「改一次全生效」，零託管成本。
- **async/sync 不是不能共享**：核心邏輯抽 pure function + 兩個薄 adapter（AsyncSession / Session）包裝，一個套件、一個版本。
- **版本釘選**：Tier 1 套件走 SemVer；consumer 釘 `^1.x`；breaking 需 major + 遷移 note（對齊 CONVENTIONS SemVer）。
- **conformance test 取代 file-diff**：consumer 證「行為符合契約」，容許實作差異、只鎖契約 → 比 drift audit 精準且不脆。
- **可逆**：path dep 出問題可暫時 vendored 回退（過渡期並存）。

### 6.1 前端 Docker build 的 vendored-in-context 標準（2026-07-23 實證修正，@ck-shared/sso 已驗）

⚠️ **實證修正 §6 第一點**：純 `file:../../shared-modules/x` 在**前端 Docker build 內無法解析**——各 repo frontend build `context: ./frontend`，shared-modules 在 context 外、node_modules 被 .dockerignore 排除 → `Rollup failed to resolve import`。host build（如 Missive 的 npm run build）不受此限，但 Docker build（lvrland/pile/DT）受限。

**標準機制（比照後端 vendored-wheel）**：
1. canonical 置 `shared-modules/<pkg>/src`（單一源、納版控）；
2. `sync.sh` 同步進各 repo `frontend/.shared-<pkg>`（**in-context 子目錄**）；
3. Dockerfile **npm install 前** `COPY .shared-<pkg> ./.shared-<pkg>/`；package.json `"@ck-shared/x": "file:./.shared-<pkg>"`；
4. **關鍵**：vendored 進 frontend 子目錄，其 peer（react/zustand）往上解析到 `frontend/node_modules`（順帶解 host tsc）；
5. **drift enforcement**：`sync.sh --check` 比對各 repo vendored copy == canonical（禁手改）；接 CI/fitness。
6. Dockerfile 加 `rm -f package-lock.json`（含 file: 依賴時避容器 npm 'extraneous' 協調錯）。

**驗證協定（每 repo）**：host tsc 0 → isolated Docker build ✓ → 部署 → 公網 200 → 瀏覽器實測（登入/dashboard/console）→ 任何異常即 revert。**已驗**：lvrland（bridge+authStore）、pile（authStore+I2 修復+順修 tokens latent 破損）。

---

## 7. 反面守則（避免重蹈覆轍）

- **禁 over-standardize**（L58）：只把「跨 repo 真一致且穩定」的東西升 Tier 1；不確定就留 Tier 3。寧可少共享、不可污染。
- **禁 advisory-only**：新 Tier 1 資源上線**必同時**接 blocking gate，否則等於沒標準化（ADR-0028 假基線）。
- **禁複製實作當共享**：共享契約/薄庫，不共享整檔業務實作。
- **禁單向強推**：下游採用要有 conformance test 證值 + 遷移路徑，不是丟一包 132 檔（L61 下游反治理）。

---

## 8. 待 owner 決策（策略分岔）

1. **Tier 1 機制**：採「path dependency（前端 `file:` + 後端 `pip -e`，零成本）」？還是要走「發佈到私有 registry」（較正式但有成本/維運）？**建議前者**。
2. **Phase 1 起點**：先做 `ck-auth` 端到端證明（痛點剛驗證、ROI 最高）？還是先做前端 `@ck-shared/tokens`（視覺一致性）？**建議 ck-auth 先**。
3. **強制時點**：Phase 2 gate 要「立即 block」還是「先 warn 一個 sprint 再 block」？**建議 warn 一輪再 block**（給 consumer 遷移窗口，對齊漸進紀律）。

---

## 9. 一句話總結

> **本專案不缺模組化知識、不缺標準文件——缺的是「import 式單一源套件（非 copy 複製）＋ 版本偏移即失敗的 CI gate（非 advisory 稽核）＋ 只標準化契約與薄庫（非整檔實作）」。前端已用 npm workspace 證明 import 式可行；把後端與最深的 auth/session 抽成同型 import 式套件（async/sync adapter 解耦），並讓分歧在 CI 硬失敗，才能「一次修、全同步、可移植」，真正成為其他專案的範本。**
