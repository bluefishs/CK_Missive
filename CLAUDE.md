# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.69（2026-08-29 晚）/ ⭐⭐⭐**同一個資源被讀取端只認一條路——同族六處，我在同一天內修了四處還漏掉兩處**：指派表的 `project_id` 是 nullable（邀標階段沒有專案可綁，只能寫 `case_code`），而讀取端 `quotation_document`(08-21)／`filing_gap`／`project_repository`／`get_user_accessible_project_ids`／**`check_user_project_access`／`apply_project_rls`** 各自只比 `project_id`。最嚴重的是最後一處是**權限過濾**：實測洪慶忠有 77 件案子而系統只讓他看到 **23** 件（admin 走短路所以看不出來）。⇒ **修完第一處要 grep 整個檔案，不是憑印象數**＋⭐⭐⭐**外層 rollback 擋不住內部自己 commit 的函式**：我在自稱「已回滾」的試算裡**真的成案了 3 件**（owner 刻意撤回待判讀的那批），是 **weekly step 28 的基線 91→88** 抓到的，已依裁示逐表還原（含還原被棘輪的基線，否則錯誤狀態會被記成新常態）＋⭐⭐⭐**公網探的那支 health 根本不查 DB**：`/api/health` 是靜態 dict，postgres 掛掉照樣回 healthy —— 而 L43 的「面向公網必須驗業務量」做在 `/health` 上。**我自己整天拿它當部署驗證**，那個綠燈比我以為的弱＋⭐⭐**「我這條路徑找不到」不等於「資料不存在」**：我 08-20 宣告「115 檔沒有承辦人資訊」，而代碼一直躺在 `legacy_quotation_no` 裡（A坤樹/B慶忠/C元宏/D廷睿/Y慶忠，**owner 講過多次而系統沒記**）⇒ 回填後報價單有承辦 **135 → 250 張**＋⭐⭐**註解指名了來源檔，不代表值是從那裡來的**：手抄的 `TEMPLATE_ITEM_CAPACITY=5` 叫使用者去合併後端輸出得出來的工項，而 tsc 全綠；**同一小時內我還漏掉同檔案的第二份**＋⭐⭐**後端算對了、前端又自己算一次**：報價單詳情頁的總計只顯示稅額，**235 張、9,206 萬元**＋⭐**設定檔整合**：三份 compose 的 14 個 postgres 參數只有 `max_connections` 不一致（而 dev/infra 定義**同一個容器**），且 `postgresql-tuning.conf` 掛載了卻**從未被讀**（Dead Config）—— 已對齊、已重新定位為規格書、weekly 88 三層守門（compose 之間／對規格／**對執行時**）＋⭐**測試庫 schema 落後正式庫 20 個欄位**且**根本沒有 `alembic_version`**（weekly 87）
> （更早版本的一行摘要同樣在 `docs/MILESTONES_ARCHIVE.md`）
>
> **2026-08-30**：⭐⭐⭐**假的事件流比沒有事件流更糟**（L109）——`scheduler_start` 事件加了卻沒有任何消費端（同 `csp_violations_total` 的形狀），我寫消費端時**自己重寫了一份路徑推導**，而**同一個檔案上方 100 行就有 `_cron_events_path()`**，它的註解寫著那條路是錯的。兩次寫錯的形狀不同：①不存在的 `ROOT` 常數 ⇒ NameError，**會吵**；②`parents[2]/"logs"` ⇒ 那個檔**真的存在** ⇒ 不報錯、不回 None、**安靜地讀了錯的檔案回 0**。它接著讓我做出「重啟太密所以 job 跑不到」這個**能解釋症狀的錯誤診斷**——實查才知 repo 根那份是 **pytest 在 host 上寫的**（`CK_LOGS_DIR` 未設），504 筆、當天還在更新、連 detail 格式都是真的，破綻只有 `test_obs_job`。⭐ 第三個錯是**拿 13 小時的觀測窗解釋 69 小時的空窗**（標記昨天才加）⇒ 補 `observed_span()`，凡用重啟史歸因先講「我看得到多遠」。⭐ 修法：消費端改用既有 helper／`longest_uptime_within` 排除「事件流開始之前」那段（首版把 24h 窗算成 10.87h 而真值 2.80h，**把「沒有資料」讀成「沒有發生」**）／窗內 0 筆回 `None` 不回 `seconds`／`conftest.py` 在 import `main` **之前**設 `CK_LOGS_DIR`（實測 504→504 未再增長、隔離檔收到寫入）。存量誘餌檔待 owner 裁示＝A44。⭐⭐⭐**A50 已辦（owner 裁示）＋一個關於「建議」的教訓**：排程改持久化 jobstore（既有 Postgres、零費用），但**光加持久化不夠** —— 讀 APScheduler 原始碼才發現 `replace_existing=True`（本檔 56 處全帶）會在重啟時把存起來的 `next_run_time` **覆蓋成未來**，持久化等於白做。實際修法三件事：持久化＋`_RecoveringAsyncIOScheduler` 只接回**已過去**的觸發＋清理殘留 job。容器內對照：**修法版執行 1 次／原生版 0 次**（對照做了三次才做對——前兩次被排程器執行緒與「我寫成 start() 再 add_job，與正式順序相反」污染）。⇒ **推薦一個修法前要確認它單獨成立**：我上午寫建議時沒讀 `_real_add_job`，那個建議聽起來合理、方向也對，但少了第二件事就是無效的。⭐ 同型複查（owner 交代）：熔斷器走 redis ✓、去重是請求內區域變數 ✓、告警冷卻在記憶體但失敗方向是噪音（不修）、**限流 `Limiter()` 沒有 `storage_uri` ⇒ 每次重啟都送使用者一份新的每日配額**（10,000/日 形同虛設）＝A51 待裁示。⭐⭐⭐**我把「我還沒讀到」寫成了「沒有人讀」並提交進版控**（L115 同日自我更正）：我宣稱走查抓到的 400「沒有人看那份產出」，逐段實查後**閉環是完整的** —— registry 已登記 `fail_key`、watchdog 實跑 exit 2、**02:02:25 queued「🚨 每日檢核 RED」、07:30:14 隨晨報送出**。真正的形狀是**延遲約 10.5 小時**（bug 進版→走查 20:41→daily 02:02→晨報 07:30），而我 09:xx 手動跑 weekly 28「發現」它時，它已經在你當天的晨報裡。⇒ **下結論說某機制沒有接收者之前，鏈路每一段都要拿到證據**（registry→退出碼→通知佇列→送出紀錄），不能因為「我是手動跑才看到」就推論沒人在跑。⭐⭐**判準去問「那個欄位長什麼樣」，而違規是「那個欄位不存在」**（L110）：§2.6 ③ 補守門時量出「0 違規」，而盲區裡躺著兩個真的 —— 發票彙總與營運帳目的年度 Select **開場是空的 ⇒ 歷年混算**（params 裡根本沒有 `year`／`fiscal_year` 這個 key）。⇒ 進場條件改成「**有沒有人在寫入年度**」再問預設值在不在；**用「有沒有人要改它」證明欄位該存在**。判準校準三次全在過寬方向（`year` 字樣命中長條圖 X 軸／別名 `currentYear`／`allowClear` 才是「全部年度」）。⭐ 修的過程差點造出**隱形篩選**：營運頁的 Select 只有 `onChange` 沒有 `value`，加了預設值會變成資料被篩而畫面說未選 —— 比不篩更糟，已一併納入判準。⭐⭐**沒有人在跑的檢核會腐爛，而腐爛的方式你猜不到**（L111）：`.claude/hooks/` 標為「手動執行」的三支**沒有任何 runner 在叫**，且**三支各壞成不同的樣子** —— ①`link-id-check` 的 `-Path "src\**\*.tsx"`：**PowerShell 的 `**` 不是遞迴 glob**，掃得到 **119/604** 個檔**而照樣印 PASS**（假綠）＋一條斷言的型別路徑過期（永久假紅）；②`route-sync-check` 專案根算高一層 ⇒ 每次 exit 1；③`link-id-validation` 報 7 個警告**但 exit 0**、抽查是假陽性。⇒ 「腳本存在 ≠ 有在強制」要再加一句：**「腳本能跑 ≠ 它說的是真的」**。⭐ 修好 `route-sync-check` 後它報「144 vs 41」看似大漂移，實際那份白名單只收導覽選單、本來就不該相等 ⇒ **修好一支壞掉的檢核不等於得到一支正確的檢核**，故刻意不接。§7 已改寫為 `link_id_fallback_audit.py`（805 檔、豁免 React `key=`）＝weekly 90，並自帶解析度下限（掃不到 400 檔直接判不可信）。另：六條無守門的核心規範實查 **8 候選 0 真違規**。⭐⭐**掛上去、會執行、也真的擋過東西的 hook，仍有一半規則從未命中**（L112）：`validate-file-location` 的 6 條規則有 **3 條帶 `^` 錨點**，而 Write/Edit **要求絕對路徑** ⇒ 路徑一律以 `D:/…` 開頭 ⇒ 三條全部落空（實測：絕對路徑 exit 0、相對路徑 exit 2），**而另外三條會命中所以它看起來正常**。同支還漏 `backend/.env`（§2 明文禁止、CI 的 config-consistency 自 2026-03-09 停用 ⇒ 那條規範零強制），已補；14/14 正負向控制全對。⭐ 修時差點放寬成另一個 bug：把 `^test_` 改套到檔名會擋掉合法的 `tests/test_*.py` ——**負向控制必須包含「原本就該放行的東西」**。⭐ 另查出 `careful-guard` 的 CRITICAL／WARNING **分級只存在於資料裡**（兩層都 exit 2 ⇒ `docker system prune` 這類被硬擋），協議有非阻擋通道；**放寬護欄屬 owner 決定，列 A43 不自行改**。12 支掛上的 hook BOM 全部正常。⭐⭐⭐**我昨天「修好」的守衛，修在一個 git 從不執行的檔案上**（L113）：`core.hooksPath = frontend/.husky/_` ⇒ `.git/hooks/pre-commit` 的 **6 項檢查全是死的**（含我 08-29 才修好的 secret guard）。實測 `.pem` 私鑰加進暫存 ⇒ **exit 0 並印「全部檢查通過」**。線索一直在畫面上：我看到的是 `[Pre-commit] 驗證 CK_Missive...` 而我改的那支印 `[Skills Hook] 驗證完成`，**兩段文字不一樣而我讀了好幾次沒對照**。根因＝兩套 hook 系統並存、較新的（husky）靜默勝出。⭐ 接上後才看見第二層：secret guard 的內容層**只警告不阻擋**且要有關鍵字接 `[:=]` ⇒ `sk-ant-…`／`ghp_…`／`AKIA…` **裸字面完全無聲**。已補供應商前綴**阻擋**層（對全 repo 量誤報＝1，為測試假值，已加 `pragma: allowlist secret`；7/7 控制通過）。⇒ **改 hook 前先 `git config core.hooksPath`；修好後要用它真正的觸發路徑驗，不是直接執行那個檔。**長度閘門要不要一併接上＝A45（會擋住 2 支既有 >1000 行的檔）。
>
> **2026-08-31**：⭐⭐⭐**知識庫的向量檢索從來沒有成功過**——`:embedding::vector` 讓參數綁不到（SQLAlchemy 的 BIND_PARAMS 正則有「參數名後面不可接冒號」的否定前瞻，而 PostgreSQL 轉型正是 `::`），**每一次查詢都 HTTP 500**；而端點的「向量失敗退回文字搜尋」兜底寫在更外層 ⇒ **連降級都沒發生**。同型前例就在本 repo（`login_history.py:178` 的註解寫著「asyncpg 不支援 :param::type」並改用動態 WHERE 繞開）——**有人踩過、繞過了，而這裡沒有跟上**。改用 `CAST(...)`，補 3 支不打 DB 的回歸鎖。⭐⭐⭐**專案團隊成員查詢從來沒成功過**：手寫 SQL 是 `FROM project_user_assignment`（**單數**）而資料表是複數 ⇒ `relation does not exist` ⇒ `except` 記一行 log 就 `return []` ⇒ **每個專案看起來都沒有成員，連帶專案通知從未寄出**。成因推測是照著 SQLAlchemy 的 Table 常數名抄——**ORM 的物件名不是資料表名**。⭐⭐**同族第七、八處**：`project_user_assignments` 有兩條互斥綁法（邀標綁 `case_code`／成案綁 `project_id`），報價單抓承辦只認前者 ⇒ 7 張看不到承辦（owner 從 `/erp/quotations/541` 回報）。找到第八處的方法是**全 repo grep 同族**：24 檔命中、粗判準標 6 個單邊、逐一讀完 4 誤報 2 真——「修完第一處要 grep 整個 repo」這次才真的做。⭐⭐**知識文庫最多落後一週**：`.git/hooks/post-commit` 有「重生知識地圖」而 `core.hooksPath` 指向 husky ⇒ **提交時從不重生**，唯一的重生者是週排程；而向量同步 04:45 又跑在地圖重生（04:51）**之前 6 分鐘**。兩者都修，daily 加第 14 步偵測，判準**分兩級**否則會做出一支天天紅的檢核（當天改的文件在 02:00 看必然「未同步」，那是待辦不是故障）。⭐⭐**判準的掃描範圍不得包含描述它的文字**——同日踩四次：教訓區塊吸收檔尾／回歸測試讀到自己註解裡的反例／`add_job` 視窗吃到下一支／**SQL 註解裡的冒號參數被 SQLAlchemy 當成真參數**（編譯後多出 `$1` 而它沒有值）。⭐**權限**：委託單位／協力廠商帳款原掛 `reports:finance:view` 而 **11/12 人持有**（含全部 staff）⇒ 等於全開，改用 `reports:erp:view`（5 admin、0 staff）；報價單改成案主軸（257→164）＋依身分限縮，跨案查詢做成**可授權的擴充點**而非寫死。⚠️ `init_navigation_data.py` 的選單權限是 `"[]"`（所有人可見）而 live DB 是 `finance:view`——**兩邊早就漂移**。⭐**成本／毛利準則的關鍵事實**：`finance_ledgers` 的支出分錄 `source_type` **只有 `erp_vendor_payable` 與 `expense_invoice` 兩種** ⇒ 帳本是應付與核銷的鏡像，**三者相加會重複計算**；且執行中 100 案的**完工日與驗收日各 0 件**，所以「該不該請款」目前只能用天數猜（門檻 365 天是拿公司自己的中位數 205 天校準的，不是拍的）。
>
> **最後更新**: 2026-08-31
>
> **近期重大里程碑**：已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)
> （2026-08-27，v6.59–v6.61 共 46,981 字元；更早的 64 條 08-24 已先移入）。
> **搬移不是刪除**——內容完整保留，只是不再每個 session 載入一遍。
> 教訓的權威來源是 [`docs/architecture/LESSONS_REGISTRY.md`](docs/architecture/LESSONS_REGISTRY.md)。

