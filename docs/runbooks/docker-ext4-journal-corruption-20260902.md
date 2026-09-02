# Docker 資料磁碟 ext4 journal 損毀 → 公網 1033 全站下線（2026-09-02）

> **等級**：P0（公網全站不可用約 10 小時，00:57 最後一次崩潰 → 10:09 修復）
> **與既有 runbook 的關係**：`docker_engine_wedge_1033_recovery`（記憶檔）描述的是**另一個**成因。
> 那一份的修法（kill `docker-mcp.exe` → `docker desktop start`）在本案**完全不適用** ——
> 本案機器上根本沒有 `docker-mcp.exe` 行程。**症狀相同，成因不同。**

---

## 0. ⭐ 這次最該記住的一件事

**Docker Desktop 的狀態欄一路顯示 `starting`，從來沒有顯示過 `error`。**

它在無限重試掛載一顆掛不起來的磁碟，而對外的表述是「還在啟動中」。
於是**一個永遠不會完成的啟動，與一個很慢的啟動，在狀態欄裡長得一模一樣**。

我自己第一時間就把它讀成「機器 8 分鐘前才開機，engine 還沒起來」——
那個判讀完全合理（開機時間是真的、Docker Desktop 啟動時間是真的），
而且它讓我決定「先做別的，稍後再看」。**若不去翻 VM 的 dmesg，這個等待可以持續一整天。**

判準：**`docker desktop status` 回 `starting` 超過 5 分鐘，就不要再等，去看 dmesg。**

```bash
wsl -d docker-desktop dmesg | grep -iE "JBD2|EXT4-fs|segfault|I/O error"
```

⚠️ 而且**不要相信 dmesg 裡的 `sdd`／`sde` 代號**——它每次開機會重排，見 §3.0。

## 1. 症狀

| 層 | 觀察 |
|---|---|
| 使用者 | `missive.cksurvey.tw` 回 **Cloudflare Error 1033**（Tunnel 無連線） |
| host CLI | `docker ps` → **500 Internal Server Error**，稍後變成 pipe「找不到檔案」 |
| Docker Desktop | `Status: starting`（**永遠**），`SessionID` 反覆更換＝它在重啟自己 |
| **VM 核心（真相在此）** | `JBD2: Invalid checksum recovering data block 231768510 in log`<br>`JBD2: journal recovery failed`<br>`EXT4-fs (sdd): error loading journal` |

⚠️ **每次重試都卡在同一個 block（231768510）** —— 這是損壞位置固定的訊號，
不是隨機的暫時性錯誤。

## 2. 因果鏈

```
記憶體位元翻轉（推定，見 §5）
  → 寫入 docker_data 的 journal 資料與其 checksum 不符
  → 重開機時 ext4 嘗試重放 journal → checksum 驗證失敗 → 拒絕掛載
  → Docker engine 沒有資料磁碟 → 起不來
  → cloudflared 容器沒跑 → Tunnel 無連線
  → 公網 1033
```

**注意**：`docker_data.vhdx`（356 GB）裡裝的是**全部**映像、容器層與 named volume，
**PostgreSQL 的資料就在裡面**。這顆磁碟掛不起來 = 整個系統下線。

## 3. 修復程序（本案實證有效，全程 3 分鐘）

### 3.0 ⛔ 先確認哪一顆才是 docker_data —— **不要相信裝置代號**

**`/dev/sdX` 的代號每次開機都可能重排。** 本案實測：

| 時間 | `/dev/sdd` 實際是誰 |
|---|---|
| 10:06（修復時） | `9334535a-…` ＝ **docker_data**（`Last mounted on: /mnt/docker-desktop-disk`） |
| 10:18（一次重啟後） | `bd6f718b-…` ＝ **main distro**（重啟前那是 `sde`） |

**同一個 `/dev/sdd`，12 分鐘後指向另一顆磁碟。**
照著寫死代號的步驟跑 `e2fsck -fy`，會修到錯的檔案系統。

每次都要重新認一次：

```bash
# docker_data 的身分特徵：Last mounted on = /mnt/docker-desktop-disk
for d in /dev/sd*; do
  echo "== $d"
  dumpe2fs -h "$d" 2>/dev/null | grep -E "Filesystem UUID|Last mounted on"
done
```

以下步驟一律把 `$DEV` 換成上面認出來的那一顆，**不要直接抄 `/dev/sdd`**。

### 3.1 先唯讀診斷，不要直接修

```bash
DEV=/dev/sdX   # ← 用 3.0 認出來的，不是抄來的
wsl -d docker-desktop dumpe2fs -h $DEV | grep -E "Filesystem state|features|Last mounted"
wsl -d docker-desktop e2fsck -fn $DEV     # -n = 唯讀，不寫入任何位元組
```

本案結果（**全部是良性的**）：

