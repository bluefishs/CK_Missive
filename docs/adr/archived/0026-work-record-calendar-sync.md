# ADR-0026: WorkRecord ↔ Calendar 自動同步 + 狀態三桶重構

- **Status**: archived（2026-04-27，feature 已上線）
- **歸檔原因**: WorkRecord ↔ Calendar 雙向同步已穩定運行，狀態三桶（pending/in_progress/closed）落地。降為實作參考
- **Date**: 2026-04-21
- **Deciders**: Aaron (jujuiacc@gmail.com, superuser)
- **Related**: ADR-0024（Calendar Visibility）, morning_report_service

---

## Context

### 痛點

1. **公文設 calendar_event**（已有），但 **work_record 設 deadline_date 不自動建 calendar_event** → 日曆頁看不到派工期限
2. 用戶需在**公文與派工兩處各設一次** → 重複、易漏、不同步
3. 「進行中」語意不清 — 原定義「未完成且無律定」與用戶直覺「進度 >0%」衝突

### 觸發事件

派工單 021（115年_派工單號021）有 work_record deadline 2026-05-03，但因無 calendar_event，狀態誤判為「進行中」（需主動推進）而非「已排程」。

---

## Decision

### 1. 狀態三桶重構

7 個狀態分層調整為 4 個「需主動關注」+ 4 個「安心」：

| 狀態 | 條件 | 顏色 | 行動 |
|---|---|---|---|
| **逾期** | deadline 已過且未完成 | 紅 | 立即處理 |
| **預警案件** | 交付期限 ≤ 7 天 | 火紅 | 即將到期 |
| **需處理** | 未完成且無律定 | 橙 | 補建期限/事件 |
| **闕漏紀錄** | 有公文但 0 records | 桃紅 | 補建 work_record |
| **排程中** | 交付期限 > 7 天 | 藍 | 等時間到 |
| **待結案** | 100% 完成但未發文 | 金 | 補發文 |
| **已交付** | 100% + work_result + has_out | 綠 | 無 |
| **已結案** | milestone closed | 灰 | 無 |

### 2. 交付期限優先 work_record

`upcoming_events.next_event_date` 計算改為：
- **優先**：未完成 work_record 的 MIN(deadline_date)
- **fallback**：日曆事件 MIN(start_date)

### 3. WorkRecord → Calendar 自動同步

**Schema 擴充**（`document_calendar_events`）：
```sql
ALTER TABLE document_calendar_events
  ADD COLUMN source_type VARCHAR(30) DEFAULT 'document' NOT NULL,  -- document | work_record | manual
  ADD COLUMN source_id INT,                                        -- 來源 ID
  ADD COLUMN dispatch_order_id INT REFERENCES taoyuan_dispatch_orders(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX uq_calendar_source
  ON document_calendar_events(source_type, source_id)
  WHERE source_type != 'manual' AND source_id IS NOT NULL;
```

**Sync helper**（`app/services/taoyuan/work_record_calendar_sync.py`）：
- `sync_work_record_to_calendar(db, work_record, actor_id)` — upsert event
- `cancel_work_record_calendar(db, work_record_id)` — 軟取消

**觸發點**（`workflow.py`）：
- `POST /workflow/create` → 建立後 sync
- `POST /workflow/{id}/update` → 更新後 sync（deadline 變動自動反映）
- `POST /workflow/{id}/delete` → 刪除前標 cancelled（保留歷史）

**Event 格式**：
- Title: `[派工期限] {dispatch_no} · {category_label}`
- Start: deadline_date + 18:00（台灣下班時間）
- all_day: true
- event_type: `work_record_deadline`

---

## Rationale

### 為什麼狀態從 2 桶拆 3 桶

原「進行中」語意矛盾（「在進行」vs「無律定」）。拆成：
- **預警案件**：期限 ≤ 7 天 → 即將到期
- **需處理**：無期限 → 等待律定
- **排程中**：期限 > 7 天 → 安心等

管理者能**一眼分辨**問題性質，而非混在同一個桶。

### 為什麼 7 天門檻

- 台灣公文常見辦理期限 7 天、14 天
- 7 天剛好是「一週前警示」合理範圍
- 可未來透過 env var `DISPATCH_WARNING_DAYS` 調整

### 為什麼 calendar source 用 VARCHAR + ID 而非多 FK

- FK 表多（document / work_record / 未來 meeting...）→ 多欄位臃腫
- `source_type + source_id` 單一對應 → 唯一索引保證冪等
- 未來擴展新來源只需新 source_type，不動 schema

### 為什麼軟取消而非硬刪

- 用戶可能誤刪 work_record → 日曆事件若硬刪會突然消失
- 軟取消保留歷史脈絡，`status='cancelled'` 可視化提醒
- 若之後 work_record 復建，event 可 reactivate

---