---

## 專案概述

CK_Missive 是一套企業級公文管理系統，搭載 Hermes Agent 智慧助理：

1. **公文管理** - 收發文登錄、流水序號自動編排、附件管理
2. **行事曆整合** - 公文截止日追蹤、Google Calendar 雙向同步、批次操作
3. **邀標/報價管理** - 案件建案(case_code)、報價紀錄上傳、承攬狀態追蹤、成案觸發
4. **承攬案件管理** - 成案專案(project_code)、人員配置、里程碑/甘特圖、公文關聯
5. **委託單位/協力廠商** - vendor_type 分離管理、inline 新增、ERP 關聯
6. **AI 代理人** - 26 真工具、自省閉環、主動推薦、Hermes Agent gateway (via ck-missive-bridge skill)
7. **ERP 財務模組** - 費用報銷、統一帳本、財務彙總、電子發票同步
8. **知識圖譜** - Code-graph 5,721 實體、DB/TS/Python AST 入圖

### 多專案架構 (v5.5.6, 2026-04-15 重整)

```
CK_Missive          (本專案·核心) — 公文 AI 引擎 + Hermes Agent 公網入口
CK_lvrland_Webmap   (兄弟專案)    — 土地查估 Webmap (Phase 2+ 接入)
CK_PileMgmt         (兄弟專案)    — 基樁管理 (Phase 2+ 接入)

[已廢止]
CK_OpenClaw         → ADR-0014 Hermes Agent 取代（2026-05-12 歸檔）
CK_NemoClaw         → ADR-0015 Cloudflare Tunnel 取代（2026-05-12 歸檔）
```

