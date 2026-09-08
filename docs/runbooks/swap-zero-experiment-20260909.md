# `swap=0` 判別實驗（owner 排定 2026-09-09 重啟時執行）

> `lifecycle: status=current reviewed=2026-09-09 owner=CK_Missive`
>
> 目的：分辨 A127 的核心層故障是**主機 RAM 本體**還是 **WSL2 的換頁路徑**（磁碟／vhdx）。
> 完整脈絡見 `docs/architecture/OPEN_ITEMS_20260819.md` 的 A127。

---

## 0. 為什麼是這個實驗，而不是先跑 memtest

| | 完整記憶體診斷（mdsched Extended／memtest86+） | `swap=0` |
|---|---|---|
| 時間 | 整夜，期間電腦不能用 | 約 10 分鐘（重開 WSL） |
| 能分辨什麼 | 只回答「RAM 有沒有壞」 | 直接移除換頁路徑 ⇒ 故障若消失＝路徑；若照舊＝回到 RAM |
| 已知的弱點 | **09-08 21:27 開機時已自動跑過一次 Standard 並 PASS** ⇒ 下一個綠燈不具排除能力 | 只移除變因、不解釋成因 |

⇒ 先做便宜且能分辨的那一個。**若 `swap=0` 之後故障照舊，才值得花一整夜跑 Extended。**

## 1. 現況（2026-09-09 06:2x 實測）

```
%UserProfile%\.wslconfig
[wsl2]
memory=24GB
swap=4GB
processors=8
```

主機實體記憶體 **63.8 GB**，WSL 只用其中 24 GB ⇒ 主機端有 40 GB 餘裕。

⚠️ **不要同時調 `memory=`**。整夜的價值就在於沒有一次同時動兩個變數
（AaaP 03:xx 拒絕停 keep-warm 的理由，同一條）。這一輪**只動 `swap`**。

## 2. 執行步驟

### 2.1 前置（重啟前，約 1 分鐘）

```bash
# 記下起點，實驗後要比對
docker run --rm --privileged alpine sh -c 'dmesg | grep -cE "segfault|general protection"; cut -d. -f1 /proc/uptime'
```

把數字抄下來。**dmesg 環形緩衝在重開 WSL 後會全部清空**，所以帳本要靠
`CK_AaaP` 的 `snapshot-kernel-faults.py`（它是唯一不會掉的那一份）。

### 2.2 改設定

編輯 `%UserProfile%\.wslconfig`，把 `swap=4GB` 改成 `swap=0`：

```ini
[wsl2]
memory=24GB
swap=0
processors=8
```

### 2.3 重開

```powershell
wsl --shutdown
# 等 10 秒，再啟動 Docker Desktop
```

⚠️ **這會停掉整台機器的所有容器**（不只 Missive），約 5–10 分鐘全平台中斷。
執行前請廣播給其他 session。

**影響面（CK_AaaP 06:3x 實測，比「全機停」精確）**：

| 對象 | 實驗期間 |
|---|---|
| 56 個容器、公網 5 站（cloudflared 也是容器）| **全停** |
| `:5200` 平台前端（`node.exe`、Windows Session 0）| **不受影響** |
| `:5201` 平台後端（`python.exe`、Session 0）| **不受影響** |
| pm2 daemon 與其服務 | **不受影響** |

⚠️ **但 `:5201` 會「活著而答錯」**：它的整合狀態、容器統計、觀測查詢全部依賴 Docker，
而那 5–10 分鐘內 Docker 不存在 ⇒ **它會回 200 而內容是降級的**。
別把那段時間的讀數當成平台健康的證據。

✅ 好消息：`wsl --shutdown` **不重開 Windows** ⇒ 今晚最脆弱的那條復原鏈（pm2 resurrect）
這次不會被觸發。

**時間上避開 19:00**：`CKProject_DailyBackup`（robocopy `/MIR` → NAS）昨晚被斷電殺掉、
今日這輪要補齊。落在 19:00 前後會互相干擾兩次 —— 備份需要容器裡的資料檔穩定，
而它本身是重 I/O，**會汙染「實驗後有沒有換頁」的觀察**。

