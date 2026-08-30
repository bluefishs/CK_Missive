# 服務建構標準化程序（Service Construction Standard）

> **建立**：2026-08-30｜**來源**：同日 12 個實測斷點的歸納，不是理論推導
> **強制等級**：高 —— 每一條都對應一次真實失效，附實例
> **與既有規範的關係**：`development-rules.md` 管「寫什麼」，本檔管「**接不接得起來**」

---

## 為什麼需要這一份

owner 2026-08-30 提問：**「為何系統如此多斷點與資訊缺漏」**。

把當天找到的斷點逐一歸類後，**只有一個形狀**：

> **一個能力由多個部件組成，而版控只保證「檔案存在」，不保證「它們接得起來」。**

| 部件 A（有人做了） | 部件 B（沒人做） | 實例（皆為 2026-08-30 實測） |
|---|---|---|
| 寫了腳本 | 沒接進 runner | `dispatch_kg_ingest.py` 寫於 04-25，**沒有任何排程在叫它**，KG 的 dispatch 停在 127 筆而 DB 有 149 筆 —— 漂了四個月 |
| 加了事件／metric | 沒有消費端 | `scheduler_start`（23 筆事件、0 支檢核在讀）／22 個 Prometheus metric 無 alert 無 panel ／**我自己當天新加的排程也沒登記 producer** |
| 修好了 hook | 修在不會執行的路徑 | secret guard 修在 `.git/hooks/pre-commit`，而 `core.hooksPath` 指向 husky ⇒ **實測 `.pem` 私鑰進暫存，回 exit 0 並印「全部檢查通過」** |
| 加了 schema 欄位 | 沒到 ORM／沒到 TS | `KBEmbedResponse` 的 `skipped`／`reason` 被 Pydantic 靜默丟棄 ⇒「我沒有做事」從未到達呼叫端 |
| **提交了程式碼** | **沒有 rebuild** | 容器映像停在前一日，**落後 38 個 commit**；當日 9 項新機制有 5 項卡在這裡 |
| **commit 了** | **漏了其中一個檔** | `937d6c35` 宣稱實作增量同步，而**不含實作檔** ⇒ 呼叫端有、被呼叫端沒有，checkout 出來跑不起來 |

### 為什麼是「這麼多」而不是一兩個

規模：**57 個排程 job、92 支 weekly 檢核、736 個 API path、402 份文件**。
每個 session 加一兩個部件，缺的那一半就累積。

而且**檢核機制自己也是多部件的**（腳本＋runner 條目＋索引宣告），
所以同一個病也長在治病的工具上 ——
當日新寫的四位一體檢核，首版就**掃到自己 docstring 裡的那句話**而把真陽性沖成 0。

---

## 一、多部件清單（新增任何能力前先對照）

每一種能力都有它的「完整部件集」。**只做部件 A 等於沒做。**

### 1.1 新增一支檢核腳本

| # | 部件 | 沒做的後果 | 誰在強制 |
|---|---|---|---|
| 1 | `scripts/checks/*.py` | — | — |
| 2 | 接進 `run_fitness.sh` 或 `run_fitness_weekly.sh` | **腳本存在但沒有人跑**（本 repo 已發生兩次，同三支腳本） | `spec_executor_audit`（weekly 39） |
| 3 | 寫進 `.claude/rules/skills-inventory.md` | 無人知道它在做什麼 | `declaration_gate`（會擋） |
| 4 | 能紅（有非 0 退出路徑），否則步驟名標「僅報告」 | 永遠不可能紅的綠燈與真守門長得一樣 | `gate_vs_report_step_audit`（weekly 89） |
| 5 | **負向對照**：注入違規 → 必須翻紅 → 還原 → 必須轉綠 | 「沒有違規」與「偵測器壞了」在畫面上完全一樣 | 無 —— 只能靠人 |

⚠️ **步驟編號要 `grep` 過再用。** 2026-08-30 一份規範書寫「Weekly Step 88」，
而 88 已被 `pg_tuning_ssot_audit` 佔用（87／89／90／91 亦然）。

### 1.2 新增一支排程 job

