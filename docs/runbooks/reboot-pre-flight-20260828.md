# 重啟前狀態固定與復原指引（2026-08-28）

> 用途：**重啟後要能分辨「本來就有的」與「重啟造成的」。**
> 沒有這份基線，任何重啟後的紅燈都會被當成新問題查一遍。
> 前一份：`reboot-pre-flight-20260824.md`（該次的已知紅燈與待辦仍請對照）

---

## 1. 重啟前的量測基線（10:30 實測）

| 項目 | 值 |
|---|---|
| 公網首頁 / `/health` | **200 / 200** |
| 業務量 | documents **2,032**｜canonical_entities **49,984** |
| 容器 | **56** 個 Up（另 3 個非 Up 屬既有：lvrland frontend-dev、tunnel builder、ollama_dev「Created」）|
| runtime 身分 | `v6.63 @ 90d93c4f-dirty`（dirty 來自其他 session 未提交的檔案，非我的）|
| CK_Missive 未推送 | **0** |
| 異地備份四類 | **GREEN 且新鮮**（資料庫／里程碑／附件／金鑰）|

### 排程稽核的 5 個 RED —— **重啟後應該還在，不是新問題**

    CK_lvrland_Webmap-SelfAudit-Static   LastTaskResult=2（未宣告的失敗碼）
    CK_lvrland_Webmap-StaticChecks       LastTaskResult=2
    CK_Missive-SOUL-Mirror-Sync          State=Disabled ／ result=3 ／ 04:45 沒跑

* lvrland 兩支：等該 repo 回覆退出碼語意（我不猜，猜錯會吞掉真的失敗）
* SOUL-Mirror-Sync 三條：**它被停用是對的**（跑的腳本 08-02 起就設計成拒絕執行），
  處置見 **A28**。⚠️ 不要因為看到紅燈就把它啟用 —— 我 08-27 這樣做過，是錯的。

---

## 2. ⚠️ 重啟前沒清掉的：其他 repo 有 19 筆未推送

    CK_Hermes        16 筆    ← session 已關閉，通知不到
    CK_AaaP           3 筆    ← session 已關閉
    CK_Website        1 筆
    shared-modules    3 筆
    CK_Missive        0（已清空）
    CK_DigitalTunnel  0（他們昨日已推完 15 筆）

**重啟不會弄丟 commit。** 真正的風險是：未推送的工作在重啟後很容易被下一個
session 當成「還沒做完」而重做一次。恢復後請先在各 repo 跑
`git log @{u}..HEAD` 確認，再決定要不要推。

---

## 3. 重啟後**必然**會看到、但不是故障的三件事

| 現象 | 為什麼 | 怎麼判 |
|---|---|---|
| `CK-Hermes-Cron-Tick` 等高頻排程「上次執行在重啟前」 | 關機期間不可能 fire | 稽核已有 boot-clamp（取「距上次執行」與「距開機」較小值），30 分鐘內不報 |
| `CK-Hermes-Health-Smoke-Daily` 仍是 `1999-11-30` 形態 | 它 08-27 才註冊，首跑是每日 09:10 | `NumberOfMissedRuns=0` 且 `NextRunTime` 在未來 ⇒ 正常 |
| Redis host 埠 `127.0.0.1:6380` 連不上 | **L76 殭屍轉發**（TCP 連得上、立刻被關閉；容器內 `redis-cli ping` 回 PONG）| ⚠️ **重啟後很可能自己好** —— 若好了，那是埠轉發重建，**不是修好了什麼**，別記成成果 |

---

## 4. 重啟後的復原順序

```bash
# ① 基礎設施（--profile tunnel 不可省，否則公網入口不會建回來）
cd D:/CKProject/CK_Missive
docker compose -f docker-compose.infra.yml --profile tunnel up -d

# ② 三層驗證（本機 → 公網 → ORM/認證鏈）
bash scripts/checks/deploy_verify.py   # 或 python scripts/checks/deploy_verify.py

# ③ 與本文件的基線對照
python scripts/checks/windows_task_liveness_audit.py    # 應仍是那 5 個 RED
python scripts/checks/business_vital_signs.py           # 業務量對照 §1
curl -s https://missive.cksurvey.tw/health              # documents 應 ≥ 2032
```

### ⚠️ 已知的重啟陷阱（不要重踩）

* **NVIDIA Container Toolkit prestart hook 崩潰**（`ld.so _dl_setup_hash` 斷言）會讓
  GPU 容器（`ck-ollama`）起不來、推論全斷，**而 healthcheck 仍是綠的**。
  解法是 `wsl --shutdown` 重啟 Docker 引擎，**不是 `docker restart`**。
* **L76 殭屍埠**：後端 rebuild 後容器 healthy 而公網 502。所以 §4 的驗證必須驗到公網，
  本機 200 不算數。
