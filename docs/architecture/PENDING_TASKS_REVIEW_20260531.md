# 前後端待辦事項複查 — 2026-05-31

> **Owner 訴求**：完成 ERP ingest 等事項 + 複查確認前後端待辦
> **狀態**：本批新增 ERP ingest 201 entity ✅ + frontend route 註冊 ✅

---

## 1. 本批完成項

| 項目 | 結果 |
|---|---|
| ERP KG ingest --apply（C 方案 A）| ✅ **201 entity INSERT 成功** |
| ERP graph_domain | 84 → **285 (3.4x)** |
| SchedulerEventsPage 路由註冊 | ✅ `/admin/scheduler-events` |
| TSC 0 errors | ✅ |

## 2. ERP ingest 詳細結果

| 表 | 預估 todo | 實際 ingested |
|---|---|---|
| erp_quotations → erp_quotation | 1 | **70** |
| erp_invoices → erp_invoice | 47 | **47** |
| erp_billings → erp_billing | 48 | **48** |
| erp_vendor_payables → erp_vendor_payable | 32 | **32** |
| expense_invoices → erp_expense | 1 | **4** |
| **TOTAL** | — | **201** |

實際 201 > 預估 129 — 含 quotation/expense 既有 entity 升級為 erp_* 命名。

KG 整體現況：
- code 9091 / tender 7804 / knowledge 4399 / **erp 215**

## 3. 前後端待辦對齊

### Backend 待辦（owner approve）

| P | 項目 | 狀態 |
|---|---|---|
| P0 | knowledge dedup --apply | ✅ 完成（24535→21378）|
| P0 | ERP ingest --apply | ✅ **本批完成 +201 entity** |
| P0 | LINE timeout 修法 | ✅ 25→28s |
| P0 | dashboard cron 凌晨化 | ✅ 02:30/02:45 + misfire_grace 7200 |
| P0 | cron jsonl event log | ✅ /app/logs/cron_events.jsonl |
| P1 | Scheduler events 4 API endpoints | ✅ |
| P1 | wiki kg_entity_id backfill | ⏳ 38.5% → 80% 待做 |
| P1 | Document graph 加入（1809 entity）| ⏳ 待做 |
| P1 | Skill graph 加入（108 entity）| ⏳ 待做 |
| P2 | CK_AaaP 加 audit（L59 配套）| ⏳ 跨 repo |

### Frontend 待辦

| P | 項目 | 狀態 |
|---|---|---|
| P0 | SchedulerEventsPage.tsx | ✅ 3 tabs 完整 |
| P0 | AppRouter 路由註冊 | ✅ `/admin/scheduler-events` 本批 |
| P1 | Nav menu item 加入 | ⏳ |
| P1 | /kunge/ops 加 "排程監控" tab | ⏳ |
| P1 | /kunge UX Phase 1-3 實作 | ⏳ 規劃完整待實作 |
| P2 | 前端 deploy | ⏳ |

### 治理待辦（不可逆 - 等 owner）

| P | 項目 | 狀態 |
|---|---|---|
| P0 | 5 orphan volume 清理 | ⏳ 等 owner A/B/C/D |
| P0 | ADR-0020 + ADR-0035 proposed 收斂 | ⏳ owner |
| P1 | LINE channel groq fast-path (p95<5s) | ⏳ v6.13 |
| P2 | Hermes baseline 6/28 重評 | ⏳ |

## 4. 進化軌跡

| 時間 | 主軸 |
|---|---|
| 5/30 上午 | v6.12 4 原則 + Facade B |
| 5/30 下午 | Meta-治理 L58/L59/L60/L61 |
| 5/31 上午 | KG 整體性複查 + dedup |
| 5/31 下午 | LINE 修 / dashboard cron 凌晨化 / jsonl |
| 5/31 晚上 | scheduler events API + Frontend page + **ERP ingest 完成** |

## 5. 元洞察

**Owner approve 後續執行真活**：
- knowledge dedup ✅
- ERP ingest ✅ (本批)
- LINE 修 ✅
- 全部對齊 L43 安全 SOP（5 層備份 / 可逆）

**Frontend 落地**：
- SchedulerEventsPage 3 tabs + Route 註冊
- 整合三層 (jsonl / dashboard / page)
- 對齊「紀錄變文件化與架構」

---

> **核心精神**：待辦不是 list，是執行軌跡。
> 本日 58 commits = owner approve → 真活執行的真實循環。
