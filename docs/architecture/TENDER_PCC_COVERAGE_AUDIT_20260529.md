# Tender PCC 抓取深度評估 (L51 task F, 2026-05-29)

> **狀態**: research / proposal — 待 owner 決策
> **觸發**: 標案功能覆盤（dashboard 效能 + LINE 通報後續）
> **關聯**: ADR-0012 / ADR-0032 / ADR-0046 / L29 PCC 50-day silent dormant

---

## 1. 現況數據（DB 實測 2026-05-29）

```
 source | total | has_date | has_budget | has_unit | linked
--------+-------+----------+------------+----------+--------
 pcc    |  4076 |     4076 |          0 |     4076 |      0
 ezbid  | 28122 |    28122 |      27760 |    28122 |    394
```

### 關鍵觀察

| 議題 | 數值 | 嚴重度 |
|---|---|---|
| **PCC budget 100% NULL** | 4,076 筆全無 budget | 🔴 高 — 業務推薦 filter 對 PCC 完全失效 |
| **ezbid 占比 87%** | 28,122 / 32,198 | 🟡 中 — 業務依賴單一爬蟲，BLOCK_THRESHOLD 觸發即失明 |
| **PCC linked = 0** | 0 / 4,076 | 設計如此（PCC 是「被 link」端，非 link source） |
| **ezbid linked 1.4%** | 394 / 28,122 | 🟡 中 — HIGH guard 嚴格，餘 26k 多無對應 PCC |

### `find_business_recommendations` 真實涵蓋

```sql
WHERE (tr.source = 'pcc' OR tr.pcc_match_unit_id IS NOT NULL)
  AND tr.budget IS NOT NULL AND tr.budget >= 1_000_000
```

→ PCC 4076 筆全 budget=NULL **全擋**
→ 實際候選 = 394 HIGH-matched ezbid × budget filter
→ Dry-run 結果：found=7（已 link + 預算 + 合作機關 + 今日新增）

**結論：業務推薦的「PCC source」分支實際從未命中**。所有 LINE 推送都來自 ezbid。

---

## 2. 三個問題鏈

### Q1: PCC 為何 budget 全 NULL？

**根因（推測，待驗）**：
- `pcc_today_scraper.py` 抓取 PCC 站時，budget 欄位 selector 沒對齊
- 或 PCC 公告本身就不公開 budget（決標前隱藏）
- g0v API 的 g0v 來源也僅在某些 endpoint 給 budget

**驗證方法**：
```bash
# 對隨機 5 筆 PCC 看 raw_data 是否真的沒 budget 欄位
SELECT id, unit_id, job_number, title,
       raw_data::jsonb -> 'budget' AS rd_budget,
       raw_data::jsonb -> 'predict_value' AS rd_predict
FROM tender_records WHERE source='pcc' ORDER BY random() LIMIT 5;
```

**修法路線**：
- A. 改 `pcc_today_scraper` 多抓 budget 欄位（若 selector 可取）
- B. 對 PCC 案件二階段 fetch 詳細頁面（per-record 慢，避免）
- C. **接受 PCC 無 budget 設計** — 業務推薦走 ezbid path 即可（reality 已如此）

**建議**: C — 邏輯已自然分流，但加 Prometheus alert `pcc_records_without_budget_pct > 95%` 視為設計，不必修。

### Q2: ezbid BLOCK_THRESHOLD 觸發時 PCC 能補嗎？

**現況**:
- ezbid: 每小時全量爬（27,760 有 budget）
- PCC: 每 2 小時爬（4,076 無 budget）
- 若 ezbid 被 block → PCC 仍可運作但**無 budget 業務推薦無法觸發**

**對策**：
1. **短期**: 加 Prometheus alert，ezbid `consecutive_failures > 3` 立即通知 owner
2. **中期**: 評估 PCC 從詳細頁補抓 budget（per-record fetch，慢但完整）
3. **長期**: 接 g0v open data 第三源（無爬蟲負擔）

### Q3: ezbid 26k 多無對應 PCC，是 enrichment 失效還是 reality？

**已知**：
- HIGH guard 嚴格（exact title match + length≥12 + agency≥0.85 + date≤3d）
- L51 Task E 新增 review queue: 1,469 MEDIUM 候選給 admin
- 估計 `1,469 / 28,122 = 5.2%` 有潛在對應

**未驗證**：26,000+ ezbid（94%）真的沒對應 PCC？還是只是 PCC 抓取覆蓋不全？
- PCC 4076 筆 vs 全國年標案數（~30 萬）= 1.4% — **PCC 抓取覆蓋極低**
- 所以「沒對應 PCC」可能因為 **PCC 端根本沒抓到**，不是 ezbid 是孤兒

---

## 3. g0v API 評估

**位置**: `pcc-api.openfun.app`
**已用**: `analytics.py:dashboard` 內 g0v keyword search
**特性**:
- 開放 API，無爬蟲負擔
- 包含 PCC 結構化資料（含 budget）
- 1-5 天延遲（vs PCC 站即時）

**潛在補強**:
- 用 g0v 補 PCC `budget` 欄位 (`UPDATE tender_records SET budget = ...`)
- 但 g0v 1-5 天延遲對「今日業務推薦」用處有限

**建議**：
- 短期: 用 g0v 跑歷史 PCC 回填 budget（一次性），4,076 筆 expect cover rate >50%
- 長期: g0v 不替代 PCC 即時，但可作為**夜間補完**來源（cron 03:00 之後）

---

## 4. 建議路線圖（v6.12 候選）

| Priority | 動作 | 預估 | 效益 |
|---|---|---|---|
| P1 | g0v 補 PCC budget 一次性 backfill | 4h | 解 LINE 推送對 PCC 全失效 |
| P1 | Prometheus alert: ezbid consecutive_failures > 3 | 1h | 失明前 owner 通知 |
| P2 | enrichment 跑完 28k 後跑 audit 評估真實覆蓋率 | 2h | 量化「ezbid 孤兒」真實比例 |
| P3 | PCC 深度頁面 fetch budget（per-record） | 6h | 治本但慢，僅高 budget 案件用 |

---

## 5. 不做（明確排除）

- ❌ 重寫 ezbid_scraper / pcc_today_scraper（覆蓋率瓶頸不在程式，在外部 API）
- ❌ 自建 PCC 爬蟲（PCC 站擋 robot，技術成本 + 法律風險）
- ❌ 切換主源為 PCC（ezbid 87% 占比是現實，切換損失大）

---

## 6. 觀測補完（L51 task F 已落地）

- `tender_page_view_total{page}` 7 labels (dashboard/detail/company/org_ecosystem/search/battle_room/price_analysis)
- 7 天後可看：
  - Company / Org 頁面真實 traffic（≤ 0 = dead UI 候選，符合 L31 ROI 治理）
  - Dashboard hit 頻率（驗證 cron warm cache 是否被「白燒」— 沒人看的話 cache 沒用）

---

## Refs

- **DB 實測**: 2026-05-29 SQL above
- **既有 metrics**: `backend/app/services/tender/metrics.py` (L51 task F)
- **業務推薦 SQL**: `backend/app/services/tender/business_recommendation.py:find_business_recommendations`
- **L31 ROI 治理原則**: `wiki/memory/lessons/L31_roi_entities_usage_rate.md`
- **L29 PCC silent dormant**: `wiki/memory/lessons/L29_*`
