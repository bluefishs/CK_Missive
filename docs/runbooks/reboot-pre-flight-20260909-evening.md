# 重啟前狀態固定與復原指引 — 2026-09-09 晚（v6.76 晚間基線）

> `lifecycle: status=current reviewed=2026-09-09 owner=CK_Missive`
>
> 用途：**今晚的重啟不是例行重啟，是主機層記憶體故障（A127）的實驗**。
> 重啟後要能分辨三種東西：本來就有的／重啟造成的／實驗改變的。
> 09-08 那份（`reboot-pre-flight-20260908.md`）的通用檢查照用；本檔只寫今晚特有的。

## 0. 今天主機層發生了什麼（給做決定的人）

| 時間 | 事實（誰量的） |
|---|---|
| 12:04 | 主動重啟（事件 1074）；開機後 8 分鐘內 6 次段錯誤，swap 一位元組沒用（CK_Website） |
| 12:12–14:47 | 安靜 2h35m |
| 14:47–15:58 | 12 次段錯誤，五個容器四個 repo（lvrland 重啟 5、tunnel exporter 5、missive 4、hermes ×2）（CK_Website 全量 dmesg） |
| 15:58:58 | 公網 502 約半分鐘（本 repo 視覺走查拍到） |
| 16:0x–16:44 | dmesg 18 → 46；missive RestartCount 4 → 11（本 repo） |
| 16:40–16:55 | **應用層放大**：容器被拉回後 mapper 懶配置競態毒化 ⇒ 每個 ORM 請求 500（含 Google 登入）15 分鐘（本 repo，已修 `2ccfe1d5`） |
| 16:44–17:05 | 安靜 21 分鐘（dmesg 仍 46） |
| **17:09–17:12** | **重開不是 owner 主動，是 Windows Update 發起**（CK_Website 實測 System 1074 ×2：17:09:30 MoNotificationUx「Service Pack 計劃之中」→ 17:11:27 開機 → TrustedInstaller 再重啟 → 17:12:32 開機）；**裝了三個新 KB**：KB5124007／KB5124008（Security）、KB5126052（17:12:33 Installed）。⇒ 主機層變更表多一列；08-12 那組 LCU 已被今天的取代，**選項 B「回退 08-12」已不可行**；而換到 9 月 LCU 後故障照樣 312 s 起 ⇒ 新 LCU 沒有讓它消失。`.wslconfig` 這次未改（見下） |
| **17:17–17:25** | **第六波：開機後 312–762 s 共 21 筆**（hermes python3.13 ×8／uvicorn 3.11 ×8／celery ×1／python3 ×2）；missive backend 17:14–17:26 被拉回 **12 次**（每 1–2 分鐘一次，其中一次死在啟動中），公網間歇 502，owner 儲存公文失敗；swap 仍 0 used、MemAvailable 15.7 GB（本 repo 實測） |
| 17:25–17:30 | 暫靜（dmesg 停在 21）；公網 3/3 200 |
| 17:36–17:54 | 續發：dmesg 21→**27**；missive 拉回 **15** 次；CK_Website 量到 swap 首次有 14 MB 用量 |
| **17:55–18:02** | **實驗①執行（owner 17:5x 拍板）**：先 `pg_dump -Fc`（容器內 15.14，173 MB／93 表）到 `backups/pre_wslconfig_revert/`；`.wslconfig` 還原為 08-19 版（memory=24GB／swap=4GB／processors=8；10:43 版另存 `.wslconfig.bak-20260909-104300-pagereporting-variant`）；`compose stop` Missive → `wsl --shutdown` 17:56:54 → Docker Desktop **3.5 分鐘沒自行拉回引擎**（distro Stopped、backend 行程還在）→ 18:00:47 重啟 Docker Desktop → 18:01:12 引擎回來 → `compose start` Missive。VM 新開機 `free -m` Swap 4096 ⇒ 設定生效。拉回後 57 容器全 Up、五站 200、`/uploads` 未登入 401、mapper 啟動期配置那一行有 |
| **18:01（VM uptime 19–20 s）** | **⛔ 實驗①結果＝陰性**：新 VM 開機 **19.7 s** uvicorn segfault（`error 15`，ip＝資料位址）、**20.0 s** hermes segfault（`at ab ip 5625fb`，與 boot3 五筆同址）。pageReporting／autoMemoryReclaim／swap 8GB 都拿掉了，故障不但沒消失、還比任何一次冷開機都早（此前最早 168 s）。⇒ **10:43 那份 `.wslconfig` 既不是起因也不是放大器**；今天四波變密要另找解釋（候選：今天 17:12 新 LCU？但 12:04 那波在它之前）。 |

