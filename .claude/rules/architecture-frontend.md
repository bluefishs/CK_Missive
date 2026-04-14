# 前端結構

## 前端元件結構

### 頁面模組化拆分 (v1.83.0)

```
frontend/src/pages/
├── codeGraph/                  # CodeGraphManagementPage 子元件
│   ├── CodeGraphSidebar.tsx    # 左側欄：統計+管理動作+篩選 (222L)
│   ├── ModuleConfigPanel.tsx   # 模組映射編輯/瀏覽面板 (131L)
│   ├── ArchitectureOverviewTab.tsx  # 架構總覽頁籤 (190L)
│   └── index.ts
├── backup/                     # BackupManagementPage 子元件
│   ├── BackupListTab.tsx       # 備份列表頁籤 (177L)
│   ├── RemoteBackupTab.tsx     # 遠端備份頁籤 (116L)
│   ├── SchedulerTab.tsx        # 排程器頁籤 (104L)
│   ├── BackupLogsTab.tsx       # 日誌頁籤 (153L)
│   ├── BackupStatsCards.tsx    # 統計卡片 (78L)
│   └── index.ts
├── knowledgeGraph/             # KnowledgeGraphPage 子元件
│   ├── GraphLeftPanel.tsx      # 左側面板 (369L) 含 CoveragePanel+TimelineTrendMini
│   ├── ShortestPathFinder.tsx  # 最短路徑搜尋 (104L)
│   ├── MergeEntitiesModal.tsx  # 實體合併對話框 (80L)
│   ├── EntityTypeDistribution.tsx  # 實體類型分布 (60L)
│   ├── TopEntitiesRanking.tsx  # 高頻實體排行 (61L)
│   └── KGAdminPanel.tsx        # 管理面板 (152L)
├── document/                   # 公文詳情頁子元件
│   └── hooks/
│       └── useDocumentProjectStaff.ts  # 公文專案人員管理 Hook (113L)
├── erpQuotation/               # ERP 報價詳情子元件
│   ├── AccountRecordTab.tsx    # 統一帳款紀錄 (應收/應付共用, 294L)
│   ├── BillingsTab.tsx         # 請款管理頁籤 (367L)
│   ├── InvoicesTab.tsx         # 開票管理頁籤 (352L)
│   ├── VendorPayablesTab.tsx   # 廠商應付頁籤 (310L)
│   └── ProfitTrendTab.tsx      # 損益趨勢頁籤 (130L)
├── pmCase/                     # PM 案件詳情子元件
│   ├── MilestonesGanttTab.tsx  # 里程碑/甘特圖頁籤 (含 XLS 匯出入)
│   ├── ExpensesTab.tsx         # 費用核銷頁籤 (統計+列表)
│   ├── QuotationRecordsTab.tsx # 報價紀錄頁籤 (225L)
│   ├── StaffTab.tsx            # 專案人員頁籤
│   └── CrossModuleCard.tsx     # 跨模組資訊卡片
├── taoyuanProject/             # 桃園工程專案詳情子元件
│   ├── TaoyuanProjectDetailPage.tsx # 專案詳情主頁 (213L)
│   ├── hooks/useTaoyuanProjectDetail.ts # 資料載入 Hook
│   └── tabs/                   # 頁籤元件 (12 files)
│       ├── BasicInfoTab.tsx, BudgetEstimateTab.tsx, EngineeringScopeTab.tsx
│       ├── DispatchLinksTab.tsx, LandBuildingTab.tsx, ReviewStatusTab.tsx
│       ├── KanbanBoardTab.tsx, ProjectWorkOverviewTab.tsx
│       ├── ProjectWorkflowTab.tsx (386L), WorkflowTimeline.tsx, WorkflowStatsCard.tsx
│       └── index.ts
├── taoyuanDispatch/            # TaoyuanDispatchDetailPage 子元件
│   ├── DispatchDetailHeader.tsx # 詳情頁標頭 (91L)
│   └── tabs/                   # 既有頁籤元件
├── knowledgeBase/              # 知識庫瀏覽器
│   ├── KnowledgeMapTab.tsx     # 樹狀目錄 + Markdown 渲染
│   ├── AdrTab.tsx              # ADR 表格 + 狀態標籤 + 詳情
│   └── DiagramsTab.tsx         # Segmented 切換 + Mermaid 架構圖
├── digitalTwin/                # 數位分身子元件 (v5.2.2+)
│   ├── CapabilityRadarTab.tsx, DashboardTab.tsx, DispatchProgressTab.tsx
│   ├── EvolutionTab.tsx, EvolutionMetricsCard.tsx (v5.5.0)
│   ├── ProfileCard.tsx, TraceWaterfallTab.tsx
├── skillEvolution/             # 技能進化頁面子元件 (v5.2.0+)
│   ├── EvolutionGraph.tsx, LegendPanel.tsx, SkillListPanel.tsx, StatsPanel.tsx
├── profile/                    # 個人檔案子元件
│   ├── AccountInfoCard.tsx, PasswordChangeModal.tsx, ProfileInfoCard.tsx
├── erpExpense/                 # 費用報銷子元件 (v5.4.0)
│   ├── SmartScanModal.tsx (251L)      # 智慧掃描 (QR+OCR) Modal
│   ├── ExpenseScanPanel.tsx (178L)    # 掃描/輸入面板 v5.5.3
│   ├── imageUtils.ts (compressImage) v5.5.3
│   ├── ExpenseImportModal.tsx (175L)  # Excel 匯入 Modal
│   └── index.ts
├── SecurityCenterPage.tsx      # 資安管理中心 (OWASP Top 10 + 掃描 + 通知)
├── ERPExpense{Create,List,Detail}Page.tsx  # 費用報銷三頁 (396/450/-L)
├── ERPLedgerPage.tsx           # 統一帳本 (科目分類+餘額)
├── ERPFinancialDashboardPage.tsx # 財務儀表板 (月趨勢+預算排名+Recharts)
├── ERPHubPage.tsx              # ERP 財務管理中心入口 (5+5 主要/進階)
├── ERPInvoiceSummaryPage.tsx   # 發票跨案件查詢 (168L)
├── ERP{Vendor,Client}Account{List,Detail}Page.tsx  # 應付/應收帳款
├── ERPAsset{List,Detail,Form}Page.tsx  # 資產 CRUD
├── ERPEInvoiceSyncPage.tsx     # 電子發票同步 (MOF 同步狀態+待核銷)
├── AdminLoginHistoryPage.tsx, CaseNatureManagementPage.tsx
├── SkillEvolutionPage.tsx, DigitalTwinPage.tsx
├── Tender{Search,Detail,Company,Dashboard,OrgEcosystem,Graph}Page.tsx  # 標案系列
├── tenderDetail/               # TenderDetailPage 子元件 (v5.5.2 拆分)
│   ├── BattleTab.tsx, PriceTab.tsx, index.ts
├── tenderSearch/               # TenderSearchPage 子元件 (v5.5.1 拆分)
│   ├── SearchTab.tsx (192L), SubscriptionTab.tsx (167L), BookmarkTab.tsx (88L)
├── AgentDashboardPage.tsx      # Agent 統一儀表板 v5.5.0
└── UnifiedAgentPage.tsx        # 雙模式 (user 聊天 / admin 儀表板) v5.5.4
```