### 平台級 Subdomain 策略 (ADR-0016)

```
missive.cksurvey.tw     →  公文系統 (UI + API)，已上線
hermes.cksurvey.tw      →  Hermes Agent gateway (Phase 1 後啟用)
lvrland.cksurvey.tw     →  土地查估，🟢 已上線（SSO 整合）
pilemgmt.cksurvey.tw    →  基樁管理，🟢 已上線（SSO 整合）⚠️ 實際 hostname；規劃曾標 pile.cksurvey.tw 但未部署
digitaltwin.cksurvey.tw →  數位孿生/隧道，🟢 已上線（SSO 整合）
kg.cksurvey.tw          →  聯邦知識圖譜 Hub (選用)
```

> **架構原則**: Cloudflare Tunnel 統一公網入口；Cloudflare Access SSO 跨專案；
> 各專案獨立 DB；Hermes 共用 gateway 跨專案聯邦。零費用全 Free 方案。

### LINE / Telegram 多頻道整合（via Hermes Agent Gateway）

```
LINE 小花貓Aroan → Hermes Agent → skill(ck-missive-bridge) → Missive Agent API
Telegram @Aaron_ckbot → Hermes Agent → skill(ck-missive-bridge) → Missive Agent API
Discord → Interactions Endpoint → Missive Agent API (直連)
```