> **崩潰位址不是隨機的（boot3 dmesg 27 筆統計）**：hermes（python3.13 靜態二進位）9 筆裡 **5 筆同一 ip `0x5625fb`、故障位址都是 `0xab`／`0xaa`／`0xa8`**；
> uvicorn（libpython3.11.so）12 筆的頁內偏移只有 **三個值重複出現**（`…f5c` ×3、`…d9f` ×3、`…cfc` ×2；基址因 ASLR 不同、偏移相同）。
> 讀法：兩個版本的直譯器都在**少數幾個固定的程式點**（讀物件標頭 `ob_type`／`tp_flags` 那類偏移 0xa8–0xab）踩到 NULL 或垃圾指標
> ⇒ 是**堆上的 Python 物件指標被改壞**，不是指令本身壞。這與「RAM 位元翻轉」和「客體核心把使用者頁面弄壞」兩個假說都相容，
> 與「某支程式的邏輯錯」不相容（四 repo、兩個 Python 版本、同一形狀）。**能分辨兩者的仍是 memtest 延長模式**。

結論不變：**與程式無關、與記憶體壓力無關**（swap 未用即發作）。候選＝RAM 硬體／08-12 Windows 累積更新。

> ⚠️ **17:30 新事實（本 repo 實測，推翻上面「`.wslconfig`（08-19）晚於起點排除」的一半）**：
> `%UserProfile%\.wslconfig` 的 mtime 是 **今天 10:43**，由 `C:\Users\User1` 啟動的另一個 session 改的
> （備份 `.wslconfig.bak-20260909-104301`，內容是 08-19 版）。diff：`swap=4GB → 8GB`，**新增 `pageReporting=true`、
> `[experimental] autoMemoryReclaim=gradual`、`sparseVhd=true`**。⇒ **12:04 是第一次用這份設定開機**；
> 今天四波（12:12／14:47／16:0x／17:17）全在它之後，（⚠️ 我原本把 dmesg 的 `hv_balloon: Cold memory discard hint enabled with order 9` 讀成「page reporting 生效的訊號」——
> **錯**：18:01 拿掉 `pageReporting` 重開 VM 後這一行照印，它是 hv_balloon 的預設訊息，不能拿來判 `.wslconfig` 有沒有生效；
> 判生效看 `free -m` 的 Swap total 4096）。08-15 起點早於它，所以它**不是起因**；但它是今天新加入、而且正好碰記憶體頁面的變數，
> 段錯誤在今天明顯變密（此前最長安靜 3.51 h；今天 5 小時內四波）。**射程限制（CK_Website 17:45）**：08-15 起點用的是 03-24 版
> （`.wslconfig.bak-20260819`），08-19 換 swap=4GB 版之後故障也在 ⇒ 還原只能回答「今天的速率是不是被 10:43 那組放大」，不能回答「原因」。
> 實驗排序＝① 還原 `.wslconfig`（零成本）→ ② memtest 延長模式 → ③ 解除 KB5124008；一次一個、每個 ≥3.5 h 觀察窗；
> 診斷期間應暫停 Windows Update 自動重啟（今天 17:12 就是不受控變數）。**這不是實驗，是把一個沒登記的變更還原到已知狀態** ——
> 做法＝`cp .wslconfig.bak-20260909-104301 .wslconfig && wsl --shutdown`（全艦隊停 1–2 分鐘），要 owner 拍板，且做了就不能同時做選項 A／B。

## 1. 重啟前必做（owner）

