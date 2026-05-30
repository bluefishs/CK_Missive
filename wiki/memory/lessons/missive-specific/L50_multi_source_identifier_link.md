---
title: L50 — Multi-source identifier ≠ entity link
type: lesson
date: 2026-05-28
fqid: CK_Missive#L50
family: data-source-integration
related: [L41, L49]
---

# L50 — Multi-source identifier ≠ entity link

> **日期**：2026-05-28（ADR-0046 觸發）
> **觸發**：tender 模組 ezbid (27k) + PCC (2.7k) 兩 source 雙紀錄，但 0 link → L49.12 系列「無此資料」根因

---

## 觀察

加新 source 容易（schema flex），但建立 source 對應需明確機制：

- **ADR-0032 (2026-04-24)** 採 URL namespace + discriminated union 處理 ezbid + PCC
  - URL 分流 ✓
  - Frontend type guard ✓
  - **但資料層仍 0 link**：兩個 source 各自獨立存於 `tender_records` 不知道對方

- **症狀** (5/28 揭發鏈)：
  - owner 看 PCC tender 詳情 → backend service 抓外部 PCC API → fail → DB only quick result → frontend 看 latest=undefined → 顯示「無此資料」
  - 本質：**ezbid 早期公告 → PCC 完整公告**生命週期沒接通

## 法則

1. **加 source 時就要設計 source 對應機制**（不是事後 patch）
2. **多 source identifier 各自獨立，entity link 需新表/欄位**
3. **fuzzy match 風險高**：trigram false positive 對短字串/同前綴/系列編號（Danas-H-XX 災復系列）
4. **threshold 必須有 guard 規則**：title_sim + agency exact + date proximity 三重 → 避免 false positive
5. **MEDIUM confidence 不要自動 link**，進 review queue 給人工確認

## 應用

| 場景 | 對應機制設計 |
|---|---|
| ezbid + PCC tender | ADR-0046 簡化版方案 A — HIGH only 自動 link + LINE 業務推薦 |
| 未來加 g0v 補充 API | 同模式：先 audit ROI，再決定全/簡/不做 |
| 加 case_code/project_code | ADR-0013（已有 join 欄位設計）|
| 跨 repo（lvrland/PileMgmt 有自己 tender 系統） | 各自獨立，無需 cross-repo link |

## 算法（Audit Script 範本）

```sql
-- LATERAL JOIN + GIN trigram index
WITH ezbid_batch AS (
    SELECT ... FROM tender_records WHERE source = 'ezbid' OFFSET :n LIMIT :batch
)
SELECT er.*, pcc.*, pcc.sim AS title_sim,
       CASE WHEN er.eunit = pcc.unit_name THEN 1.0 ELSE 0.0 END AS agency_match,
       CASE WHEN ABS(er.edate - pcc.announce_date) <= 3 THEN 1.0 ELSE 0.0 END AS date_proximity,
       (0.5 * title_sim + 0.3 * agency_match + 0.2 * date_proximity) AS confidence
FROM ezbid_batch er
CROSS JOIN LATERAL (
    SELECT pr.*, similarity(pr.title, er.etitle) AS sim
    FROM tender_records pr
    WHERE pr.source = 'pcc' AND pr.title % er.etitle  -- GIN trigram 命中
    ORDER BY similarity DESC LIMIT 1
) pcc
WHERE pcc.sim > 0.5;
```

**關鍵**：
- LATERAL JOIN 避免 CROSS JOIN N×M timeout
- `title %% etitle` operator 走 GIN trigram index 高效
- Batched (500/batch) 避 statement_timeout

## ROI 試算範本

對任何「N source × M source」對應，先跑 audit 取真實 match rate：

| ROI | 動作 |
|---|---|
| ≥ 20% | 全套（auto + scheduler + LINE）|
| 5%-20% | 簡化版 — HIGH only auto + LINE 推薦 |
| < 5% | 延後 / 改 lazy on-demand |

---

## Sealed Knowledge

- **多 source 不等於多 entity** — 同物在不同 source 有不同 identifier 是常態
- **link 表是架構債** — 不建立會在每個用戶感受面顯現（如 L49.12「無此資料」）
- **trigram similarity 對中文短字串高 false positive** — 需 agency + date 三重 guard
- **CROSS JOIN N×M 對 30k×3k 即超時** — 必用 LATERAL + GIN index
- **「ROI < 20% 全套不划算」** — 1 hour audit 比 11 hour 全套投資先得真實數據

## 引用

- ADR-0046 tender ezbid ↔ PCC enrichment
- ADR-0032 multi-source identifier unification (URL 分流)
- Audit: `scripts/checks/tender_ezbid_pcc_match_audit.py`
- 相關 lessons: [[L41]] cross-repo secret SSOT / [[L49]] container host dependency family
