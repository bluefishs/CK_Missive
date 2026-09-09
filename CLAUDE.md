# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.76（2026-09-09）/ ⭐⭐⭐**這一輪的主軸是「異值同工」**：owner 定調「統計應建構統一服務端，不應依各別頁面各自建構」。盤點實測承攬金額 **4 份**實作、已請款／已收款／應付各 3 份、「誰是全公司視角」2 份、案件統計範圍兩份平行程式碼；**而同一天三處是「分歧存在、結果相同、只是還沒發作」**（已收款三份狀態條件各不相同卻同值，因為 59 筆狀態剛好全是 paid；承攬金額兩層 vs 三層；全公司視角兩份判準）⇒ **數字對得起來不能證明只有一份實作，要數程式碼**（L149）。收斂＝中心服務 `services/stats/`（指標 `finance`／範圍 `case_scope`）＋ `core/case_scope.has_company_wide_scope` 唯一判準＋15 條口徑鎖＋weekly 132（新增即紅、存量 7 處走基線）；統一到最嚴謹的那份**實測不改變任何現有數字**；線上驗證三個畫面同值 108,108,873、12 位使用者範圍一致。⭐⭐**同日六個「兩份宣告分家」實例各自修好並各補一道守門**：表頭篩選鍵三處分家（128，`buildServerFilters` 讓打錯字由 tsc 擋）／承辦身分合併沒展開（129，「顯示 (3) 卻 0 家」的 380 萬）／13 處 `getattr` 猜欄位（130）／列表與統計卡身分口徑（131，靜態掃描誤報改行為判準）／財務儀表板上下兩個年度口徑差 1,693 萬（類別分解仍用案號年）／PM 統計卡沒接 `staff_user_id`。⭐**weekly 統整**：131 步分 10 領域，彙總器只把「本週新紅」判紅（44 支非綠裡真的變壞的是 6 支，全清）；runner 檔頭「12 步 ~3 分鐘」過期十倍。⭐**判準自我更正五次，全是假綠**：命中自己的註解（兩次）、動態比對兩邊用同一份 SQL、小樣本印 0%、靜態掃描看不到 schema 裡的參數。⭐**我自己的量測錯誤七次**：管線退出碼、錯的工作目錄、手動執行的編碼崩潰當成排程在崩、只讀函式前半段（兩次）、探針比對自己的表達式、把建置中的部署當成程序死掉——**先排除自己，再談系統**。⚠️ 主機層 A127：swap=0 前提被推翻，三個選項待 owner。
> （v6.75 那一輪的摘要在下一段）
> **v6.75（2026-09-08）**: ⭐⭐⭐**這一輪的主軸是「機制要真的在跑」**：owner 指出「都進完成一半就停駐且無複查」，實查證實——weekly 117–122 六支檢核 README 與 skills-inventory 都登記了、`run_fitness_weekly.sh` **一支都沒有** ⇒ 從未被排程執行；`declaration_gate` 因此加第三腳（腳本／索引／runner 三處同時成立才算存在）。⭐⭐**業務同仁看不到自己有權限的頁面**：staff 有專案帳款等 7 頁的碼，父群組「報表分析」要 `reports:view` 而 staff 沒有 ⇒ 前端先問父階、整棵子樹消失（每層單獨看都對，鏈是斷的）；weekly 119 ⑤ 立刻多抓 finance／ops 的 ERP 圖譜同型。⭐⭐**`/uploads` 是 StaticFiles 掛載 ⇒ 1,642 個附件公網未登入 200**（L148），而 weekly 64 還明文豁免它（「靜態、本來就該公開」）——改帶認證路由＋`Cache-Control: private, no-store`（CF 依副檔名快取 PDF，登入者抓一次之後未登入也拿得到），再補**附件層級**規則（A116）。⭐**收斂**：民國年解析 8 份定義＋19 處散裝 `+1911` 收成 `app/core/roc_date.py`（A119）；LINE 去重改 redis（A117）。⭐**備份**：`D:\報價單\` 整棵樹（總表＋106 個回簽原件）此前沒有任何異地備份，已納入 NAS current 鏡像＋試算表日期快照（A123）。⭐**文件**：8 份 2025 規劃期文件（`claude_plant/`、SQLite、8003「優化版」）仍是活文件且被引用，全數作廢入 `archived/`＋weekly 122 守；文件生命週期檔頭 A118 與 CK_AaaP 同格式（`lifecycle: status/reviewed/owner`，90 天）。⭐**build 身分**：`MSYS_NO_PATHCONV=1` 讓 `git -C /d/…` 與 python 讀不到路徑 ⇒ 映像被標成 `unknown @ unknown-dirty` 而建置全程無錯，且部署閘門比對 `= "unknown"` 對 `unknown-dirty` 完全放行；兩處皆修。
> （更早版本的一行摘要同樣在 `docs/MILESTONES_ARCHIVE.md`）
>
> 📜 **2026-08-30～09-04 的日記式紀錄已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)**（09-01～03 於 09-04 搬、08-30／08-31／09-04 十一輪於 09-09 覆盤搬；搬移不是刪除，教訓本體在 `LESSONS_REGISTRY.md`）。
>
> ⭐⭐⭐**09-07：一份宣告改了、另一份沒改——同一天三次**（L145）。①拆出委託／協力帳款各自的權限碼時
> **只改角色層 `role_permissions`**，而前端判權限讀的是**使用者層 `users.permissions`** ⇒ 管理員打開那兩頁是空的，
> 而畫面上看不出原因（owner 回報才發現）；②「逾期幾天」有**三份各自實作**，把自動建立的請款日改留白時，
> 漏改一處那 86 筆佔位就從該消費端整批消失（實測 198→118），畫面只顯示「逾期變少了」；
> ③改委託單位主檔名稱，列表與下拉還是舊名——**名字讀的是建案當下的快照，不是主檔**，選了新名就是空表。
> 三者修法同形：定義收成一份＋補一支盯「有沒有第二份」的檢核（weekly 119 角色↔使用者、121 稽催錨點、
> 改名時傳播快照）。⭐**兩次判準自我更正**：weekly 121 首版判「檔案有沒有出現模組名」，而三個消費端的**註解**
> 都寫著模組名 ⇒ 拿掉 import 也不會紅、**判準等於沒有作用**；weekly 120 首版把**同案不同版次**
> （`B114-C031-0` vs DB 的 `-1`）報成漏匯入——**把誤報當事實交出去，會讓人做出錯的清理動作**。
> ⭐**型別只有實跑看得到**：`COALESCE(billing_date, quoted_at)` 前者 date、後者 datetime ⇒ Python 端 TypeError、
> SQL 端回 interval（畫面印「逾期 557 days 天」）。⭐⭐**匯入器讀到彙總區塊的欄位**（L146）：總表右側第 38–43 欄
> 是各承辦年度小計，「報價金額」因此在同一張表出現兩次，而欄位對應是**後面覆蓋前面** ⇒ `B110-020-0A` 被寫成
> 351,200（那是某人的年度小計），正確是 39,000。⇒ 同名表頭取最左邊。⭐ 同日另兩個「不會報錯的略過」：
> 沒有報價單編號的列**連略過都沒記錄**（4 列約 246 萬從未進系統）、唯一索引不排除軟刪列（重建被刪過的編號整批回滾）。
> ⭐**路由此前只問有沒有登入**：`AppRouter` 用了 117 次 `ProtectedRoute`、傳 `permissions` 的 **0 次** ⇒
> 選單藏起來的頁面打網址一律進得去。改成照選單自己的宣告擋（改一處、117 條全涵蓋）。
> ⚠️ 這是**介面層**守衛不是資安邊界：API 738 支端點裡只 require_auth 的仍有 415 支。

> ⭐⭐⭐**09-07 晚：owner「整個系統四分五裂，重覆優化架構鬆散」→ 收斂 A／B 落地**（L147，全文 `docs/architecture/CONSOLIDATION_20260907.md`）。
> 診斷：一天十次同一形狀——**同一件事有兩份宣告，改一份另一份不動，沒有任何一方報錯**；而我每次的反應是加一支檢核
> （本月 +89、總數 214）。檢核是**看著**兩份宣告分家，不是讓它們**不可能**分家 ⇒ 事故照樣重演，只是早點被看見。
> **收斂 A**：角色是權限唯一來源——儲存角色即同步、改角色即推導、`is_admin` 改為由角色推導的鏡像（前後端 `isAdmin` 同步只看角色）。
> **收斂 B**：選單表是選單／路由守衛／**API** 三邊唯一來源——API 只宣告「我屬於哪個頁面」（`require_page_permission`），
> 權限碼從 `app/core/capabilities.py` 的快取讀；實測改選單表 → 財務打 API 200→403→200，**零程式碼零部署**。
> ⇒ weekly 119 ③④ 由 RED 降 YELLOW（**檢核數量下降才是架構變緊的訊號**）。
> ⭐ 兩個過程中的錯：依 exec「全域唯讀」的**設計註解**移除其寫入權——實測三位 exec 全是承辦（一位 81 案）；
> 前端 `USER_ROLES.default_permissions` 差點被當權威套回 DB——那是建角色的**範本**，照套管理員會失去 ERP 財務。
> **角色看人實際在做什麼，宣告看是誰在維護給誰用，不看它叫什麼名字。**

> ⭐⭐⭐**09-08：owner 拿一份 2025 規劃期附件問了 A1–A5／B1–B8／C1–C5／D1–D10，逐項實查**（全表在 `CONSOLIDATION_20260907.md` §六、`OPEN_ITEMS` A116–A119）。
> 大多數「兩套」都不存在（sqlite／8003／Adminer 8080／OAuth 行事曆／無 Alembic／無排程）——出處是 **8 份未作廢的活文件**，全部作廢入 `docs/archived/`＋weekly 122 守。
> **但 D6 是真的**（L148）：`/uploads` 是 StaticFiles 掛載、1,642 個附件公網未登入 200；weekly 64 還把它明文豁免（「靜態、本來就該公開」）。
> 修成帶認證路由＋`Cache-Control: private, no-store`（第二層：CF 依副檔名快取 PDF，登入者抓一次之後未登入也拿得到）。**已在 CF 邊緣快取的檔只有 purge 能清＝owner。**
> 另兩個真缺口：D7 還原演練日期此前無守門（offsite 稽核加 `check_restore_drill`）、B6 民國年解析 8 份實作（A119）。

> ⭐**09-09 晚（重啟後覆盤）**：12:04 重啟五步全綠（build `768c8165`＝HEAD、公網 3/3、附件 401、四層 GREEN）；每日 02:00 三紅為舊映像所致，容器內複跑 0／10 GREEN、14 YELLOW。**swap=0 實驗未執行**（`.wslconfig` 仍 8GB）。09-08 21:26 硬當成因已定＝本 repo session 的 MagicMock 負向測試 OOM（**L150**，`docs/incidents/`），與 A127 分家；測試規範補「負向測試的記憶體邊界」。TESTING_MAP 產生器寫死「17／114 步」改讀 runner（實際 17／132）。整體覆盤與三個月規劃＝[`docs/architecture/ARCHITECTURE_REVIEW_20260909.md`](docs/architecture/ARCHITECTURE_REVIEW_20260909.md)；owner 決策總表＝`OPEN_ITEMS_20260819.md` 檔頭。
>
> **最後更新**: 2026-09-09
>
> **近期重大里程碑**：已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)
> （2026-08-27，v6.59–v6.61 共 46,981 字元；更早的 64 條 08-24 已先移入）。
> **搬移不是刪除**——內容完整保留，只是不再每個 session 載入一遍。
> 教訓的權威來源是 [`docs/architecture/LESSONS_REGISTRY.md`](docs/architecture/LESSONS_REGISTRY.md)。

---

## 專案概述

CK_Missive 是企業級公文管理系統（公文／行事曆／邀標報價／承攬案件／ERP 財務／知識圖譜／Hermes Agent）。功能與模組請直接看 `backend/app/api/endpoints/`、`frontend/src/pages/`；多專案角色與 subdomain 策略見上層 `D:/CKProject/CLAUDE.md`。

### LINE / Telegram（via Hermes Agent Gateway）

- **重點**: Skill 中 API URL 必須用 `host.docker.internal:8001`（不是 `localhost`）
- **重點**: LINE webhook 需要公網 HTTPS，由 Cloudflare Tunnel 提供
- Hermes 部署包：`CK_AaaP/runbooks/hermes-stack/`；Skill 定義：`docs/hermes-skills/ck-missive-bridge/`

## 規範索引

> 以下規範位於 `.claude/rules/`。**載入時機分兩種**（2026-09-08 /doctor 校正）——
> 沒有 `paths:` frontmatter 的每個 session 都載入；有的只在動到那些路徑時載入。
> ⚠️ 原表列了一份 `security.md`，而**那個檔案不存在**（安全規範的實際位置見下方「其他重要文件」
> 與 `C:/Users/User1/.claude/rules/security.md`）——一份宣告說有、而檔案沒有，
> 是本 repo 反覆記載的同一個形狀，只是這次方向相反。

| 規範檔案 | 載入 | 說明 |
|---------|------|------|
| `skills-inventory.md` | 常駐 | Skills / Commands / Agents 清單（檢核腳本正典在 `scripts/checks/README.md`）|
| `development-rules.md` | 常駐 | 開發強制規範 (SSOT, 型別, API, 服務層, DI) |
| `cross-file-ssot-governance.md` | 常駐 | 跨檔資源 SSOT 治理（L41–L45 家族）|
| `architecture.md` | 常駐 | 專案結構總覽（索引） |
| `testing.md` | 常駐 | 測試規範 |
| `architecture-backend.md` | `backend/**` | 後端：Models/Services/API/Repositories |
| `architecture-frontend.md` | `frontend/**` | 前端：Pages/Hooks/型別/錯誤處理 |
| `adr-anti-half-wired-sop.md` | `docs/adr/**`、`docs/architecture/**` | ADR 級半接通防範 |
| `hooks-guide.md` | `.claude/hooks/**`、`.claude/settings*.json`、`frontend/.husky/**`、`.git/hooks/**` | Hooks 自動化配置與協議 |
| `ci-cd.md` | `.github/**`、`scripts/checks/**` | CI/CD 工作流 |
| `auth-environment.md` | `frontend/src/config/**`、`frontend/src/api/**`、`backend/app/core/auth*` | 認證與環境檢測規範 |

### 其他重要文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ 強制性開發檢查清單 (開發前必讀) |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引與常見錯誤 |
| `.claude/CHANGELOG.md` | 完整版本更新記錄 |

## 快速連結

### 開發環境
- 後端 API: http://localhost:8001/docs
- 前端開發: http://localhost:3000
- 資料庫: PostgreSQL **15.14**（image `pgvector/pgvector:0.8.0-pg15`，Docker，**127.0.0.1:5434** 僅本機）
  <!-- 2026-08-10 更正：原記「PostgreSQL 16」與實際不符。這不是無害的筆誤 ——
       備份是 backend 容器的 pg_dump 17.10 產生的，而伺服器是 15.14，
       dump 裡帶著 15 認不得的 transaction_timeout，帶 ON_ERROR_STOP 還原會中止。
       版本記載錯誤會讓人在災難當下判斷錯誤。詳見 docs/runbooks/disaster-recovery.md §4 -->
- 行事曆憑證：**只有服務帳號**（`GOOGLE_CREDENTIALS_PATH` → 容器內 `/app/GoogleCalendarAPIKEY.json`）；`GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` 是 **SSO 登入**用，與行事曆無關（2026-09-08 owner 誤讀為兩條路線，成因是 `.env.example` 一個標題包兩個功能，已拆）
- ⛔ **沒有的東西**（2026-09-08 逐項實查，別再從舊附件抄）：沒有 sqlite（`documents.db`／`ck_documents.db` 都不存在，sqlite 只在測試的 in-memory）；沒有 8003「優化版」後端（無程序監聽、只剩歸檔報告提過）；沒有 Adminer/pgAdmin 8080（只在 2026-05 歸檔 wiki）；`C:\GeminiCli\…` 是 2026-03 遷移前的路徑。守門＝weekly 122
- 客戶端工具版本落差（**還原時會咬人**）：postgres 容器 psql 15.14／backend 容器 pg_dump·psql **17.10**
- ~~NemoClaw 監控塔: http://localhost:9000~~ — **廢止** (ADR-0015)
- vLLM 本地推理: http://localhost:8000 (Docker, Qwen2.5-7B-AWQ)
- Ollama: http://localhost:11434 (Docker, nomic-embed)

### 常用命令

已改為 skill `dev-commands`（`.claude/skills/dev-commands/SKILL.md`），需要時載入；一句話：`.\scripts\dev\dev-start.ps1` 啟動、`bash scripts/deploy/deploy-public.sh` 部署、`npx tsc --noEmit` 驗證。

---

> 配置維護: Claude Code Assistant | 版本: v1.86.0
