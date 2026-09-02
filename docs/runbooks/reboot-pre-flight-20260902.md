# 重啟前狀態固定與復原指引（2026-09-02）

> 用途：**重啟後要能分辨「本來就有的」與「重啟造成的」。**
> 前一份：`reboot-pre-flight-20260901.md`（其第 0 節的 A66 段落仍有效，見下方 §4）

---

## 0. ⛔ 關機前必做三件事（做完再關）

| # | 事情 | 誰做 | 為什麼是關機前 |
|---|---|---|---|
| **1** | **`git push origin main`（203 commits）** | **owner** | 我做不到 —— push 被權限分類器擋下（慢性紅燈 34 記載的就是這件事）。<br>**這台機器的磁碟今天壞過一次**，203 個 commit 目前只存在於這一顆磁碟上 |
| **2** | **啟動 `mdsched`（A66-P3）** | **owner** | 我沒有管理員權限，`bcdedit` 設不了。<br>**它必須在重開機時才能跑**，今早兩次重開機都錯過了 |
| **3** | 決定要不要部署 scheduler 修法 | owner | 三態退出碼修法**只在 host 檔案裡**（`backend/app/` 未掛載、程式碼在映像裡）。<br>不部署的話，明天 02:00 的 daily 仍是舊行為 |

### 1 — 推送

在 Claude Code 的輸入框直接打（`!` 前綴會在這個 session 裡執行）：

```
! git push origin main
```

### 2 — 記憶體診斷

兩種都可以，選一個：

```
# 方式 A：GUI（會問「立即重新啟動並檢查」或「下次啟動時檢查」）
mdsched

# 方式 B：命令列（需要**系統管理員**的 PowerShell / cmd）
bcdedit /bootsequence {memdiag}
```

**預期**：開機時先跑 30–60 分鐘記憶體測試，期間電腦不能用、公網也還沒回來。
**結果去哪看**：測完進入 Windows 後，事件檢視器 →
`Windows 記錄 → 系統`，來源 **`MemoryDiagnostics-Results`**。
或直接：

```powershell
Get-WinEvent -LogName System -MaxEvents 3000 |
  Where-Object { $_.ProviderName -like "*MemoryDiagnostic*" } |
  Select-Object TimeCreated, Id, Message | Format-List
```

⚠️ **本機從未執行過記憶體診斷**（2026-09-02 實查，該來源 0 筆事件）。
所以「查不到結果」＝**還沒跑**，不是「跑了沒問題」。

### 3 — 部署（可選）

```bash
bash scripts/deploy/deploy-public.sh
```

---

## 1. 重啟前基線（2026-09-02 10:45 實測）

| 項目 | 值 |
|---|---|
| 容器總數 | **56**（unhealthy / Restarting = **0**） |
| documents | **2,047** |
| canonical_entities | **50,189** |
| 公網 `/api/health` | **8/8 為 200**（多次抽樣，L76 殭屍埠） |
| 容器死亡事件總計 | **58 筆**（`backend/logs/container_die_events.log`） |
| **今日 09:46 重開機以來的死亡事件** | **0 筆** |
| `ck_missive_backend` RestartCount | **1**（來自 10:18 Docker Desktop 自行重啟，非崩潰） |
| 未推送 commit | **203** |
| 最新備份 | `ck_missive_backup_20260902_015959.sql` 538 MB（本地 D:\ ＋ NAS 雙份）＋附件 1,572 檔 |

⚠️ **「重開機以來 0 筆崩潰」不足以說明任何事** —— 觀測窗只有約 1 小時，
而重啟前的**最長間隔是 109 分鐘**。這個安靜同時相容於「修好了」與「還沒輪到」。

---

## 2. 重啟後檢查清單（依序）

