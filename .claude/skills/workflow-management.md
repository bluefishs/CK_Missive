---
name: workflow-management
description: 作業歷程管理 (Workflow Management)
version: 2.0.0
category: project
triggers:
  - workflow
  - 作業歷程
  - 時間軸
  - chain
  - timeline
  - 鏈式
  - InlineRecordCreator
  - work_category
  - WorkRecordStatsCard
  - useDeleteWorkRecord
  - useWorkRecordColumns
updated: '2026-03-05'
---

# 作業歷程管理 (Workflow Management)


## 概述

桃園派工系統的**作業歷程**模組，追蹤每個工程項次（TaoyuanProject）的公文往返與工作進度。
v2 採用**鏈式時間軸**架構，將離散的公文關聯整合為有因果鏈的紀錄序列。

---

## 資料模型

### TaoyuanWorkRecord（核心表）

| 欄位 | 類型 | 說明 | 版本 |
|------|------|------|------|
| `dispatch_order_id` | FK → TaoyuanDispatchOrder | 關聯派工單 (必填) | v1 |
| `taoyuan_project_id` | FK → TaoyuanProject | 關聯工程 (可選) | v1 |
| `incoming_doc_id` | FK → OfficialDocument | 機關來文 (舊格式) | v1 |
| `outgoing_doc_id` | FK → OfficialDocument | 公司發文 (舊格式) | v1 |
| `document_id` | FK → OfficialDocument | **統一公文** (新格式) | v2 |
| `parent_record_id` | FK → self | **前序紀錄** (鏈式) | v2 |
| `work_category` | String(50) | **作業類別** (新) | v2 |
| `milestone_type` | String(50) | 里程碑類型 (舊，NOT NULL) | v1 |
| ~~`batch_no` / `batch_label`~~ | ~~Int / String~~ | ~~結案批次分組~~ | ~~v2~~ → **已遷移至 DispatchOrder** |
| `sort_order` | Int | 排序順序 | v1 |
| `status` | String | pending/in_progress/completed/overdue/on_hold | v1+v2 |

### 向後相容策略

| 項目 | 策略 |
|------|------|
| 現有紀錄 (`milestone_type`) | 保留不動，顯示時 fallback |
| 新紀錄 (`work_category`) | `milestone_type` 自動填 `'other'` |
| `incoming_doc_id`/`outgoing_doc_id` | 保留，新紀錄用 `document_id` |
| 顯示函數 | 先查 `work_category`，fallback `milestone_type` |

---

## 作業類別 (WorkCategory)

固定 6+1 種，程式碼內定義（非 DB 配置表）：

| 分組 | 值 | 標籤 | 顏色 |
|------|-----|------|------|
| 派工作業 | `dispatch_notice` | 派工通知 | blue |
| 派工作業 | `work_result` | 作業成果 | cyan |
| 開會(審查)作業 | `meeting_notice` | 會議通知 | purple |
| 開會(審查)作業 | `meeting_record` | 會議紀錄 | geekblue |
| 會勘作業 | `survey_notice` | 會勘通知 | orange |
| 會勘作業 | `survey_record` | 會勘紀錄 | gold |
| 其他 | `other` | 其他 | default |

**定義位置 (SSOT)**: `frontend/src/components/taoyuan/workflow/workCategoryConstants.ts`（葉節點，無內部 import）

---

## 前端元件架構

### 依賴流向 (DAG，無循環)

```
workCategoryConstants.ts (葉節點，零內部 import)
    ↓
chainConstants.ts (鏈式視圖專用常數)
chainUtils.ts (算法 + 共用篩選/統計)
    ↓
useProjectWorkData.ts / useDispatchWorkData.ts (資料 Hook)
    ↓
View Components (ChainTimeline, CorrespondenceMatrix, ...)
    ↓
index.ts (barrel export — 外部頁面統一入口)
```

**import 規則**：
- workflow/ 內部元件 → 直接 import 葉節點 (`./workCategoryConstants`)
- workflow/ 外部頁面 → 從 barrel import (`../workflow`)

### 檔案清單

```
frontend/src/components/taoyuan/workflow/
├── workCategoryConstants.ts  # 里程碑/狀態/作業類別 常數 + 顯示函數 (SSOT 葉節點)
├── chainConstants.ts         # 鏈式視圖專用：CHAIN_STATUS_OPTIONS, getStatusLabel/Color
├── chainUtils.ts             # buildChains + 公文配對 + 共用篩選/統計 (SSOT)
├── ChainTimeline.tsx         # 鏈式時間軸主元件
├── InlineRecordCreator.tsx   # Tab 內 Inline 新增表單
├── WorkflowTimelineView.tsx  # 批次分組時間軸（舊視圖）
├── WorkflowKanbanView.tsx    # Kanban 看板視圖
├── CorrespondenceMatrix.tsx  # 雙欄公文對照（標題=dispatch_no+work_type）
├── CorrespondenceBody.tsx    # 對照內容（優先使用 matrixRows）
├── useProjectWorkData.ts     # 工程作業資料 Hook（WorkTypeStageInfo, matrixRows）
├── useDispatchWorkData.ts    # 派工單作業資料 Hook
├── useDeleteWorkRecord.ts    # 共用刪除 mutation（React Query invalidation）
├── useWorkRecordColumns.tsx  # 共用表格欄位定義（可配置顯示欄位）
├── WorkRecordStatsCard.tsx   # 共用統計卡片（dispatch/project 雙模式）
├── index.ts                  # 統一匯出（外部頁面入口）
└── __tests__/
    └── chainUtils.test.ts    # 核心算法單元測試
```

