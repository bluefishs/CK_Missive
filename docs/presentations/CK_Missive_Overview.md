---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-family: 'Microsoft JhengHei', 'Noto Sans TC', sans-serif; }
  h1 { color: #1a365d; font-size: 2.2em; }
  h2 { color: #2d3748; font-size: 1.6em; }
  table { font-size: 0.75em; }
  .columns { display: flex; gap: 24px; }
  .col { flex: 1; }
  .highlight { color: #1890ff; font-weight: bold; }
  .stat-box { background: #f0f5ff; border-radius: 8px; padding: 12px 16px; text-align: center; margin: 4px; }
  .stat-num { font-size: 2em; font-weight: bold; color: #1890ff; }
  .stat-label { font-size: 0.8em; color: #666; }
---

# CK_Missive 公文管理 AI 引擎

### 乾坤測繪科技 — 企業級智能公文與專案管理系統

<div class="columns" style="margin-top: 40px;">
<div class="col">

**核心定位**
- 公文全生命週期管理
- NemoClaw 自覺型 AI 代理人
- 7 大知識圖譜統一搜尋
- LLM Wiki 編譯式知識庫

</div>
<div class="col">

**技術棧**
- FastAPI + PostgreSQL + Redis
- React + TypeScript + Ant Design
- Gemma 4 8B 本地 GPU 推理
- Karpathy 4-Phase 知識管理

</div>
</div>

**v5.5.4** | 922 commits | 1,616 原始碼檔 | 3,263 自動化測試

---

# 1. 系統規模與數據

<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin: 30px 0;">
<div class="stat-box"><div class="stat-num">1,698</div><div class="stat-label">公文總數</div></div>
<div class="stat-box"><div class="stat-num">82</div><div class="stat-label">承攬案件</div></div>
<div class="stat-box"><div class="stat-num">127</div><div class="stat-label">派工單</div></div>
<div class="stat-box"><div class="stat-num">94</div><div class="stat-label">往來機關</div></div>
<div class="stat-box"><div class="stat-num">2,869</div><div class="stat-label">標案紀錄</div></div>
<div class="stat-box"><div class="stat-num">2,539</div><div class="stat-label">KG 實體</div></div>
<div class="stat-box"><div class="stat-num">220</div><div class="stat-label">Wiki 知識頁</div></div>
<div class="stat-box"><div class="stat-num">19</div><div class="stat-label">排程任務</div></div>
</div>

| 模組 | 後端 Python | 前端 TSX/TS | 測試 | 覆蓋 |
|------|------------|-------------|------|------|
| 公文管理 | 421L service | 15+ pages | 800+ | ✅ |
| ERP 財務 | 10 sub-services | 12 pages | 500+ | ✅ |
| 桃園派工 | 7 repositories | 8 tabs | 400+ | ✅ |
| AI/Agent | 11 子包 120+ files | 5 pages | 1000+ | ✅ |
| **總計** | **649 files** | **967 files** | **3,263** | **0 TSC / 0 ESLint** |

---

# 2. NemoClaw 自覺型 AI 代理人

<div class="columns">
<div class="col">

### 架構特色
- **26 真工具** — 不是 prompt trick，是可執行的 DB 查詢、分析、寫入
- **ReAct 雙層評估** — 規則 0ms 快路徑 + LLM 慢路徑
- **自省閉環** — SelfEvaluator 5 維度 → EvolutionScheduler 自動調參
- **CRITICAL TTL 30min** — 即時回饋 + 自動回滾
- **Domain-aware** — 4 域並行 (doc/pm/erp/dispatch)

### 進化閉環
```
觀察 → 評分 → 學習 → 調參 → 驗證
  ↑                              │
  └──────── 失敗自動回滾 ────────┘
```

</div>
<div class="col">

### 工具分類

| 類型 | 工具 | 用途 |
|------|------|------|
| 查詢 | query_documents | 公文搜尋 |
| 分析 | project_analytics | 案件分析 |
| 圖譜 | kg_query | 知識圖譜 |
| 標案 | search_tenders | 標案檢索 |
| 派工 | dispatch_query | 派工管理 |
| 財務 | erp_query | 帳務查詢 |
| Wiki | wiki_search | 知識搜尋 |
| 寫入 | wiki_ingest | 知識寫入 |

**串流問答**: SSE → 即時顯示思考 / 工具呼叫 / 結果

</div>
</div>

---

# 3. 七大知識圖譜統一搜尋

<div class="columns">
<div class="col">

### 圖譜架構
```
KG-1  公文圖譜     機關↔公文↔專案
KG-2  派工圖譜     派工單↔工程↔公文
KG-3  NER 實體圖譜  人名↔機關↔地點
KG-4  ERP 財務圖譜  報價↔請款↔帳本
KG-5  Code 程式圖譜 模組↔類別↔函數
KG-6  標案圖譜     廠商↔機關↔標案
KG-7  Skills 能力圖 技能↔工具↔進化
```

**統一搜尋**: Unified Search + case_code 跨圖橋接

</div>
<div class="col">

### 技術亮點
- **2,539 實體 / 2,890 關係** (knowledge domain)
- **Graph-RAG 2-hop** — 自動注入周邊上下文
- **CTE 動態降級** — branching>20→max_hops=2
- **Embedding 預熱** — 每日 04:45 top-500
- **graph_domain 分離** — knowledge vs code vs erp
- **Confidence + Centrality** 排序

### 前端視覺化
- force-graph 2D/3D
- 節點設定面板
- 最短路徑搜尋
- 實體合併工具

</div>
</div>

---

# 4. LLM Wiki — Karpathy 知識編譯架構

<div class="columns">
<div class="col">

### 四階段閉環

| Phase | 動作 | 實作 |
|-------|------|------|
| **Ingest** | 蒐集原始資料 | Excel/API 匯入→DB |
| **Compile** | LLM 編譯知識 | WikiCompiler (增量) |
| **Query** | 搜尋 + 問答 | Wiki-RAG 融合 |
| **Lint** | 矛盾/缺漏掃描 | 每日 05:30 排程 |

### 成果
- **220 頁** (62 機關 + 30 案件 + 127 派工)
- **10,603 行**結構化知識
- **477 cross-links** 頁面互引
- **Wiki ↔ KG 獨立雙源** 不互相污染

</div>
<div class="col">

### 架構圖
```
DB (PostgreSQL)
  ├→ WikiCompiler (週一 05:00)
  │    ├→ 機關 wiki (往來統計+案件)
  │    ├→ 案件 wiki (工程+派工+公文)
  │    ├→ 派工單 wiki (完整時間軸)
  │    └→ Interest Signal (近 7 天焦點)
  │
  └→ NER Pipeline (每次公文入庫)
       └→ KG canonical_entities
```

### 與 KG 比對
- 79 exact match (36.1% 覆蓋)
- 獨立雙源，Coverage API 唯讀比對
- kg_entity_id 嵌入 wiki frontmatter

</div>
</div>

---

# 5. ERP 財務管理模組

<div class="columns">
<div class="col">

### 跨模組架構 (ADR-0013)
```
case_code (跨模組橋樑)
  ├→ PM Cases (建案/報價)
  ├→ Contract Projects (成案/執行)
  ├→ ERP Quotations (報價紀錄)
  ├→ ERP Billings (請款管理)
  ├→ ERP Invoices (開票管理)
  ├→ Expense Invoices (費用報銷)
  ├→ Finance Ledgers (統一帳本)
  └→ Assets (資產管理)
```

### 統一編碼 (ADR-0013 Phase 1+2)
- `CK{yyyy}_{MOD}_{CC}_{NNN}` 格式
- project_code 全面 CK 前綴化
- billing/invoice/ledger 自動生成
- **併發保護**: SAVEPOINT retry × 3

</div>
<div class="col">

### 財務功能清單

| 功能 | 端點 | 自動化 |
|------|------|--------|
| 報價 CRUD | 7 端點 | 案號自動生成 |
| 請款管理 | 含收款入帳 | BL_ 自動編碼 |
| 開票管理 | 含作廢 | IV_ 自動編碼 |
| 廠商應付 | 含付款確認 | 帳本自動入帳 |
| 費用報銷 | QR+OCR+手動 | 步驟式核銷 |
| 統一帳本 | 6 端點 | FL_ 5 位序號 |
| 資產管理 | 13 端點 | AT_ 自動編碼 |
| 財務儀表板 | 月趨勢+排名 | Recharts |

**Domain Events**: 4 ERP 事件 → 即時入圖 + 財務異常偵測 (3 規則)

</div>
</div>

---

# 6. 標案分析與多通道整合

<div class="columns">
<div class="col">

### 標案三源統一
```
PCC 政府採購網  → 1,921 筆
ezbid.tw 即時  → 1,000 筆
g0v 開放資料    → 補充
─────────────────────────
合計              2,869 筆
```

### 分析功能
- 投標戰情室 (雷達圖+對手排行)
- 底價分析 (預算/決標/推估)
- 機關生態圈 (得標分佈)
- 廠商 profile (歷史統計)
- 訂閱排程 (每日 3 次 + 推播)
- **Redis 30min 快取** + 並行查詢

</div>
<div class="col">

### 多通道智能整合
```
LINE 小花貓Aroan
  └→ OpenClaw (Claude Haiku)
       └→ bash curl → Missive Agent API

Telegram @Aaron_ckbot
  └→ OpenClaw → Missive Agent API

Discord
  └→ Interactions Endpoint → Agent API
```

### 主動推播
- 派工逾期警報 → LINE/Discord/Telegram
- 財務異常偵測 → Telegram admin
- 晨報 morning_report → 每日 08:00
- Wiki Lint → 每日 05:30
- 健康檢查 → 每 5 分鐘

</div>
</div>

---

# 7. 開發工程與品質保證

<div class="columns">
<div class="col">

### 測試與 CI

| 層級 | 數量 | 工具 |
|------|------|------|
| 單元測試 | 2,400+ | pytest / vitest |
| 整合測試 | 300+ | pytest + DB |
| 前端元件 | 500+ | vitest + RTL |
| E2E | 17 spec | Playwright |
| **總計** | **3,263** | **0 failure** |

### 自動化守衛
- **Pre-commit**: TSC + ESLint + Python compile + 敏感檔偵測
- **Post-commit**: 知識地圖增量更新
- **PostToolUse**: TypeScript/Python 自動檢查
- **PreToolUse**: 檔案位置驗證 + 危險命令攔截

</div>
<div class="col">

### Claude Code 工程化

| 資產 | 數量 |
|------|------|
| Skills (領域知識) | 28 + 16 共享 |
| Slash Commands | 30 |
| Agents (專業代理) | 13 |
| Hooks (自動化) | 9 |
| 排程任務 | 19 |
| ADR (架構決策) | 15 |

### 程式碼規模
- **649** Python files (Backend)
- **967** TypeScript files (Frontend)
- **34** Repository classes
- **50+** Service classes
- **15** ADR 架構決策紀錄

</div>
</div>

---

# 8. 系統架構總覽

```
┌─────────────────────────────────────────────────────────────┐
│                    CK_Missive 系統架構                        │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  React    │  │ FastAPI  │  │PostgreSQL│  │  Redis   │   │
│  │ Ant Design│  │ uvicorn  │  │ pgvector │  │  快取    │   │
│  │  Vite     │→│ 8001     │→│ 5434     │  │  6380    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↑              ↑              ↑                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ PM2 進程 │  │ Gemma 4  │  │  Ollama  │                 │
│  │ 管理     │  │ 8B Q4    │  │ nomic    │                 │
│  │          │  │ GPU推理  │  │ embed    │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │              NemoClaw Agent 26 Tools             │       │
│  │  ┌────────┬────────┬────────┬────────┬────────┐ │       │
│  │  │ 公文   │ 派工   │  ERP   │ 標案   │  Wiki  │ │       │
│  │  │ 查詢   │ 管理   │ 財務   │ 分析   │ 知識庫 │ │       │
│  │  └────────┴────────┴────────┴────────┴────────┘ │       │
│  │  SSE 串流 │ ReAct │ 自省 │ 進化 │ Graph-RAG  │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
│  LINE ←→ OpenClaw ←→ Agent API                             │
│  Telegram ←→ OpenClaw ←→ Agent API                         │
│  Discord ←→ Interactions ←→ Agent API                      │
└─────────────────────────────────────────────────────────────┘
```

---

# 9. 創新亮點與差異化

<div class="columns">
<div class="col">

### 🏆 技術創新

1. **Agent 自主進化閉環**
   Layer 1→2→3 完整貫通 (95%)
   業界少見的 self-evolution 實作

2. **LLM Wiki 編譯架構**
   Karpathy 模式首次應用於企業系統
   220 頁知識自動編譯 + KG 比對

3. **7 圖譜統一搜尋**
   跨公文/派工/ERP/標案/Code 融合
   Graph-RAG 2-hop 上下文注入

4. **統一編碼體系 (ADR-0013)**
   15 編碼機制歸一 + 併發 SAVEPOINT retry

</div>
<div class="col">

### 🎯 業務價值

1. **公文處理效率**
   1,698 件公文全索引 + AI 摘要分類

2. **標案情報**
   2,869 筆三源統一 + 每日 3 次更新
   投標戰情室 + 底價分析

3. **財務透明度**
   統一帳本 + 冪等入帳 + 三方同步
   每筆交易可追溯至原始公文

4. **知識不流失**
   Wiki 每週自動編譯
   Agent 回答成為組織知識

5. **多通道觸達**
   LINE/Telegram/Discord 統一
   逾期 + 異常主動推播

</div>
</div>

---

# 10. 發展藍圖

<div class="columns">
<div class="col">

### 近期 (Q2 2026)
- [ ] Wiki LLM narrative (Gemma 4 敘述摘要)
- [ ] Agent Memory Snapshot (對話快照/恢復)
- [ ] Orchestrator 整合測試
- [ ] 費用報銷 Excel 匯入

### 中期 (Q3 2026)
- [ ] RAG v3 多模態 (圖片+表格)
- [ ] 標案決標自動爬取
- [ ] Token 成本追蹤面板
- [ ] dispatch_no 西元年遷移

### 長期 (2027+)
- [ ] Multi-Agent 協作
- [ ] KG 聯邦 v2 跨系統
- [ ] 離線推理模式

</div>
<div class="col">

### 關鍵指標追蹤

| 指標 | 現值 | 目標 |
|------|------|------|
| 公文數 | 1,698 | 3,000+ |
| KG 實體 | 2,539 | 5,000+ |
| Wiki 頁面 | 220 | 500+ |
| 測試數 | 3,263 | 4,000+ |
| 標案紀錄 | 2,869 | 5,000+ |
| Agent 工具 | 26 | 35+ |
| Wiki-KG 覆蓋 | 36.1% | 60%+ |

### 核心理念

> **測試驅動** | **系統化優於臨時性**
> **簡潔為首要** | **證據優於聲稱**
> **AI 編譯知識** | **人做判斷 AI 做整理**

</div>
</div>

---

<!--
_class: lead
_paginate: false
-->

# 謝謝

**CK_Missive** — 讓 AI 成為測繪公司的知識引擎

乾坤測繪科技有限公司

`v5.5.4` | 2026-04-13