```bash
# 1. Docker engine 起來了嗎
docker desktop status          # 期望 running
docker ps -q | wc -l           # 期望 56 左右

# 2. ⛔ 若卡在 starting 超過 5 分鐘 —— 不要再等，去看 dmesg
wsl -d docker-desktop dmesg | grep -iE "JBD2|EXT4-fs|segfault|I/O error"
#    → 出現 JBD2 / journal recovery failed
#      ＝ 今天那個事故重演，走 docker-ext4-journal-corruption-20260902.md

# 3. 業務量（不是只看容器 Up；/api/health 是靜態 dict，DB 掛了也回 healthy）
curl -s http://localhost:8001/health | grep -o '"documents":[0-9]*'
#    期望 2047（少於 100 或查不到 ⇒ 空殼 volume，見 L43）

# 4. 公網 —— **多次抽樣**，單次 200 不足以證明埠轉發是好的（L76）
for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{http_code} " https://missive.cksurvey.tw/api/health; done

# 5. A66 是否還在（這是這次重開機真正要回答的問題）
wc -l < backend/logs/container_die_events.log     # 基線 58
docker inspect -f '{{.RestartCount}}' ck_missive_backend
```

### 判讀 A66

| 觀察 | 意義 |
|---|---|
| 數小時後死亡事件仍為 0，且 `mdsched` 也乾淨 | 好消息，但**兩者都不是證明** —— 繼續留樣本 |
| 死亡事件又開始累積 | 重開機無效（與 `wsl --shutdown` 一樣），硬體嫌疑上升 |
| `mdsched` 報出錯誤 | **結案**：換記憶體 |

---

## 3. 這次重啟**沒有**的風險（與 08-31 那份不同）

08-31 的指引第 0 節警告「今日修法只在容器裡、映像沒有 ⇒ `--force-recreate` / `down` 會全部消失」。

**這一次沒有這個問題**：今天所有修法都在 host 的檔案上
（`scripts/*.sh` 的 CRLF、`backend/app/core/scheduler.py`、文件），
沒有任何一項是直接改容器內部。重開機不會讓它們消失。

⚠️ 唯一的反面：**`scheduler.py` 的三態修法也因此還沒生效**（見 §0 第 3 項）。

---

## 4. A66 現況摘要（完整版見 CLAUDE.md 檔頭與 OPEN_ITEMS）

**今天證據換了一個類別**：此前全部是「行程崩潰」（139 / 136 / 1），
今天新增「**靜態資料的校驗碼對不上**」——

```
Directory inode 1707113, block #0: directory passes checks but fails checksum.
```

目錄結構通過所有檢查、只有 checksum 不符。若是磁碟或驅動層問題，
壞掉的通常是整個區塊；「內容對、校驗碼錯」是**單一位元翻轉**的簽名。

加上停機前崩潰率**單調加速**（09-01 10時 1 次/小時 → 23時 **19 次/小時**，
軟體缺陷通常是穩定速率）。

### 已逐項排除（實測，非推測）

我們的原生擴充／httptools・uvloop／numpy 版本／共用基底映像（3.11 與 3.13 都中）／
記憶體壓力（MemAvailable 全程 13–14 GiB）／容器 OOM／單一壞核心／
**VM 累積狀態（`wsl --shutdown` 後 4 小時內又 6 筆）**。

**最有資訊量的一筆**：`runc` 也在 `libc.so.6` 裡 segfault ——
runc 不是 Python，所以這不是任何語言執行期或套件的問題。

### 剩下的候選

* WSL2 核心 `6.6.87.2-1` 或 Docker Desktop `29.7.2` 的缺陷
* **硬體記憶體** —— WHEA 近 3 天 0 筆，但**消費級非 ECC 常常不產生 WHEA**，
  所以這一項**沒有被排除**。⇒ 這就是 §0 第 2 項存在的理由。

---

> 建立：2026-09-02 10:45
> 相關：`docker-ext4-journal-corruption-20260902.md`（今天的事故）／
> `reboot-pre-flight-20260901.md`（前一份）／L130–L134