### 前端 Hooks 結構 (39 檔, 150+ hooks)

```
frontend/src/hooks/
├── index.ts                        # 統一匯出
├── useCodeWikiGraph.ts             # 程式碼圖譜資料載入
├── business/                       # 業務邏輯 (13 檔)
│   ├── useDocuments{,WithStore}.ts, useProjects{,WithStore}.ts
│   ├── useVendors{,WithStore}.ts, useAgencies{,WithStore}.ts
│   ├── useDocumentCreateForm.ts (v2.0, 364L) + useDocumentFormData/FileUpload
│   ├── useTaoyuan{Projects,Dispatch,Payments}.ts
│   ├── useDropdownData.ts (全域下拉快取 10-30min)
│   ├── useERPFinance.ts (expenses/ledger/dashboard/einvoice)
│   └── createEntityHookWithStore.ts (工廠)
├── system/                         # 系統服務 (11 檔)
│   ├── useCalendar{,Integration}.ts, useDashboard{,Calendar}.ts
│   ├── useAdminUsers.ts, useDepartments.ts (5min 快取)
│   ├── useDocument{Stats,Analysis}.ts
│   ├── useNotifications.ts (4 hooks)
│   ├── useAI{Synonyms,Prompts}.ts
│   ├── useStreamingChat.ts (re-export @ck-shared)
│   └── useAgentSSE.ts (Agent SSE 串流)
├── utility/                        # 工具 (8 檔)
│   ├── useAuthGuard.ts, usePermissions.ts, useAppNavigation.ts
│   ├── useResponsive.ts, useTableColumnSearch.tsx, useIdleTimeout.ts
│   ├── usePerformance.ts, useApiErrorHandler.ts
└── taoyuan/                        # 派工專用 (2 檔)
    ├── useDispatchMutations.ts (241L), useDispatchQueries.ts (110L)
```

