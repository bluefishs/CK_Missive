# 重啟 Pre-Flight — 2026-08-02

> 前次：[`reboot-pre-flight-20260730.md`](reboot-pre-flight-20260730.md)
> 本輪主題：自我檢核跨專案化、第 6 階價值層起步、Prometheus 缺席修復

---

## ⭐ 重啟後最高優先

### 1. 看一眼自我檢核有沒有自己跑起來（新機制的第一次重啟考驗）

重啟後 04:15 / 04:30 / 04:50 三個 Missive 排程會自動執行。隔日確認：

```bash
python scripts/checks/.shared-selfaudit/ui_smoke_freshness.py   # 應 GREEN
```

RED 就代表**新建的排程沒撐過重啟**——那正是本輪一直在治的「註冊 ≠ 會跑」。
五個排程都已設 `StartWhenAvailable=true`（錯過會補跑），但這是第一次實戰驗證。

### 2. Prometheus 是否仍在抓 CK_Missive

```bash
curl -s "http://127.0.0.1:19090/api/v1/query?query=up{job=\"ck-missive\"}"
```

本輪才發現 **Missive 自 2026-04-19 起就不在任何抓取目標中**（約 3.5 個月，
5 個儀表板與 alert rule 全無資料）。設定已補進 `CK_AaaP/platform/observability/
prometheus/prometheus.yml` 並 commit，但**重啟後要確認它真的回來**——
這是第 6 階價值層唯一的資料來源，斷了就整條鏈失效。

---

## 重啟前狀態（2026-08-02 實測）

| 項目 | 狀態 |
|---|---|
| 容器 | **55 個，0 非健康**，全部 `unless-stopped`（會自動拉回） |
| 五系統公網 | missive / lvrland / pilemgmt / digitaltwin / www 全 **200** |
| 業務量 | **1970 docs / 49530 KG**，`biz_ok=true`（L43 守衛健在） |
| cron | 近 200 筆 **success=200 / fail=0** |
| Prometheus | `ck-missive` target **up**（本輪補回） |
| DB volume | `ck_missive_postgres_dev_data` + `external: true`，**與 compose 對齊**（L43） |
| 異地備份 | 今晨 03:00 success、NAS **30 份**、最新 `20260802_015956.sql` |
| 排程 | **13 個全 Ready**，全部 `StartWhenAvailable=true` |
| 自我檢核 | 深度 **7/7 PASS**、廣度 86/87、新鮮度 GREEN |
| 治理 | drift GREEN / 19 producer 0 blind spot / 異質同工 GREEN / 導覽一致 GREEN |
| git | 五 repo **0 未推送**；未提交者全為自動產物（備份狀態／治理儀表板／SOUL 輪替） |

---

## 本輪完成（已 push）

| repo | 內容 |
|---|---|
| `shared-modules` | selfaudit 引擎 canonical；型態 A 兩類假陽性降級；截圖可外置；`extra_tasks`；排程補跑設定 |
| `CK_Missive` | 改 vendored 消費並納 drift gate；價值層收集器；測試 collection 中斷修復；A2/A7 記載更正 |
| `CK_lvrland_Webmap` | 導入全套 + 告警接通（走 Missive LINE proxy、7 天去重）；修 SecurityCenterPage 7 支 API 路徑；LR-043 |
| `CK_AaaP` | prometheus.yml 補回 `ck-missive` scrape job |

---

## ⚠️ Watch items（非重啟阻斷）

| # | 項目 | 說明 |
|---|---|---|
| W1 | **測試套件不可安全執行** | `conftest.py` 用生產 DB + `scope="function"`，跑全量會耗盡連線。**重啟後也不要跑全量測試**，需先做測試 DB 隔離（獨立 session） |
| W2 | 價值層資料深度不足 | TSDB 15 天、Missive 才剛接回；**判定時點 2026-08-31**，在那之前 `capability_usage_snapshot` 一律 exit 2 不給結論 |
| W3 | 型態 A 對 pile/DT 不可用 | 重複執行 FAIL 數不穩定（19/35/10），已劃入 README 界線；要有效需 auth adapter |
| W4 | lvrland 4 項頁面缺陷 | 已交接 `CK_lvrland_Webmap/docs/health/FINDINGS_20260801.md`，屬該專案 |
| W5 | tests/ 是 baked 非掛載 | 本輪測試修法需 rebuild 才進容器；不影響 runtime |

---

## 重啟後驗收 SOP（6 步）

1. **容器自動拉回** — `docker ps -q | wc -l` 應 ≈55、`--filter health=unhealthy` 應 0
2. **公網五系統** — 五個 host 全 200
3. **業務量守衛** — `curl -s http://localhost:8001/health` 的 `business_data.ok` 應為 `true`
   且 documents ≥ 1970（低於門檻會回 503，cloudflared 就不會把流量打進來）
4. **L76 埠轉發** — host `:8001` 與公網都要 200。不通則 `docker restart ck_missive_backend`
   （Windows Docker 殭屍埠轉發，重啟後高風險）
5. **Prometheus 抓取** — `up{job="ck-missive"}` 應為 1（見上方最高優先 2）
6. **自我檢核** — 隔日跑 `ui_smoke_freshness.py` 應 GREEN（見上方最高優先 1）

任一步不過，先看 `docs/architecture/LESSONS_REGISTRY.md` 對應條目再動手。

---

## 相關文件

- `docs/architecture/SELF_AUDIT_EVOLUTION_STANDARD.md` — 六階階梯與移植標準
- `docs/architecture/RETRO_20260801_SELFAUDIT_CROSS_PROJECT.md` — 本輪覆盤
- `docs/architecture/FULL_SYSTEM_REVIEW_20260801.md` — 未解議題 A1–A8
- `shared-modules/selfaudit/README.md` — 引擎導入（型態 A/B 與適用界線）
