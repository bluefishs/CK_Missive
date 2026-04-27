# Services 頂層 Bounded Context 映射表

> **產出**：2026-04-25
> **目的**：將 `services/` 頂層 85 個散戶檔案對應到 bounded context（DDD 領域）
> **策略**：先**加註不搬檔**（降低風險，保留 git history），未來再批次遷移到子包
> **關聯**：
> - 標準：`docs/architecture/STANDARD_REFERENCE.md` §1.2 目標結構
> - Feedback：`memory/feedback_ddd_over_line_count.md` — 領域驅動 > 行數驅動

---

## 使用方式

### 給讀者（理解現況）
- 查某檔屬於哪個 context → 搜本表
- 若找不到 → 該檔尚未分類，歡迎 PR 補上

### 給維護者（加新 service）
1. 先定義新 service 的 bounded context（見 §1.1 決策樹）
2. 若 context 已存在 → 放入該子包（若子包不存在則留頂層但必入本表）
3. 若是新 context → 本表新增欄位

### 給重構者（未來遷移到子包）
每個 context 可獨立做批次 rename commit：
```
commit title: refactor: services/* → services/<context>/ (bounded context migration)
```

---

## 1. 映射表

### 1.1 Context 決策樹

```
收到新 service 檔 → 問：
  1. 它處理的主要實體是？
     - OfficialDocument / Attachment / DocNumber → document
     - ContractProject / PMCase / CaseCode → contract
     - GovernmentAgency / PartnerVendor → agency / vendor
     - 第三方通訊 API（LINE/TG/Discord）→ integration.<channel>
     - 財務實體（Quotation/Invoice/Ledger/Asset）→ erp
     - 桃園派工 → taoyuan
     - 標案 → tender
     - 行事曆 → calendar
     - Wiki / KG / RAG → ai 或 wiki（看層次）
  2. 是否橫切 3+ context？ → common / observability / security
  3. 是否純技術 middleware？ → core (app/core/)
```

### 1.2 完整映射（85 檔 × 16 context）

> **Wave 1 完成狀態（2026-04-27, v5.9.9）**：
> 6 contexts × 28 檔已實際遷移到子包，原路徑保留 stub（DeprecationWarning + re-export）。
>
> | Context | 檔數 | 狀態 | Commit |
> |---|---|---|---|
> | document | 11 | ✅ migrated | sub-batch A |
> | contract | 6 | ✅ migrated | sub-batch B contract |
> | agency | 3 | ✅ migrated | sub-batch B vendor+agency |
> | vendor | 1 | ✅ migrated | sub-batch B vendor+agency |
> | audit | 3 | ✅ migrated | sub-batch C |
> | notification | 4 | ✅ migrated | sub-batch C + pilot |
> | **Wave 1 小計** | **28** | **Wave 1 100%** | v5.10.0-rc |
> | erp (extension) | 9 | ✅ migrated | Wave 2 |
> | integration (line/telegram/discord/共用) | 10 | ✅ migrated | Wave 3 |
> | **Wave 1+2+3 累計** | **47** | — | v5.10.0+ |
>
> 其他 context（tender / erp / integration / calendar / ai / ...）尚未遷移，
> 散戶仍在頂層。等 Wave 2 排程。
>
> Stub 預計 2026-Q3 移除（給內部 import 3 個月遷移時間）。


