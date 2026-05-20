# 策略級體檢報告 — 2026-05-19

> **覆盤類型**：策略級體檢（非戰術 backlog）
> **基準**：CK_Missive v6.10 P1（5/18 落地後 1 天）
> **方法**：4 平行專家代理（service / DB+RLS / 跨切面 / frontend+跨 repo）+ owner 文件追蹤
> **承接**：[`RETRO_20260515_BACKLOG.md`](RETRO_20260515_BACKLOG.md) + [`RETRO_20260515_UPDATE.md`](RETRO_20260515_UPDATE.md)
> **核心訊息**：v6.10 P1「真模組化」門面已立，但內部接通仍真空 — 抽象層被自己繞過，監督機制自己成孤兒 daemon

---

## §1 體檢總覽（一張表）

| 層 | 5/15 早盤 | 5/15 下午 | **5/19 本次** | 趨勢 | 主因 |
|---|---|---|---|---|---|
| Service 拆分 / DDD | GREEN+ | GREEN+ | **GREEN+** | → | 真實 entropy < 3%；新增 12 facades / 4 Ports skeleton |
| **Facade 利用率** | — | — | **🔴 RED 14%** | NEW | **9/12 facade 零 caller / 4 Ports 0 caller** |
| Repository / DB | YELLOW | YELLOW+ | **YELLOW** | → | D1 wiring 真活；裸 user_id 仍 42 處 |
| **RLS 真接通** | RED | RED | **🔴 RED 0/12 contexts** | → | RLSPort 建好 0 caller；Calendar 4 處最高炸雷風險 |
| 觀測棧 / 錯誤合約 | YELLOW- | YELLOW- + E1/E2/E3 | **🔴 RED-** | ↓ | 5 RED 環節中 2 條從 yellow-fail 退化為 hard ERROR |
| 認證 / RLS（業務面） | RED | RED | **RED** | → | 同人多帳號分支訪問仍會「資料消失」 |
| Frontend | GREEN- | GREEN- | **YELLOW** | ↓ | 2 useEffect+apiClient 違規未修；endpoints 從 124/130 → 271/284 反向惡化 |
| ADR 治理 | GREEN- | YELLOW | **GREEN-** | ↑ | 5/18 ADR TEMPLATE 已加 §How to apply A-E + L1-L4 ✓ |
| AI 推理韌性 | — | YELLOW | **YELLOW-** | ↓ | shadow p95 64.6s → 90.0s；success 97.96% → 93.33% |
| 跨 repo / FQID | — | YELLOW- | **🔴 RED** | ↓ | consumers.yml 6 中 1 個真採用；ck-auth frontend 即將重演 LR-015 |
| **Pipeline 整合度** | — | — | **🔴 RED 50%→ERROR** | ↓ | Orchestrator 自身 timeout > 300s；自我成 dead loop |

**體檢結論**：v6.10 P1 把「該長什麼樣」搭得很完整（contracts/ + ck-auth + 32 fitness step + ADR-0036），但**新建抽象層全成空殼**，老問題（RLS 42 處 / silent except 311 處）沒動。**散修速度 < dead 累積速度**。

---

## §2 結構性問題 5 大發現

### §2.1 **空殼抽象（Empty Abstraction）反模式** — v6.10 P1 最大破口

ADR-0036 落地 24 個 contracts/ 檔案、4 Ports + 4 DefaultAdapters + 12 Facades + 59 public methods，但：

| 抽象層 | 真實 caller 數 | 狀態 |
|---|---|---|
| 12 Facades | **9 個 0 外部 caller** / 3 個 ≤ 3 caller | Memory/Wiki/Integration 3 個有用，其餘是 facade-of-zero |
| 4 Ports（RLSPort/AuditPort/MessagingPort/CachePort）| **全部 0 production caller** | 介面建了無人 inherit |
| 4 DefaultAdapters | facade 內 hardcode `DefaultMessagingAdapter()` | **Facade 繞過 Port 直 import Adapter** = 違反 hexagonal 本意 |

**Evidence**（`backend/app/services/contracts/facades/integration.py:52-54`、`audit.py:29`）：
```python
def send_line_message(...):
    from app.services.contracts.adapters.messaging_default import DefaultMessagingAdapter
    msg = DefaultMessagingAdapter()  # ← 繞過 MessagingPort 直接綁 default impl
```

**這是 LR-015 ck-navigation「真採用 1.0 → 19 TS errors」的鏡像版**：建好門面 + 自評通過，但內部接通是 0。**ROI = 0 × 24 檔 = 0**（L31 lesson 第二次活案例）。

### §2.2 **RLS Half-Wired 第三次倒數** — Calendar 是引爆點

| 5/15 揭發 | 5/19 實況 |
|---|---|
| services/contract/core.py + document/core.py 兩處用 `apply_*_rls`，其餘 32 service 裸 `user_id ==` | **零變化** + RLSPort 新建但 0 caller |
| audit 「0 risks」是 narrow regex 假乾淨 | audit 已升級偵測 repo 層（5/18 P0-2），但**無 CI enforce + 無 baseline lock** → 5/15 揭發後 13 天再次躺平 |

**42 處裸比對熱區**（按炸雷可見性排）：
1. `calendar_repository.py` L355/475/508/537 — `DocumentCalendarEvent.created_by == user_id` ×4
2. `notification_repository.py` ×8 — `SystemNotification.user_id == user_id`
3. `session_repository.py` ×7、`staff_certification_repository.py` ×5、`project_staff_repository.py` ×6
4. `erp/ledger_repository.py` + `erp/expense_invoice_repository.py` + `ai_search_history_repository.py` 各 ×1