### 通用元件 + 工具

```
frontend/src/components/common/
├── ClickableStatCard.tsx (v5.5.0)        # 可點擊統計卡片
├── ExpenseQRCode.tsx (v5.5.3)            # 案件核銷 QR Code
├── GlobalApiErrorNotifier.tsx            # 全域 API 錯誤通知 (429/403/5xx)
├── MarkdownRenderer.tsx                  # GFM + Mermaid
├── PreviewDrawer/, PageLoading.tsx

frontend/src/utils/tableEnhancer.ts        # enhanceColumns (排序/篩選)
```

### 作業歷程模組 (v2.0.0)

```
frontend/src/components/taoyuan/workflow/
├── workCategoryConstants.ts / chainConstants.ts / chainUtils.ts
├── ChainTimeline.tsx / InlineRecordCreator.tsx
├── WorkflowTimelineView.tsx / WorkflowKanbanView.tsx
├── CorrespondenceMatrix.tsx / CorrespondenceBody.tsx
├── useProjectWorkData.ts / useDispatchWorkData.ts / useDeleteWorkRecord.ts
├── useWorkRecordColumns.tsx / WorkRecordStatsCard.tsx
└── __tests__/chainUtils.test.ts
```

### DocumentOperations 模組 (v1.13.0)

```
frontend/src/components/document/operations/
├── types.ts / documentOperationsUtils.ts
├── useDocumentOperations.ts / useDocumentForm.ts
├── CriticalChangeConfirmModal.tsx / DocumentOperationsTabs.tsx
├── DocumentSendModal.tsx / DuplicateFileModal.tsx
├── ExistingAttachmentsList.tsx / FileUploadSection.tsx
└── index.ts
```

## 前端型別 SSOT (v5.3.24)

```
frontend/src/types/
├── api.ts (132L barrel)           + api-{project,user,calendar,entity,knowledge}.ts
├── ai.ts (28L barrel)             + ai-{document,search,knowledge-graph,services}.ts
├── document.ts / forms.ts / admin-system.ts / taoyuan.ts
├── pm.ts (234L SSOT) / erp.ts (1080L SSOT) / tender.ts / navigation.ts
└── index.ts (統一匯出+相容別名)
```

## 前端全域錯誤處理 (v1.79.0)

```
frontend/src/api/endpoints/     # API 端點常數 (v2.0 域拆分)
├── core.ts (172L)    # 公文/行事曆/通知/檔案
├── users.ts (186L)   # 使用者/認證/權限
├── projects.ts (59L) # 承攬案件/機關/廠商
├── taoyuan.ts (158L) # 桃園派工
├── ai.ts (218L)      # AI/Agent/知識圖譜
├── erp.ts (261L)     # PM + ERP 財務
├── admin.ts (95L)    # 管理/備份/部署/資安
└── index.ts          # Barrel + API_ENDPOINTS

frontend/src/api/errors.ts       # ApiException + ApiErrorBus
frontend/src/api/client.ts       # Axios 客戶端
frontend/src/api/interceptors.ts # 340L (拆分自 client)
frontend/src/api/throttler.ts    # RequestThrottler (GLOBAL_MAX=200)

frontend/src/components/common/GlobalApiErrorNotifier.tsx
```

錯誤分流規則：
- **業務錯誤** (400/409/422): 元件自行 catch 處理
- **全域錯誤** (403/429/5xx/網路): `GlobalApiErrorNotifier` 自動通知，3 秒去重
- **429 熔斷**: `RequestThrottler` 超過上限 → `ApiException(429)` → 用戶通知