- Hermes 部署指南: `CK_AaaP/runbooks/hermes-stack/`
- Skill 定義: `docs/hermes-skills/ck-missive-bridge/`
- **重點**: Skill 中 API URL 必須用 `host.docker.internal:8001`（不是 `localhost`）
- **重點**: LINE webhook 需要公網 HTTPS，由 Cloudflare Tunnel 提供

> **歷史**: OpenClaw 整合已於 ADR-0014 廢止（2026-05-12），由 Hermes Agent 取代。
> 舊運維指南: `docs/LINE_OPENCLAW_OPERATIONAL_GUIDE.md`（僅供參考）

---

## 規範索引

> 以下規範位於 `.claude/rules/`，啟動時**自動載入**，無需手動引用。

| 規範檔案 | 說明 |
|---------|------|
| `skills-inventory.md` | Skills / Commands / Agents 完整清單 |
| `hooks-guide.md` | Hooks 自動化配置與協議 |
| `ci-cd.md` | CI/CD 工作流 |
| `auth-environment.md` | 認證與環境檢測規範 |
| `development-rules.md` | 開發強制規範 (SSOT, 型別, API, 服務層, DI) |
| `architecture.md` | 專案結構總覽（索引） |
| `architecture-backend.md` | 後端：Models/Services/API/Repositories |
| `architecture-frontend.md` | 前端：Pages/Hooks/型別/錯誤處理 |
| `directory-structure.md` | `.claude/` 配置目錄結構 |
| `security.md` | 安全規範 |
| `testing.md` | 測試規範 |

