# Tier 3 跨 repo 刻意分歧 Registry（Portfolio SSOT）

> **建立**：2026-07-25（owner：「太多無標準化與潛在風險議題」→ 決定先砍噪音）
> **目的**：**把「刻意 per-repo 分歧」寫死**，讓 audit / 覆盤 / 未來 session **停止對它們重複報警**。
> **核心洞察**：portfolio 的「議題清單」裡有一大部分**不是問題**，是刻意差異被誤報為 drift/風險。
> 分清「刻意（Tier 3，別再碰）」vs「真 drift（待收斂）」= 立刻縮短議題清單、止住覆盤疲勞。
> **每條均已核實**（2026-07-25 讀碼確認），非臆測。

---

## 0. 標準化分層（治理語彙 SSOT）

| Tier | 定義 | 機制 | 違反處置 |
|---|---|---|---|
| **Tier 1** | import 式單一源共享 | wheel（`ck_auth`）/ npm（`@ck-shared/*`） | 版本偏移 = CI 硬失敗（fitness step 70/71） |
| **Tier 2** | 共享契約 + conformance（非整檔實作） | 各 repo 獨立實作 + audit 守契約 | 契約破壞 = audit RED（step 72/73） |
| **Tier 3** | **刻意 per-repo，不標準化** | 各 repo 自管 | **不報警**（本 registry 登記，audit exempt） |

> **鐵律**：登記於本 registry 的分歧 = **Tier 3 刻意**。任何 audit / 覆盤 / session **不得**把它們列為 drift、風險、或待辦。若要挑戰某條「其實該標準化」，改本 registry（附理由）再動，不得逕自「發現→報警→修」。

---

## 1. Tier 3 刻意分歧（別再報警）

### 1.1 後端執行模型（async vs sync）— 根源性
| repo | 模型 | 佐證 |
|---|---|---|
| Missive / DigitalTunnel | **async**（AsyncSession/await） | `async def sso_bridge` |
| lvrland / pile | **sync**（Session） | `def sso_bridge` |

**為何刻意**：各 repo 原生技術棧選擇，改寫 = 全 repo 重構風險。**驅動下游所有 auth async/sync 分裂**（sso_bridge/csrf/session）。→ 這是「為何 auth 不能單一 flow 共享」的根因，非 drift。

### 1.2 User model 位置
| repo | 路徑 |
|---|---|
| Missive | `app.extended.models.User` |
| lvrland / pile | `backend.app.models.user.User` |
| DigitalTunnel | 自有（UUID PK paradigm） |

**為何刻意**：各 repo 領域模型獨立演化、DB schema 不同。**Tier 3，勿統一。**

### 1.3 稽核服務
| repo | 服務 |
|---|---|
| Missive / pile | `AuditService.log_auth_event` |
| lvrland | `LoginHistoryService.log_event`（不同介面） |
| DigitalTunnel | 無（none） |

**為何刻意**：各 repo 稽核需求/schema 不同。**Tier 3。**

### 1.4 SSO user-not-found 政策（安全政策，最易被誤報）
| repo | 行為 |
|---|---|
| Missive / lvrland | **404**（須先原方式登入過，不 auto-provision） |
| pile | **auto-provision pending 帳號**（2026-06-02 incident 修：SSO 員工幾乎全 404） |
| DigitalTunnel | auto-create（role 僅首次套用） |

**為何刻意**：安全政策差異。pile 是唯一 auto-provision。詳見 `SSO_BRIDGE_DIVERGENCE_MATRIX.md §3`。**Tier 3，強行統一 = 過度抽象 auth（HH-2）。**

### 1.5 SSO session TTL
| repo | TTL |
|---|---|
| Missive | **8h**（`SSO_ACCESS_TOKEN_EXPIRE_MINUTES`，L74/L78 編輯途中過期止血） | 
| lvrland / pile | 預設 |

**為何刻意**：主產品編輯場景長、止血需求特有。⚠️ **例外**：與 IdP cookie TTL 的對齊屬 Tier 1 契約（見 I10/L80，跨讀 CK_Website callback.ts）——那個要對齊，但**各消費端之間**的 TTL 差異是 Tier 3。

### 1.6 DigitalTunnel auth paradigm
- **不檢 `has_system_permission`**（政策：任何已驗證 CK 員工皆可進）
- **bearer/XOR token paradigm**（`dev_tokens`/`service_token`，非 cookie-session）

**為何刻意**：DT 產品定位不同。conformance audit 已 documented-exempt（C3/C4）。**Tier 3。**

### 1.7 CSRF redis import 路徑（cosmetic）
| repo | 路徑 |
|---|---|
| pile | `unified_redis_client`（直接） |
| lvrland | `redis_client`（相容包裝，re-export 同一 UnifiedRedisClient） |

