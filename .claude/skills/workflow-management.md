# 作業歷程管理 (Workflow Management)

> **觸發關鍵字**: workflow, 作業歷程, 時間軸, chain, timeline, 鏈式, InlineRecordCreator, work_category
> **版本**: 1.0.0
> **日期**: 2026-02-17

---

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
| `batch_no` / `batch_label` | Int / String | 結案批次分組 | v2 |
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

**定義位置**: `frontend/src/components/taoyuan/workflow/chainConstants.ts`

---

## 前端元件架構

```
frontend/src/components/taoyuan/workflow/
├── chainConstants.ts        # 類別/狀態常數 + 顯示函數 (SSOT)
├── chainUtils.ts            # buildChains + 相容工具 (SSOT)
├── ChainTimeline.tsx         # 鏈式時間軸主元件
├── InlineRecordCreator.tsx   # Tab 內 Inline 新增表單
├── WorkflowTimelineView.tsx  # 批次分組時間軸（舊視圖）
├── WorkflowKanbanView.tsx    # Kanban 看板視圖
├── CorrespondenceMatrix.tsx  # 雙欄公文對照
├── CorrespondenceBody.tsx    # 對照內容
├── useProjectWorkData.ts     # 工程作業資料 Hook
└── index.ts                  # 統一匯出
```

### 核心工具函數 (chainUtils.ts)

| 函數 | 說明 |
|------|------|
| `buildChains(records)` | flat → 鏈式樹 (`ChainNode[]`) |
| `flattenChains(roots)` | 樹 → 深度優先 flat |
| `isOutgoingDocNumber(docNumber)` | 「乾坤」開頭 = 發文 (**SSOT**) |
| `getEffectiveDocId(record)` | 新/舊格式公文 ID |
| `getEffectiveDoc(record)` | 新/舊格式公文摘要 |
| `buildDocPairs(records)` | 分組為來文/發文配對 |
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

## 常見陷阱

1. **FastAPI 路由順序**: `/workflow/batch-update` 必須在 `/workflow/{record_id}` 之前
2. **刪除 parent**: 必須先將 child 的 `parent_record_id` 設為 NULL
3. **批量操作**: 必須驗證 record_ids 屬於同一派工單
4. **分頁無上限**: `page_size` 必須設定 `le=200`
5. **新紀錄 milestone_type**: 必須填 `'other'`（NOT NULL 約束）
6. **公文方向**: 統一使用 `isOutgoingDocNumber()` 判斷