| 發現 | 數量 | 性質 |
|---|---|---|
| `extent tree could be shorter` | 31 | **最佳化建議，不是錯誤** |
| orphaned inode | 3 | 未完成刪除的殘留，例行 |
| 目錄 checksum 不符 | 2 | 「**passes checks but fails checksum**」＝內容對、校驗碼不對 |
| free block/inode 計數偏差 | 54 MB | 例行 |

**沒有** illegal block、**沒有** unattached inode、**沒有** 重複佔用區塊
⇒ 判定為「journal 未重放造成的一致性偏差」，`e2fsck` 可完全修復。

### 3.2 ⚠️ 修之前必須確認裝置沒有被掛載

```bash
wsl -d docker-desktop sh -c "mount | grep $(basename $DEV)"
```

**不要用 `grep -c` 看數字就下結論。** 本案 `grep -c` 回 `1`，
展開才看到 `/dev/sdd on /tmp/chk type ext4 (ro,relatime)`（當時 sdd 才是 docker_data） ——
那是 Docker Desktop 被 kill 時留下的殘影記錄（`umount` 回 `not mounted`）。
**在掛載中的裝置上跑 `e2fsck -y` 會毀掉檔案系統**，這一步不能靠推測。

### 3.3 停 Docker Desktop（停掉無限重試，避免掛載競爭）

```powershell
Get-Process -Name "Docker Desktop","com.docker.backend","com.docker.build" |
    Stop-Process -Force
```

⚠️ 不要用 `wsl --shutdown` —— 那會連 distro 一起停掉，`/dev/sdd` 就消失了，
反而做不了修復。**要停的是 Docker Desktop，不是 WSL。**

### 3.4 修復

```bash
wsl -d docker-desktop e2fsck -fy $DEV
```

本案 14 秒完成、**零錯誤輸出**；inode 4,577,361 → 4,577,226（殘留已清）。

### 3.5 驗證旗標真的解除了

```bash
wsl -d docker-desktop dumpe2fs -h $DEV | grep "Filesystem features"
```

修復前 features 含 **`needs_recovery`**，修復後該旗標消失 ⇒ 這是「真的修好了」的證據，
不是「fsck 沒報錯」。**`fsck` 沒報錯與 `needs_recovery` 已清除是兩回事。**

### 3.6 啟動並驗證掛載

```bash
# 啟動 Docker Desktop 後
wsl -d docker-desktop dmesg | grep "EXT4-fs"
# 要看到：mounted filesystem ... r/w with ordered data mode
```

## 4. 驗收（不能只看容器起來）

| # | 驗什麼 | 為什麼 |
|---|---|---|
| 1 | 容器全數 Up | 基本 |
| 2 | `/health` 的**業務量**（documents / canonical_entities 筆數） | `/api/health` 是靜態 dict，postgres 掛掉照樣回 healthy（CLAUDE.md 08-30 記載） |
| 3 | 公網 200，且**多次抽樣** | L76 殭屍埠是間歇性的，單次 200 不足以證明埠轉發是好的 |
| 4 | 容器重啟次數（A66 是否繼續） | 本次事故的上游假設仍未排除 |

## 5. 與 A66（全機隨機 segfault）的關係

**本案是 A66 迄今最強的一筆證據，而且它換了一個證據類別。**

在此之前 A66 的證據全部是「行程崩潰」（139/136/1）。本案新增的是
**「靜態資料的校驗碼對不上」** —— 兩者的交集只有一個解釋：**記憶體內容被改動過**。

特別是這一行：

```
Directory inode 1707113, block #0: directory passes checks but fails checksum.
```

**目錄結構本身通過了所有檢查，只有 checksum 不符。** 這正是單一位元翻轉的簽名 ——
若是磁碟或驅動層的問題，壞掉的通常是整個區塊而不是「內容對、校驗碼錯」。

### 尚未排除

`mdsched`（Windows 記憶體診斷）**從未執行過**。2026-09-02 早上 owner 重開機兩次
（09:00:55、09:46:24，皆為正常關機、無 Kernel-Power 41），**兩次都錯過了**。
WHEA 事件近 3 天 0 筆，但消費級非 ECC 記憶體的錯誤常常不產生 WHEA ⇒ **未排除**。

⇒ 待辦 **A66-P3**：下次重開機時跑 `mdsched`。

## 6. 預防

| 做什麼 | 為什麼 |
|---|---|
| `docker desktop status` 卡 `starting` > 5 分鐘 → 直接看 dmesg | 見 §0 |
| 保持 daily 02:00 備份 | 本案備份完好（本地 D:\ ＋ NAS 雙份，538 MB dump ＋ 附件 1,572 檔），**是它讓「直接修」變成可接受的風險** |
| 不要把「重開機」當成通用解 | 本案重開機**兩次都沒有解決**，因為損壞在磁碟上而不是在記憶體狀態裡 |

---

> 建立：2026-09-02
> 實證：全程指令與輸出見本次 session
> 相關：A66（全機 segfault）／記憶檔 `docker_engine_wedge_1033_recovery`（另一成因）／L76（殭屍埠）