| # | 部件 | 沒做的後果 |
|---|---|---|
| 1 | `@tracked_job("<id>")` 裝飾子 | 不寫 `cron_events` ⇒ 存活稽核看不到它 |
| 2 | `scheduler.add_job(..., id=<同一個 id>, replace_existing=True)` | id 不一致 ⇒ freshness 對不上；缺 `replace_existing` ⇒ 持久化 jobstore 下重啟拋 `ConflictingIdError` |
| 3 | **回傳 detail dict** | 「做了 30 件事」與「什麼都沒做」在 cron_events 裡長得一模一樣 |
| 4 | **登記 `producer_outcome_registry.json`**，或加進 `NON_PRODUCER_JOBS` **並寫明理由** | 會跑、會報 success，而沒有人檢查它有沒有真的產出 |
| 5 | 早退路徑也要回**同一個 key** | 只回 `{skipped, reason}` 時 watchdog 會報「未回報 <key>」，真正的原因反而看不見 |

⚠️ **producer 的 key 要挑「壞掉時一定是 0」的那個**，不是「常態是 0」的那個。
實例：KB 增量同步取 `files_total`（0＝掃不到或 provider 死）而不是 `updated`
（0＝全部未變，是常態且是好事，拿它當判準會天天假紅）。

### 1.3 新增／修改 API 契約

| # | 部件 | 沒做的後果 |
|---|---|---|
| 1 | `backend/app/schemas/` 的 Pydantic 模型（**禁止**在 endpoints 本地定義） | `schema_ssot_audit`（weekly 59）會擋 |
| 2 | ORM 欄位（若需持久化） | schema 收得到但存不進去 |
| 3 | Alembic migration ＋ 確認**單一 head** | — |
| 4 | 回應 schema 要宣告**所有**會回傳的欄位 | **Pydantic 預設靜默丟棄多餘欄位** |
| 5 | `npm run api:generate:file` 重生前端型別 ＋ `npx tsc --noEmit` | 後端有、TypeScript 沒有 ⇒ 前端接的時候編譯期看不見 |

⚠️ `npm run api:generate`（不帶 `:file`）打的是**執行中的容器**。
容器落後時，重生型別會拿到**舊契約**。
正確作法：先從 host 的新程式碼產生 `docs/openapi.json`，再 `api:generate:file`。

### 1.4 新增一個 hook

| # | 部件 | 沒做的後果 |
|---|---|---|
| 1 | 腳本本體 | — |
| 2 | **接進 `.claude/settings.json` 或 `frontend/.husky/`** | 檔案在、沒有任何事件會觸發它 |
| 3 | 確認 `git config core.hooksPath` 指向哪裡 | **改在不會被執行的目錄上** |
| 4 | 含中文的 `.ps1` 必須有 **UTF-8 BOM** | PowerShell 以 cp950 誤讀 ⇒ 語法崩潰或條件永不成立 |
| 5 | 逐條給違規輸入實測 | 「它有在擋東西」不代表它的每條規則都在擋 |

---

## 二、五個判準原則（都來自當日的誤判）

### 2.1 先量再判斷，而且**量兩次**

單一量測無法自我檢驗。當日案例：

* 「連結率剩 5% 沒補」→ 實測 **12%**，而其中 **27/29 在 KG 裡根本沒有對應實體**，backfill 補不了 —— **順序反了，要先 ingest**。
* 「所有 add_job 都有 `replace_existing`」——`grep -c` 說 56/56，AST 說 55/56（差的那個是我自己的 `super().add_job()`）。

### 2.2 判準的**寬窄兩端**都要用真實案例校準

* 過寬：`\byear\b` 命中長條圖的 X 軸；Mermaid node 85 個候選裡只有 4 個像類別名。
* 過窄：`items\.reduce` 漏掉 `pendingItems`；收窄後得到的「0」要**再查一次**。

> **過寬給你一堆假陽性 —— 吵，但看得見。
> 過窄給你一個乾淨的零 —— 安靜，且看起來像好消息。代價完全不對稱。**

### 2.3 判準的掃描範圍不得包含**描述該判準的文字**

