# ERP 財務體系開發任務清單 (Task Tracker)

> **同步版本**: Master Plan v12.0
> **狀態**: 全系列包含底層防呆、供應商關聯、交易邊界防範機制均已竣工。下階段將推進前端 BI 與 LINE 行動化。

## ✅ 階段 A：基礎模組與架構隔離 (100%)
- [x] ORM Models 與 Repository 架構
- [x] 多幣別自動換算本位幣機制 (`@model_validator`)

## ✅ 階段 B：智能預算防線與金流拋轉 (100%)
- [x] **多層狀態機**：`APPROVAL_TRANSITIONS`
- [x] **動態預算聯防**：`_check_budget` 雙層警戒阻擋
- [x] **AP/AR 跨模組拋轉**：吸納請款出納與廠商採購之金流

## ✅ 階段 C：大數據分析與 ACID 底層鞏固 (100%)
- [x] **BI 大數據效能引擎**：N+1 高效解決方案、月均線、排行榜聚合。
- [x] **ACID 交易邊界**：控制 `Ledger` 的 `flush/commit` 單一交易保護。

## ✅ 階段 D：主檔關聯與全線跨模組防呆 (100%)
- [x] **供應商智慧關聯**：導入 `vendor_id` 外鍵，透過 `seller_ban` 自動組聯 `PartnerVendor` 主檔。
- [x] **超級案號防呆鎖**：`_validate_case_code` 三重跨模組探測，杜絕幽靈專案支出。

## ⏳ 階段 E：前台整合與智能維運 (Upcoming)
- [ ] 供應商對帳單匯出：以 `vendor_id` 為基礎實作廠商應付表 (Vendor Statement)
- [ ] LINE 行動端接入：接收 `line_upload` 影像推播，免等待實體驗收
- [ ] React 儀表板開發：對接月均線/熱點排版與錯誤 UX (AlertDialog) 攔截
