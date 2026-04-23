# ADR-0031：Frontend Page Consolidation v6.0 — 意識體入口統一 + 圖譜元件共用

> **狀態**：accepted
> **日期**：2026-04-22
> **決策者**：專案 Owner
> **關聯**：ADR-0022 Memory Wiki、ADR-0023 坤哥意識體、ADR-0028 錯誤合約化、ADR-0029 ADR Lifecycle

---

## 背景

v5.7~v5.8 快速迭代累積出**多個職責重疊的頁面**：

- 意識體入口：`UnifiedAgentPage`（/agent/dashboard）/ `DigitalTwinPage`（/ai/digital-twin）/ `KungePage`（/kunge）3 路並行 → v5.8.1 已 Navigate redirect 統一至 `/kunge/ops`，但 import 路徑 / 命名仍沿用舊稱
- 記憶類：`pages/kunge/MemoryTab` + `MemoryDashboardPage` 的 6 張 stats card 完全重複
- 進化類：`kunge/EvolutionTab` / `digitalTwin/EvolutionTab` / `SkillEvolutionPage` 三套同名但資料源不同
- 圖譜類：5 個獨立 Graph 頁面（KG/Code/DB/ERP/Tender）+ Wiki/SkillNebula 合計 8+ 處散落 `react-force-graph-2d` lazy import
- 死路由常數：`AI_ASSISTANT_MANAGEMENT` / `CODE_WIKI` / `AGENT_DASHBOARD` / `DIGITAL_TWIN` 已無生產引用但常數仍在

新人閱讀成本與前端 bundle 肥大問題日益嚴重。

---

## 決策

### 1. 意識體入口單一化 — 坤哥為唯一入口

`/kunge` 為**敘事型**首頁，7 tabs（Chat / Identity / Memory / Evolution / Nebula / Dialogues / Ops），
其中 `Ops` tab 內嵌運維儀表板（admin 見 12 子 tab，一般使用者見 7 子 tab）。

`UnifiedAgentPage` 降格為 `components/kunge/OpsDashboard.tsx` 子元件（不再是獨立 page）。

### 2. 圖譜整合策略（方案 B：保留獨立頁 + 共用元件）

**不合併成 Hub + tab**（每個圖譜互動模型差異太大），但：

- 共用 `<ForceGraphLazy>` 統一 `react-force-graph-2d` lazy import（消除 8+ 處重複）
- 長期（v6.1+）擴充 `<GraphCanvas v2>` 統一 hover / click / zoom / highlight 行為
- 新增 `/ai/graphs` index 頁（5 張 preview card）作為導覽入口

### 3. Wiki 釐清 — LLM Wiki 與 Memory Wiki 並存

| 系統 | 路由 | 定位 | 資料性質 |
|---|---|---|---|
| LLM Wiki | `/ai/wiki` | **外顯世界** — 業務領域知識 | 220 pages（機關 62 + 專案 30 + 派工 127） |
| Memory Wiki | `/ai/memory` | **內在心智** — 助理自我記憶 | diary / patterns / proposals / crystal / autobiography |

禁止合併。UI 上 `MemoryDashboardPage` 標題明確為「記憶中樞 Memory Wiki」，避免歧義。

### 4. Evolution 命名正名（三套視角職責分工）

| 舊名 | 新名 | 資料源 | 職責 |
|---|---|---|---|
| `kunge/EvolutionTab` | `CrystalEvolutionTab`（tab label 改「結晶進化」）| `/ai/memory/{patterns,proposals,crystals}` | 坤哥人格視角 |
| `digitalTwin/EvolutionTab` | `AgentHealthEvolutionTab`（tab label 改「健康進化」） | `/ai/agent/evolution/{status,journal,tool-health}` | Agent 品質監控 |
| `SkillEvolutionPage` (`/ai/skill-evolution`) | `/ai/skill-lineage` + SkillLineagePage | `AI_ENDPOINTS.GRAPH_SKILL_EVOLUTION` | 技能族譜樹 |

舊 URL 保留 Navigate redirect 6 個月。

### 5. 死路由常數處理

本 ADR 保守策略：加 `/** @deprecated v6.0.0 — removed in v6.1.0 */` JSDoc 註解，**不立即刪除**。
v6.1.0 release 前清除書籤 6 個月 buffer。