**炸雷觸發條件**：李昭德類同人多帳號（canonical=hotmail / alias=gmail）登入 gmail → 查「我建立的行事曆事件」→ **hotmail 那邊建的事件整批消失**。比 ADR-0025 第一次（公文）更明顯，因為 Calendar 直接綁晨報。

### §2.3 **Pipeline Orchestrator 自我成 Dead Loop** — 監督機制的諷刺

5/16 OPTIMIZATION_PIPELINE.md 列 10 條環節 5 RED。**4 天後（5/19）追蹤 5 條 RED 狀態**：

| 環節 | 5/16 | 5/19 |
|---|---|---|
| 3 Shadow Observability | p95=64.6s success=97.96% | **p95=90.0s success=93.33% — 惡化** |
| 4 Diary → Autobiography | 0 檔（7 diary days） | **仍 0 檔**（28→29 days 累積） |
| 6 Fitness → Owner | 37P/5W/4F | **fitness timed out >300s — 退步為 ERROR** |
| 7 Capability Audit | dead=107 | **JSON parse fail — 退步為 ERROR** |
| 10 7d Follow-up | 完全未實作 | `commit_post_check_scheduler` 仍不存在 |

**Orchestrator 自身在 5/19 已掛**（環節 6 + 7 從 yellow-fail 退化為 hard ERROR）。**這是 LR-015「真採用 1.0 + 自己沒測」的監督機制版本**：建了 daily orchestrator 但 push channel 未接，自己掛掉也沒人收到通知 → 標榜 5 RED 修復實際無人看。

### §2.4 **散修速度 < Dead 累積速度** — 7 天淨退化

| 指標 | 5/12 v6.9 | 5/15 揭發 | 5/19 |
|---|---|---|---|
| `silent except Exception` 檔案 | 72 | 72 | **131**（+82%）|
| occurrence | — | 1325 | **311**（重複統計差異，仍 +N 處新增） |
| endpoints/ai.ts 行數 | 124 | 124 | **271**（+118%） |
| endpoints/erp.ts 行數 | 130 | 130 | **284**（+118%） |
| Shadow p95 | 58s | 64.6s | **90.0s**（+38%） |
| consumers.yml `real_installations` | 0 | 0 | **1**（lvrland ck-navigation v2.0）|

**結論**：散修補丁速度跟不上業務新增 dead 速度。**v6.10 P1 13 散修補丁全綠** + **24 contracts skeleton** 的整體 ROI 不及「修 calendar 1 處 RLS + 接 orchestrator push channel + 拆 endpoints/ai.ts 二級分類」3 件 hard fix。

### §2.5 **ck-auth Frontend 即將重演 LR-015（CRITICAL）**

ADR-0036 §Lessons 自承 ck-navigation v1.0 → 19 TS errors 諷刺對齊事件，但 **ck-auth v1.0 frontend 完全重演同形 pattern**：

| 對比點 | ck-navigation v1.0（已爆） | ck-auth v1.0（即將爆） |
|---|---|---|
| frontend artifacts | 14 components + 8 hooks | **6 components + hooks** |
| 業務 ROUTES hardcode | useMenuItems 30+ Missive ROUTES | **withAuth.tsx + useAuthGuard.ts import `ROUTES` from `router/types`** |
| Transitive deps | 5 層未列 | **5 層未列**（`../../hooks/services/config/utils`） |
| manifest `transitive_dependencies` 欄位 | 無 | **無**（schema v1.0，未對齊 v1.1） |
| 自評 portability | 1.000 | **87%**（dry-run 兩 repo） |
| 真採用驗證 | dry-run 100% → 19 TS errors | **dry-run 87% → 等用戶 force install 必爆** |

**ADR-0036 「待補」項目**：
- [ ] Owner 真 `--force` 安裝實測（WIP）
- [ ] CHANGELOG v6.10 P1 條目（未補）
- [ ] Prometheus contracts/portability gauge（未補）
- [ ] 5/25 lvrland 真試用回報（pending）

**5/25 大概率重演 5/18 LR-015**。預測：**第一個 force install 必爆 ≥ 10 TS errors**。

---

## §3 風險與漏洞（按炸雷可能性排序）

### 🔴 R1 — Calendar RLS Dormant 第三次（高 / 隨時）

- **位置**：`calendar_repository.py` L355/475/508/537
- **觸發**：staff 同人多帳號登入 alias 那邊查行事曆
- **影響**：建立於 canonical 帳號的事件整批消失
- **預估雷時**：任何具 alias 的 staff 嘗試 cross-account 查行事曆即觸發
- **守護現況**：alias_rls_audit 已升級偵測但**無 CI enforce + 0 baseline lock**

### 🔴 R2 — ck-auth Frontend Force Install 必爆（高 / 5/25 前）

- **位置**：`shared-modules/ck-auth/frontend/{components/withAuth.tsx, hooks/useAuthGuard.ts}`
- **觸發**：lvrland / PileMgmt owner 跑 `install.sh --force`
- **影響**：>= 10 TS errors + pre-commit hook 阻擋 + 「ck-auth 87% portable」標榜不攻自破
- **預估雷時**：ADR-0036 D 項目 5/25 lvrland 試用 = 大概率引爆

### 🟠 R3 — Pipeline Orchestrator 自我 Dead Loop（中 / 已發生）

- **位置**：`backend/app/services/optimization_pipeline_orchestrator.py`
- **觸發**：每日 03:00 cron 自動跑
- **狀態**：**5/19 已 timeout > 300s + capability_audit JSON parse fail**
- **影響**：監督機制自己壞，10 條環節健康度無人收到通知；標榜「daily digest」是 stdout 孤兒
- **諷刺等級**：LR-015 同型 — 建好監督機制 + 自己沒測

