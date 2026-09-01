# 重啟前狀態固定與復原指引（2026-09-01）

> 用途：**重啟後要能分辨「本來就有的」與「重啟造成的」。**
> 前一份：`reboot-pre-flight-20260831.md`（那一份的第 0 節已解除，映像已對齊）

---

## 0. ⛔ 這一次最重要的一件事：**全機 Python 行程隨機 segfault，`wsl --shutdown` 沒有解決**

**這不是 CK_Missive 的問題，也不是任何單一 repo 的問題。**

### 證據鏈（三層獨立確認）

| 層 | 觀察 |
|---|---|
| **應用層** | `ck_missive_backend` 一天重啟 17 次；三種死法 **136(SIGFPE) / 1(TypeError) / 139(SIGSEGV)** |
| **跨 repo** | 8 分鐘內 **3 個不同 repo 的 HTTP 後端全部 SIGSEGV**（CK_AaaP 統計 P = 3.5×10⁻⁵） |
| **核心層** | `wsl -d docker-desktop dmesg`：故障在 **`libpython3.11.so`／`libc.so.6`／`python3.13`** 裡 |

### ⭐ 已排除的（逐項實測，不是推測）

| 假設 | 為什麼排除 |
|---|---|
| 我們的原生擴充（torch/cv2/sklearn） | **沒裝它們的 repo 照樣崩潰** |
| httptools / uvloop | 版本不同（0.6.4 vs 0.8.0）；**uvloop 我們根本沒裝** |
| numpy / scipy 版本 | 三家版本互不相同 |
| 共用基底映像 | **Python 3.11 與 3.13 都中**，那是不同映像 |
| 記憶體壓力 | Prometheus 實測窗口內 MemAvailable 全程 13.3–14.1 GiB |
| 容器記憶體 / OOM | 443MB/23GB、無成長、`OOMKilled=false` |
| **VM 累積狀態** | **`wsl --shutdown` 後 4 小時內又 6 筆故障** ⇒ 重啟不解決 |
| 單一壞核心 | dmesg 顯示 `CPU 6 (core 3)` 與 `CPU 1 (core 0)` 都中 |

### ⭐ 最有資訊量的一筆

```
runc:[2:INIT][23362]: segfault at ... in libc.so.6[...]
```

**`runc` 不是 Python。** 故障不限於 Python 行程 ⇒ **這是整個 WSL2 VM 的問題**，
而不是任何語言執行期或套件的問題。

### 剩下的候選（我沒有能區分它們的證據）

* WSL2 核心 `6.6.87.2-1` 或 Docker Desktop `29.7.2` 的缺陷
* **硬體記憶體**（⚠️ WHEA 事件近 3 天 **0 筆**，但**消費級非 ECC 記憶體的錯誤常常不會產生 WHEA**，所以這一項**沒有被排除**）

### ⇒ 這對重啟的意義

| 方式 | 預期 |
|---|---|
| `wsl --shutdown` | **已試過，無效**（重啟後 4 小時內 6 筆故障） |
| 機器重開 | 未試。若是 VM／驅動層的累積狀態，可能有效 |
| **記憶體診斷 `mdsched`** | **未試**。需重開機並跑數十分鐘，但這是唯一能排除硬體的方法 |

**下次重啟時建議順便跑一次 `mdsched`** —— 那是目前唯一還沒被檢驗的候選，
而且它需要的正好是一次重開機。

---

## 1. 重啟前的量測基線（2026-09-01 實測）

| 項目 | 值 |
|---|---|
| 公網 `/api/health` | 200（重啟後三次抽樣 502/200/200，第一次是後端啟動窗口） |
| 業務量 | documents **2,047**｜canonical_entities **50,184**｜pm_cases **253**｜contract_projects **226**｜erp_quotations **257**｜erp_billings **63** |
| 容器 | **56** 個 Up（`wsl --shutdown` 後 55，`ck-platform-prometheus` 未自動回來，屬 CK_AaaP） |
| Alembic head | `20260830a001` |
| **容器 vs 映像** | **一致** —— 怎麼重啟都不會失去修法（與 08-31 那份最大的不同） |
| CK_Missive 未推送 | **199** ⚠️ 需 owner 執行 `! git push origin main` |

