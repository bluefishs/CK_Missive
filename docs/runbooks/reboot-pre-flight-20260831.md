# 重啟前狀態固定與復原指引（2026-08-31）

> 用途：**重啟後要能分辨「本來就有的」與「重啟造成的」。**
> 沒有這份基線，任何重啟後的紅燈都會被當成新問題查一遍。
> 前一份：`reboot-pre-flight-20260828.md`（該次的已知紅燈仍請對照）

---

## 0. ⛔ 這一次最重要的一件事：**14 個修法只在容器裡，映像沒有**

今天所有後端修改都是 `docker cp` 進執行中的容器，**映像 `ck-missive-backend:production`
一個都沒有**。

> ⚠️ **2026-08-31 19:4x 更正：下面這份清單原本是手抄的，列了 14 個而真實是 25 個。**
> 差的 11 個沒有任何訊號會說出來。**權威答案改由檢核自己算**（整棵樹兩次
> `find | md5sum`，不可能漏、也不會過期）：
>
> ```bash
> python scripts/checks/container_image_freshness_check.py
> #   → 「容器 vs 映像」那一段列出的就是重建後會失去的全部檔案
> ```
>
> 下表保留是因為它寫的是**症狀**（那才是推導不出來的部分），不是清單。

| 一旦容器被**重建**就會退回舊版 |
|---|
| `app/services/ai/misc/kb_embedding.py` — 知識庫向量檢索的 `CAST` 修法 |
| `app/api/endpoints/knowledge_base.py` — 知識卡片摘要的繁中兩層 |
| ~~`app/core/scheduler.py`~~ — ⚠️ **方向相反，見下方** |
| `app/services/erp/filing_gap.py` — 待辦顯示成案編號／應請款缺口／類別分流 |
| `app/schemas/erp/filing_gap.py`、`app/api/endpoints/erp/filing_gaps.py` |
| `app/api/endpoints/erp/__init__.py` — 兩支帳款頁改 `reports:erp:view` |
| `app/scripts/init_navigation_data.py` — 選單權限 |
| `app/core/rls_filter.py` — `get_user_accessible_case_codes` |
| `app/schemas/erp/quotation.py`、`repositories/erp/quotation_repository.py` |
| `app/services/erp/quotation_service.py` — 成案主軸／RLS／承辦雙路 |
| `app/api/endpoints/erp/quotations.py` — 依身分限縮 |
| `app/services/notification/project_notification.py` — 專案團隊查詢 |
| **`app/repositories/sort_utils.py`（新檔）＋ 8 個 repository** — 排序欄位解析 |

### ⚠️ `scheduler.py` 是**反過來**的：改了但沒進容器

`e87e52d7`（今早 10:03）把 KB 向量同步從 04:45 改到 05:15，理由是它原本
跑在知識地圖重生（`CK_Missive-Dossier-Compile`，04:50 觸發、04:51 寫檔）
**之前 6 分鐘** ⇒ 當天改的文件要等隔天才進向量庫。

**但那個檔從來沒有 `docker cp` 進容器**（容器 == 映像 == 舊版）。
19:4x 實測差異：容器內仍是 `hour=4, minute=45`。

⇒ **這個修法在 runtime 上還沒生效**，要等部署。
今晚 22:00 的部署會一併帶進去，明天早上才會是 05:15。
在那之前，08-31 當天改的文件不會即時進向量庫。

⚠️ 那 8 個 repository（agency／document／user／vendor／erp.quotation／
pm.case／taoyuan.dispatch_order／taoyuan.project）**import 了 `sort_utils`**。
容器被重建時三者一起退回舊版，狀態是一致的（舊版不 import 它），
不會出現「有人 import 一個不存在的模組」的半套狀態 —— 已逐檔比對確認。

**退回舊版的具體症狀**（不是抽象風險，都是今天實測過的）：

* 知識庫搜尋**每一次查詢都回 HTTP 500**
* `/erp/quotations/541` 等 7 張報價單**看不到承辦同仁**
* 專案團隊成員查詢**永遠回空**（連帶專案通知寄不出去）
* 委託單位／協力廠商帳款**全部 staff 又看得到**
* 報價單列表回到 257 筆（含 93 筆未成案）且不分使用者
* 排序參數退回無防護版 —— `?sort_by=metadata` 之類會 500
  （容器內實測 `metadata`、`registry` 皆爆）

### ⇒ 重啟方式決定風險

| 方式 | 那 14 個修法 |
|---|---|
| `docker restart <容器>` | **保留**（容器檔案系統不變） |
| 機器重開 → 容器依 `restart: unless-stopped` 自行拉回 | **保留**（同上，不是重建） |
| `docker compose up -d --force-recreate` | **全部消失** |
| `docker compose down` 後再 `up` | **全部消失** |
| 跑 `deploy-public.sh`（rebuild image） | **進映像，永久生效** ← 正解 |

**建議：重啟前先跑一次部署**，讓映像與 git HEAD 一致，之後怎麼重啟都安全。
已排定 `CK_Missive-Deploy-Once-20260831`（今日 22:00）；若要提前，
在終端機執行 `bash scripts/deploy/deploy-public.sh`。

---

## 1. 重啟前的量測基線（2026-08-31 實測）

