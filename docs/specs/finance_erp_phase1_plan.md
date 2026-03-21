# 財務與發票模組重構：覆盤與階段實作計畫

> **時間點**: 第一期 (Model 重構與代碼清理) 完成後
> **目標**: 記錄由開發團隊/使用者方直接提交的大規模重構，並擬定後續待辦。

## 覆盤紀錄 (Retrospective)

目前系統已漂亮地完成了最底層核心架構的翻新，奠定後續整合安全穩固的基礎。

1. **嚴謹的 Model 實踐**：
   - 舊的 `Ledger` 與 `Invoice` 已轉變為 `FinanceLedger`, `ExpenseInvoice`, `ExpenseInvoiceItem`。
   - 完全採納 `case_code` 作為軟參照橋樑，使得非專案支出（一般營運）能夠順利入帳。
   - `FinanceLedger` 的多態參照 (`source_type`, `source_id`) 設計能直接反查原始的報銷發票。
2. **徹底的技術債清理**：
   - 移除不合規（混用同步 Session、違規邏輯）的舊代碼。

## 後續階段實作計畫 (Next Steps)

按照 `invoice_system_architecture_plan.md` v2.0，接下來優先進行以下開發行動：

1. **補齊資料契約 (Schema Layer)**：
   - 建立 `backend/app/schemas/erp/expense.py`
   - 建立 `backend/app/schemas/erp/ledger.py`
2. **實作持久化層 (Repository Layer)**：
   - 建立 `expense_invoice_repository.py` 和 `ledger_repository.py`
   - 統一繼承專案既有之 `BaseRepository[T]` 並以 Async 查詢為主。
3. **完成 Alembic 遷移 (Migration)**：
   - 生成全新的資料庫遷移腳本。
4. **重建業務邏輯與 API 端點 (Service & Endpoint)**：
   - 開發 `ExpenseInvoiceService` ( QR 掃描準備 ) 和 `FinanceLedgerService`。
   - 將路由加入 `/erp` 體系中。
