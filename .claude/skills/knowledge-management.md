# 知識管理規範

> 觸發關鍵字：ADR, 決策, 架構圖, 知識管理, 功能生命週期, decision, architecture diagram

## ADR (Architecture Decision Records)

### 位置
- 模板：`docs/adr/TEMPLATE.md`
- 索引：`docs/adr/README.md`
- 使用 `/adr` 命令操作

### 狀態流程
```
proposed → accepted → implemented
                   → deprecated → removed
                   → superseded by ADR-XXXX
         → rejected
```

### 建立時機
- 選擇新技術或框架
- 改變系統架構或資料流
- 新增外部服務整合
- 改變認證/授權策略
- 建置大型功能（>4 小時工作量）

### 超前開發防範
參見 [ADR-0011](docs/adr/0011-ai-config-db-crud-removed.md) 教訓：
1. 功能建置前在 ADR 記錄需求來源和預期使用者
2. 使用 `proposed` → `accepted` 狀態流程取得確認
3. 大型功能先建 MVP（唯讀/最小可用），驗證後再完整實作

## 架構圖

### 位置
- 索引：`docs/diagrams/README.md`
- 格式：Mermaid-in-Markdown（GitHub 原生渲染）

### 現有圖表
| 圖表 | 說明 |
|------|------|
| `system-overview.md` | 系統全景 |
| `ai-pipeline.md` | AI 四層架構 + Agent + RAG |
| `data-flow.md` | 請求生命週期 |
| `auth-flow.md` | 認證流程 |
| `deployment.md` | 混合部署拓撲 |

### 更新時機
- 新增或移除系統元件時更新 `system-overview.md`
- 修改 AI 管線時更新 `ai-pipeline.md`
- 修改認證邏輯時更新 `auth-flow.md`
- 修改部署架構時更新 `deployment.md`

## 混合模式整合

| 層級 | 工具 | 內容 |
|------|------|------|
| 技術決策 | git (docs/adr/) | ADR 記錄 |
| 架構視覺化 | git (docs/diagrams/) | Mermaid 架構圖 |
| 變更記錄 | git (.claude/CHANGELOG.md) | 版本變更細節 |
| 跨 session | memory/MEMORY.md | 操作性上下文 |
| 高層規劃 | Heptabase | 功能規劃白板、里程碑 |
| 專案管理 | Notion | 路線圖、待辦事項 |

## 與 CHANGELOG 的關係

- CHANGELOG 記錄「做了什麼」（what changed）
- ADR 記錄「為什麼這樣做」（why this approach）
- 兩者互相引用：ADR 的「關聯」欄位指向 CHANGELOG 版本
