---
paths:
  - frontend/**
---

<!-- 2026-08-27 /doctor：加上 paths 讓這份改為**延遲載入**（前端目錄結構與契約 —— 只在動到 frontend/ 時才需要）。
     內容零刪除；只是不再每個 session 都進 context。 -->
# 前端結構

> **v5.9.1 頁面整合（ADR-0031）**：坤哥為唯一意識體入口；死路由 @deprecated 保留 Navigate redirect 6 個月。

## 意識體入口統一架構（ADR-0031）

```
/kunge  (KungePage) ← 唯一意識體入口
  # 2026-06-02 整併聚焦服務鏈：7 tab → 5 核心主軸（對話→心智→進化→圖譜→運維）
  ├── chat       → ChatTab（RAGChatPanel embedded，唯一對話入口）
  ├── mind       → 心智（嵌套：我是誰 IdentityTab + 記憶圖譜 MemoryTab + 對話精選 DialoguesTab）
  ├── evolution  → EvolutionTab（「結晶進化」= pattern→crystal 學習閉環）
  │                 └── 2026-08-02 上方加「成長總覽」一排結論（學習閉環／回答品質／記憶存量）
  │                     ——原本這件事散在四處而沒有結論，詳見下方 §Evolution 三路
  ├── graph      → NebulaTab（圖譜 / 技能星雲）
  └── ops        → OpsTab → <OpsDashboard>
                    # ⚠️ OpsDashboard 是 re-export，實作在 pages/UnifiedAgentPage.tsx
                    #    （ADR-0031 原文寫反了，2026-08-02 更正）
                    └── 2026-08-02 由 11 個扁平 tab 收斂為**三組**（owner：資訊過多、營運核心雜亂）
                        ├── 營運    → 晨報與推播（預設）、派工進度
                        ├── 系統    → 儀表板（+admin: 服務狀態/資料管線/數據分析）
                        └── AI 診斷 → 自省/追蹤/健康進化/拓撲（+admin: Agent 效能/DualMode）
                        分組準則＝「這個資訊是誰每天要看的」

  向後相容（PATH_TO_TAB）：舊 /kunge/{identity,memory,dialogues}→mind；/kunge/nebula→graph

Redirect（6 個月相容期）：
  /agent/dashboard         → Navigate /kunge/ops
  /ai/digital-twin         → Navigate /kunge/ops
  /admin/ai-assistant      → Navigate /kunge/ops
  /ai/code-wiki            → Navigate /ai/code-graph

/ai/graphs  (GraphHubPage) ← 圖譜與 Wiki 中樞（ADR-0031 Phase 7）
  圖譜：KG / Code / DB / ERP / Tender（5 preview card）
  Wiki：LLM Wiki（外顯世界）/ Memory Wiki（內在心智）
```

## 共用元件（ADR-0031 提取）

| 元件 | 路徑 | 用途 |
|---|---|---|
| `OpsDashboard` | `components/kunge/OpsDashboard.tsx` | **re-export**；實作在 `pages/UnifiedAgentPage.tsx`（ADR-0031 原文方向寫反，2026-08-02 更正） |
| `MorningReportOpsTab` | `pages/digitalTwin/MorningReportOpsTab.tsx` | 晨報與推播（營運核心）：預覽/推送＋近 7 日派送狀態＋LINE 月配額＋近 14 日快照 |
| `ErpFormPageShell` | `components/erp/ErpFormPageShell.tsx` | ERP/PM 填報頁共用**版面**（返回/標題/送出/RWD）；刻意不抽成萬用表單引擎 |
| `MemoryStatsRow` | `components/memory/MemoryStatsRow.tsx` | 6-Card 記憶統計（kunge/MemoryTab + MemoryDashboardPage 共用，省 126L） |
| `ForceGraphLazy` | `components/graph/ForceGraphLazy.tsx` | react-force-graph-2d 統一 lazy wrapper（generic） |

## v5.10.x 新增元件（ADR-0025 認證整合 + bug fixes）

| 元件 | 路徑 | 用途 | FQID |
|---|---|---|---|
| `AliasIntegrationDrawer` | `components/admin/AliasIntegrationDrawer.tsx` | 使用者認證方式整合 UI（後端 user_alias_admin endpoints 接通），雙 Tab：潛在分身偵測 + 合併歷史 | `CK_Missive#AliasIntegrationDrawer_v1.0` |

**範本價值**：Drawer 雙 Tab + Modal 多選操作模式 — 任何「admin 對 N records 做 batch action」場景可借鏡。
詳見 `docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md` §6.5（Dead UI 反模式案例）。

## v5.10.x 重要 React Query Cache Invalidate 規約（morning-status 修復）

派工總覽 (`/taoyuan/dispatch?tab=0`) 的 `dispatch-morning-status` queryKey 涉及 **8 處 mutation 必須 invalidate**：

| Hook / 元件 | 為何 invalidate | Commit |
|---|---|---|
| `useDispatchMutations.updateMutation` | 派工單更新 → display_status 變動 | `244593d0` |
| `useDispatchMutations.deleteMutation` | 派工單刪除 | 同上 |
| `useDispatchMutations.linkProjectMutation` | 工程關聯影響顯示 | 同上 |
| `useDispatchMutations.unlinkProjectMutation` | 工程解除關聯 | 同上 |
| `useDeleteWorkRecord` (通用) | 作業紀錄刪除 → work_progress 變動 | 同上 |
| `useWorkRecordFormLogic.createMutation` | 作業紀錄建立 | 同上 |
| `useWorkRecordFormLogic.updateMutation` | 作業紀錄更新 | 同上 |
| `InlineRecordCreator.createMutation` | 內聯作業紀錄建立 | 同上 |
| `KanbanBoardTab.statusMutation` | 看板批次狀態切換 | 同上 |

配合 `DispatchOverviewTab.useQuery` 的 `refetchOnMount: 'always'` + staleTime 30s 形成雙保險。

**範本提取**（LESSON L11）：任何 useQuery `staleTime > 0` + 跨 tab/詳情頁變更場景都應採此雙管齊下規約。

## Evolution 三路職責分工（ADR-0031 Phase 5）

| 路徑 | 舊名 | 新意涵 | 資料源 |
|---|---|---|---|
| `/kunge/evolution` | 進化史 | **結晶進化** — pattern→crystal 學習閉環；2026-08-02 上方加「成長總覽」聚合三路結論 | `/ai/memory/{patterns,proposals,crystals}` + `agent/evolution/status` + memory stats |
| `/kunge/ops` (evolution tab) | 進化 | **健康進化** — Agent 品質監控 | `/ai/agent/evolution/{status,journal,tool-health}` |
| `/ai/skill-evolution` | 技能演化樹 | **技能族譜** — DB skill lineage 樹 | `AI_ENDPOINTS.GRAPH_SKILL_EVOLUTION` |

## 前端元件結構

### 頁面模組化拆分 (v1.83.0)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

### 前端 Hooks 結構 (39 檔, 150+ hooks)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

### 通用元件 + 工具

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

### 作業歷程模組 (v2.0.0)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

### DocumentOperations 模組 (v1.13.0)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

## 前端型別 SSOT (v5.3.24)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

## 前端全域錯誤處理 (v1.79.0)

> 目錄清單已移除（2026-08-27 /doctor）——`ls`／`Glob` 就能得到，
> 而它每個 session 都要載入一次。**不可推導的部分（職責、契約、
> 例外、為什麼這樣切）仍留在本檔其餘章節。**

錯誤分流規則：
- **業務錯誤** (400/409/422): 元件自行 catch 處理
- **全域錯誤** (403/429/5xx/網路): `GlobalApiErrorNotifier` 自動通知，3 秒去重
- **429 熔斷**: `RequestThrottler` 超過上限 → `ApiException(429)` → 用戶通知
