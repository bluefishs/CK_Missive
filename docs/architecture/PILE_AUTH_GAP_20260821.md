# CK_PileMgmt 無認證端點診斷（2026-08-21）

> ## ⚠️ 2026-08-23 更新：本文件已過時，以 pile 的 ADR-035 為準
>
> **① 我當初寫的「沒有 session 在處理」是錯的。** pile session 於 08-22 開始
> 處理並產出 9 個 commit —— 我當時是從 `ListAgents` 看不到而下的結論，
> 但那只反映「我問的那一刻」。⇒ **「沒有人在做」這種結論，不能只憑一次觀察。**
>
> **② 他們找到的比我深一階。** 我量到的是**讀取**外洩（控制點統計、22 縣市、
> 11,025 點）；他們找到 **31 個 mutation 端點未認證公網可寫**。我當時看到
> `crawler/tasks/{id}/{cancel,pause,resume}` 就停手（破壞性操作不在授權範圍，
> 那個界線是對的），但**沒有從程式碼側把整批 mutation 找出來** ——
> 只做了「能不能讀」而沒問「能不能寫」。
>
> **③ 本文件第 3 節那 319 條，是用 Missive 座標系算的，本來就不是結論。**
> 以他們自己的 `ADR-035 無認證端點稽核座標系` 為準。
>
> **④ ⚠️ pile 後端 08-23 當下 hang 住**（首頁 200 但容器內打 `/health` 逾時、
> `FailingStreak=4355`、log 停在 08-22 14:25）—— 與 08-08 lvrland 同型，
> 已通報該 session。**那是另一件事，與本文件的認證缺口無關。**

> **為什麼由 CK_Missive 寫這份**：owner 2026-08-21 指示各專案同步開 session
> 自行處理，五個 repo 裡**只有 CK_PileMgmt 沒有 session**。owner 隨後問
> 「不動產 數位孿生 樁位都沒問題嗎」——樁位有問題，而沒有人在看。
>
> **本文件只做診斷，沒有動 CK_PileMgmt 任何一行程式碼**（跨 repo 紀律）。
> 修法需要 owner 指派。

---

## 1. 實測證據（公網，未帶任何憑證）

```
POST https://pilemgmt.cksurvey.tw/api/spatial/control-points/cities   → 200
  {"success":true,"message":"22 cities with control points",
   "data":[{"city_code":"C","city_name":"基隆市","point_count":79}, ...]}

POST https://pilemgmt.cksurvey.tw/api/spatial/control-points/levels   → 200
  {"success":true,"message":"10 control point levels",
   "data":[{"level_code":"B","level_name":"衛星追蹤站","point_count":17}, ...]}
```

量測方法已依 2026-08-21 判準 9 驗過（真實瀏覽器 UA、單次不快打、
不經 bash `while read`）——**這四種失敗都會給出「已經擋住了」的錯誤結論**。

CK_AaaP session 另行獨立驗證過同一批（POST 回 200、11,025 筆控制點）。
**兩個 session 各自量到、結論一致**（判準 3：同一件事量兩次，兩次一致才算數）。

---

## 2. 比「資料外洩」嚴重一階：無認證的**控制**端點

runtime dependency 樹掃描（`--container ck_pilemgmt-backend-1`）：

```
端點總數 1275｜無認證 391｜套 Missive 白名單後缺口 319｜非登入/健檢類 302
其中控制點/樁位相關 48 條
```

⚠️ 這 48 條裡包含**動作類**而不只是查詢：

```
/api/spatial/control-points/crawler/tasks/{task_id}/cancel
/api/spatial/control-points/crawler/tasks/{task_id}/pause
/api/spatial/control-points/crawler/tasks/{task_id}/resume
/api/spatial/control-points/crawler/tasks/list
/api/spatial/control-points/import/template/{format}
```

**這幾條我刻意沒有實測** —— cancel/pause/resume 會改變該系統的運作狀態，
那是破壞性操作，不在授權範圍內（L85：破壞性指令先確認作用範圍）。
**但「存在且無認證」本身就要報**：若確實可達，任何人都能停掉正在跑的爬蟲任務。

---

## 3. ⚠️ 這 319 不是最終數字

依判準 11（**座標系有兩半**），上表是用 **Missive 的**認證函式名單與公開白名單
算出來的，對 pile 不可採信為結論。實例：對 lvrland 不帶座標系掃出 121 條
「缺口」，套上他們自己的之後剩 60，而他們用自家判定本尊逐一歸類的答案是
**真缺口 0**。

**接手的人第一件事**是產生 pile 自己的座標檔，不是照著上面的清單改：

```bash
cd D:/CKProject/CK_Missive
python scripts/checks/public_endpoint_auth_audit.py \
    --emit-coordinates --repo ../CK_PileMgmt          # 產生後**改成 pile 自己的**
python scripts/checks/public_endpoint_auth_audit.py \
    --container ck_pilemgmt-backend-1 --repo ../CK_PileMgmt
```

座標檔（`docs/health/auth-coordinates.json`）要填三件事，每條白名單**寫明理由**：

| 欄位 | 內容 |
|---|---|
| `auth_dependency_names` | pile 實際用的認證相依名稱（lvrland 有 service-token 家族 12 個，Missive 15 個，各不相同） |
| `public_routes` | 刻意公開的路由 pattern **＋為什麼不需要登入** |
| `exit_code_semantics` | 退出碼語意（L89：lvrland 是 1=FAIL/2=未驗完，portfolio 標準是 2+=RED，混用會讓檢核變啞） |

工具會擋下座標系不匹配的情況並 exit 2。

---

## 4. 修法方向（不是清單，是判準）

1. **在 router 層加，不要逐一改端點參數。** Missive 今天的實例：
   `documents/list.py` 多數端點有 `require_auth`，唯獨 by-project 與
   integrated-search 漏掉 —— **逐一改會漏，而漏掉的那條不會有人發現**。
2. **先問「病症的源頭是不是預設拒絕沒有落實」。** Missive 的根因不是某條路由
   忘了加，是 `TUNNEL_GUARD_ENABLED=false`（all-or-nothing，開了會擋掉整個 SPA）
   ⇒ 所有沒有自帶認證的端點一律對外。pile 若有同型的總開關，先查它。
3. **CSRF 不是認證。** 帶著公開可取的 CSRF token 之後仍然 401 才算真的擋住。
   ⚠️ 適用性取決於該 repo 的檢查順序：lvrland 是認證先於 CSRF 所以不適用，
   Missive 適用。**pile 是哪一種要自己驗，不能照抄。**
4. **對外開放的端點若會消耗運算資源，性質不同** ——
   owner 2026-08-21 立規範「不得要新增額外費用之設計」
   （`.claude/rules/development-rules.md` §0，各 repo 適用）。
   pile 的爬蟲任務端點正屬此類。

---

## 5. 相關

| 項目 | 位置 |
|---|---|
| 工具 | `scripts/checks/public_endpoint_auth_audit.py`（weekly 64） |
| 判準 9/10/11/12/13/14 | `docs/architecture/OPEN_ITEMS_20260819.md` §D |
| 待 owner 指派 | 同上 A10 |
| pile 08-08 前例 | 文檔治理 7 端點補認證（當時只有 tunnel_guard 擋著，守衛一關就公開） |
