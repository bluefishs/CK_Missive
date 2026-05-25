# Phase 3: 前端頁面規劃
# 供 Claude CLI 執行

> 日期: 2026-02-12
> UI 框架: Ant Design 5.x + React 18 + TypeScript

---

## 需新增/修改的檔案清單

### 3.1 前端常數
**修改: `frontend/src/constants/taoyuanOptions.ts`**

新增以下常數:

```typescript
/** 里程碑類型選項 */
export const MILESTONE_TYPE_OPTIONS = [
  { value: 'dispatch', label: '派工', color: 'green', order: 1 },
  { value: 'survey', label: '會勘', color: 'blue', order: 2 },
  { value: 'site_inspection', label: '查估檢視', color: 'cyan', order: 3 },
  { value: 'submit_result', label: '送件/檢送成果', color: 'gold', order: 4 },
  { value: 'revision', label: '修正成果', color: 'orange', order: 5 },
  { value: 'review_meeting', label: '審查/價審會議', color: 'purple', order: 6 },
  { value: 'negotiation', label: '協議價購', color: 'magenta', order: 7 },
  { value: 'final_approval', label: '定稿核定', color: 'lime', order: 8 },
  { value: 'boundary_survey', label: '土地鑑界', color: 'geekblue', order: 9 },
  { value: 'closed', label: '結案', color: 'red', order: 99 },
  { value: 'other', label: '其他', color: 'default', order: 50 },
] as const;

/** 發文類別選項 */
export const SUBMISSION_TYPE_OPTIONS = [
  { value: '檢送成果(紙本+電子檔)', label: '檢送成果(紙本+電子檔)' },
  { value: '檢送修正後成果(紙本+電子檔)', label: '檢送修正後成果(紙本+電子檔)' },
  { value: '檢修正後成果(協議市價-電子檔)', label: '檢修正後成果(協議市價-電子檔)' },
  { value: '檢送成果(電子檔)', label: '檢送成果(電子檔)' },
  { value: '檢修正後成果', label: '檢修正後成果' },
  { value: '檢送成果定稿版(繳送)', label: '檢送成果定稿版(繳送)' },
] as const;

/** 結案批次顏色對應 */
export const BATCH_CLOSE_COLORS: Record<number, string> = {
  1: '#52c41a',  // 綠
  2: '#1890ff',  // 藍
  3: '#faad14',  // 黃
  4: '#eb2f96',  // 粉
  5: '#722ed1',  // 紫
};
```

### 3.2 API 模組
**新增: `frontend/src/api/taoyuanWorkflowApi.ts`**

```typescript
import { apiClient } from './client';

export interface WorkRecord {
  id: number;
  dispatch_order_id: number;
  taoyuan_project_id?: number;
  incoming_doc_id?: number;
  outgoing_doc_id?: number;
  milestone_type: string;
  description?: string;
  submission_type?: string;
  record_date: string;
  deadline_date?: string;
  completed_date?: string;
  status: string;
  sort_order: number;
  notes?: string;
  // 嵌套公文資訊
  incoming_doc_number?: string;
  incoming_doc_date?: string;
  outgoing_doc_number?: string;
  outgoing_doc_date?: string;
}

export interface ProjectWorkflow {
  project_id: number;
  sequence_no: number;
  project_name: string;
  sub_case_name?: string;
  batch_close_no?: number;
  total_incoming_docs: number;
  total_outgoing_docs: number;
  milestones: WorkRecord[];
  current_stage?: string;
}

export const workflowApi = {
  getProjectWorkflow: (projectId: number) =>
    apiClient.get<ProjectWorkflow>(`/taoyuan/workflow/projects/${projectId}`),

  listRecords: (params?: Record<string, any>) =>
    apiClient.get<WorkRecord[]>('/taoyuan/workflow/records', { params }),

  createRecord: (data: Omit<WorkRecord, 'id'>) =>
    apiClient.post<WorkRecord>('/taoyuan/workflow/records', data),

  updateRecord: (id: number, data: Partial<WorkRecord>) =>
    apiClient.put<WorkRecord>(`/taoyuan/workflow/records/${id}`, data),

  deleteRecord: (id: number) =>
    apiClient.delete(`/taoyuan/workflow/records/${id}`),

  getSummary: (params?: { contract_project_id?: number; batch_close_no?: number }) =>
    apiClient.get<ProjectWorkflow[]>('/taoyuan/workflow/summary', { params }),

  exportWorkflow: (projectIds: number[]) =>
    apiClient.get('/taoyuan/workflow/export', {
      params: { project_ids: projectIds.join(',') },
      responseType: 'blob',
    }),
};
```

