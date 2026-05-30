# 坤哥 /kunge UX 重設計規劃 — Sprint 3.P3.14

> **觸發**：Sprint 3.P3.14 pending（自 5/12 規劃以來未動）
> **建立**：2026-05-30
> **設計理念**：v6.12 整合 SSOT Dashboard 後，/kunge 應從「7 tabs 展覽」轉為「3 軸操作中樞」
> **時程**：規劃→實作 1-2 週

---

## 1. 現況分析

### 當前 7 tabs（v5.9.1 ADR-0031）

| Tab | 用途 | 真實使用率（owner 反饋）|
|---|---|---|
| `chat` | RAG 對話 | 🟢 高（主路徑）|
| `identity` | SOUL 三信念 + 倫理紅線 | 🟡 中（少看）|
| `memory` | 6-Card 記憶統計 | 🟢 中（dashboard 化）|
| `evolution` | 結晶進化 pattern→crystal | 🟡 中（owner 監控）|
| `nebula` | 技能星雲 force-graph | 🔴 低（看了一次）|
| `dialogues` | 對話精選 | 🔴 低（無時間看）|
| `ops` | OpsDashboard（原 UnifiedAgentPage 降格）| 🟢 高（owner 監控）|

### 真實問題

1. **7 tabs 太多** — owner 主要用 chat / memory / ops，其他 4 tab 為「展覽」
2. **整合 SSOT Dashboard 後重疊** — `docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md` 已涵蓋 ops 部分內容
3. **記憶監控不夠即時** — 6-Card 不能直接看 metric trend
4. **進化視覺化弱** — pattern→crystal 流程缺乏視覺引導

---

## 2. 重設計方案 — 3 軸操作中樞

### 新架構

```
/kunge
├── 💬 對話 (Chat)
│   └── RAGChatPanel embedded
│       + 即時 metric 浮層 (右下角 governance metric 摘要)
│       + 一鍵 quick action (記憶 / 進化 / 觀測)
│
├── 🧠 心智 (Mind)
│   ├── Identity (SOUL 三信念，摘要版)
│   ├── Memory Stats (6-Card，即時連 metric)
│   └── Evolution (pattern→crystal 視覺化流程)
│
└── 📊 觀測 (Observability)
    ├── OpsDashboard（原 ops，含 governance metric 即時）
    ├── 整合 SSOT Dashboard 入口
    └── 漂移看板（cross_repo / fitness / lessons）
```

### 移除 / 整合

- ❌ `nebula` 技能星雲 → 整合進 Mind 內 collapsible（一鍵展開）
- ❌ `dialogues` 對話精選 → 整合進 Chat 內 history sidebar
- ✅ 從 7 tabs → 3 軸

### 新 UX 4 原則

1. **3 軸不超過** — 對話 / 心智 / 觀測，符合人類短期記憶上限
2. **即時 metric 化** — 心智頁面直接讀 prometheus governance_* gauge
3. **一鍵跨域** — Chat 內可直接跳 Mind/Observability，反之亦然
4. **整合 SSOT 入口** — Observability 頁面 §1 顯示 `GOVERNANCE_INTEGRATED_DASHBOARD.md` 連結

---

## 3. 具體實作清單

### Phase 1（3 天）— 核心結構重構

| 任務 | 檔案 | 工時 |
|---|---|---|
| KungePage.tsx 改 3 軸 Tab | `frontend/src/pages/KungePage.tsx` | 2h |
| MindTab.tsx 新建（含 Identity + Memory + Evolution sub-tab）| `frontend/src/components/kunge/MindTab.tsx` | 4h |
| ObservabilityTab.tsx 新建（含 OpsDashboard + Dashboard 入口 + 漂移看板）| `frontend/src/components/kunge/ObservabilityTab.tsx` | 4h |
| 移除 nebula / dialogues 主 tab（保留 sub） | 同 KungePage | 1h |
| Redirect 舊路徑 `/kunge/nebula` `/kunge/dialogues` 半年相容 | `AppRouter.tsx` | 1h |

### Phase 2（3 天）— 即時 metric 整合

| 任務 | 工時 |
|---|---|
| MemoryStatsRow 升級：直接讀 `/metrics` governance_* gauge | 3h |
| ChatPanel 浮層：右下角 metric 摘要（diary_density / facade adoption / cross_repo） | 3h |
| Evolution 流程視覺化：pattern→proposal→crystal 三階段 timeline | 4h |
| Observability §1：整合 SSOT Dashboard 渲染 | 2h |

### Phase 3（1-2 天）— Quick Action + 文件對齊

| 任務 | 工時 |
|---|---|
| 一鍵跨域 button group | 2h |
| 漂移看板（cross_repo / fitness daily / 7 governance metric）| 3h |
| 更新 ADR-0031 (頁面整合 v6.0 → v6.5) | 1h |
| 寫 lesson L55: /kunge UX 7→3 簡化 | 1h |

---

## 4. 驗收標準

### 量化指標

- ✅ Tab 數 7 → 3
- ✅ MemoryStatsRow 直連 `/metrics` 5 個 gauge
- ✅ ChatPanel 右下角浮層 3 個即時 metric
- ✅ Observability 含 dashboard 入口 + 漂移看板

### 質化指標

- ✅ Owner 連續 3 天使用後反饋「主要在 Chat + Observability，3 軸夠用」
- ✅ 訪客 30 秒內理解「對話 / 心智 / 觀測」三件套
- ✅ 不影響既有功能（無 regression）

---

## 5. 風險評估

| 風險 | 等級 | 緩解 |
|---|---|---|
| 舊路徑用戶誤入 nebula/dialogues | 中 | Navigate redirect 6 個月 |
| 心智頁面整合過多 metric 載入慢 | 中 | useQuery cache + lazy load |
| 觀測頁面太技術 owner 不看 | 低 | 加摘要卡 + 一鍵連 dashboard |

---

## 6. 與整合 SSOT Dashboard 的關聯

`docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md` 是「規範 + 現況 + 覆盤」single SSOT。
/kunge Observability 是「即時操作介面」配套：

| 用途 | Dashboard md | /kunge Observability |
|---|---|---|
| 完整快照 | ✅ 10 章節 | ❌ 太多 |
| 即時 trend | ❌ 靜態 | ✅ 5 metric chart |
| Owner action 入口 | ✅ §10 | ✅ 一鍵跳 admin |
| 規範索引 | ✅ §1 | ❌ 不重複 |

設計：**Dashboard md = 靜態完整視角 / /kunge = 即時動態介面**。

---

## 7. 60 天 trial 對齊

新 UX 上線後 60 天 audit:
- Tab 真實使用率（前端 GTM 或 prometheus 埋點）
- ChatPanel 浮層觸發頻率
- 一鍵跨域使用次數

→ 若任一 < 10% → 廢該 feature（對齊 L31 ROI 公式 + L53 30 天裁判 SOP）

---

## 8. 下批執行順序

```
Day 1-3: Phase 1 核心結構
Day 4-6: Phase 2 metric 整合
Day 7-8: Phase 3 quick action
Day 9:   驗收 + commit + 寫 L55 lesson
Day 60: audit + 廢未活 feature
```

---

> **元洞察**：/kunge 不再是「展覽坤哥多厲害」，而是「操作 + 觀測」中樞。
> 7 tabs 是炫技，3 軸是真實工作流。
> 對齊 v6.12 第 3 句立法「規範散落是必然，整合 SSOT 是責任」 — UX 也適用。
