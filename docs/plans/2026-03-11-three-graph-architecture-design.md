# 三圖譜架構設計：公文圖譜 / 代碼圖譜 / 資料庫圖譜

> **日期**: 2026-03-11
> **狀態**: 設計確認，待實作
> **版本**: 1.0.0

## 設計決策摘要

| 決策點 | 選擇 |
|--------|------|
| 圖譜數量 | 三個獨立圖譜（公文/代碼/資料庫） |
| DB 圖譜核心 | ER 關聯視覺化為主 + 資料流追蹤 + 資料治理 |
| 模組化策略 | 模板複製 + 配置驅動，目前先用 TS 常數 |
| AI 助理架構 | 公文助理（業務）/ 開發助理（代碼+DB），兩者分離 |
| 助理整合方式 | 全域浮動面板，路由感知自動切換身份 |
| 頁面佈局 | 三個獨立頁面，管理工具內嵌左側面板 |
| DB Schema 來源 | 雙軌合併（ORM 解析 + DB 反射） |
| 配置檔 | 暫不做 YAML，先用 TypeScript 常數 |

---

## 1. 頁面佈局

### 三個圖譜頁面

| 頁面 | 路由 | 存取權限 | 核心功能 |
|------|------|---------|---------|
| 公文圖譜 | `/ai/knowledge-graph` | 一般使用者 | 公文實體關聯視覺化、最短路徑、高頻實體排行 |
| 代碼圖譜 | `/ai/code-graph` | 一般使用者 | Python/TS 模組依賴、繼承、匯入關聯視覺化 |
| 資料庫圖譜 | `/ai/db-graph` | 一般使用者 | ER Diagram 視覺化、FK 關聯、欄位結構 |

### 導覽調整

| 原有 | 新設計 |
|------|--------|
| 知識圖譜探索 (`/ai/knowledge-graph`) | 公文圖譜（不變） |
| 代碼圖譜 (`/ai/code-wiki`) | 代碼圖譜 → `/ai/code-graph`（吸收管理功能） |
| 代碼圖譜管理 (`/admin/code-graph`) | 移除（併入代碼圖譜左側面板） |
| AI 助理管理 (`/admin/ai-assistant`) | 保留（與圖譜無關） |
| *(新增)* | 資料庫圖譜 (`/ai/db-graph`) |

### 各頁面結構

```
┌─────────────┬──────────────────────────────┐
│  左側面板    │                              │
│  (280-300px) │     中央圖譜視覺化區域        │
│             │     (ForceGraph 2D/3D)        │
│  - 篩選條件  │                              │
│  - 統計資訊  │                              │
│  - 管理工具  │                              │
│    (admin)  │                              │
│             │                              │
└─────────────┴──────────────────────────────┘
                              ┌──────────────┐
                              │ 浮動AI助理    │
                              │ (全域, 400px) │
                              │              │
                              │ 路由感知切換   │
                              │ 公文/開發模式  │
                              └──────────────┘
```

---

## 2. 全域浮動 AI 助理

### 設計

- 右下角浮動按鈕，點擊展開側邊面板（400px）
- 根據當前路由自動切換身份：
  - `/ai/knowledge-graph` → **公文助理**
  - `/ai/code-graph` → **開發助理**
  - `/ai/db-graph` → **開發助理**
  - 其他頁面 → **開發助理**（通用模式）
- 對話歷史按助理模式分開管理
- 公文助理 vs 開發助理在 `Layout.tsx` 層級渲染

### 工具分配

| 助理 | 可用工具 |
|------|---------|
| 公文助理 | search_documents, summarize_entity, navigate_graph, draw_diagram |
| 開發助理 | search_documents, summarize_entity, navigate_graph, draw_diagram + 代碼/DB 專用查詢 |

---

## 3. 資料庫圖譜

### 資料來源（雙軌合併）

1. **ORM 解析**：從 `backend/app/extended/models/` 解析 Column/FK/Index
2. **DB 反射**：連線 PostgreSQL 用 `inspect()` 讀取實際 Schema
3. 合併策略：ORM 為基底，DB 反射補充索引/預設值/資料量

### 節點類型

| 節點 | 說明 |
|------|------|
| `db_table` | 資料表 |
| `db_column` | 欄位（展開時顯示） |

### 關聯類型

| 關聯 | 說明 |
|------|------|
| `has_column` | 表→欄位 |
| `references_table` | FK 引用 |
| `has_index` | 索引 |

---

## 4. 模組化架構

### 共用元件（已建立/待建立）

| 模組 | 位置 | 狀態 |
|------|------|------|
| `codeGraphOptions.ts` | `constants/` | ✅ 已建立 |
| `filterGraphByRelationTypes()` | `utils/graphFiltering.ts` | ✅ 已建立 |
| `useCodeWikiGraph` | `hooks/useCodeWikiGraph.ts` | ✅ 已建立 |
| `CodeWikiFiltersCard` | `components/ai/CodeWikiFiltersCard.tsx` | ✅ 已建立 |
| `dbGraphOptions.ts` | `constants/` | ❌ 待建立 |
| `useDbGraph` | `hooks/` | ❌ 待建立 |
| `DbGraphFiltersCard` | `components/ai/` | ❌ 待建立 |
| `GlobalAIAssistant` | `components/ai/` | ❌ 待建立 |
| `DatabaseGraphPage` | `pages/` | ❌ 待建立 |

---

## 5. 實作階段

### Phase 1: 基礎整理（共用模組 + 現有頁面重構）
1. 完成 KnowledgeGraphPage / CodeGraphManagementPage 共用模組套用
2. 合併 CodeGraphManagementPage 管理功能到代碼圖譜頁面
3. 更新路由（`/ai/code-wiki` → `/ai/code-graph`）

### Phase 2: 資料庫圖譜
4. 建立 DB 圖譜常數 + Hook
5. 建立 DatabaseGraphPage
6. 後端：DB Schema 反射 API

### Phase 3: 全域浮動 AI 助理
7. 提取 RAGChatPanel 為 GlobalAIAssistant
8. 從 KnowledgeGraphPage 移除內嵌面板
9. 路由感知 + 助理模式切換

### Phase 4: 導覽同步
10. 更新 init_navigation_data.py
11. 更新 router/types.ts + AppRouter.tsx
12. TypeScript 編譯驗證
