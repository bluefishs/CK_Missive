# CK_Missive 財務中樞建置總結與長線發展藍圖 (Final Roadmap)

> **版本**: v2.0.0
> **日期**: 2026-03-22
> **定位**: 宏觀戰略層級藍圖 — 引領未來三個季度的維運與智能化方向
> **適用對象**: 技術主管 / 專案經理 / 高階決策者
> **前身**: v1.0 初版架構演進摘要 → v2.0 三季度戰略展開

---

## 一、第一期戰役總結 (Phase 1~7B 竣工報告)

### 建設成果一覽

| 維度 | 量化指標 |
|------|---------|
| **資料基礎** | 4 DB 表、8 Repository、20 API 端點、24+ Schema classes |
| **前端體驗** | 5 頁面、18 React Query Hooks、路由三方同步 |
| **智能引擎** | 3 Agent 工具、2 主動觸發器、6 子掃描器 |
| **安全合規** | 20/20 端點認證保護、0 直接 DB 操作、Decimal 全精度 |
| **測試品質** | 220 ERP 相關測試通過、0 失敗、0 TSC 錯誤 |
| **架構評級** | **A+** (9 維度全 A 以上) |

### 核心技術資產

```
                    ┌─────────────────────────────────┐
                    │     FinanceLedger (統一帳本)      │
                    │   source_type + source_id 多態    │
                    │   case_code 軟參照橋樑            │
                    └──────────┬──────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
   │ ExpenseInv  │     │ ERPBilling  │     │ VendorPay   │
   │  費用報銷    │     │  應收請款    │     │  應付帳款    │
   │  approve()  │     │  update()   │     │  update()   │
   │  → verified │     │  → paid     │     │  → paid     │
   │  → 自動入帳  │     │  → AR拋轉   │     │  → AP拋轉   │
   └─────────────┘     └─────────────┘     └─────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Budget Firewall    │
                    │  80% 預警 / 100% 攔截 │
                    │  Modal.warning/error │
                    └─────────────────────┘
```

### 已消除的技術債清單

| 債務 | 狀態 | 修復方式 |
|------|------|---------|
| C02 雙重帳本 | ✅ | create() 改 pending，帳本僅 approve() 寫入 |
| N+1 查詢 (財務彙總) | ✅ | 遷移至 Repository SQL GROUP BY |
| 39 處直接 DB 操作 | ✅ | 全面遷移至 8 個 Repository |
| 8 處 ERP Service 合規 | ✅ | Phase 7-B repo.create/update/delete |
| 前端 toast 預算警報 | ✅ | Phase 7-A AlertDialog 升級 |
| 散落的 API response 型別 | ✅ | 統一至 types/erp.ts (SSOT) |

---

## 二、戰略定位：從「功能建設」到「營運智能」

第一期專注於**資料層與交易邏輯**的正確性 — 確保每一筆金流進出有據、帳本精準、預算可控。

下一階段的核心命題是：

> **如何讓這套已經堅實的財務引擎，從被動記帳工具進化為主動決策助理？**

三大戰略支柱：

| 支柱 | 定義 | 目標季度 |
|------|------|---------|
| **可見性 (Visibility)** | 讓數據說話 — 損益表、趨勢圖、預算儀表板 | Q2 |
| **可觸及 (Accessibility)** | 隨地決策 — LINE 簽核、行動審批、推播警報 | Q3~Q4 |
| **可預測 (Predictability)** | AI 前瞻 — 現金流預測、異常偵測、支出趨勢 | Q4+ |

---

## 三、Q2 近期規劃 (2026-04 ~ 2026-06)：前台體驗與 BI 儀表板

### 主題：讓已建好的引擎「看得見、用得著」

#### Q2-1: NemoClaw 夜間吹哨者 (Phase 7-C)

**目標**: 每晚自動盤點險區專案，推播預警至 LINE / 系統通知