當日實例：四位一體檢核把 `scripts/` 納入原始碼掃描 ⇒
**它找到自己 docstring 裡寫的「`IntentParsedResult` 找不到」這句話**，
判定該符號存在，把唯一的真陽性沖成 0。**檢核把自己證偽了。**

### 2.4 在**正確的抽象層**搜尋

當日實例：grep `AdrTab.tsx` 找 mermaid ⇒ 0 命中 ⇒ 我宣告「沒有渲染」。
實際上它用的 `MarkdownRenderer` 早就把 ```` ```mermaid ```` 代理給 `MermaidBlock`。
**在錯的層搜尋會得到有信心的錯誤答案。**

### 2.5 啟發式負責常見情況，**重試負責尾巴**

當日實例：`text[:8000]` 註解寫「建議 8192 tokens」——**把字元當 token**。
實測中文約 **4 token/字**，`[:8000]` 對純中文等於送 32,000 tokens。
改按估算 token 截斷後仍有例外（`_Relationship-Map.md` 估 5,128 tok 仍 400），
加上「400 且訊息含 context length 就對半重試」才保證成功。

---

## 三、收尾程序（Definition of Done）

一個變更**不是** commit 完就結束。當日有 5/9 項卡在最後一步。

```
① 寫 → ② 部件集補齊（見第一節）→ ③ 負向對照 → ④ commit
                                                    ↓
⑦ 驗證執行層 ← ⑥ rebuild／部署 ← ⑤ 確認 commit 本身是完整的
```

### ⑤ 確認 commit 本身是完整的

⚠️ **當日實例**：`937d6c35` 宣稱實作 KB 增量同步，`git add` 列了 10 個檔案，
**唯獨漏掉實作檔**。呼叫端有、被呼叫端沒有 ⇒ checkout 出來跑不起來，
而且**要等 04:45 排程觸發才會 AttributeError**。

既有機制都擋不住它：pre-commit 只驗語法與 secret；`py_compile` 過得了
（未定義的方法是執行時才解析）；AST 回歸測試驗的是呼叫端的結構。

⇒ **提交前跑一次 `git diff --stat HEAD` 對照「這次改了哪些檔」**，
或用 `git add -A` 後逐項檢視，不要手打檔案清單。

### ⑥⑦ 部署與驗證

* `backend/app` **不是 bind mount** ⇒ 後端改動一定要 rebuild 才生效。
* `frontend/dist` 是 bind mount ⇒ 前端只需 `npm run build`。
* 部署後**必須驗 runtime commit**（`CK_BUILD_COMMIT`）與公網 200，
  且**公網 200 要多次抽樣** —— 間歇性殭屍埠會讓單次剛好通過（L76）。

---

## 四、自查清單（貼在 PR／session 收尾用）

- [ ] 這個能力的**部件集**是哪一組？（§1.1–1.4）逐項打勾
- [ ] 判準有沒有**負向對照**？注入違規會紅、還原會綠？
- [ ] 判準的掃描範圍有沒有包含描述它自己的文字？
- [ ] 得到「0」的時候，有沒有**再查一次**是不是判準太窄？
- [ ] commit 有沒有漏檔？（`git diff --stat HEAD` 對照）
- [ ] 後端改動有沒有 rebuild？有沒有驗 runtime commit？
- [ ] 新增的排程／metric／事件，**誰是它的接收端**？

---

## 五、與既有規範的關係

| 規範 | 管什麼 | 與本檔的關係 |
|---|---|---|
| `development-rules.md` | 寫什麼（SSOT／型別／API／服務層） | **互補** —— 那份管內容，本檔管接線 |
| `cross-file-ssot-governance.md` | 跨檔資源的單一水源 | **同源** —— 那份是本檔第 1.3 節的深化 |
| `adr-anti-half-wired-sop.md` | ADR 級的半接通防範 | **同型不同層** —— 那份管 ADR，本檔管每一次日常變更 |
| `LESSONS_REGISTRY.md` | 事故的權威紀錄 | **本檔的來源** —— 每一條原則都指得出對應的 L 編號 |

> **核心精神**：這個系統的斷點不是「哪裡寫錯了」，
> 是**部件之間的連結沒有被強制**。
> 寫程式碼很容易；讓它真的接上、真的在跑、真的有人看，才是工程。