| Context | 檔案 | 子職責 | 備註 |
|---|---|---|---|
| **document** (7) | `document_service.py` | core | 公文 CRUD 主入口 |
| | `document_dispatch_linker_service.py` | integration | 公文↔派工關聯（拆自 service）|
| | `document_import_logic_service.py` | io.import | Excel/CSV 匯入邏輯 |
| | `document_filter_service.py` | query | 篩選專用 |
| | `document_statistics_service.py` | analytics | 統計 |
| | `document_export_service.py` | io.export | |
| | `document_import_service.py` | io.import | 匯入 facade |
| | `document_processor.py` | processor | Pipeline 處理 |
| | `document_query_filter_service.py` | query | 複合篩選 |
| | `document_serial_number_service.py` | identifier | 文號產生 |
| | `receiver_normalizer.py` | utility | 收發文單位正規化 |
| **contract** (5) | `project_service.py` | core | 承攬案件 CRUD |
| | `project_staff_service.py` | staff | 人員配置 |
| | `project_analytics_service.py` | analytics | |
| | `case_code_service.py` | identifier | `case_code` 跨模組橋樑 |
| | `case_field_sync_service.py` | sync | 欄位同步 |
| | `project_agency_contact_service.py` | contact | 專案-機關聯絡人 |
| **agency** (3) | `agency_service.py` | core | 機關 CRUD |
| | `agency_matching_service.py` | matching | 智慧匹配 |
| | `agency_statistics_service.py` | analytics | 統計 |
| **vendor** (1) | `vendor_service.py` | core | 協力廠商 |
| **audit** (3) | `audit_service.py` | core | 審計主入口 |
| | `audit_event_loggers.py` | loggers | Mixin loggers |
| | `audit_mixin.py` | mixin | CRUD 審計 Mixin |
| **notification** (4) | `notification_service.py` | core | 通知服務 |
| | `notification_dispatcher.py` | dispatcher | 派發 |
| | `notification_template_service.py` | template | 模板 |
| | `notification_helpers.py` | helpers | |
| | `project_notification_service.py` | project | 專案通知（跨 context，可考慮移 contract）|
| **integration.line** (4) | `line_bot_service.py` | core | LINE Bot |
| | `line_flex_builder.py` | flex | Flex Message |
| | `line_image_handler.py` | image | 圖片處理 |
| | `line_push_scheduler.py` | scheduler | 推播排程 |
| **integration.telegram** (2) | `telegram_bot_service.py` | core | Telegram Bot |
| | `telegram_content_sanitizer.py` | sanitizer | PII 遮罩（ADR-0027）|
| **integration.discord** (2) | `discord_bot_service.py` | core | Discord Bot |
| | `discord_helpers.py` | helpers | 格式化 |
| **integration** (3) | `channel_adapter.py` | adapter | 跨通道抽象 |
| | `sender_context.py` | context | 發送者 context |
| | `agent_stream_helper.py` | agent-stream | Agent 串流 |
| **tender** (8) | `tender_search_service.py` | search | |
| | `tender_search_query.py` | search-query | |
| | `tender_data_transformer.py` | transform | |
| | `tender_subscription_scheduler.py` | subscription | |
| | `tender_analytics_service.py` | analytics-facade | Facade |
| | `tender_analytics_battle.py` | analytics-battle | 戰情室 |
| | `tender_analytics_price.py` | analytics-price | 底價 |
| | `tender_cache_service.py` | cache | DB 持久化 |
| | `ezbid_scraper.py` | scraper.ezbid | |
| | `pcc_today_scraper.py` | scraper.pcc | |
| **erp** (10) | `expense_invoice_service.py` | expense.facade | 費用報銷 v2.0 Facade |
| | `expense_approval_service.py` | expense.approval | 審批工作流 |
| | `expense_import_service.py` | expense.io | 匯入匯出 |
| | `invoice_recognizer.py` | invoice.ocr-facade | QR+OCR Facade |
| | `invoice_ocr_parser.py` | invoice.ocr-parser | |
| | `invoice_ocr_service.py` | invoice.ocr-service | |
| | `invoice_qr_decoder.py` | invoice.qr | |
| | `finance_ledger_service.py` | ledger | 統一帳本 |
| | `financial_summary_service.py` | summary | 財務彙總 |
| | `finance_export_service.py` | export | 報表匯出 |
| **wiki** (4) | `wiki_service.py` | core | |
| | `wiki_compiler.py` | compiler | Karpathy Phase 2 |
| | `wiki_formatter.py` | formatter | |
| | `wiki_coverage_service.py` | coverage | KG 覆蓋率 |
| **calendar** (4) | `document_calendar_integrator.py` | integration | 公文→行事曆 |
| | `document_calendar_service.py` | service | 行事曆 CRUD |
| | `document_calendar_sync.py` | sync | |
| | `google_calendar_client.py` | client.google | Google API |
| | `google_sync_scheduler.py` | scheduler.google | |
| **reminder** (2) | `reminder_service.py` | core | |
| | `reminder_scheduler.py` | scheduler | |
| **ai.complement** (3) | `skill_evolution_service.py` | skill-evolution | 技能演化（可能入 ai/） |
| | `kb_embedding_service.py` | embedding | KB embedding |
| | `search_optimizer.py` | search | 搜尋優化 |
| **system** (3) | `admin_service.py` | admin | 管理端 |
| | `system_health_service.py` | health | 健康檢查 facade |
| | `system_health_checks.py` | health-checks | 檢查項 |
| **security** (1) | `security_scanner.py` | scanner | OWASP 15 規則 |
| **taoyuan** (1) | `taoyuan_link_service.py` | link | 派工頂層 link（已有子包）|
| **backup** (1) | `backup_scheduler.py` | scheduler | 舊 scheduler（已有子包）|
| **user** (1) | `user_alias_service.py` | alias | 使用者別名 |
| **navigation** (1) | `navigation_sync_service.py` | sync | 導覽同步 |
| **common** (3) | `csv_processor.py` | csv | |
| | `coding_helpers.py` | helpers | |
| | `excel_import_service.py` | excel | |
| | `import_validators.py` | validators | |