### 共用模組 (v2.0.0 新增)

| 模組 | 說明 | 消費者 |
|------|------|--------|
| `useDeleteWorkRecord` | 封裝 `useMutation` + 確認對話框 + React Query invalidation | DispatchWorkflowTab, ProjectWorkOverviewTab |
| `useWorkRecordColumns` | 可配置的 Table columns 定義（deadline/outgoingDoc 可選顯示） | DispatchWorkflowTab, ProjectWorkOverviewTab |
| `WorkRecordStatsCard` | 統計卡片，`mode: 'dispatch' | 'project'` 雙模式，早期 narrowing 無型別斷言 | DispatchWorkflowTab, ProjectWorkOverviewTab |

### 核心工具函數 (chainUtils.ts)

| 函數 | 說明 |
|------|------|
| `buildChains(records)` | flat → 鏈式樹 (`ChainNode[]`) |
| `flattenChains(roots)` | 樹 → 深度優先 flat |
| `isOutgoingDocNumber(docNumber)` | 「乾坤」開頭 = 發文 (**SSOT**) |
| `getEffectiveDocId(record)` | 新/舊格式公文 ID |
| `getEffectiveDoc(record)` | 新/舊格式公文摘要 |
| `buildDocPairs(records)` | 分組為來文/發文配對 |
| `buildCorrespondenceMatrix(...)` | 三階段匹配：parent_record_id → 日期鄰近 → 未指派 |
| `filterBlankRecords(records)` | 過濾空白紀錄（保留被引用的 parent） |
| `computeDocStats(records)` | 計算不重複來文/發文數 |
| `computeCurrentStage(records)` | 計算當前作業階段標籤 |
| `getDocDirection(record)` | 判斷公文方向 |

### InlineRecordCreator

Tab 內嵌的快速建立表單，不離開頁面：
1. 選擇關聯公文（可選）→ 自動帶入主旨
2. 選擇作業類別（OptGroup 分組）
3. 自動預選最後一筆紀錄為前序
4. 建立後 invalidate React Query → 時間軸自動更新

---

## 後端架構

### API 端點 (`taoyuan_dispatch/workflow.py`)

| 端點 | 說明 | 安全措施 |
|------|------|---------|
| `POST /workflow/list` | 依派工單列表 | `page_size` ≤ 200 |
| `POST /workflow/by-project` | 依工程列表 | `page_size` ≤ 200 |
| `POST /workflow/create` | 建立紀錄 | 自動填入 + 自動關聯 |
| `POST /workflow/batch-update` | 批量更新 | **同派工單驗證** |
| `POST /workflow/summary/{id}` | 歷程總覽 | max 500 筆 |
| `POST /workflow/{id}` | 單筆查詢 | — |
| `POST /workflow/{id}/update` | 更新 | — |
| `POST /workflow/{id}/delete` | 刪除 | **清理孤兒子紀錄** |

**路由順序**: 靜態路由 (list, create, batch-update, summary) **必須** 在動態路由 ({record_id}) 之前。

### Service (`work_record_service.py`)

| 方法 | 說明 |
|------|------|
| `create_record()` | 自動排序 + 自動填日期 + 自動關聯 + 防環檢查 |
| `delete_record()` | 清理子紀錄 `parent_record_id` → NULL |
| `verify_records_same_dispatch()` | 批量操作前安全驗證 |
| `_check_chain_cycle()` | 沿 parent 回溯，最大深度 100 |
| `_auto_link_document()` | 自動建立 DispatchDocumentLink |
| `_sync_review_status()` | 完成時推進工程審議進度 |

---

## 結案批次管理

**重要**: `batch_no` / `batch_label` 已從 `TaoyuanWorkRecord` 遷移至 `TaoyuanDispatchOrder`（2026-03-04）。

| 欄位 | 所在模型 | 說明 |
|------|---------|------|
| `batch_no` | `TaoyuanDispatchOrder` | 結案批次序號 (1-5)，nullable |
| `batch_label` | `TaoyuanDispatchOrder` | 自動衍生標籤 (如「第1批結案」) |

- 前端使用 Select 下拉選單（非 InputNumber），`batch_label` 由 `batch_no` 自動衍生
- 批量設定 API: `POST /dispatch/batch-set-batch`
- `useProjectWorkData.ts` 的 `groupByBatch()` 改為按派工單分組

## 常見陷阱

1. **FastAPI 路由順序**: `/workflow/batch-update` 必須在 `/workflow/{record_id}` 之前
2. **刪除 parent**: 必須先將 child 的 `parent_record_id` 設為 NULL
3. **批量操作**: 必須驗證 record_ids 屬於同一派工單
4. **分頁無上限**: `page_size` 必須設定 `le=200`
5. **新紀錄 milestone_type**: 必須填 `'other'`（NOT NULL 約束）
6. **公文方向**: 統一使用 `isOutgoingDocNumber()` 判斷
7. **Pydantic 回應 Schema 禁 ge/le**: `DispatchOrderBase` 不可加輸入驗證約束，否則 DB 有非法值時 response 序列化 500
8. **常數 import 規則**: workflow/ 內部用 `./workCategoryConstants`，外部用 barrel `../workflow`
9. **React.memo props 穩定性**: 傳遞 hook 回傳的 memoized 物件，勿用 inline `{{...}}`
10. **useMutation 依賴**: `useCallback` deps 用 `deleteMutation.mutate`（穩定引用），勿用 `deleteMutation`（每次新物件）
11. **on_hold 狀態標籤**: 全域統一為「暫緩」，鏈式視圖用「辦理中」（非「進行中」）