### 其他重要文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ 強制性開發檢查清單 (開發前必讀) |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引與常見錯誤 |
| `.claude/CHANGELOG.md` | 完整版本更新記錄 |

### 架構標準化（v5.9.6 ~ v5.9.8, 2026-04-25）

| 文件 | 說明 |
|------|------|
| `docs/architecture/STANDARD_REFERENCE.md` | 📘 **跨 repo 架構標準** — DDD/SSOT/Hermes/觀測棧 12 章 + §13 AI-Native UX |
| `docs/architecture/SERVICE_CONTEXT_MAP.md` | 🗂 services/ 頂層 85 散戶 × 16 bounded context 映射（漸進 DDD）|
| `docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` | 🧠 坤哥意識體 5 整合面向 + O1-O6 路線（v5.9.7/v5.9.8 落地紀錄）|
| `docs/architecture/WIKI_KG_BACKFILL_STRATEGY.md` | 📋 Wiki↔KG 三方案 ROI（已執行 X，連結率 30%→86%）|
| `docs/ops/baseline-fix-patch-preview.md` | ⚙️ Hermes baseline 修復 patch 預覽（Patch A+B 三路徑）|
| `scripts/checks/run_fitness.sh` | 🧪 本地 fitness runner — **6 step**（零 CI 費用）|
| `scripts/checks/service_dir_entropy.py` | 📊 services/ 頂層散戶比例（閾值 20%）|
| `scripts/checks/config_dead_reader_scan.py` | 🔍 yaml config dead reader 偵測（含 module function）|
| `scripts/checks/soul_mirror_drift_check.py` | 🔄 SOUL.md 跨 repo drift（fitness step 3）|
| `scripts/checks/wiki_kg_link_audit.py` | 🔗 Wiki↔KG 連結率 by entity_type（fitness step 4）|
| `scripts/checks/kg_embedding_coverage_check.py` | 🎯 KG pgvector 覆蓋率（fitness step 5）|
| `scripts/sync/sync_soul_to_hermes.sh` | 🔁 SOUL.md 跨 repo 手動同步（--apply gate）|
| `scripts/sync/dispatch_kg_ingest.py` | 🆕 方案 X Phase 1 — dispatch → KG ingest |
| `scripts/sync/backfill_wiki_*.py` | 🆕 wiki frontmatter 補 kg_entity_id（dispatch/project）|
| `scripts/sync/backfill_kg_embeddings_all.py` | 🎯 KG embedding 通用 backfill（critical/types/all 模式）|
| `/arch-fitness` slash command | 本地月度架構覆盤觸發 |

### v5.9.8 落地里程碑

