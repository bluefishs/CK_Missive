---
name: wiki-authoring
description: LLM Wiki (Karpathy Pattern) 4-Phase 開發與維運規範
version: 1.0.0
category: ai
triggers:
  - wiki
  - LLM Wiki
  - Karpathy
  - Ingest
  - Compile
  - wiki lint
  - wiki-rag
  - kg_entity_id
  - wiki orphan
  - broken links
---

# LLM Wiki 開發規範 (Karpathy 4-Phase)

## 架構定位

LLM Wiki 是 **「可驗證的 LLM 記憶層」** — 把原始資料（公文 / 派工 / 機關 / 工程）編譯成可查詢、可稽核、可增量更新的 Markdown 頁面，形成 RAG 的**高可信來源**。

```
docs/公文/派工 → [1 Ingest] → wiki/entities/
                                        ↓
                                [2 Compile] ← KG entities
                                        ↓
                              wiki/*.md (220 pages)
                                        ↓
            RAG Query ←─ [3 Query Fusion] ─→ synthesis
                                        ↓
                                [4 Lint] 每日 05:30
```

## 四階段規範

### Phase 1: Ingest
- **來源**：文件、派工單、機關、工程專案
- **產出**：`wiki/entities/{type}/{slug}.md`
- **約定**：page 必須含 frontmatter `kg_entity_id`（若存在於 KG），否則留空等 Phase 4 補齊。
- **log**：`wiki/log.md` append-only，格式：`[date] ingest | entity | {name} ({type})`

### Phase 2: Compile
- **觸發**：每週一 05:00 `wiki_compile` 排程 + 手動 `/knowledge-map` 指令
- **特性**：**增量** compile（diff-based，只重編修改過的頁面）
- **token panel**：UI 呈現本次 compile 消耗 token 與耗時
- **輸出**：更新 `wiki/*.md` + index

### Phase 3: Query
- **Wiki-RAG 融合**：wiki search 命中 → RAG sources boost（similarity=0.95）
- **禁止**：直接從 wiki 回答而跳過 RAG；wiki 只是 **來源加權**，答案仍由 LLM synthesis 產生
- **KG 橋接**：wiki page 帶 `kg_entity_id` 時自動注入 2-hop KG context

### Phase 4: Lint
- **排程**：每日 05:30 `wiki_lint`
- **檢查**：broken links / orphan pages / stale refs
- **輸出**：推送到 `/health/summary` + Discord 告警（目前 orphan=71, broken=5）

## 前端位置

- 路由：`/ai/wiki` (獨立頁面)
- 4-Tab：圖譜 / 瀏覽 / KG 比對 / 管理
- 圖譜：`force-graph 2d`，log scale + collision

## 禁止事項

1. **禁止手動編輯 `wiki/*.md`** — 一律由 Phase 2 Compile 產出。手寫內容會在下次 compile 被覆蓋。
2. **禁止在 wiki page 存放推論結論** — wiki 只存事實（ground truth），推論留給 synthesis 層。
3. **禁止繞過 `kg_entity_id`** 直接以字串匹配 KG — 必須走 id。
4. **禁止 wiki ↔ KG 互相寫入** — 雙源獨立，比對由 Phase 4 lint 完成（目前 exact match 36.1%）。

## 常見任務

| 任務 | 做法 |
|---|---|
| 新增實體類型到 wiki | 擴充 `wiki_compiler.py` 的 entity_builder，加 Phase 4 lint 規則 |
| 補 `kg_entity_id` 失敗 | 檢查 canonical_entity.name 是否 normalize（見 `unicode-handling.md`） |
| Wiki orphan 解除 | 建立反向連結（在其他 page 引用），或 archive 到 `wiki/archive/` |
| Broken link 修復 | 跑 lint 取清單 → 修正目標 slug → 重 compile |

## 相關檔案

- `backend/app/services/ai/wiki/` — compiler / linter / ingest
- `frontend/src/pages/WikiPage.tsx` — /ai/wiki 頁面
- `wiki/SCHEMA.md` — wiki 約定定義
- `wiki/log.md` — append-only 操作日誌

## 驗證指令

```bash
# 手動重編
node .claude/scripts/generate-knowledge-map.cjs --diff

# Lint
curl -X POST http://localhost:8001/ai/wiki/lint

# KG coverage
curl http://localhost:8001/ai/wiki/kg-coverage
```