### 🟠 R4 — Token Budget 無 Hard Cutoff + Triple-provider Silent Fallback（中 / 隨時）

- `_generate_fallback_response` 在 ai_connector.py:449,773 兩處仍**無 counter**（5/15 揭發後 4 天未動）
- `token_usage_tracker.record()` budget_exceeded=True **0 caller** 用此值拒絕
- llm_quota_check_job 6 小時跑一次
- **觸發**：Groq 429 + NVIDIA 配額 + Ollama OOM 三 CB 同時 OPEN → 走 6 關鍵字罐頭回應，InferenceNoCompletions alert **看不到**

### 🟡 R5 — pgvector model_version Schema 漂移風險（低 / 月級）

- 5 個 Vector(768) 表全無 model_version 欄位
- 換 embedding model（nomic-embed → bge-m3）會 silent drift：舊向量留著但語意空間不同，cosine similarity 全部誤判
- 修法：1 個 alembic migration 加 column + backfill default — 半小時內可清

### 🟡 R6 — Scheduler 04:00-06:30 同分時段 + 無 max_runtime（低 / 月級）

- 04:30 + 04:35 已 5/18 P1 commit 錯開，但 batch 跑超 5min 仍會撞
- 11 job 集中時段、APScheduler `misfire_grace_time` 預設 1s → 過時間 silent skip
- 修法：jitter=300 + max_runtime guard

---

## §4 ROI / 治理效率（建表 vs 用表的量化差距）

L31 lesson「建表不等於用表」在 v6.10 P1 出現第二代鏡像：

### §4.1 v6.10 P1 抽象層投資 ROI 表

| 投資項目 | 投入（檔案 / 行數）| 真實使用率 | ROI |
|---|---|---|---|
| 24 contracts/ files (4 Ports + 4 Adapters + 12 Facades) | ~1500 lines | Facade 14% / Port 0% / Adapter 100%（但被 facade 繞過 import） | **<10%** |
| ck-auth shared-module 26 files | ~3000 lines | 真採用 0 repo（lvrland/pile/AaaP 都 pending） | **0%** |
| 5 新 fitness step (28-32) | ~500 lines | step 32 facade_only_check baseline 84 → 78（4 天 -6 處）| **低** — 沒有強制收斂機制 |
| NAMING_CONVENTIONS v1.0 SSOT | 312 lines | step 31 baseline 26 → ??（無 enforce）| **未量測** |
| MODULARIZATION_STANDARDS v1 + CAPABILITY_GOVERNANCE + OPTIMIZATION_PIPELINE 三份標準 | ~1500 lines | PR template 未加 checklist；orchestrator 已掛 | **低** |
| ADR-0036 / ADR-0035 GitNexus / ADR-0034 dynamic role-permissions | 3 ADR | ADR-0035 GitNexus 部署但 agent tool 未註冊 / ADR-0036 12 facade 9 個 0-caller | **30%** |

**累積投資 ~6800 lines + 3 ADR**，**真實業務 ROI < 15%**。

### §4.2 同期 dead capability 累積

- 90 manual+skill tools dead（無人觸發）
- 14 KG entity types dead（0 mention 命中）
- 3 memory loops dead（autobiography 半年 0 檔 / crystals 4 月 0 筆 / proposals 25 天卡）
- 4 alert rule 從未 fire
- ck-missive-bridge skill 仍 tool=1（v6.9 後 4/14 mtime 35 天未動，46 真工具未透出）
- HNSW default/fast/batch 3 檔位 0 caller

**Dead 累積速度 > Activate 速度** — capability_usage_audit 跑了沒人 ABC 決策。

### §4.3 治理效率改善建議

| 改變 | ROI |
|---|---|
| 接 Calendar 4 處 RLS → 修第 1 個真實 RLSPort caller | **極高** — 證明 Port 不是空殼 + 解 R1 dormant + ck-auth/contracts 投資首次兌現 |
| Orchestrator push channel 接 LINE | **極高** — 5 RED 環節同步活 + 防 R3 諷刺 |
| ck-auth v1.0 → v2.0 BREAKING（複製 ck-navigation v2.0 後端 only）| **極高** — 避免 R2 必爆 + LR-015 第三次教訓 |
| 修 2 處 useEffect+apiClient | 中 — 對 GREEN 影響大但業務面無感 |
| 拆 endpoints/types | 低 — 美觀 + 無炸雷風險 |

---

## §5 演進方向（3 個策略級提議）

### §5.1 提議 A — RLSPort 強制接通計畫（ADR-0037 候選）

**問題**：v6.10 P1 建了 4 個 Port 但 0 caller，等於 ADR-0036 自承「真模組化」是空殼。

**策略**：
1. **2026-Q3 Phase 1**：Calendar / Notification / Session / Staff 4 個 repository 強制注入 RLSPort（共 25/42 處）
2. **2026-Q3 Phase 2**：ERP / Taoyuan / AI 系列共 17 處
3. **同步 fitness step**：alias_rls_audit baseline lock + CI enforce → 修一個減一個，禁淨增

**真活定義**：calendar_repository.py 任一處改用 RLSPort + integration test 鎖定 alias group 雙向可見 → 該 commit 7 天後跑 capability audit 看 calendar 業務面有無 friction → **才算 RLS 真接通**。

### §5.2 提議 B — Pipeline Push Channel（ADR-0038 候選）

**問題**：5 RED 環節 4 天淨退步，orchestrator 自身掛了沒人知。

