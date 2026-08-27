# CSP：從 Report-Only 轉為強制執行

> **建立**：2026-08-27
> **狀態**：觀察中，最早可於 **2026-09-03** 判定
> **相關**：`backend/app/core/security_headers.py`（政策）／`backend/app/api/endpoints/csp_report.py`（回報收集）

---

## 為什麼這份文件存在

「先掛 Report-Only、觀察一段時間、確認零違規再轉強制」這句話寫在
`get_default_csp()` 的註解裡（2026-08-18）。它聽起來完整，但**它不是一個可以收束的計畫**：

沒有說觀察多久、沒有說「零違規」由誰判、也沒有說判完之後誰去改那一行。
這個專案已經在同一件事上跌過兩次：

| 日期 | 缺的那一段 | 結果 |
|---|---|---|
| 2026-08-18 | CSP 標頭裡**既沒有 `report-uri` 也沒有 `report-to`** | 瀏覽器算出違規後回報給沒有人 ⇒「零違規」永遠成立 |
| 2026-08-19 | 補上端點了，但**只支援舊式 `blocked-uri`**、漏了 Reporting API 的 `blockedURL` | 端點有在收，收到的是空報告，而「有 log 行」看起來像正常運作 |
| 2026-08-27 | 端點正常了，但 **log 沒有任何接收者** | 違規只寫進容器 stdout（json-file 10m×3），重啟就沒了 |

三次的形狀一樣：**機制往前推進一格，而「誰去看」始終沒有人。**

---

## 現在的接收者是什麼

2026-08-27 起，每一筆違規同時累加 Prometheus counter：

```
csp_violations_total{directive, disposition}
```

* 每一筆都算 —— 去重只影響「寫不寫 log」，不該影響「發生了幾次」
* label **不放 `blocked-uri`** —— 它由外部輸入決定、基數無上限，當 label 會被灌爆
* 要看是**哪個來源**被擋，去看 log 行：`grep CSP-VIOLATION`

⇒ 判準因此變成一個可以查證的句子，而不是一種感覺：

```promql
increase(csp_violations_total[7d]) == 0
```

---

## 判定步驟

### 1. 查 7 天內有沒有違規

```bash
# 直接問 counter（backend 重啟會歸零，所以同時看 log）
curl -s http://localhost:8001/metrics | grep '^csp_violations_total'

# 看是哪個來源被擋（counter 只講 directive，不講 blocked-uri）
docker logs ck_missive_backend --since 168h 2>&1 | grep CSP-VIOLATION
```

⚠️ **counter 會隨 backend 重啟歸零** —— 看到 0 要先確認 backend 起來多久：

```bash
docker inspect ck_missive_backend --format '{{.State.StartedAt}}'
```

**容器起來不到 7 天，counter 的 0 不算數。** 這一條不是形式 ——
「還沒到門檻」與「永遠到不了門檻」在畫面上長得一模一樣，是本專案記過的判準。

### 2. 有違規 → 逐一判斷是「該放行」還是「該擋」

已知的一次（2026-08-27，也是這份文件的起因）：

```
directive=style-src-elem  blocked=https://accounts.google.com/gsi/style
document=https://missive.cksurvey.tw/entry
```

那是 Google 登入按鈕的樣式表 —— **該放行**，`style-src` 已補
`https://accounts.google.com`。若當初直接上強制，登入頁的按鈕會變成沒有樣式，
而**樣式被擋不會有錯誤畫面**，沒有人會知道發生了什麼。

判斷方式：對每一筆問「這個來源是我們自己要用的嗎？」
* 是 → 補進對應 directive，**然後重新觀察 7 天**（改了政策，前面的觀察就不算數）
* 否 → 那正是 CSP 要擋的東西，可以進入下一步

### 3. 零違規滿 7 天 → 轉強制

`backend/app/main.py` 的註冊改一個參數名：

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy=get_default_csp(),          # 原本是 ..._report_only=
)
```

然後**照 SOP 部署**（`docs/architecture/CONTAINER_DEPLOYMENT_SOP.md`），
不要 docker cp。

### 4. 轉強制後的回退條件

強制之後 `csp_violations_total` 的 `disposition` 會從 `report` 變成 `enforce`
—— **那個標籤就是「現在真的擋到東西了」的訊號**。

```promql
increase(csp_violations_total{disposition="enforce"}[1h]) > 0
```

出現就代表有功能正在被靜默擋掉。回退是改回 `..._report_only=` 再部署一次，
成本很低；**不要因為「應該沒事」而不回退** —— CSP 造成的失敗多半沒有錯誤畫面。

---

## 還沒做、而且刻意沒做的事

* **沒有設 Prometheus alert rule。** 現階段違規是預期會有的（正在觀察），
  設了就是每天響一次的噪音。**轉強制之後**才該對 `disposition="enforce"` 設 alert，
  那時候「有違規」才等於「有東西壞了」。
* **沒有收緊 `script-src` 的 `'unsafe-inline'` / `'unsafe-eval'`。**
  那是另一件事，不該和「先讓 CSP 存在」混在一起做 —— 一次改太多，出事時分不出是哪一項。