* **有程式會持續停用 Windows 排程**（C1）。復原後用
  `python scripts/checks/windows_task_liveness_audit.py` 確認，
  ⚠️ 但 `State=Disabled` **不等於該啟用**（見 §1 的 SOUL-Mirror-Sync）。

---

## 5. 重啟後最該先看的一件事（本輪新發現）

**A31：Groq 與 NVIDIA 的模型都已下架，agent 已在本地 ollama 上跑了約 27 天。**

    GROQ_DEFAULT_MODEL   = llama-3.3-70b-versatile                  → 不在 Groq 模型清單
    NVIDIA_DEFAULT_MODEL = nvidia/llama-3.3-nemotron-super-49b-v1.5 → 不在 NVIDIA 清單
    （兩家 models API 皆回 200 ⇒ API key 有效，是模型名的問題）

現場：`Groq circuit OPEN → 走 NVIDIA` → `NVIDIA circuit OPEN → 走 Ollama` →
`Synthesis timed out after 35s`。

⚠️ **重啟會清掉斷路器狀態**（它是 per-process 的記憶體物件），所以重啟後
「Groq circuit OPEN」那幾行會暫時消失 —— **但模型仍然不存在**，
幾次請求後又會開回來。**不要把那個空窗讀成問題消失了。**

換哪個模型是 owner 決策（影響品質、TPM 假設與成本），可用清單見 `OPEN_ITEMS` A31。

---

## 6. 待 owner 決定的清單（重啟不會改變它們）

`docs/architecture/OPEN_ITEMS_20260819.md`：**A19–A31**。其中本輪新增：

* **A28** SOUL-Mirror-Sync 排程要不要移除（它只剩製造紅燈的功能）
* **A29** `ck_missive_frontend` 容器去留（健康、陳舊、連不到、不在使用者路徑上）
* **A30** `actual_llm_provider` 修法已上線但**生產尚未驗到**
* **A31** 兩個雲端模型已下架（見 §5）

---

## 7. 另一條 session 線同日的變更（重啟後看到這些「變了」是正常的）

本文件 §1–§6 由 inference／排程那條線寫。以下是 **ERP／自我檢核那條線**同日的
變更，寫在這裡是因為它們**會改變重啟後的觀感**，不寫的話很容易被當成新問題。

### 7.1 ⚠️ `careful-guard` 修好了，而它會誤判

`.claude/hooks/careful-guard.ps1` 原本**沒有 UTF-8 BOM**，PS 5.1 用 cp950
解析中文 ⇒ 每次 exit 1。30 天內 12,491 次呼叫**一次都沒攔到東西**。
已補 BOM，實測現在真的會擋（危險刪除指令 exit 2 並說出理由）。

**代價是它一小時內就給了第一個誤判**：commit message 裡引用危險指令的
字面值當說明，整個 `git commit` 被擋下。守衛掃的是**整個指令字串**，
分不出「要執行的指令」與「heredoc 裡的說明文字」。

⇒ **重啟後若有指令被 `[CAREFUL] CRITICAL` 擋下，先確認那個字串是不是只出現在
訊息/註解裡**。繞法：`git commit -F <file>`。
**不要因為誤判就把守衛關掉** —— 它壞了 30 天沒人發現，正是因為它從不出聲。

### 7.2 容器內 daily 的輸出變了：traceback 5 -> 0，SKIP 6

先前容器內 daily 有 5 段 traceback 而 `EXIT=0`（runner 用 `|| true` 接住）：

* **11 支硬編 `localhost:5434`** —— 那是 host 的對外埠，容器內不存在。
  已改為讀 `DATABASE_URL`（並 `.replace("postgresql+asyncpg://", "postgresql://")`，
  asyncpg 不吃那個 scheme）。
* **3 支需要 host 資源**（git／前端原始碼）—— 改為**大聲 SKIP** 而非崩掉。

⇒ **重啟後看到 6 行 `[SKIP]` 是正常且刻意的**，每一行都說得出「這個環境驗不了什麼」。
看到 traceback 才是新問題。

### 7.3 記憶檔瘦身 56%（內容沒有刪，是搬走了）

    CK_Missive/CLAUDE.md       57,347 -> 8,036 字元
    rules/skills-inventory     25,466 -> 4,498
    rules/architecture-backend 22,002 -> 7,320
    rules/architecture-frontend 12,461 -> 5,360

里程碑在 `docs/MILESTONES_ARCHIVE.md`、變更史在 `.claude/CHANGELOG.md`、
目錄樹用 `ls` 就有。三支 rules 加了 `paths:` 改為**延遲載入**
（動到 `backend/**` 或 `frontend/**` 時才進 context）。

⇒ **重啟後覺得「CLAUDE.md 怎麼少了那麼多」是預期的，不是被誤刪。**