### 6. Shared Components 提取清單

| 新元件 | 取代的散落實作 | 優先度 |
|---|---|---|
| `components/memory/MemoryStatsRow` | kunge/MemoryTab + MemoryDashboardPage 各 60+L 重複 | P1（本 ADR 落地） |
| `components/graph/ForceGraphLazy` | 8+ 處 `react-force-graph-2d` lazy import | P1（本 ADR 落地） |
| `components/kunge/OpsDashboard` | 原 UnifiedAgentPage | P1（本 ADR 落地） |
| `components/graph/GraphCanvas v2` | 5 圖譜頁共用 force-graph 元件 | **P2（v6.1.0）**— 分 4 子 PR |
| `components/evolution/JournalTimeline` | digitalTwin/EvolutionTab 內部 journal | P3 |

---

## 後果

### 正面

1. **意識體入口清晰**：用戶一個 `/kunge` 地址覆蓋所有 AI 能力
2. **bundle 瘦身**：共用 ForceGraphLazy 後 vendor chunk 單一化
3. **命名不撞車**：三套 evolution 視角職責明確
4. **ADR 治理落實**：首次讓 ADR-0023 有具體實作細則記錄
5. **降低新人 onboarding 成本**：從 14+ 頁面縮為 7 意識體 tab + 5 圖譜 + 2 Wiki 清晰層級

### 負面

1. **rename 衝擊**：Evolution 命名改動需 release notes 告知使用者
2. **re-export stub 過渡期**：UnifiedAgentPage 保留 thin stub ~6 個月才能真正刪除
3. **GraphCanvas v2 遷移風險**：拆 4 子 PR 但仍可能破壞 KG Merge/ShortestPath（留 P2 處理）

### 中性

- DIGITAL_TWIN_ENDPOINTS 後端命名保留（語義落差記錄於 architecture-frontend.md）

---

## 執行 Phase（7 步，詳見 planner report）

| Phase | 內容 | Effort | 本 ADR 交付 |
|---|---|---|---|
| 1 | 死路由常數加 @deprecated | S | ✅ |
| 2 | UnifiedAgentPage → OpsDashboard | S | ✅ |
| 3 | MemoryStatsRow 共用元件 | S | ✅ |
| 4 | ForceGraphLazy 統一 wrapper | M | ✅ |
| 5 | Evolution 三路命名 | M | ✅ |
| 6 | GraphCanvas v2（分 4 子 PR） | L | ❌ 延 v6.1 |
| 7 | GraphHub 入口 + 文件 | S | ✅ |

---

## 驗證

```bash
# Phase 1 驗證
grep -rn "AI_ASSISTANT_MANAGEMENT\|CODE_WIKI\|AGENT_DASHBOARD\b" frontend/src --include="*.tsx" --include="*.ts"
# 期望：只剩 types.ts + AppRouter.tsx Navigate 條目

# Phase 2 驗證
grep -rn "UnifiedAgentPage\|OpsDashboard" frontend/src --include="*.tsx"
# 期望：OpsDashboard 為 primary；UnifiedAgentPage 僅為 re-export stub

# Phase 4 驗證
grep -rn "react-force-graph-2d" frontend/src --include="*.tsx" --include="*.ts"
# 期望：只剩 ForceGraphLazy 一處 import

# Phase 5 驗證
curl -I http://localhost:3000/ai/skill-evolution
curl -I http://localhost:3000/ai/skill-lineage
# 期望：兩個都 200（舊的 Navigate 到新的）
```

---

## 狀態記錄

- 2026-04-22：accepted，Phase 1-5 + 7 本 session 落地，Phase 6 延至 v6.1
- 2026-10-22：6 個月後 review，判斷是否 v6.1.0 真正移除 deprecated 常數

---

## 參照

- ADR-0022：Memory Wiki（本 ADR 保留 Memory Wiki 獨立頁）
- ADR-0023：坤哥意識體（本 ADR 實現入口統一細則）
- ADR-0028：錯誤合約化（Phase 4 ForceGraphLazy 應用 timeout 合約）
- ADR-0029：ADR Lifecycle（本 ADR 為 active status，v6.1 可考慮 archive）