**策略**：
1. **Step 1**：fix orchestrator timeout + JSON parse — 監督本身必須先能跑
2. **Step 2**：接 LINE push 通道（既有 line_bot_service）— 每日 08:00 推紅燈 step + 紅燈摘要
3. **Step 3**：`/kunge/ops` 加 tab `pipeline-health` — 10 環節即時 traffic light
4. **Step 4**：commit_post_check_scheduler 補 — 7d follow-up 自動 verify

**真活定義**：owner 連續 3 天收到 push 訊息 + 至少 1 紅燈被回應 → orchestrator 真活宣告。

### §5.3 提議 C — Shared Package Packaging Policy v2.0（PACKAGING_PATTERN.md）

**問題**：ck-navigation v1.0 + ck-auth v1.0 frontend 連續犯 LR-015 反模式。

**策略**（補完 5/18 已有規則）：
- Rule 9（已存）Frontend UI Component 慎重模組化
- Rule 10（新）Target Path 必須可配置（L36 補登）
- Rule 11（新）**Shared package 內絕不 import 業務 ROUTES / API_ENDPOINTS / 業務 enum**
- Rule 12（新）**真採用嚴格定義 4 件齊備**（install + 編譯 + 啟動 + hook 通過）
- Rule 13（新）每個 ck-* package 必有 `transitive_dependencies` manifest 欄位 + step 34 enforce
- Rule 14（新）**dry-run conflicts=0 ≠ install 成功** — install.sh `--strict` 必跑 consumer tsc + py_compile

**真活定義**：ck-auth v2.0 BREAKING 拆出 backend-only + lvrland force install → exit 0 ✓ → R2 解除。

---

## §6 立即可動 P0（5 項，半天內，按 ROI 排序）

| # | 任務 | Effort | 解 |
|---|---|---|---|
| **P0-A** | calendar_repository.py 4 處 `created_by == user_id` 改用 RLSPort（首個 Port 真 caller） | 1.5 h | R1 dormant + Port 不再空殼 |
| **P0-B** | Pipeline orchestrator timeout + JSON parse fail 修 + 加 LINE push（手動模式即可）| 2 h | R3 諷刺 + 5 RED 環節有人看 |
| **P0-C** | ck-auth v1.0 frontend force install dry-run 驗證 + 若必爆則先標 `INSTALL_PARTIAL_N_OF_4` 防誤宣 | 1 h | R2 預防 LR-015 第三次 |
| **P0-D** | `_generate_fallback_response` 加 1 行 counter（5 min PR） | 5 min | R4 silent fallback 可見 |
| **P0-E** | alias_rls_audit baseline lock = 42（修一個減一個，禁淨增） | 30 min | R1 enforce 不再 silent 累積 |

**合計約 5 h** — 半天可完。**ROI 遠勝 v6.10 P1 任何單一 P 階段的累積投資**。

---

## §7 元教訓（Meta-Lesson）

### §7.1 LR-015 已連續第三次同形變異

| # | 場景 | 「真活宣告」 | 實際 |
|---|---|---|---|
| 1（5/18） | ck-navigation v1.0 | portability 1.000 / dry-run 100% | force install 後 19 TS errors |
| 2（5/18） | ADR-0036 contracts/ 12 facades | accepted L2 / fitness step 28-32 監控 | 9/12 facade 0 caller / Port 0 caller |
| 3（5/19 預測） | ck-auth v1.0 frontend | dry-run 87% portable | force install 仍會爆 |

**共同病灶**：「**建好門面 + 自評通過**」≠「**真接通 + 用戶用到**」。

### §7.2 監督機制自己變空殼

5/15 早盤代理用錯路徑 grep 誤判 D1（RETRO_UPDATE §1 自承）→ 5/16 orchestrator skeleton → 5/19 orchestrator 自己 timeout → 4 天內**監督本身**也成 LR-015 同形反模式。

**Pattern Z 加強**：覆盤代理（含 LLM）回傳「找不到」時，**先驗證搜尋目標存在**再下結論；建好的監督**自己也要 dogfood 1 週才能宣告真活**。

### §7.3 散修 vs 整合的速率失衡

v6.9 → v6.10 P1（5/12 → 5/18，6 天 36 commits）+ v6.10 P1 → 本次（5/18 → 5/19，1 天 374 unstaged files）= **平均 60+ commits/週的散修速度**。

但同期：
- silent except 從 72 檔 → 131 檔（+82%）
- endpoints/ai.ts 從 124 → 271 行（+118%）
- Shadow p95 從 58s → 90s（+55%）
- Facade 利用率 14%、Port 利用率 0%、consumer 真採用 0

**散修速度 < dead 累積速度**，整體系統健康度淨退化。

### §7.4 改善建議：「3 件事優先」原則

每週只做：
1. **1 個 hard fix**（解 1 個 R 級風險，必須 7 天追蹤真活）
2. **1 個 dead 清理**（按 capability_usage_audit 第一名）
3. **1 個 pipeline 接通**（5 RED 環節之一）

**禁做**：新建抽象層 / 新建守護腳本 / 新建標準文件 — 除非該週 3 件事都做完。

---

## §9 自我檢視 — 本報告自身的 7 個缺陷（同型反模式自查）

> 依 ADR-0036 §Lessons LR-015「真活宣告 vs 真接通」精神，誠實列出本報告自身的弱點。
> 不附自我檢視的覆盤報告本身就是 LR-015 候選（建好門面 + 自評通過 + 無 dogfood）。

### §9.1 自相矛盾（最嚴重）

§5 三個 ADR 候選 vs §7.4「禁做新建標準文件」原則：

- §5.B 提議「ADR-0038 Pipeline Push Channel」= 新建標準文件
- §5.C 提議「PACKAGING_PATTERN.md Rule 10-14」= 新建標準文件
- §7.4 自己寫：「禁做：新建抽象層 / 新建守護腳本 / 新建標準文件」