| 任務 | 說明 | 優先級 |
|------|------|--------|
| 排程註冊 | 將 `ERPTriggerScanner.scan_all()` 加入 APScheduler (每日 00:30) | P0 |
| 80~100% 區間掃描 | 擴充 `check_budget_overrun()` 輸出分級預警 (warning/critical) | P0 |
| 警報去重 | 24h 內同 case_code 不重複推播 (Redis/DB dedup key) | P1 |
| LINE 推播整合 | `LinePushScheduler` 增加 `budget_overrun` 類型標籤與格式 | P1 |
| 系統通知持久化 | `NotificationService.create_notification()` 寫入 DB | P1 |

**技術架構**:
```
APScheduler (每日 00:30)
  → ProactiveTriggerService.scan_all()
    → ERPTriggerScanner.check_budget_overrun(threshold=80)
      → List[TriggerAlert] (severity: warning / critical)
        → dedup filter (Redis SET, TTL 24h)
          → NotificationService.create_notification() → DB
          → LinePushScheduler.push_message() → LINE
```

**驗收標準**: 測試 case 預算使用 85% → 夜間產生 warning 通知 → LINE 收到推播

#### Q2-2: Dashboard 擴展 (Phase 7-D)

**目標**: 從「KPI 卡片」進化為「損益儀表板」

| 任務 | 說明 | 優先級 |
|------|------|--------|
| 即時損益表 | 新增 `/erp/financial-summary/income-statement` API | P0 |
| 預算使用率排行 | Top N 專案預算消耗率排行 (BarChart + ProgressBar) | P0 |
| 月度趨勢線 | 收入/支出月度趨勢 (LineChart, 近 12 個月) | P1 |
| 快捷期間選擇器 | 本月 / 上月 / 本季 / 年度至今 (YTD) 按鈕 | P1 |
| AR/AP 帳齡分析 | 應收/應付 30/60/90+ 天帳齡分布 (StackedBar) | P2 |

**損益表結構** (簡化版，適合中小企業):
```
  營業收入 (ERPBilling paid)
- 營業成本 (VendorPayable paid + 外包費)
─────────────────────────────
= 營業毛利
- 營業費用 (ExpenseInvoice verified, by category)
─────────────────────────────
= 營業淨利
```

**前端新增元件**:
- `IncomeStatementCard.tsx` — 損益表卡片 (Descriptions + Divider)
- `BudgetRankingChart.tsx` — 預算排行 (recharts BarChart)
- `MonthlyTrendChart.tsx` — 月度趨勢 (recharts LineChart)
- `PeriodSelector.tsx` — 快捷日期按鈕組

#### Q2-3: 前端細節優化

| 任務 | 說明 | 優先級 |
|------|------|--------|
| 費用列表批次核准 | 勾選多筆 → 批次 approve (含預算校驗) | P2 |
| 帳本匯出 PDF | openpyxl → WeasyPrint 或 reportlab 輸出 PDF | P2 |
| Dashboard 權限分級 | 一般員工只看自己專案、主管看全公司 | P2 |

---

## 四、Q3 中期規劃 (2026-07 ~ 2026-09)：實體解耦與 AI 助理

### 主題：憑據數位化與智能問答

#### Q3-1: StorageService 抽象化

**目標**: 將收據/憑據從本地檔案系統解耦，支援雲端儲存

| 任務 | 說明 |
|------|------|
| `StorageService` 介面 | 定義 `save()/get_url()/delete()` 抽象方法 |
| `LocalStorageBackend` | 現有 `aiofiles` 邏輯包裝 (向下相容) |
| `S3StorageBackend` | boto3 + Signed URL (presigned_url, 30min TTL) |
| `MinIOStorageBackend` | 自建 MinIO (Docker, S3 API 相容) |
| 遷移腳本 | 既有 `uploads/` 批次遷移至 S3/MinIO |
| 環境切換 | `STORAGE_BACKEND=local|s3|minio` 環境變數控制 |