### 重啟後應該仍在的既有紅燈 —— **不是重啟造成的**

* **全機 segfault**（見第 0 節）—— 重啟後仍會發生，`RestartCount` 會繼續漲
* weekly 長期紅燈 13 支，登記於 `scripts/checks/.chronic_red_registry.json`
* A17 FT_StorageTank 三個訊號｜A55 `ck-showcase-audit`｜A56 區網＝超級管理員

---

## 2. 重啟後的複驗清單（照順序）

```bash
# ① 容器與公網（三次抽樣 —— 單次 200 不足以證明埠轉發，L76）
docker ps -q | wc -l                       # 期望 56
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code}\n" \
  --max-time 20 https://missive.cksurvey.tw/api/health; sleep 3; done

# ② 業務量（零筆增減）
docker exec ck_missive_backend python -c "..."   # 對照第 1 節的六個數字

# ③ 容器 vs 映像（這一次應該是一致的）
python scripts/checks/container_image_freshness_check.py

# ④ 重啟迴圈（今日新增，daily 15）
python scripts/checks/container_restart_loop_check.py
#    ⚠️ 它會分辨「容器被重建（部署）」與「又重啟了」——
#       重開機後第一次跑會顯示「容器已重建，基準重設」，那是正常的

# ⑤ 核心層是否仍在報故障（決定重啟有沒有效的唯一依據）
wsl -d docker-desktop dmesg | grep -E "segfault|general protection fault"
#    ⚠️ 緩衝只涵蓋開機後。**「沒有故障」在頭幾小時內同時相容於
#       「修好了」與「還沒輪到」** —— 重啟前最長間隔 109 分鐘，
#       至少觀察數小時才有意義。
```

---

## 3. 今日變更摘要（重啟後若行為與預期不符，先看這裡）

### 下拉選單（owner 從 `/documents/2748` 回報選不到案件）

* 承攬案件 226 筆而下拉寫死 `limit: 100` ⇒ 第 144 名的那筆選不到。
  **它前一天還在界內（第 93 名）**，是當天成案 51 筆把它擠出去的。
* PM 案件 253/100、機關 99/100（下一筆就破）—— 一併放寬到 1000
* 新增 `useSearchableOptions`（伺服器端搜尋，**尚未接線**＝A65）
* 後端 `search` 從「只比對案名」擴充到案名／成案編號／建案案號

### 成案（owner 裁示「已承攬案件建立成案編號」）

* 91 筆已承攬未成案 → **成案 51 筆**，剩 40 筆是**同一件工作建了兩次案**（A61）
* 逐組對照：`docs/runbooks/quotation_revision_dups_20260901.md`

### 新增的守門（都做過負向對照）

| 排程 | 檢核 | 負向對照 |
|---|---|---|
| **daily 15** | 容器重啟迴圈（間歇 502 的來源） | 3/3 |
| **weekly 95** | 下拉取數上限 vs 資料筆數 | 4/4 |
| **weekly 96** | 設定目錄 SSOT（不得長出第三個） | 2/2 |

### 設定目錄收斂（A63）

* `config/`（只裝一個過期複本）與兩份非權威的 `remote_backup.json` 已標
  `_remove_after: 2026-09-15`，**P1 只標記不刪**
* P2 移除需 owner 再確認一次

---

## 4. 待 owner 決定（重啟不影響，但別忘了）

| 項目 | 內容 |
|---|---|
| **推送** | **199 個 commit 未推送** —— `! git push origin main` |
| **記憶體診斷** | 下次重開機順便跑 `mdsched` —— 唯一還沒被檢驗的候選 |
| **A61** | 40 筆重複建案逐案判斷（清冊已備） |
| **A57-舊** | 已成案的 136 筆 `pm_cases` 要不要刪 |
| **A63 P2** | `config/` 目錄移除（09-15） |
| **A64** | SSO 到期靜靜變「訪客」（`X-Reauth-Required` 程式碼裡一個都沒有，期程 09-08） |
| **A65** | 下拉接伺服器端搜尋的時機 |
| **A56** | 區網＝超級管理員 |