**這份報告自己已是「建門面 + 沒驗證」第 4 個 LR-015 同型實例**。
**修法**：§5 提議 B/C 降級為「P0-A/B/C/D/E 真活 7 天追蹤後再啟動」，不該與 P0 並列。

### §9.2 Effort 估計過度樂觀（3-4 倍）

| 項目 | 我估計 | 真實預估 | 樂觀倍率 |
|---|---|---|---|
| P0-A Calendar RLSPort | 1.5h | 3-4h（含 alias 同人實測 + SQL 效能驗證） | 2x |
| P0-B Orchestrator + LINE push | 2h | 4-6h（含 step timeout / 排版 / 頻率限制） | 2-3x |
| P0-C ck-auth dry-run | 1h | 6-8h 才算真修（v2.0 BREAKING 拆 backend-only） | 6x |
| P0-D counter 1 行 | 5min | **30min（含 alert rule + dashboard panel + 修 drift bug）— 實測** | 6x |
| P0-E baseline lock | 30min | 1.5h（含 baseline file 設計 + pre-commit wire） | 3x |
| **合計** | **5h** | **15-19h（2 個工作日）** | **3-4x** |

§6「5 h 半天清完」是樂觀情境估計，現實必有 R3 監督壞掉的副作用。

### §9.3 ROI 量化方法不嚴謹

§4「ROI < 15%」混淆「**使用率**」與「**ROI**」：
- Facade 14% 是 **caller 覆蓋率**，不是 ROI
- 真 ROI 需要算「投資 ÷ (fix 的 bug 數 + 解的 dormant + 防的 incident)」
- 我沒做這個換算

**修法**：應改寫為「**抽象層真實使用率 14% / Port 利用率 0% / 跨 repo 真採用 0%**」，避免暗示 ROI 已計算。

### §9.4 §3 R1「Calendar 隨時觸發」缺實際量測

**我沒驗證**：
- DB 內當前 staff 有 alias group 的人數
- 過去 7 天 Calendar cross-account 訪問實際發生過嗎
- 是否已有任何 user friction report

「隨時觸發」是**預測式 hyperbole**，證據基礎只是「裸比對存在 + alias 機制存在」。實際炸雷率取決於 `staff with alias 數 × Calendar cross-query 頻率`，可能很低。
**修法**：改為「**隨時可觸發（但實際引爆率待量測 DB staff with alias group 人數）**」。

### §9.5 §6 P0 ROI 排序錯誤（前置依賴未識別）

§6 列 P0-A → P0-B → ... 但 **P0-A 真活定義依賴 capability audit**（§5.1：「7 天後跑 capability audit 看 calendar 業務面無 friction → 才算真接通」），而 capability audit **5/19 已掛**（R3）。

→ 邏輯依賴鏈：**P0-B (修監督) → P0-A (修 RLS) → 7 天追蹤**

正確順序：P0-B 必須優先。但 §6 列 P0-A 在前。**ROI 排序與依賴鏈衝突**。
**修法**：拆「優先順序」與「依賴順序」兩維展開。

### §9.6 §2.4「7 天淨退化」數字 cherry-pick

| 數字 | 原表 | 校準後 |
|---|---|---|
| silent except: 72 → 131 (+82%) | OK 但代理 4 自承「實際 311 occurrence」與 5/15 的 1325 同維度比較才對 | 模糊 |
| endpoints/ai.ts: 124 → 271 | 5/15 retro 124 是「**端點數**」，5/19 271 是「**行數**」 | **混淆** — 不可比 |
| Shadow p95: 58s → 90s (+55%) | 真實退化 | 可信 |
| consumers.yml real_installations: 0 → 1 | **我把改善列在退化欄** | **錯放** |

### §9.7「真活定義」依賴掛了的監督機制

§5 三個提議都用「真活定義 = 7 天追蹤 + capability audit」，但 capability audit **5/19 已 JSON parse fail**（P0-B in_progress 已修 fail-safe）。
→ 我建議的「真活宣告」標準本身是 **mythical capability**（CAPABILITY_GOVERNANCE.md §1.2）。
**修法**：暫用 manual verification（owner 親自 grep + 看 git log）取代 capability audit；待 P0-B 修好 orchestrator 後才用自動化。

### §9.8 修正後的最小可信 P0（取代 §6）

| 排序 | 任務 | Effort | 為何此優先 | 狀態 |
|---|---|---|---|---|
| 1 | **P0-D** counter + alert rule（**附帶**修既有 inference_fallbacks_total/inference_fallback_total drift bug）| 30min | 唯一真實小到不會崩計畫；建立信心 | ✅ **完成** 5/19 |
| 2 | **P0-B** Orchestrator parse-fail 保留 raw stdout + markdown digest 寫入 | 4-6h | 監督本身必須先活 | 🟡 **WIP**（已修 fail-safe + markdown 寫入，timeout root cause 待跑驗證） |
| 3 | **P0-C** ck-auth dry-run + 標 INSTALL_PARTIAL | 1h | 防 5/25 LR-015 第三次 | ⏳ pending |
| 4 | **P0-A** Calendar RLSPort 接通（依賴 P0-B 完成）| 3-4h | 解 R1 + 證 Port 不空殼 | ⏳ pending |
| 5 | **P0-E** baseline lock 42（依賴 P0-A）| 1h | enforce | ⏳ pending |

**合計實際 effort: ~10-13h**（2 個工作日，**不是半天**）。

---

## §10 5/19 新增風險：Docker Volume 不可發生資料遺失