```
# ① 推送（本機 32 個 commit 未推送；重啟後若磁碟／WSL 出事就沒了）
git push origin main

# ② 確認線上＝HEAD（1p 部署完成後 build 欄應為 2ccfe1d5，不是 -dirty）
curl -s http://localhost:8001/api/health/detailed | python -c "import sys,json;print(json.load(sys.stdin)['build'])"

# ③ 固定證據（dmesg 全文與艦隊重啟數，重啟就沒了）
docker run --rm --privileged alpine dmesg > docs/health/kernel/dmesg_20260909_evening_pre_reboot.txt
docker ps -a --format '{{.Names}} {{.Status}}' > docs/health/kernel/containers_20260909_evening.txt
```

## 2. 今晚的實驗（二選一，不要同時做——同時做就無法歸因）

### 選項 A：mdsched **Extended**（整夜，電腦不能用）
```
mdsched.exe   → 選「立即重新啟動並檢查問題」→ 開機測試畫面按 F1 → Test mix: Extended, Pass count: 2
```
結果在事件檢視器 `MemoryDiagnostics-Results`（事件 1201 乾淨／1102 有錯）。
⚠️ 09-08 21:27 跑過一次 **Standard** 乾淨——Standard 不足以排除（弱否定）。

### 選項 B：08-12 累積更新回退對照
```powershell
Get-HotFix | Where-Object HotFixID -in 'KB5121003','KB5120708','KB5123304'
wusa /uninstall /kb:5121003 /quiet /norestart   # 三筆依序，最後一筆才重啟
```
⚠️ 回退後**至少觀察 4 小時**（已知最長安靜期 3.51 h，今天最長 2h35m）才能說「有差」；
少於 4 小時的安靜不構成證據。回退對照只在 A 乾淨之後做才有歸因力（CK_Website P2-4）。

## 3. 重啟後檢查（依序；前五步同 09-08 §2）

```bash
docker ps --format "{{.Names}}\t{{.Status}}"                     # Missive 5 個 Up
curl -s http://localhost:8001/api/health/detailed | python -c "import sys,json;d=json.load(sys.stdin);print(d['build'])"   # 2ccfe1d5
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code} " https://missive.cksurvey.tw/health; sleep 2; done   # 200 ×3
python scripts/checks/deploy_verify.py                             # GREEN
# ⭐ 今晚新增：mapper 在啟動期配置（沒有這一行＝映像不是 2ccfe1d5）
docker logs ck_missive_backend 2>&1 | grep -c "mappers configured at startup"   # 1
# ⭐ 段錯誤基線歸零，之後每小時看一次（實驗驗收就是看這個數字 4 小時不動）
docker run --rm --privileged alpine sh -c 'dmesg | grep -cE "segfault|general protection"; cut -d. -f1 /proc/uptime'
docker inspect ck_missive_backend --format 'RestartCount={{.RestartCount}}'     # 0
```

## 4. 已知會紅、不是重啟造成的

| 項目 | 狀態 |
|---|---|
| weekly 134 R1 | RED 3 筆（788／793／794 總表發票掛在無日期佔位）＝A135，等 owner 補日期 |
| weekly 133 基線 7 組 | 機關／廠商／專案全域統計等，待 owner 判是否算列表卡片 |
| weekly 132 | 兩處永久豁免（上限／超支要含佔位），GREEN |
| `CKProject_DailyBackup` rc=0xC000013A | 09-08 那次被關機中止，CKProject 層排程 |

## 5. 這次重啟前剛改過、要特別看的

| 改動 | 重啟後怎麼確認 |
|---|---|
| 啟動期 `configure_mappers()`（`2ccfe1d5`） | 上面第 5 步那一行；再打 `POST /api/auth/refresh` 應 401 不是 500 |
| 六個列表頁翻頁修正 | 流程走查 `--only=quotation-pagination` PASS |
| `CaseFilterBar` 四頁 | `/erp/quotations`、`/erp/client-accounts`、`/erp/vendor-accounts`、`/contract-cases` 篩選列都在 |
| 已請款＝有請款日期 | `/erp/client-accounts` 2026：承攬 108,108,873／已請款 40,888,276／已收 11,389,413／應收未收 96,719,460 |
| 部署腳本髒工作樹守門 | `git status` 乾淨時 `deploy-public.sh` 正常起跑；髒時 exit 3 |
