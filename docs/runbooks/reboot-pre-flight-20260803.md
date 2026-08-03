# 重啟前檢查與重啟後驗收 — 2026-08-03

> 上一份：`reboot-pre-flight-20260802.md`
> 本輪期間改動較多（LINE 通知統整、wiki 管線、測試庫、多支檢核），
> 重啟後的驗收重點也隨之不同，見 §3。

---

## 1. Pre-flight 檢查結果（2026-08-03 執行）

| 檢查項 | 結果 |
|---|---|
| 未推送 commit | **0** |
| 非自動產物的未提交檔案 | **0**（wiki/ 下為 cron 自動產物） |
| **DB volume**（L43 關鍵） | `ck_missive_postgres_dev_data` ✅ 與 compose `name:` 一致 |
| 容器 restart policy | 全部 `unless-stopped` / `always` |
| Windows 排程 | 7 支 CK 相關全部 `Ready` + `StartWhenAvailable=True` |
| 五系統公網 | missive / lvrland / pilemgmt / digitaltwin / www 全 **200** |
| 容器 | **55 個、0 非健康** |
| Hermes gateway / ollama | 200 / 200 |
| 異地備份 | 2026-08-03 03:00、NAS 30 份、最新 501.3MB |

**業務量基線（重啟後用來對照）**：`documents=1974`、`canonical_entities=49549`

### Windows 排程清單
```
CK-Hermes-Cron-Tick                    Ready  SWA=True
CK-Hermes-Health-Smoke                 Ready  SWA=True
CK-Missive-Offsite-Backup              Ready  SWA=True
CK_Missive-SelfAudit-Flow              Ready  SWA=True
CK_Missive-SelfAudit-Sweep             Ready  SWA=True
CK_Missive-SelfAudit-CapabilityUsage   Ready  SWA=True
CK_lvrland_Webmap-SelfAudit-{Flow,Static,Sweep}  Ready  SWA=True
```
`StartWhenAvailable=True` 表示關機期間錯過的排程會在開機後補跑
（2026-08-02 才全數補上這個設定，在那之前關機即整個跳過且無訊號）。

---

## 2. 重啟前不需要做的事

- **不必手動停容器**：全部 `unless-stopped`，Docker 會自行拉回
- **不必備份 DB**：異地備份今晨 03:00 已完成（NAS 30 份）
- **不必 `--force-recreate`**：自 v6.32（opencc 烤入 image）起該禁令已解除，
  但也沒有理由主動 recreate

---

## 3. 重啟後驗收（依本輪改動調整）

### 3.1 基礎（照舊）
```bash
docker ps -q | wc -l                    # 期望 55
docker ps --format '{{.Status}}' | grep -ciE 'unhealthy|Restarting'   # 期望 0
curl -s -o /dev/null -w '%{http_code}' https://missive.cksurvey.tw    # 期望 200
curl -s https://missive.cksurvey.tw/health   # docs≈1974 kg≈49549（只會增不會減）
```

⚠️ **L76**：若 host `localhost:8001` 不通但公網通（或相反），
`docker restart ck_missive_backend`（Windows 殭屍埠轉發）。

### 3.2 本輪新增，重啟後要特別確認

| 項目 | 驗法 | 期望 |
|---|---|---|
| **晨報改 07:30** | 隔日 07:30 前收到 LINE，且內容含「昨日主題摘要」分群 | 8 點前送達 |
| **LINE 統一出口** | 同上；不應再有分散時段的零星推播 | 一天一則 |
| **測試庫仍在** | `docker exec ck_missive_postgres psql -U ck_user -l \| grep ck_documents_test` | 存在 |
| **模組 wiki 補齊** | 下週一 05:00 後 `ls wiki/modules/*.md \| wc -l` | 應由 12 增加 |
| **wiki 健康** | `python scripts/checks/producer_output_watchdog.py` | 含「Wiki 健康檢查」GREEN |

### 3.3 檢核基線（重啟後跑一次，與此對照）
```
fitness daily            exit 0（all passed）
producer watchdog        GREEN 24 producer、0 blind spot
三者對應                  GREEN（前端打不到 0／圖譜漏收 0）
doc 引用完整性            GREEN（失效率 7.5%）
wiki lint                health=good、orphans 0、broken 0、292 頁
test_suite_health        GREEN（41 vs 41，約 9 分鐘）
```

⚠️ **不要在 rebuild 期間跑檢核** —— 2026-08-03 實測會產生假 RED
（DB 連線被打斷 → `ConnectionResetError`、測試 3 項假失敗），
假 RED 會消耗對檢核的信任。

---

## 4. 本輪期間的已知狀態（非故障，重啟後仍會看到）

| 現象 | 說明 |
|---|---|
| 41 個測試失敗 | 既有測試債，已鎖在 `backend/tests/known_failures.json` 基線 |
| 255 條端點無前端引用 | 需真實流量判定，時點 2026-08-31 |
| doc 引用失效率 7.5% | GREEN 門檻內，多為文件裡的舊路徑 |
| 模組 wiki 12/120 | 每週一補最多 20 頁，約 6 週收斂 |
| canonical 業務關係 328 筆 | NER 欄位名 bug 已修，但**存量公文不會自動重抽**（需 owner 決定 backfill 時機） |
| 明日晨報少 10 則摘要 | 2026-08-03 驗證 digest 時誤用 `drain_digest`（破壞性）清空了當日 buffer |

---

## 5. 若重啟後出問題

| 症狀 | 處置 |
|---|---|
| GPU 容器起不來、推論全斷 | `wsl --shutdown` 後重啟 Docker（NVIDIA prestart hook 崩潰，**勿用 `docker restart`**） |
| host 8001 不通、公網通 | `docker restart ck_missive_backend`（L76） |
| 公網 1033 | Docker engine 卡死 → kill `docker-mcp.exe` 後 start |
| 業務 API 全 500 且 DB 表數異常 | 查 volume 是否掛成 `ck_missive_postgres_data`（空殼）— L43 |