### 3.3 頁面元件

**新增檔案清單:**

```
frontend/src/pages/taoyuanWorkflow/
├── ProjectWorkflowPage.tsx       # 主頁面（工程歷程總覽）
├── ProjectWorkflowCard.tsx       # 單一工程卡片（含摘要+時間軸）
├── WorkflowTimeline.tsx          # 歷程時間軸元件
├── WorkRecordTable.tsx           # 公文明細表格
├── WorkRecordFormModal.tsx       # 新增/編輯歷程 Modal
├── WorkflowFilters.tsx           # 篩選列元件
└── index.ts                      # 統一匯出
```

### 3.4 元件規格

#### ProjectWorkflowPage.tsx
- 頂部: WorkflowFilters (承攬案件/行政區/批次/狀態篩選)
- 主體: ProjectWorkflowCard 列表 (Collapse 可展開)
- 底部: 分頁 + 匯出按鈕
- 使用 React Query 管理資料

#### ProjectWorkflowCard.tsx
```
Collapse.Panel 結構:
  Header:
    - 項次 + 工程名稱
    - Tag: 批次標籤 (對應顏色)
    - 承辦人、統計數字
    - 迷你進度條 (Steps mini)
  
  Content (展開後):
    Tabs:
      Tab1 "歷程時間軸" → WorkflowTimeline
      Tab2 "公文明細"   → WorkRecordTable
      Tab3 "契金管控"   → 既有 PaymentTable
    
    FloatButton: [+ 新增歷程]
```

#### WorkflowTimeline.tsx
```
Ant Design Timeline 元件:
  每個 Timeline.Item:
    - dot: 對應 milestone_type 的顏色圓點
    - children:
      - 日期 + 里程碑名稱 (Tag)
      - 機關來文文號 (可點擊跳轉)
      - 事項描述
      - 公司發文文號 + 發文類別 (如有)
      - 操作: [編輯] [刪除]
```

#### WorkRecordFormModal.tsx
```
Modal + Form 結構:
  Form.Item:
    - 里程碑類型 (Select - MILESTONE_TYPE_OPTIONS)
    - 紀錄日期 (DatePicker - 支援民國輸入)
    - 關聯派工單 (Select - 遠端搜尋)
    - 關聯工程 (Select - 遠端搜尋)
    - 機關來文 (Select - 可搜尋文號)
    - 事項描述 (Input.TextArea)
    - 公司發文 (Select - 可搜尋文號)
    - 發文類別 (Select - SUBMISSION_TYPE_OPTIONS)
    - 狀態 (Radio: 待處理/進行中/已完成)
    - 備註 (Input.TextArea)
```

### 3.5 路由設定
**修改: `frontend/src/router/AppRouter.tsx`**

```typescript
// 新增路由
{ path: '/taoyuan/workflow', element: <ProjectWorkflowPage /> }
```

**修改: `frontend/src/config/navigationConfig.ts`**

```typescript
// 在「桃園派工管理」下新增子項
{
  key: 'taoyuan-workflow',
  label: '工程歷程',
  path: '/taoyuan/workflow',
  icon: 'HistoryOutlined',
}
```

---

## 檔案影響範圍

| 操作 | 檔案路徑 | 變更類型 |
|------|---------|---------|
| 修改 | `constants/taoyuanOptions.ts` | 新增常數 |
| 新增 | `api/taoyuanWorkflowApi.ts` | 新檔案 |
| 新增 | `pages/taoyuanWorkflow/` 目錄 (6個檔案) | 新檔案 |
| 修改 | `router/AppRouter.tsx` | 新增路由 |
| 修改 | `config/navigationConfig.ts` | 新增導航項 |
| 修改 | `pages/index.ts` | 新增匯出 |