**合計**：85 檔 → 16 contexts

---

## 2. 遷移路線圖（漸進 DDD）

### Phase 1（標註期）✅ 本次完成
- 產出本映射表
- 更新 `.claude/rules/architecture-backend.md` 提及本表
- 不動任何檔案位置

### Phase 2（小 context 批次搬）— 每 context 1 commit
優先順序（先搬容易的）：

1. **wiki/**（4 檔）— 已有共同前綴，低耦合
2. **audit/**（3 檔）— 自洽 Mixin
3. **tender/**（8 檔）— 已有 `api/endpoints/tender_module/` 子包範本
4. **integration.line/telegram/discord**（8 檔）— 通道隔離
5. **erp/**（10 檔）— 已有 `services/erp/` 子包（補遷即可）
6. **notification/**（4 檔）

### Phase 3（核心 context 搬）— 需跨 repo import 修正
7. **document/**（11 檔）
8. **contract/**（6 檔）
9. **agency/** + **vendor/**（4 檔）

### Phase 4（最後的跨域 context）
10. **calendar/** / **reminder/** / **ai.complement/**
11. **integration/**（facade 類）

每階段結束後：
- 跑 `scripts/checks/verify_architecture.py` 驗證
- 跑完整 pytest（unit + integration）
- 更新本表「備註」欄

---

## 3. 何時真正搬？

**不急**。本映射表足以讓新人理解現況 + 給未來重構指路。

**觸發條件**（滿足任一即啟動 Phase 2）：
- ADR-0020 Phase 1 啟動（4 bridge skills 需要 context-aware routing）
- Services 頂層超過 100 檔（擁擠度臨界點）
- 新加入大型領域（如 `lvrland` bounded context 併入本 repo）

---

## 4. 交叉引用

- `docs/architecture/STANDARD_REFERENCE.md` §1「服務層 DDD 組織原則」
- `backend/app/services/__init__.py` — 考慮未來加 context-aware re-export
- `memory/feedback_ddd_over_line_count.md` — 原則：領域 > 行數
- `CK_AaaP/CONVENTIONS.md` §3「跨 repo 文件位置標準」

---

**變更歷史**
- v1.0（2026-04-25）：首版映射，85 檔 → 16 contexts