## Consequences

### 正面

- 單一設定多處顯示：設 work_record deadline → 日曆自動出現
- 狀態桶語意清楚，管理者行動明確
- 來源可追溯，避免重複與漂移

### 負面 / 風險

- `source_id + source_type` 唯一索引如有 race condition 可能 insert 衝突
  - 緩解：使用 ORM session lock，衝突時 fallback 到 update
- `document_calendar_events` 表行數預期略增（每個 work_record.deadline 一筆）
  - 緩解：小量級，索引覆蓋

### 測試

- `backend/tests/unit/test_work_record_calendar_sync.py` 6 tests：
  - 無 deadline → 無 event
  - deadline 被清除 → 既有 event 標 cancelled
  - 刪除 work_record → event 標 cancelled
  - cancel_calendar 冪等

---

## Implementation

### 檔案變動

| 檔案 | 變動 |
|---|---|
| `alembic/versions/20260421a002_calendar_source_tracking.py` | Schema migration |
| `app/extended/models/calendar.py` | `DocumentCalendarEvent` 加 source_type/source_id/dispatch_order_id |
| `app/services/taoyuan/work_record_calendar_sync.py` | 新建 sync helper |
| `app/api/endpoints/taoyuan_dispatch/workflow.py` | create/update/delete 掛 hook |
| `app/services/ai/domain/morning_report_service.py` | SQL: upcoming_events 兩路徑；closure_level 加 `warning` / `needs_action` |
| `app/api/endpoints/taoyuan_dispatch/statistics.py` | display_status 映射新狀態 |
| `frontend/src/components/taoyuan/MorningReportTrackingTable.tsx` | STATUS_CONFIG 新增「預警案件」「需處理」+ tooltip |
| `frontend/src/components/taoyuan/DispatchOverviewTab.tsx` | 統計卡片從 4 → 6（拆預警/需處理/逾期/闕漏獨立）|
| `frontend/src/components/taoyuan/workflow/ChainTimeline.tsx` | 主日期顯示 deadline 優先 |
| `backend/tests/unit/test_work_record_calendar_sync.py` | 6 regression tests |

---

## v5.8.1 更新（2026-04-21）— Title 統一模板

### 修訂動機

backfill 58 筆後發現：
- 標題 `[派工期限] {dispatch_no} · {category}` 過於空洞，無業務主題
- 與現有 document event（`[REMINDER] {doc.subject}`）語意密度落差大
- 公文自動建立 event 時無統一模板，使用者自行編輯無規則

### 決議：統一 title 模板

```
【{動詞+類別}】派工單號{no3}({team})_{project_name}_{item}
```

**範例**：
```
【提交成果】派工單號010(昇揚)_平鎮區新興路179巷9弄..._協議價購報告
【召開會議】派工單號003(全國)_中壢區龍岡路..._協議價購市價審查會議
【接收派工】派工單號008(全國)_大溪區大漢溪右岸新闢道路工程_土地徵收市價查估作業
```

### 8 類「動詞+類別」組合

| work_category | 組合標籤 |
|---|---|
| dispatch_notice | 【接收派工】|
| work_result | 【提交成果】|
| meeting_notice | 【召開會議】|
| meeting_record | 【提交會議紀錄】|
| survey_notice | 【辦理會勘】|
| survey_record | 【提交會勘紀錄】|
| admin_notice | 【發布行政】|
| other | 【辦理事項】|

### 元件位置

- **共用模板函數**：`app/services/common/calendar_title_template.py`
  - `build_calendar_event_title()` 公用 API
  - `SURVEY_UNIT_ABBR` 查估團隊縮寫表（9 家預設 + fallback 前 2 字）
  - `WORK_CODE_ITEM_MAP` (category, 業務代碼) → 項目名稱映射（≈48 組）
- **套用點 1**：`work_record_calendar_sync.py` - 派工自動同步
- **套用點 2**：`document_calendar_integrator.py` - 公文加入行事曆
- **使用者 Override**：WorkRecordForm `description` 欄位
  - 留空 → 套自動模板
  - 以 `【` 或 `[` 開頭 → 整段作為標題（尊重用戶自訂）

### Backfill（2026-04-21）

```
41 筆 work_record events title
  updated: 41  skipped: 0  errors: 0
```

## Next Steps

- [ ] Calendar 頁面 UI 顯示 event 來源 tag（document/派工單/手動）
- [x] ~~批次 backfill：既有 work_records.deadline_date 逐筆同步為 event~~（已完成）
- [x] ~~統一 title 模板~~（v5.8.1 已完成）
- [ ] `DISPATCH_WARNING_DAYS` env var 讓 7 天閾值可調
- [ ] Form 加 Checkbox「同步行事曆」給管理員控制權
- [ ] 查估團隊縮寫映射表支援 admin UI 維護（目前寫死）
