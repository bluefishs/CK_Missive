# ADR-0013: 統一編碼體系架構設計

> **狀態**: **accepted** (Phase 1 + 2 已交付；Phase 3-4 延後)
> **日期**: 2026-04-02
> **接受**: 2026-04-10 (使用者選 Plan A — 接受 Phase 1' 範圍並重新規劃)
> **決策者**: 系統架構覆盤
> **關聯**: ADR-0012 (標案檢索), case_code_service.py, CHANGELOG v5.3.24

## 2026-04-10 重新評估註記

原 ADR phase 計畫 (v5.4/v5.5 目標) 版本號已過期，當前為 v5.5.4。
實際進度盤點 (2026-04-10)：

| 原 Phase | 目標 | 實際狀態 |
|---------|------|---------|
| Phase 1 | project_code 統一 (CK 前綴) | ✅ **已完成** 2026-04-10 — migration `20260405a002` DB 回補 70 contract_projects + 48 pm_cases + 70 erp_quotations；雙 generator 對齊 (`project_repository.get_next_project_code` + `case_code_service.generate_project_code`) |
| Phase 1 | asset_code 自動生成 | ⏳ 未完成 |
| Phase 2 | billing_code / invoice_ref / ledger_code 欄位 | ✅ **已完成** — migration `20260405a004` 已加入 3 欄位 (尚未接通自動生成) |
| Phase 3 | dispatch_no 西元年遷移 | ⏸ **延後** — 影響既有紙本對照，blast radius 高 |
| Phase 4 | CodeGenerationService 統一入口 | ⏸ **取消** — 現有 Repository 分散實作已足夠，ROI 低 |

**下一步優先級**:
1. P1 — asset_code 自動生成 (填補 Phase 1 剩餘部分)
2. P2 — 接通 billing_code / invoice_ref / ledger_code 的自動生成邏輯 (欄位已在 DB)
3. P3 — dispatch_no 漸進遷移 (可選，等業務需要時)

原文件後續內容保留供參考，但請以上表為準。

---

## 背景

### 現狀問題

系統經過多階段擴充（公文→派工→PM→ERP→標案），累積 15 種編碼機制，存在以下問題：

| # | 問題 | 影響範圍 | 嚴重度 |
|---|------|---------|--------|
| 1 | **project_code 雙生成器**：`CaseCodeService` 產出 `2026_01_01_001`，`ProjectRepository` 產出 `CK2026_01_01_001` | 專案管理 | HIGH |
| 2 | **dispatch_no 使用民國年**：`115年_派工單號011`，其餘系統使用西元年 | 派工/公文 | MEDIUM |
| 3 | **finance_ledger 無業務碼**：僅有 auto-increment ID，無法從代碼辨識來源 | 帳本 | LOW |
| 4 | **asset_code 無自動生成**：範本建議 `AST-2026-001` 但完全手動 | 資產 | MEDIUM |
| 5 | **billing 無編號**：free text `第1期` 無法結構化查詢 | 請款 | LOW |
| 6 | **ERP invoice 無系統參照碼**：使用手工輸入的統一發票號碼 | 發票 | LOW |
| 7 | **併發保護不一致**：僅 dispatch_no 有 3 次重試，其餘靠 unique constraint | 全域 | MEDIUM |
| 8 | **生成邏輯分散**：CaseCodeService、各 Repository、各 Service 各自實作 | 維護性 | MEDIUM |

### 現有編碼清單

```
自動生成 (6):
  case_code      CK{yyyy}_{MOD}_{CC}_{NNN}     跨模組橋樑
  project_code   CK{yyyy}_{CC}_{NN}_{NNN} *    成案專案 (*格式不一致)
  auto_serial    {R|S}{NNNN}                    公文流水號
  dispatch_no    {ROC}年_派工單號{NNN}           派工單號 (民國年)
  account_code   OP_{yyyy}_{XX}_{NNN}           營運帳目
  (無)           finance_ledger 無業務碼

外部/手動 (9):
  doc_number     政府公文字號 (外部)
  agency_code    機關代碼 (外部)
  vendor_code    統編/自訂 (手動)
  invoice_number 統一發票號碼 (手動)
  inv_num        電子發票 XX12345678 (手動/QR)
  asset_code     AST-2026-001 (手動)
  billing_period 第1期/尾款 (free text)
  unit_id        標案機關 ID (外部)
  job_number     標案工程號 (外部)
```

## 決策

### 一、統一編碼命名規範

```
┌─────────────────────────────────────────────────────────────┐
│                    CK 統一編碼體系                            │
│                                                             │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌───────┐         │
│  │ 企業前綴 │  │ 年度 4碼 │  │模組 2碼│  │類別2碼│ │序號3碼│ │
│  │   CK     │  │  2026    │  │  PM    │  │  01   │ │ 001  │ │
│  └─────────┘  └──────────┘  └────────┘  └───────┘         │
│                                                             │
│  完整格式: CK{yyyy}_{MOD}_{CC}_{NNN}                        │
│  範例:     CK2026_PM_01_001                                 │
└─────────────────────────────────────────────────────────────┘
```

### 二、模組代碼分配

| 模組代碼 | 全名 | 適用實體 | 編碼格式 | 現狀 |
|---------|------|---------|---------|------|
| **PM** | Project Management | 案件 (pm_cases) | `CK{yyyy}_PM_{CC}_{NNN}` | ✅ 已實作 |
| **FN** | Finance | 報價 (erp_quotations) | `CK{yyyy}_FN_{CC}_{NNN}` | ✅ 已實作 |
| **PJ** | Project | 成案專案 (contract_projects) | `CK{yyyy}_PJ_{NN}_{NNN}` | ⚠️ 需統一 |
| **DP** | Dispatch | 派工單 (dispatch_orders) | `CK{yyyy}_DP_{CC}_{NNN}` | ⚠️ 需遷移 |
| **OP** | Operations | 營運帳目 (operational_accounts) | `OP_{yyyy}_{XX}_{NNN}` | ✅ 已實作 (獨立) |
| **BL** | Billing | 請款 (erp_billings) | `BL_{yyyy}_{NNN}` | 🆕 新增 |
| **IV** | Invoice | 系統發票參照 (erp_invoices) | `IV_{yyyy}_{NNN}` | 🆕 新增 |
| **AT** | Asset | 資產 (assets) | `AT_{yyyy}_{CC}_{NNN}` | 🆕 新增 |
| **FL** | Finance Ledger | 帳本 (finance_ledgers) | `FL_{yyyy}_{NNN}` | 🆕 新增 |

> **設計決定**: PM/FN 使用 `CK` 前綴（跨模組橋樑），其餘模組使用自身前綴（模組內部）。

### 三、各實體詳細編碼規格

#### 3.1 case_code (維持不變)
```
格式:  CK{yyyy}_{MOD}_{CC}_{NNN}
範例:  CK2026_PM_01_001  (PM 委辦招標第1號)
       CK2026_FN_01_003  (ERP 報價單第3號)
生成:  CaseCodeService.generate_case_code()
角色:  跨模組橋樑 — PM ↔ ERP ↔ 帳本 ↔ 費用 ↔ 資產
```

#### 3.2 project_code (需統一)
```
現況:  CaseCodeService → 2026_01_01_001 (無CK前綴)
       ProjectRepository → CK2025_01_01_001 (有CK前綴)

統一為: CK{yyyy}_PJ_{NN}_{NNN}
範例:   CK2026_PJ_01_001  (地面測量第1號)
        CK2026_PJ_09_002  (資訊系統第2號)

變更:  CaseCodeService.generate_project_code() 加 CK 前綴
       ProjectRepository.get_next_project_code() 改用相同格式
       新增 module code "PJ"，NN 直接使用 case_nature
       既有資料: migration 加前綴 (WHERE project_code NOT LIKE 'CK%')
```

#### 3.3 dispatch_no (需遷移)
```
現況:  115年_派工單號011 (民國年)

保留:  不遷移既有資料（影響外部報表/紙本對照）
新規:  新建派工單使用 CK{yyyy}_DP_{CC}_{NNN}
       前端顯示時轉換 (可選)
過渡:  dispatch_order_repository.get_next_dispatch_no() 增加 format 參數
       default='legacy' (維持民國年格式)
       format='unified' → CK2026_DP_01_001
```

#### 3.4 billing_code (新增)
```
格式:  BL_{yyyy}_{NNN}
範例:  BL_2026_001  (2026年第1筆請款)
生成:  新增 BillingCodeGenerator 或整合至 CaseCodeService
欄位:  erp_billings 新增 billing_code VARCHAR(20) UNIQUE
保留:  billing_period 維持 free text (業務描述用途)
```

#### 3.5 invoice_ref (新增)
```
格式:  IV_{yyyy}_{NNN}
範例:  IV_2026_001  (2026年第1筆系統發票)
生成:  同上
欄位:  erp_invoices 新增 invoice_ref VARCHAR(20) UNIQUE
保留:  invoice_number 維持 (統一發票號碼，外部系統)
用途:  系統內部參照，不取代法定發票號碼
```

#### 3.6 asset_code (加自動生成)
```
格式:  AT_{yyyy}_{CC}_{NNN}
範例:  AT_2026_EQ_001  (2026年設備第1項)

類別碼:
  EQ = 設備 (Equipment)
  VH = 車輛 (Vehicle)
  OF = 辦公 (Office)
  IT = 資訊 (IT)
  OT = 其他 (Other)

生成:  AssetRepository.generate_code() 或 CaseCodeService 擴充
欄位:  asset_code 已存在，改為可自動生成 (保留手動輸入選項)
```

#### 3.7 ledger_code (新增)
```
格式:  FL_{yyyy}_{NNNNN}
範例:  FL_2026_00001  (2026年第1筆帳目)
生成:  LedgerRepository.generate_code()
欄位:  finance_ledgers 新增 ledger_code VARCHAR(20) UNIQUE
序號:  5碼 (帳目量大，預估年 10,000+ 筆)
```

### 四、架構設計 — 統一編碼服務

```python
# backend/app/services/code_generation_service.py (新增)

class CodeGenerationService:
    """統一編碼生成服務
    
    所有自動編碼的單一入口，確保：
    1. 格式一致性
    2. 併發安全 (retry + unique constraint)
    3. 可追蹤審計
    """
    
    async def generate(self, entity_type: str, **kwargs) -> str:
        """
        entity_type: 'case', 'project', 'dispatch', 'billing', 
                     'invoice_ref', 'asset', 'ledger', 'operational'
        kwargs: year, category, case_nature, etc.
        """
        generator = self._get_generator(entity_type)
        code = await generator.generate(**kwargs)
        return code
    
    # 內部委派至各 repository 的生成方法
    # 統一 3 次重試 + unique constraint 保護
```

**遷移策略**: 漸進式，不破壞現有流程

```
Phase 1 (v5.4.0): 統一 project_code 格式 + 加自動 asset_code
Phase 2 (v5.5.0): 新增 billing_code + invoice_ref + ledger_code 欄位
Phase 3 (v5.6.0): dispatch_no 新格式 (legacy 模式共存)
Phase 4 (v6.0.0): CodeGenerationService 統一入口
```

### 五、跨模組編碼關係圖

```
                        ┌──────────────┐
                        │   case_code   │  CK2026_PM_01_001
                        │  (跨模組橋樑) │
                        └──────┬───────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐ ┌──────▼──────┐ ┌───────▼──────┐
       │  pm_cases    │ │erp_quotations│ │   expenses   │
       │  case_code   │ │  case_code   │ │  case_code   │
       └──────┬───────┘ └──────┬───────┘ └──────────────┘
              │                │
       ┌──────▼──────┐ ┌──────▼──────┐
       │  contract_   │ │ erp_billings│──→ billing_code (BL_)
       │  projects    │ │             │
       │project_code  │ ├─────────────┤
       │(CK_PJ_)     │ │ erp_invoices│──→ invoice_ref (IV_)
       └──────────────┘ └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │  finance_   │──→ ledger_code (FL_)
                        │  ledgers    │
                        └─────────────┘

  獨立實體:
  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
  │   assets     │  │ operational  │  │  dispatch_   │
  │ asset_code   │  │ account_code │  │  orders      │
  │  (AT_)       │  │  (OP_)       │  │dispatch_no   │
  └──────────────┘  └──────────────┘  │(CK_DP_ 新)  │
                                      └──────────────┘
```

### 六、編碼生成一覽表 (統一後)

| 實體 | 欄位 | 格式 | 前綴 | 年度 | 模組 | 類別 | 序號 | 生成方式 | 併發保護 |
|------|------|------|------|------|------|------|------|---------|---------|
| PM 案件 | case_code | `CK{yyyy}_{MOD}_{CC}_{NNN}` | CK | 西元 | PM | 2碼 | 3碼 | 自動 | unique |
| ERP 報價 | case_code | `CK{yyyy}_{MOD}_{CC}_{NNN}` | CK | 西元 | FN | 2碼 | 3碼 | 自動 | unique |
| 成案專案 | project_code | `CK{yyyy}_PJ_{NN}_{NNN}` | CK | 西元 | PJ | 性質2碼 | 3碼 | 自動 | unique + retry |
| 派工單 | dispatch_no | `CK{yyyy}_DP_{CC}_{NNN}` (新) | CK | 西元 | DP | 2碼 | 3碼 | 自動 | unique + retry |
| 公文 | auto_serial | `{R\|S}{NNNN}` | — | — | — | 收/發 | 4碼 | 自動 | unique |
| 營運帳目 | account_code | `OP_{yyyy}_{XX}_{NNN}` | OP | 西元 | — | 2碼 | 3碼 | 自動 | unique |
| 請款 | billing_code | `BL_{yyyy}_{NNN}` | BL | 西元 | — | — | 3碼 | 自動 | unique |
| 發票參照 | invoice_ref | `IV_{yyyy}_{NNN}` | IV | 西元 | — | — | 3碼 | 自動 | unique |
| 資產 | asset_code | `AT_{yyyy}_{CC}_{NNN}` | AT | 西元 | — | 2碼 | 3碼 | 自動 (可手動) | unique |
| 帳本 | ledger_code | `FL_{yyyy}_{NNNNN}` | FL | 西元 | — | — | 5碼 | 自動 | unique |
| 統一發票 | invoice_number | XX12345678 | — | — | — | — | — | 手動/QR | unique |
| 電子發票 | inv_num | XX12345678 | — | — | — | — | — | 手動/QR | unique |
| 廠商 | vendor_code | 統編/自訂 | — | — | — | — | — | 手動 | unique |
| 機關 | agency_code | 政府代碼 | — | — | — | — | — | 外部 | — |
| 公文字號 | doc_number | 政府格式 | — | — | — | — | — | 外部 | — |
| 標案 | unit_id+job_no | 政府系統 | — | — | — | — | — | 外部 | — |

## 後果

### 正面
- 所有自動生成的業務碼格式統一，可讀性高
- project_code 不再有雙格式歧義
- 帳本/請款/發票有可讀的業務碼，方便查詢和審計
- 資產自動編碼減少人為錯誤
- 併發保護統一為 retry + unique constraint
- CodeGenerationService 作為單一入口便於監控和審計

### 負面
- 需要 DB migration 新增 4 個欄位
- dispatch_no 遷移涉及既有紙本報表對照
- 額外的 DB 查詢開銷 (MAX+1 策略)
- 需要補錄既有資料的新欄位值

## 替代方案

### A. 使用 DB Sequence
```sql
CREATE SEQUENCE billing_code_seq START 1;
```
**排除原因**: 跨年度重置困難，與 prefix+serial 模式不相容。

### B. UUID 取代流水號
**排除原因**: 失去業務可讀性（`CK2026_PM_01_001` vs `550e8400-e29b-...`），公文系統使用者習慣編號檢索。

### C. 全部納入 CK 前綴
**排除原因**: 營運帳目 (OP) 和帳本 (FL) 是公司內部管理，非案件層級，使用 CK 前綴語意不清。