- ✅ Wiki↔KG 連結率 **30% → 86%**（dispatch 0% → 100%, project 56% → 86%）
- ✅ KG pgvector embedding 業務 entity **0% → 100%**（10,792 筆 / 5 分鐘 / zero cost）
- ✅ SOUL.md 跨 repo 同步（CK_Missive ↔ CK_AaaP）+ Soul fidelity groq 75% → 80%
- ✅ ADR-0030 GO 條件 4/5 達標（#5 P95 待 5/20 會議重訂方案）

---

## 快速連結

### 開發環境
- 後端 API: http://localhost:8001/docs
- 前端開發: http://localhost:3000
- 資料庫: PostgreSQL **15.14**（image `pgvector/pgvector:0.8.0-pg15`，Docker，**127.0.0.1:5434** 僅本機）
  <!-- 2026-08-10 更正：原記「PostgreSQL 16」與實際不符。這不是無害的筆誤 ——
       備份是 backend 容器的 pg_dump 17.10 產生的，而伺服器是 15.14，
       dump 裡帶著 15 認不得的 transaction_timeout，帶 ON_ERROR_STOP 還原會中止。
       版本記載錯誤會讓人在災難當下判斷錯誤。詳見 docs/runbooks/disaster-recovery.md §4 -->
- 客戶端工具版本落差（**還原時會咬人**）：postgres 容器 psql 15.14／backend 容器 pg_dump·psql **17.10**
- ~~NemoClaw 監控塔: http://localhost:9000~~ — **廢止** (ADR-0015)
- vLLM 本地推理: http://localhost:8000 (Docker, Qwen2.5-7B-AWQ)
- Ollama: http://localhost:11434 (Docker, nomic-embed)

### 常用命令
```powershell
# === 推薦：統一管理腳本 ===
.\scripts\dev\dev-start.ps1              # 混合模式啟動（推薦）
.\scripts\dev\dev-start.ps1 -Status      # 查看所有服務狀態
.\scripts\dev\dev-start.ps1 -Restart     # 重啟 PM2 服務
.\scripts\dev\dev-start.ps1 -FullDocker  # 全 Docker 模式
.\scripts\dev\dev-stop.ps1               # 停止所有服務
.\scripts\dev\dev-stop.ps1 -KeepInfra    # 僅停 PM2，保留 DB/Redis

# === 手動啟動 ===
docker compose -f docker-compose.infra.yml --profile tunnel up -d
# ⚠️ `--profile tunnel` 不可省：`cloudflared` 有 `profiles: ['tunnel']`，
#    不帶它 `up -d` **不會把公網入口建回來**（`config --services` 也不列它）。
#    `restart: unless-stopped` 只救重啟，救不了「容器被移除」。
#    2026-08-26 由 CK_AaaP 指出容器不在 `config --services` 裡而查出。
      # 基礎設施
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001
cd frontend && npm run dev
pm2 start ecosystem.config.js

# === 公網部署 ===
bash scripts/deploy/deploy-public.sh     # v2.0.0 一鍵：前端 build → 後端 image build（帶 build 身分）
                                         #   → 換容器 → health → 驗 runtime commit → 驗公網 200
                                         # 只改前端：bash scripts/deploy/deploy-public.sh --frontend-only

# === 驗證 ===
cd frontend && npx tsc --noEmit          # TypeScript 檢查
cd backend && python -m py_compile app/main.py  # Python 語法檢查

# === Skills/知識地圖 ===
node .claude/scripts/validate-all.cjs            # Skills/Agents 格式驗證
node .claude/scripts/generate-index.cjs          # 索引重建
node .claude/scripts/generate-knowledge-map.cjs  # 知識地圖生成（全量重建）
node .claude/scripts/generate-knowledge-map.cjs --diff      # 差異報告（Heptabase 增量更新）
node .claude/scripts/generate-knowledge-map.cjs --if-stale  # 僅在源檔案更新時重建
node .claude/scripts/promote-learned-patterns.cjs # 學習模式升級
```

---

## 整合來源

本配置整合以下最佳實踐：

- [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) - Skills/Hooks/Agents/Commands 架構
- [superpowers](https://github.com/obra/superpowers) (v4.0.3) - TDD、系統化除錯、子代理開發
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) - 生產級工作流自動化

**核心理念**: 測試驅動開發 | 系統化優於臨時性 | 簡潔為首要目標 | 證據優於聲稱

---

> 配置維護: Claude Code Assistant | 版本: v1.86.0
