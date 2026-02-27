# 架構圖索引

本目錄以 Mermaid 格式記錄系統架構圖，可在 GitHub 上直接渲染。

## 圖表列表

| 圖表 | 說明 | 最後更新 |
|------|------|---------|
| [system-overview.md](system-overview.md) | 系統全景：前端、後端、資料庫、AI 服務 | 2026-02-27 |
| [ai-pipeline.md](ai-pipeline.md) | AI 四層架構 + Agent 工具流 + RAG 管線 | 2026-02-27 |
| [data-flow.md](data-flow.md) | 請求生命週期：元件 → Hook → API → Service → DB | 2026-02-27 |
| [auth-flow.md](auth-flow.md) | 四種環境認證流程 + Token Rotation | 2026-02-27 |
| [deployment.md](deployment.md) | 混合部署拓撲：Docker infra + PM2 app | 2026-02-27 |

## 編輯指南

- 使用 Mermaid 語法，GitHub 原生渲染無需額外工具
- 線上編輯器：https://mermaid.live
- 每張圖附上 2-3 句文字說明
- 更新後同步修改本索引的「最後更新」欄位