**介面設計**:
```python
class StorageService(ABC):
    async def save(self, file: bytes, filename: str, content_type: str) -> str:
        """返回 storage key (本地路徑或 S3 key)"""

    async def get_url(self, key: str, expires_in: int = 1800) -> str:
        """返回可存取 URL (本地路徑或 presigned URL)"""

    async def delete(self, key: str) -> bool:
        """刪除已儲存檔案"""
```

#### Q3-2: OCR 智能預填強化

| 任務 | 說明 |
|------|------|
| OCR 信心度 UI | 低信心欄位標紅框，高信心綠框 |
| 多語 OCR | 增加 `eng+chi_tra+chi_sim` 語言包 |
| OCR 結果快取 | 同一圖片 hash → 快取 OCR 結果 (Redis, 24h) |
| 學習回饋 | 人工修正後的值回饋至 Agent 學習記憶 |

#### Q3-3: NemoClaw 財務問答能力

**目標**: 讓 Agent 能回答「本季度哪些專案虧損？」「交通費佔比多少？」

| 任務 | 說明 |
|------|------|
| 新增 3 Agent 工具 | `get_income_statement`, `get_ar_aging`, `get_budget_ranking` |
| 自然語言→工具 | Agent 解析財務查詢意圖 → 呼叫對應工具 |
| 圖表生成 | Agent 回覆中嵌入 Mermaid pie/bar 圖表 |
| 跨模組關聯 | 「這個專案的外包費為什麼這麼高？」→ 關聯 VendorPayable 明細 |

---

## 五、Q4 遠期規劃 (2026-10 ~ 2026-12)：行動決策圈

### 主題：讓高階主管隨地核決

#### Q4-1: LINE Bot 卡片式簽核

**目標**: 基於已建好的 `APPROVAL_TRANSITIONS` 狀態機，實現 LINE 上的一鍵核決

| 任務 | 說明 |
|------|------|
| Rich Message 模板 | Flex Message 卡片：發票摘要 + 金額 + 預算使用率 |
| Postback 處理 | approve/reject 按鈕 → 呼叫 `/erp/expenses/approve` API |
| 安全驗證 | LINE user_id → DB User.line_user_id 綁定 + 簽核權限校驗 |
| 審核歷程 | 卡片底部顯示：主管已核准 → 待財務核准 |
| 駁回理由 | 駁回時彈出 LINE 文字輸入 → 附加至 reject reason |

**LINE Flex Message 示意**:
```
┌─────────────────────────┐
│  費用報銷審核通知         │
│                         │
│  發票: AB12345678        │
│  金額: NT$ 15,000        │
│  類別: 交通費             │
│  申請人: 王小明           │
│  專案: P114-003          │
│  預算使用: ████░░ 72%    │
│                         │
│  [✅ 核准]  [❌ 駁回]     │
└─────────────────────────┘
```

#### Q4-2: Mobile Web 審批介面

| 任務 | 說明 |
|------|------|
| 響應式審批頁 | `/m/approve/:id` — 手機優先設計 |
| PWA 離線支援 | Service Worker 快取審核清單 |
| 推播通知 | Web Push API → 新報銷待審時推播 |
| 快速掃碼報銷 | 手機相機 → QR 掃描 → 一鍵提交 |

#### Q4-3: AI 預測與異常偵測

| 任務 | 說明 |
|------|------|
| 支出趨勢預測 | 基於歷史 FinanceLedger 的時間序列預測 (Prophet/ARIMA) |
| 異常支出偵測 | Z-score / IQR 偵測異常高額報銷 → 主動警報 |
| 現金流預測 | AR 預計收款 + AP 預計付款 → 未來 30/60/90 天現金流 |
| 季度財報自動生成 | Agent 自動撰寫季度財務摘要報告 (Markdown → PDF) |

---

## 六、技術演進路線圖