> **觸發**：用戶 5/19 指出「Docker Desktop 升級會清 volume」+「不可發生之錯誤」
> **發現深度**：超越覆盤代理當天 evidence，揭發**平時保險本身也是 LR-015 反模式**

### §10.1 災難狀態盤點（5/19 15:42）

| 資產 | Volume | 內容 | 最新備份（揭發前）|
|---|---|---|---|
| PostgreSQL | `ck_missive_postgres_dev_data` | 1698 docs + 22k KG + 117k mentions + 891 Redis keys | 5/16 02:00（**3 天前**）|
| Redis | `ck_missive_redis_dev_data` | 891 keys（pattern catalog / domain_scores / session）| **從未備份** |
| Ollama models | `ck_missive_ollama_dev_data` | Gemma 4 8B / nomic-embed ~11GB | 從未備份 |
| vLLM cache | `ck_missive_vllm_dev_cache` | Qwen2.5-7B-AWQ ~5GB | 從未備份 |
| shadow_trace.db | host bind mount ✓ | 30 天 query trace | git ✓ |
| wiki/memory/ | host filesystem ✓ | diary/patterns/crystals | git ✓ |

**揭發後即時補救**：
- 跑 `pre_upgrade_backup.sh`（新建）→ PG 79MB custom dump + 76MB SQL.gz + 193MB volume tar + Redis 380KB rdb + 149KB volume tar
- 異地同步 NAS `Z:/03.專案管控專區/.../CK_Missive_PREUPGRADE_20260519/`（272MB）

### §10.2 結構性根因（三重 LR-015 反模式）

| 反模式 | 證據 | 修法 |
|---|---|---|
| **「排程應該在」≠「排程真在」** | `Get-ScheduledTask "*CK_Missive*"` 0 hit；scripts/backup/setup_scheduled_task.ps1 寫了但從未跑（或被移除）| 重建 Task Scheduler 任務 + 7 天 last_run_time monitoring |
| **「sync_enabled 該 true」≠「實際是 true」** | `backend/config/remote_backup.json` 14 天 `sync_enabled: false`，異地備份 0 次 | §1.2 改 true + 加 sync_status alert |
| **「named volume 可用」≠「升級後仍可用」** | 全 docker-compose.infra.yml 用 named volume；Docker Desktop reset 必清 | §1.3 bind mount 切換 |

**5/12 0B backup 事故**：`backups/database/ck_missive_backup_20260512_020000.sql` size=0，**pg_dump 失敗但仍 touch 檔案**。沒人察覺直到 5/19。是 ADR-0028 silent failure 同類事故的備份版。

### §10.3 立即措施（已完成）+ 7 天追蹤

| 項目 | 狀態 | 證據 |
|---|---|---|
| 緊急 4 層備份（PG dump × 2 + Redis rdb + volume tar × 2）| ✅ | `backups/database/ck_missive_PREUPGRADE_20260519_154227.dump`（79MB）等 |
| 異地同步 NAS Z | ✅ | `Z:/.../CK_Missive_PREUPGRADE_20260519/` 272MB |
| `pre_upgrade_backup.sh` 可重複跑 | ✅ | `scripts/backup/pre_upgrade_backup.sh`（96 行）|
| `restore_from_volume_tar.sh` 災難復原 | ✅ | `scripts/backup/restore_from_volume_tar.sh`（102 行）|
| SOP runbook | ✅ | `docs/runbooks/docker-desktop-upgrade-sop.md`（9 段）|
| Task Scheduler 重建 | ⏳ owner 須 admin 跑 | `powershell -ExecutionPolicy Bypass -File scripts\backup\setup_scheduled_task.ps1 -BackupTime "02:00" -RetentionDays 14` |
| `sync_enabled: true` | ⏳ owner 決定 | `backend/config/remote_backup.json` |
| Named volume → bind mount | ⏳ owner 決定（停機 5min）| SOP §1.3 完整遷移步驟 |
| backup script 加 `[[ -s file ]]` 0B 檢查 | ⏳ P1 | 防 5/12 同類事故 |

### §10.4 對 §1 體檢總覽表的影響

新增一層健康度：

| 層 | 5/19 早盤 | 5/19 Docker 危機後 | 主因 |
|---|---|---|---|
| **基礎建設備份**（新欄）| — | **🔴 RED → 🟡 YELLOW**（已補緊急備份）| Task Scheduler 不在 / Redis 0 備份 / Named volume 高風險 |

### §10.5 元教訓（補 §7 第 5 條）

**§7.5 「平時保險也是 LR-015 反模式高發區」**

過去討論 LR-015 都聚焦「**新建抽象層 + 自評通過**」，但 Docker volume 危機揭發「**平時保險 + 從未驗證**」是同型反模式：
- 寫了 `db_backup.sh` 但沒驗證 Task Scheduler 真活
- 寫了 `remote_backup.json` 但 `sync_enabled: false` 14 天無人察覺
- 用了 named volume 但沒驗證升級情境下會清

**Pattern Z 加強版**：除 `dogfood 1 週`規則外，**所有「保險機制」必每月跑一次 restore drill**（real restore，非假設）才算真活。本月 5/19 危機是 first restore drill。

---

## §12 Post-P0 整體系統覆盤（5/19 終盤 evidence-based）

> 經 P0-D / P0-B / P0-C / P0-A / P0-E 5 件完成 + Docker volume 緊急 + 自我檢視 後的第三輪覆盤。
> 與 §1-§11（早盤 + 中午自查）對比，這是「**首個 RLSPort 真 caller 落地後**」的整合性結論。

### §12.1 4 天時間軸量化（evidence-based）

