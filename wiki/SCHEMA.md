# CK_Missive LLM Wiki Schema

> 基於 Karpathy LLM Wiki Pattern，適配公文管理+標案+ERP 領域。
> LLM 維護此 wiki，人類閱讀與引導。

## 目錄結構

```
wiki/
├── SCHEMA.md          # 本文件 — wiki 結構與約定
├── index.md           # 內容索引 (LLM 維護)
├── log.md             # 操作日誌 (append-only)
├── entities/          # 實體頁面 (機關/廠商/專案/人員)
├── topics/            # 主題頁面 (概念/流程/技術)
├── sources/           # 來源摘要 (公文/標案/會議紀錄)
└── synthesis/         # 綜合分析 (比較/趨勢/洞察)
```

## 頁面格式

每個 wiki 頁面都是 markdown，包含 YAML frontmatter：

```yaml
---
title: 頁面標題
type: entity | topic | source | synthesis
created: 2026-04-09
updated: 2026-04-09
sources: [doc-001, tender-123]  # 引用的原始來源
tags: [機關, 桃園, 工程]
confidence: high | medium | low
---
```

## 連結約定

- 使用 `[[wiki links]]` 格式連結其他 wiki 頁面
- 連結格式: `[[entities/機關名稱]]` 或 `[[topics/主題名稱]]`
- 每個頁面至少有 2 個入站連結 (避免孤立頁面)

## 操作流程

### Ingest (來源攝入)
1. 新公文/標案/ERP 資料進入系統
2. LLM 讀取原始資料，提取關鍵資訊
3. 建立/更新 `sources/` 下的摘要頁面
4. 更新相關 `entities/` 和 `topics/` 頁面
5. 更新 `index.md` 和 `log.md`

### Query (知識查詢)
1. 讀取 `index.md` 定位相關頁面
2. 深入閱讀相關 wiki 頁面
3. 結合 KG 圖譜資料綜合回答
4. 有價值的回答存入 `synthesis/`

### Lint (健康檢查)
- 孤立頁面 (無入站連結)
- 過時資訊 (新來源已超越舊結論)
- 缺失頁面 (被引用但不存在)
- 跨頁矛盾
- 低信心度頁面需要補充來源

## 與 KG 的關係

Wiki 和 Knowledge Graph 互補：
- **KG**: 結構化關係 (entity-relation-entity)，機器查詢最佳化
- **Wiki**: 敘述性知識 (markdown)，人類閱讀最佳化
- **橋接**: wiki 頁面的 `sources` 欄位對應 KG entity IDs
- **同步**: ingest 時同時更新 KG + wiki