**為何刻意**：同一 client、不同 import 慣例。csrf drift audit（step 73）正規化此差異、其餘須逐行相同。**Tier 3（此 1 行）。**

### 1.8 前端共享套件消費模式
| repo | 模式 |
|---|---|
| Missive | `file:` direct（monorepo sibling 可及） |
| lvrland / pile | vendored-in-context（`.shared-*` 複本，Docker build context 限制） |

**為何刻意**：Docker build context 無法及 sibling（2026-07-23 實證）。canonical 仍單一源（`shared-modules/*`），drift 由 step 71 守。**Tier 3（消費模式），非 drift。**

---

### 9. SOUL.md：坤哥（Missive）vs meta（Hermes/AaaP）＝不同意識體，非鏡像

| 端 | 檔案 | 身分 |
|---|---|---|
| Missive | `wiki/SOUL.md`（5246 chars） | **坤哥** —— Missive 平臺的意識體 |
| Hermes 生效檔 | 容器 `/opt/data/profiles/meta/SOUL.md`（8806 chars） | **meta** —— AaaP 的整體大腦 |
| Hermes 部署包 | `CK_AaaP/runbooks/hermes-stack/SOUL.md`（5513 chars） | 對應 root `/opt/data/SOUL.md`，**不生效** |

**為何刻意**：ADR-CK-003 意識體聯邦（2026-06-03）明確區分「各平臺後端各有會成長的意識體」
與「meta profile ＝ AaaP 整體大腦」。**兩者本來就不該相同**。

**兩個必須知道的陷阱**（2026-08-02 查證）：
1. `soul_mirror_drift_check` 的前提寫於 2026-04-25（早於 ADR-CK-003），假設兩者應為鏡像，
   長期報 🔴 SEVERE。已改判定基準為「Hermes 端人格檔是否還可用」，不再以一致性為準。
2. `scripts/sync/sync_soul_to_hermes.sh` 的目標是**不生效的 root 檔**
   （`active_profile=meta`）。**不要跑它**：寫過去無效；若有人照著同步進 meta，
   會蓋掉 6/16 加入的業務查詢強制規則（baseline GO 的關鍵）。

**另有實證支持不要動 Hermes 人格**：6/16 實測 SOUL 強化（D-α wiki-first 回憶／D-β 反捏造）
為**負向** —— qwen 仍捏造，且觸發慢檢索 113-280s，已還原並立法
「瓶頸在模型強度不在 prompt，勿再投 prompt 層」。這與 `AI_ROLE_REPOSITIONING`
「對話智慧夠用即可、停止加碼」的方向一致。

---

## 2. ⚠️ 真 drift（**不是** Tier 3，待收斂 — 別誤放進上表）

分清這些，才是砍噪音的另一半：以下是**真的該處理**，勿因本 registry 而誤判為「刻意」。

| 項 | 狀態 | 去向 |
|---|---|---|
| lvrland `env.ts` 散落（Missive/pile 各有單一 `config/env.ts`，lvrland 0 個 = 散在多處） | 真 drift | Tier 2 候選：先各自集中化再共享，focused session |
| csrf 真 import-式收斂（目前僅 drift audit 守，非單一源） | 部分（Tier 2 守契約） | 若要 Tier 1：獨立 `ck-csrf` 套件（避 ck_auth wheel 波及主產品），focused session |
| shared-modules 96 未提交（chart-components/navigation-module 等舊 UI 模組） | 他人 WIP | 非本 portfolio auth 範圍，owner 自決 |

---

## 3. 使用方式（給未來 session / audit）

1. **覆盤發現某跨 repo 差異** → 先查本 registry。列於 §1 = **刻意，不報警、不列待辦**。
2. **不在本 registry** → 才判定為 drift，進 §2 或修。
3. **要主張某 §1 條目「其實該標準化」** → 改本 registry（附理由 + 影響 + owner 決策）再動，禁逕自 find→patch。
4. **新 audit** → 對 §1 條目應 exempt（如 conformance audit 的 `GUARD_EXEMPT`），並在此登記。

---

## 4. 相關
- `SSO_BRIDGE_DIVERGENCE_MATRIX.md`（sso_bridge 專項，§1.4 展開）
- `MODULARIZATION_CROSS_PROJECT_STRATEGY.md`（Tier 1/2/3 策略、缺口 C/D、L58 範本污染）
- `scripts/checks/sso_bridge_conformance_audit.py`（step 72，DT exempt）
- `scripts/checks/csrf_service_drift_audit.py`（step 73，redis import 正規化）