| 指標 | 5/12 v6.9 | 5/15 早盤 | 5/19 早盤 | **5/19 終盤** | 趨勢 |
|---|---|---|---|---|---|
| RLSPort production callers | 0 | 0 | 0 | **1 (calendar)** | **首個真 caller** ↑↑ |
| RLS 真接通 contexts | 2/12 | 2/12 | 2/12 | **3/12** | ↑ |
| Repository 層裸 user_id == 處 | — | 42 | 42 | **38** (calendar -4) | ↑ |
| alias_rls risks total (audit) | — | ~30 | 29 | **29 (baseline locked)** | enforce ✓ |
| Facade-of-zero | 0 | — | 9/12 | 9/12 | → |
| 78 cross-context imports | — | — | 84→78 | **78** | → |
| pipeline orchestrator | dead | dead | dead | **GREEN 4/5 step + .md digest** | ↑↑ |
| Silent dead alert | 不知 | 不知 | 揭發 1 | **修 1 + 加 1 critical** | ↑↑ |
| Audit false-positive | 不知 | RLS audit 0=假乾淨 | RLS audit | **揭發 2 個機制偏差** | 認知升級 |
| Docker volume backup gap | 不知 | 不知 | 不知 | **3 天 gap → 269+272MB NAS** | ↑↑↑ |
| Task Scheduler 真活 | 假設 | 假設 | 假設 | **揭發 0 hit** | 認知升級 |
| 自我檢視機制 | 無 | 早盤 D1 誤判 | 7 缺陷自查 | **L37/L38 制度化** | 制度化 |

**核心訊息**：4 天散修 ~250 commits + 整合 6h ≈ **散修略勝量、整合勝質**。**P0-A 首個 RLSPort 真 caller 是真模組化分水嶺** — ADR-0036 從空殼變部分真活。

### §12.2 跨層結構性問題優先級重排

#### 🔴→🟠 RLS 半接通（從紅降橘）

| 5/19 早盤 | 5/19 終盤 |
|---|---|
| Calendar 4 處未解 / Port 0 caller / R1 隨時觸發 | **calendar 4 處解 + Port 1 caller + R1 觸發範圍縮 1/5** |

**剩 5 個高優先 RLSPort 接通目標**（v6.11 兩週，依潛在炸雷影響排）：

1. `notification_repository.py` ×8（推播該收到的人沒收到）
2. `staff_certification_repository.py` ×5（憑證到期沒提醒）
3. `project_staff_repository.py` ×6（跨案件人員看不到）
4. `session_repository.py` ×7（活躍 session 列表不對 — 安全敏感）
5. `erp/ledger_repository.py` + `expense_invoice_repository.py` ×2（財務面 cross-account drift）

**Total**：剩 28 處 → v6.11 目標降至 ≤ 15。

#### 🟠 抽象層內部接通真空（最大價值機會）

**Facade ROI 排序**（依「現有 cross-context import 數量 / 接通難度」）：

1. **NotificationFacade**（接 dispatcher + helpers + templates 共 7 import 收斂）
2. **DocumentFacade**（document_calendar/events 內 doc 查詢，剝 calendar→document 依賴）
3. **AIFacade**（ai/agent/orchestrator 內 6 個本地 import → facade）
4. **CalendarFacade**（已修 RLSPort 後最容易，morning_report 內查 calendar）

#### 🟡 觀測 + 監督部分活

| 環節 | 5/19 早盤 | 5/19 終盤 |
|---|---|---|
| 3 Shadow Observability | RED p95=64.6s | YELLOW（修法已備，alert push 待 LINE 接） |
| 6 Fitness → Owner | RED（timeout）| **GREEN 36 P / 6 W / 5 F**（orchestrator 真活）|
| 7 Capability Audit | RED parse fail | **YELLOW (fallback + raw_stdout 除錯)** |
| 4 Diary → Autobiography | RED 0 檔 | RED 仍 0 檔（5 天累積，根因待查）|
| 10 7d Follow-up | RED 未實作 | RED 仍未實作 |

**剩餘破口**：環節 4 autobiography silent fail 5 天 0 檔 + 環節 10 7d follow-up 未實作 = 監督機制下一波修法重點。

#### 🟢 模組化規約已立基

- NAMING_CONVENTIONS v1.0 / ADR TEMPLATE §How to apply / 三件套 standards ✓
- L30-L38（9 條新 lessons，5/16-5/19）✓
- P0-A 模式 = v6.10 P1 後首個 2/2 真活範本（audit 認可 + unit test 鎖定）

### §12.3 路線圖 v6.10 → v6.11 → v6.12

#### v6.10.1（1 週，5/20-5/26）— Owner Action + 真活鞏固

**Owner 必做**（不可委任，admin 權限 / 業務決策）：
- O1 重建 Task Scheduler（admin PowerShell `setup_scheduled_task.ps1`）
- O2 `backend/config/remote_backup.json` `sync_enabled: true`
- O3 評估 named volume → bind mount（30min 停機）
- O4 評估 ck-auth v2.0 BREAKING 拆 backend-only
- O5 升級 Docker Desktop 前再跑 `pre_upgrade_backup.sh`

**Claude 可做**：
- ck-auth v2.0 BREAKING（複製 ck-navigation v2.0 模式）
- RLSPort 接 notification (8) + staff_cert (5) = 13 處
- pipeline orchestrator 接 LINE push（既有 line_bot_service）
- alert drift monthly audit script（防 inference_fallback drift 同型）

#### v6.11（2 週，5/27-6/9）— 模組化第二期

**目標**：cross-context imports 78 → < 55（-30%）
- NotificationFacade 真接通（剝 dispatcher / helpers / templates 7 import）
- DocumentFacade 真接通（calendar→doc 依賴）
- ai/agent/ 40 檔二級拆分（6 個子包）

