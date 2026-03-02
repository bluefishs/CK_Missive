---
name: knowledge-map
description: 知識地圖一鍵重建與差異報告
version: 1.0.0
category: project
triggers:
  - /knowledge-map
  - 知識地圖
updated: '2026-03-02'
---

# /knowledge-map — 知識地圖管理

執行知識地圖重建或差異檢查。

## 執行步驟

### 1. 重建索引

```bash
node .claude/scripts/generate-index.cjs
```

確認 Skills/Agents/Commands 索引正確。

### 2. 知識地圖重建 + 差異報告

```bash
node .claude/scripts/generate-knowledge-map.cjs --diff
```

使用 `--diff` 模式，同時重建知識地圖並產生差異報告。

### 3. 檢視差異報告

讀取 `docs/knowledge-map/_Diff-Report.md`，向使用者報告：
- 新增了多少張卡片
- 修改了多少張卡片
- 刪除了多少張卡片

### 4. 匯出建議（若有變更）

若差異報告顯示有新增卡片：
- 告知使用者哪些新卡片需要匯入 Heptabase
- 建議將新增卡片的 `.md` 檔案單獨壓縮匯入

若差異報告顯示有修改卡片：
- 列出修改的卡片名稱
- 建議在 Heptabase 中手動更新內容

若無變更：
- 告知使用者知識地圖與源檔案完全同步

## 可用選項

| 選項 | 說明 |
|------|------|
| `--diff` | 比較新舊卡片差異（預設） |
| `--clean` | 清除舊卡片後完全重建 |
| `--if-stale` | 僅在源檔案更新時才重建 |

## 相關

- `node .claude/scripts/validate-all.cjs` — Skills 格式驗證
- `node .claude/scripts/generate-index.cjs` — 索引重建
- `node .claude/scripts/promote-learned-patterns.cjs` — 學習模式升級