### 7.4 重啟是跑那支提權腳本的好時機

cmd 視窗每天彈約 **718 次**，80% 來自兩個每 5 分鐘跑的排程
（`CK_AaaP_ContainerHealthAlerts` 289／`CK-Hermes-Cron-Tick` 288）。
根因是 `Principal.LogonType = Interactive`（**`-WindowStyle Hidden` 擋不住**，
那兩支之一本來就帶著它）。

    以系統管理員身分開 PowerShell，執行：
    <scratchpad>/fix-task-popups.ps1

它會**先印還原資訊 -> 改 S4U -> 手動觸發驗 LastTaskResult 仍為 0 -> 印還原指令**。
已確認那兩支腳本沒有 `Z:` 或 `\CKNAS` 參照（S4U 拿不到對應磁碟機）；
會碰 NAS 的備份排程**刻意不動**。

---

## 8. ERP／案號體系的待決（重啟不影響，但工具已備妥）

owner 2026-08-27~28 已確立編號職責：

    建案案號 case_code    CK{年}_PM_{類別}_{流水}   案子的身分，跨三張表的橋樑
    成案編號 project_code CK{年}_{類別}_{流水}      = 建案案號去掉 `_PM_`（無須連號）
    報價單編號            quotation_no（線上）／legacy_quotation_no（歷史，凍結）

已完成：產號器批次撞號修復、成案編號改去 PM 規則、自動成案失敗不再靜默、
承辦同仁字母對應回填（A 張坤樹／B 洪慶忠／C 邱元宏／D 曾廷睿／Y 洪慶忠，5/5 完整）。

**dry-run 工具已備妥且預設不寫入**：`scripts/sync/backfill_case_code_ck.py`

    待轉換 175／新案號互異 175／與既有 292 個案號逐筆實查零相撞
    轉換後可直接成案 95／仍被防重擋 80／缺合約金額 0

待 owner：

| # | 議題 |
|---|---|
| **A** | 175 筆轉換要不要執行（`--apply`；執行前先完整備份） |
| **B** | 80 筆同名的是「已建過只是沒接上」還是「不同案」 |
| **C** | 26 組分身（`B114-B003` vs `B114-B003-0`）—— ⚠️ 有碼那一側都有金流，**不要當漏記帳去補** |
| **D** | 3 筆廠商姓名矛盾哪個對（`林晉廷` vs `林宥廷` **是不同的字**） |
| **E** | 金粟科技 320 萬應付（4 期）沒有合約經費 ⇒ 依「合約經費是上位」規範，那 320 萬沒有上限在管 |

⚠️ **第 6 步（匯入服務補呼叫建案／成案程序）有順序相依**：必須等 A 執行完才能做。
反過來先改匯入 ⇒ 新舊制比對不上 ⇒ **每次匯入都重複建案**（08-20 造成 36 組重複的同型）。

---

## 9. 🔴 重啟後最優先查的一件事（08-28 11:xx 新發現）

**公文附件的異地備份只涵蓋 1,552 檔裡的 120 檔 —— 92% 從未備份，而它每天回報正常。**

    backend/uploads 實際          1,552 檔 / 1.2G
    manifest_20260828 列出          120 檔
    在 uploads 但不在 manifest    1,432 檔（92%）

七份 manifest（08-22~08-28）數字**完全相同**：`total=120 copied=0 skipped=120`。
「copied=0」看起來像「沒有新東西要備份」，實際是「**它只看得到那 120 個**」。

**分布是決定性的**：manifest 只涵蓋 `2026/01`(44) + `2026/02`(76)，
漏掉的是 **2026/03 起全部**，外加 `pm_attachments`／`asset_photos`／`receipts`
三個目錄整個不在範圍。`attachments_latest` 最後修改停在 **5/18**、
目錄快照停在 **2026-03-09** —— 三個訊號一致。

⚠️ **長檔名那條線是岔路，只解釋 2 個檔**（且機制早已處理：`remote_backup.json`
寫著「附件 2 檔為長檔名，已打包 1 個目錄」）。
`LongPathsEnabled` **已經是 1**、來源最長路徑 213 字元、超過 260 的 **0 個**。
CK_Website 後來查出的真限制是**檔名的 UTF-8 位元組數 > NAME_MAX 255**
（Windows 算 UTF-16 字元＝122 合法，Linux/NAS 算 UTF-8 位元組＝268 非法），
**那個診斷是對的、我用自己的資料驗證過** —— 但它不是這 1,432 檔的原因。

**重啟不會改變也不會修復這件事**，但它是目前已知最嚴重的一項。
細節與待查項見 `OPEN_ITEMS_20260819.md` **A38**。

⚠️ **我刻意沒有在重啟前動備份機制** —— 改備份是高風險操作，重啟前不是做它的時機。