**配套**：
- transitive_deps_audit fitness step 34 真活 enforce
- consumers.yml 9 條 v6.9 範本進 pending_review

#### v6.12（1 月，6/10-7/9）— v7.0 baseline 達標

| v7.0 指標 | 5/19 baseline | 6 月底目標 |
|---|---|---|
| channel_diversity | 1 (LINE only) | ≥ 4 |
| reference_density_diary_pct | 1.1% | ≥ 50% |
| reference_density_critique_pct | 100% | 100% |
| soul_drift_lines | 57 | ≤ 5 |
| provider_fidelity_gap_pct | 待量測 | < 20% |
| alias_rls_risks | 29 | ≤ 15 |
| facade_utilization | 14% | ≥ 50% |
| port_utilization | 8% | ≥ 30% |

### §12.4 散修 vs 整合 — 本日對抗成績單

| 維度 | 散修（既有 374 unstaged） | 整合（P0 5 項 + Docker） | 勝 |
|---|---|---|---|
| Lines changed | ~17000 | ~750（含 SOP）| 散修量 |
| 解的具體風險 | 0 R | 4 R（R1 / R3 / R4 + Docker）| **整合質** |
| 新建抽象層 | 24 contracts/ + ck-auth 26 | 0（皆只用既有）| 整合自律 |
| Dead capability 累積 | +∞（新建未驗）| -1（calendar Port 真活）| **整合** |
| Backup gap | 0 → 5 天惡化 | 補 3 層保險 | **整合** |
| 自身 LR-015 同型反模式 | +2（ck-auth v1 / contracts 空殼）| -1（自我檢視 §9）| **整合** |

**結論**：散修量大但 ROI < 整合。P0-A 比 24 contracts/ + 32 fitness step + 4 份標準文件加起來 ROI 更高 — 因為前者真接通 1 個 use case，後者 0 use case。

### §12.5 三個跨層整合性建議

#### 建議 A — Single Caller Per Port 週度節奏

每週只挑 1 個 Port × 1 個目標 context 做真接通：
- 5/26 週：RLSPort × notification_repository（8 處最大 + ADR-0025 同源）
- 6/02 週：MessagingPort × line_bot_service（剝 facade 內 hardcode adapter）
- 6/09 週：AuditPort × 6 大 silent except 熱區

**Why**：避免「修 5 個 ports 但每個只 0.5 caller」分散；走 v7.0 port_utilization ≥ 30% 路徑。

#### 建議 B — 監督機制 Dogfood 1 週原則制度化

5/16 orchestrator skeleton → 5/19 才真活 = 3 天延遲。新建監督類型機制必走 7 天 dogfood：
- Day 1: 建好
- Day 2-6: owner 每日跑 1 次（手動 + log），記錄掛掉 / false-positive
- Day 7: 真活宣告，加入 cron / pre-commit / 月跑

**落地點**：`commit_post_check_scheduler`（環節 10，待 v6.10.1 實作）。

#### 建議 C — 「真活宣告」雙指標強制

新功能 / 修法 PR 必達 2/2：
1. Audit / fitness 認可（**token 在邏輯路徑內**，非只 grep 字串存在）
2. Unit test 鎖定關鍵 invariant（如 P0-A 3 個 test 鎖 expand_alias 真調用 + IN clause + lazy singleton）

**範本**：P0-A 是 v6.10 P1 後第一個 2/2 達標案例。後續 RLSPort 接通必照此範本。

### §12.6 三個必避反模式（從本日教訓）

1. **「建好門面 + 自評通過」≠「真接通」** — LR-015 第 4 次（本報告 §5）已主動標記不再重演
2. **「腳本存在」≠「守護生效」** — Task Scheduler 不在 / cron 漏跑 / alert drift 同型
3. **「audit 0 risks」≠「真乾淨」** — audit false-positive ok 揭發後仍需 AST 升級（v6.11 候選）

下個月（6 月）月度 retro 議程加入「**本月有沒有新增第 5/6/7 次 LR-015 同型**」必檢點。

---

## §11 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-19 | v1.0 | 首版 — 5/19 策略級體檢，4 平行代理輸出整合，主軸「空殼抽象 vs 半接通 dormant」對立 |
| 2026-05-19 | v1.1 | 補 §9 自我檢視（7 缺陷自查）+ §10 Docker volume 危機紀實（觸發事件：「不可發生之錯誤」）+ §7.5 元教訓 + 修正 P0 排序與 Effort 估計 |
| 2026-05-19 | v1.2 | 補 §12 Post-P0 整體覆盤（evidence-based）— 4 天時間軸 + 路線圖 v6.10→v6.11→v6.12 + 散修 vs 整合對抗 + 建議 A/B/C 三條跨層整合 + 三個必避反模式 |

---

## 附錄 A：本次覆盤工具鏈

- 4 平行 Agent（code-review × 3 + database-reviewer × 1）
- grep / git status / 文件交叉驗證
- 對 5/15 RETRO_BACKLOG + RETRO_UPDATE 做 time-delta evidence 比對
- 對 v6.10 P1 ADR-0036 自承「諷刺對齊事件」做同形反模式追溯

## 附錄 B：未動但需追蹤的 5 項

1. `wiki/compiler.py` 1899L 單一職責（驗證 OK，不拆）
2. `memory/autobiography.py` 687L silent fail 根因（環節 4，5 天 0 檔）
3. `ai/agent/` 40 檔 12,515 lines 二級拆分計畫（P3）
4. `SLOW_QUERY_THRESHOLD_MS = 5000` 未調為 1000ms（pgvector 1.5s 仍 silent）
5. ADR-0035 GitNexus bridge agent tool 註冊（環節 8）