```
Q2 (04-06)               Q3 (07-09)               Q4 (10-12)
─────────────────────    ─────────────────────    ─────────────────────
  夜間吹哨者排程            StorageService 抽象       LINE 卡片式簽核
  損益表 API + 前端         OCR 信心度 UI             Mobile Web PWA
  月度趨勢圖               Agent 財務問答             AI 異常偵測
  預算排行榜               跨模組工具 +3              現金流預測
  帳齡分析                 學習回饋迴路               季度報告自動化
─────────────────────    ─────────────────────    ─────────────────────
  重點: 可見性              重點: 可觸及               重點: 可預測
  (Visibility)            (Accessibility)           (Predictability)
```

---

## 七、風險與緩解策略

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| LINE API 政策變更 | Q4 簽核功能受阻 | 同步建設 Mobile Web 作為備選管道 |
| S3 成本超預期 | Q3 儲存方案選型 | MinIO 自建 + lifecycle policy (90天歸檔) |
| OCR 辨識率不足 | Q3 智能預填品質 | 維持「預填+人工確認」流程，不自動 verified |
| 預測模型冷啟動 | Q4 AI 預測準確度 | 需累積 6+ 個月交易資料方可啟用 |
| VRAM 限制 (8GB) | Agent 推理負載 | vLLM AWQ 量化 + Ollama embed 共存已驗證 |

---

## 八、成功指標 (KPI)

| 季度 | 指標 | 目標值 |
|------|------|--------|
| Q2 | 夜間掃描器覆蓋率 | 100% 活躍專案 |
| Q2 | Dashboard 日均瀏覽 | >5 次/日 |
| Q2 | 預算超支事前攔截率 | 100% (0 漏網) |
| Q3 | 憑據雲端儲存遷移率 | 100% |
| Q3 | Agent 財務問答準確度 | >85% |
| Q4 | LINE 簽核使用率 | >50% 審核透過 LINE 完成 |
| Q4 | 異常偵測召回率 | >80% |

---

## 九、依賴與前置條件

| 項目 | 狀態 | 說明 |
|------|------|------|
| FinanceLedger 統一帳本 | ✅ 就緒 | 多態 source_type/source_id |
| APPROVAL_TRANSITIONS 狀態機 | ✅ 就緒 | 2/3 層審核 + 金額門檻 |
| AR/AP 自動拋轉 | ✅ 就緒 | Billing.paid → income, VendorPayable.paid → expense |
| Budget Firewall | ✅ 就緒 | 80% warn / 100% block + AlertDialog |
| ERPTriggerScanner | ✅ 就緒 | 6 子掃描器 + TriggerAlert 資料結構 |
| NotificationService | ✅ 就緒 | DB 持久化 + safe_* 隔離 session |
| LineBotService | ✅ 就緒 | Webhook + push_message (待擴充 Rich Message) |
| LinePushScheduler | ✅ 就緒 | scan_and_push() 整合 (待排程註冊) |
| React Query Hooks | ✅ 就緒 | 20+ hooks 全覆蓋 |
| recharts 圖表庫 | ✅ 已安裝 | BarChart / PieChart / LineChart |

---

## 十、文件索引

| 文件 | 用途 |
|------|------|
| `specs/finance_erp_task.md` | 任務追蹤器 (開發者視角) |
| `docs/specs/finance_erp_master_plan.md` | 主藍圖 SSOT (技術細節) |
| `docs/specs/finance_erp_audit_report_20260321.md` | 架構審計報告 (品質追蹤) |
| `specs/finance_erp_final_roadmap.md` | **本文件** — 戰略藍圖 (管理層視角) |

---

> **結語**: 第一期戰役奠定了堅實的資料層與交易邏輯基礎。未來三個季度的重心從「把帳記對」轉向「讓帳說話」— 透過可見性、可觸及性、可預測性三大支柱，將 CK_Missive 財務模組從記帳工具進化為決策引擎。
>
> 此藍圖為戰略指引文件，具體實作細節由 `master_plan.md` 逐任務追蹤。