### 2.4 驗證設定真的生效

```bash
docker run --rm --privileged alpine sh -c 'grep SwapTotal /proc/meminfo'
```

**必須看到 `SwapTotal: 0 kB`。** 看到 4194304 就是設定沒吃到
（`.wslconfig` 位置錯、或 Docker Desktop 沒有真的重開）——那時**不要繼續**，
否則後面幾小時的觀察是在錯的前提上做的。

## 3. 觀察與判讀

### 3.1 要跑的負載

故障是陣發的，光是「安靜」不算證據。跑與昨夜相同量級的工作：

```bash
bash scripts/deploy/deploy-public.sh            # 完整建置＋換容器
cd backend && python -m pytest tests/unit -q     # 約 4,500 筆
```

### 3.2 判準（**先寫下來，不要事後定義**）

| 觀察 | 結論 |
|---|---|
| 24 小時內 0 筆核心故障，且期間跑過上述負載 | **強烈指向換頁路徑**（磁碟／vhdx）⇒ 下一步查 `docker_data` 那顆磁碟（L130 記過它 e2fsck 有殘留 inode） |
| 24 小時內仍有故障 | **換頁路徑被排除** ⇒ 回到 RAM，值得花整夜跑 memtest86+ |
| 出現 OOM kill（`dmesg` 有 `Out of memory` 或容器 `OOMKilled=true`） | 這是移除 swap 的**預期副作用**，不是新故障。若頻繁到影響服務，回滾（見 §4）並改用 `swap=1GB` 再試 |

⚠️ **24 小時是最低門檻**：昨夜最長的自然安靜期是 3.51 小時，AaaP 台帳的硬判準是 19.81 小時。
少於 24 小時的安靜**不足以下結論**。

⚠️ **讀數時必須記下「期間有沒有跑重活」**（AaaP 強調，這是最容易被省略的一步）：
今晚已經證明有沒有負載會改變基準 —— Missive 的部署 77 頁/秒零故障、DT 兩次 47 分鐘
測試套件零故障。**24 小時零故障但期間完全沒有負載，證據力遠低於 24 小時零故障且跑過
部署＋pytest。**

**證據凍結（實驗前的基準，已由 CK_AaaP 備妥）**：
`CK_AaaP/platform/evidence/kernel-faults-20260909-pre-swap-zero.jsonl`，**271 筆**、
跨 3 個 `boot_id`、本次開機 150 筆。⚠️ 平台的活狀態帳本**不在版控**（`.gitignore` 刻意排除，
理由是機器層狀態每次執行都會變）—— 所以凍結副本另存一份，那是實驗後唯一能比較的基準。

### 3.3 每小時採一次

```bash
docker run --rm --privileged alpine sh -c 'dmesg | grep -cE "segfault|general protection"; grep -E "SwapTotal|MemAvailable" /proc/meminfo; head -1 /proc/pressure/memory'
```

另外對照 `docs/health/majflt_baseline_20260909.json`（平靜期的每行程主要缺頁基準，
採樣指令在同目錄的 README，**`--pid=host` 不可省**）。

## 4. 回滾（隨時可做，約 5 分鐘）

把 `.wslconfig` 的 `swap=0` 改回 `swap=4GB`，再 `wsl --shutdown` 並重開 Docker。
沒有資料風險 —— swap 是暫存，不含持久資料。

## 5. 重啟前的其他事項

沿用 `docs/runbooks/reboot-pre-flight-20260908.md` 的關機前清單與重啟後 5 步檢查。
額外兩件（2026-09-09）：

1. **未推送必須為 0**（本 session 每次改動都已推送，重啟前再確認一次）。
2. **NAS 上 08-14 那份 dump 已移出輪替**（`missive_databsae/known_good_pre_20260815/`），
   那是 08-15 爆發期之前最後一份乾淨參考，不受 30 天輪替影響。
