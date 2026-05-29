# ADR-0046: Tender ezbid ↔ PCC Enrichment Mechanism (簡化版方案 A)

> **狀態**: accepted
> **日期**: 2026-05-28
> **決策者**: @bluefishs（基於 Phase 2 audit ROI 5.6% 真實數據）
> **接通完整度**: L2（2026-05-29 升級，Phase 3+4+5 全落地 + 34 unit tests 鎖定 false positive guard 與 LINE 訊息格式 — L51 commit）
> **關聯**: ADR-0012（tender 模組設計）/ ADR-0032（多源識別碼統一）/ ADR-0028（錯誤合約）

---

## 背景

ADR-0032 (2026-04-24) 採用 URL namespace 分流（`/tender/pcc/...` vs `/tender/ezbid/...`）+ discriminated union，但**資料層仍各自獨立**：

| Source | Records | 識別 | 完整度 |
|---|---|---|---|
| ezbid | 27,286 (91%) | `ezbid_id` 純數字 | 摘要 (title/budget/deadline/url) |
| PCC | 2,741 (9%) | `(unit_id, job_number)` 複合 | 部分 (僅 import 時欄位) |
| 雙來源 link 紀錄 | **0** | — | **無對應機制** |

5/28 owner 發現 `/tender/pcc/NzEyMzE5MzI%3D/115KL93S` 顯示「無此資料」（L49.12 系列），追到「ezbid 抓到的標案應該跟 PCC 對應更新但目前沒這個機制」。

## Phase 2 ROI 試算結果（2026-05-28 全量跑）

```
audit: 27,286 ezbid × 2,741 PCC fuzzy match
algorithm: 0.5 × title_sim + 0.3 × agency_match + 0.2 × date_proximity
─────────────────────────────────────────────────
Total actionable matches:   1,526 (5.6% of ezbid)
HIGH (≥0.85, 安全 auto-link)
MEDIUM (0.70-0.85, manual review)
LOW (<0.70, reject)
```

**真實洞察**：
- 完美 match (sim 1.0 / agency 1.0 / date 1.0) 是真實同案雙紀錄
- 但 trigram false positive：「30吋閘閥」對「30吋對銲長徑彎頭」sim 高但不同物
- Danas-H-XX-XX 系列（颱風災害復建）短前綴 + 數字編號高 sim 風險高

## 決策

採 **簡化版方案 A**（避免 11h 全套低 ROI 投資）：

### 落地範圍

1. **HIGH only 自動 link**（confidence ≥ 0.85 + 額外 guard）
   - title_sim ≥ 0.85 AND agency exact match AND date diff ≤ 3d
   - 避 trigram false positive 風險（短字串 + 同前綴 issue）

2. **MEDIUM 進 review queue**（不自動 link，給 admin 看 + 手動 confirm）
   - 給後續觀察 + 增強 algorithm

3. **LINE 業務推薦** — 不依賴 enrichment（獨立路徑）
   - 條件：新增 PCC 或 HIGH-matched ezbid，預算 > 100 萬，機關曾合作
   - 訊息：標題 / 機關 / 預算 / 截止 / 連結

### 不做

- **MEDIUM/LOW 自動 link**（false positive 風險）
- **整體 PCC API 補充 enrichment**（per-record fetch 太慢，外部 API 限制）
- **變動 ADR-0032 URL 分流**（保留 discriminated union）

### Phase 落地計劃

| Phase | 動作 | 時間 | 狀態 |
|---|---|---|---|
| 1 | 本 ADR + L50 lesson | 1h | ✓ 5/28 |
| 2 | audit script + ROI 試算 | 2h | ✓ 5/28 (1,526 matches/5.6%) |
| 3 | Schema 變更（pcc_match_* 4 欄位）+ enrichment service（HIGH only） | 2h | pending owner approval |
| 4 | LINE 業務推薦 cron + flow | 2h | pending |
| 5 | scheduler 接 Registry + audit step 55（v6.12）| 1h | pending |

### Schema 變更（Phase 3）

```sql
ALTER TABLE tender_records ADD COLUMN pcc_match_unit_id VARCHAR(50);
ALTER TABLE tender_records ADD COLUMN pcc_match_job_number VARCHAR(50);
ALTER TABLE tender_records ADD COLUMN pcc_match_confidence REAL;
ALTER TABLE tender_records ADD COLUMN pcc_match_at TIMESTAMP;
CREATE INDEX idx_tender_pcc_match
    ON tender_records(pcc_match_unit_id, pcc_match_job_number)
    WHERE pcc_match_unit_id IS NOT NULL;
```

## 後果

### 正向
- ezbid → PCC 對應 1,526 高信心案件（直接業務價值）
- LINE 業務推薦觸發點明確（HIGH-matched + 合作機關 + 預算門檻）
- 避免 11h 全套低 ROI 投資（簡化 5h 落地）
- Registry + Scheduler 整合既有架構（v6.11 Step 5A/5C 模式）

### 負向 / Trade-off
- MEDIUM 1,526 - HIGH count = 顯著未 link 數量（後續手動 review）
- trigram false positive 風險（HIGH 也可能誤判，需 guard 規則）
- audit script SQL CROSS JOIN LATERAL 跑全量 1m9s（每日 cron 可接受）

### 跨 repo 影響
- 無（lvrland / PileMgmt / Showcase 無對應 ezbid 系統）

## Refs

- **Audit Script**: `scripts/checks/tender_ezbid_pcc_match_audit.py` (Phase 2 完成)
- **Lesson**: `wiki/memory/lessons/L50_multi_source_identifier_link.md`
- **Related Commits**: L49.12 系列（tender detail empty 議題揭發）
- **Existing**: ADR-0032 URL namespace / ADR-0028 silent failure

## Phase 3-5 owner approval

待 owner 認可後執行：
- Phase 3 Schema + service（2h）
- Phase 4 LINE 業務推薦（2h）
- Phase 5 Scheduler（1h）

總 5h 簡化版（vs 原 11h 全套）。