| 項目 | 值 |
|---|---|
| 公網 `/api/health` | **200 / 200 / 200**（三次抽樣，依 L94(c)）|
| 業務量 | documents **2,040**｜canonical_entities **50,166** |
| 容器 | **56** 個 Up |
| Alembic head | `20260830a001`（五支新 migration 皆已套用）|
| 知識庫向量 | **2,927 段｜覆蓋 100%｜與 docs/ 完全同步（未同步 0）** |
| CK_Missive 未推送 | **174** ⚠️ 需 owner 執行 `! git push origin main` |
| 工作區非 wiki 變更 | 56（多為其他 session 的既有檔案，非本次）|

### 重啟後應該仍在的既有紅燈 —— **不是重啟造成的**

weekly 的長期紅燈 13 支已全數登記在
`scripts/checks/.chronic_red_registry.json`，逐項寫明「為什麼還紅著／
誰要決定／追到哪個待辦」。重啟後看到它們**不必重查**，直接讀那份名冊。

其中與重啟無關但值得知道的三項：

* **A17 FT_StorageTank** — 備份 61 天無新檔 ＋ `sw-api` 跑 `--reload`
  ＋ `sw-adminer` 綁 `0.0.0.0:8095`（資料庫管理主控台對區網）
* **A55 `ck-showcase-audit`** — 跨過兩個週一沒觸發（CK_AaaP 的排程）
* **A56 區網＝超級管理員** — 待 owner 裁示，見下

---

## 2. 重啟後的複驗清單（照順序）

```bash
# ① 容器與公網（三次抽樣，單次 200 不足以證明埠轉發是好的 —— L76）
docker ps -q | wc -l                       # 期望 56
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code}\n" \
  --max-time 20 https://missive.cksurvey.tw/api/health; sleep 3; done

# ② 業務量（/api/health 現在真的查 DB，見 L106）
curl -s http://127.0.0.1:8001/api/health   # business_data.ok 必須 true

# ③ 那 14 個修法還在不在 —— **這一項最容易被忽略**
python scripts/checks/container_image_freshness_check.py
#   若容器是重建的，這裡會顯示大量 drift，且行為已退回舊版

# ④ 知識庫檢索（退回舊版的話這裡會 500）
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"query":"vector","limit":3}' \
  http://127.0.0.1:8001/api/knowledge-base/search

# ⑤ 報價單承辦（退回舊版的話 541 會沒有承辦）
#    → /erp/quotations/541 應顯示「洪慶忠」

# ⑥ 排程有沒有接回（A50 的持久化 jobstore 會接回錯過的觸發）
python scripts/checks/cron_silent_dormant_check.py
```

---

## 3. 今日變更摘要（重啟後若行為與預期不符，先看這裡）

### 知識文庫（owner：「要與系統同步更新」）

* **post-commit 接回 husky** —— 原本躺在 `.git/hooks/`，而 `core.hooksPath`
  指向 husky ⇒ 提交時從不重生知識地圖，地圖只有**週排程**會更新
* 向量同步 **04:45 → 05:15**（原本跑在地圖重生之前 6 分鐘）
* **向量檢索修好** —— `:embedding::vector` 讓參數綁不到，**從來沒成功過**
* daily 加第 14 步「知識文庫新鮮度」，判準分兩級（待同步＝黃／同步後仍舊＝紅）

### 儀表板待辦（owner 三項回報）

* 顯示 `project_code` 而非 `case_code` ⇒ 含 `_PM_` 的由 87+ 降到 1
* 依案件收合成樹（158 項 → 101 個節點）
* 新增「該請款未開單」43 筆（門檻 365 天，用公司自己的中位數 205 天校準）
* 請款日在未來的不再算未收（12 → 2）

### 權限（owner：「應對應登入權限管控機制顯示」）

* 委託單位／協力廠商帳款：`reports:finance:view`（11/12 人有）→
  **`reports:erp:view`**（5 admin、0 staff）
* 報價單：成案主軸（257 → 164）＋ 依身分限縮，跨案查詢做成**可授權的擴充點**
* ⚠️ `init_navigation_data.py` 的選單權限原本是 `"[]"`（所有人可見）而
  live DB 是 `finance:view` —— **兩邊早就漂移**，已一併對齊

### 同族缺陷（第七、八處）

* 報價單承辦只認 `case_code` ⇒ 7 張看不到承辦（含 541）
* `project_notification` 的 SQL 寫**單數表名** ⇒
  `relation does not exist` ⇒ except 吞掉 ⇒ **專案團隊查詢從來沒成功過**，
  連帶專案通知從未寄出

---

## 4. 待 owner 決定（重啟不影響，但別忘了）

| 項目 | 內容 |
|---|---|
| **推送** | 174 個 commit 未推送 —— `! git push origin main` |
| **A56** | 區網可對整個資料庫下任意 SELECT。兩個「其實還好」的理由已排除（CSRF 對此路徑透明、綁 loopback 擋的是直連） |
| **A17** | FT_StorageTank 三個訊號 |
| **成本／毛利準則** | 已量出關鍵事實：**帳本支出完全衍生自應付與核銷**（`source_type` 只有那兩種）⇒ 三者相加會重複計算。準則待律定 |
| **零流量 API** | 35 個候選待人工核實（判定時點 08-31 已到） |
| **完工日／驗收日** | 執行中 100 案 **0 件**有填 ⇒「該不該請款」只能用天數猜 |
