---
description: "工程回顧 — per-author 統計 + session 偵測 + 指標追蹤"
---

# Retro — 工程回顧與指標追蹤

> 靈感來源: [gstack/retro](https://github.com/garrytan/gstack) — 團隊感知回顧分析
> **版本**: 2.0.0 (v1→v2: per-author + compare + session + version range)

分析 commit 歷史、工作模式、程式碼品質指標，生成結構化工程回顧報告。

## 使用方式

```
/retro              # 預設 7 天回顧
/retro 24h          # 24 小時回顧
/retro 14d          # 14 天回顧
/retro 30d          # 30 天回顧
/retro compare      # 與上次回顧比較（趨勢分析）
/retro v5.1.14..v5.1.16  # 版本範圍回顧
```

## 資料收集（並行 git 查詢）

執行以下 git 命令收集資料：

```bash
# 基本統計
git log --since="7 days ago" --oneline --format="%H|%an|%ae|%ai|%s"
git log --since="7 days ago" --numstat --format=""
git log --since="7 days ago" --format="%ai" | cut -d' ' -f2 | cut -d: -f1 | sort | uniq -c

# 檔案熱點
git log --since="7 days ago" --name-only --format="" | sort | uniq -c | sort -rn | head -20

# 作者統計
git shortlog --since="7 days ago" -sn

# 測試比率
find frontend/src -name "*.test.*" | wc -l
find backend/tests -name "test_*.py" | wc -l
```

## 指標計算

| 指標 | 計算方式 |
|------|---------|
| Commits | 期間內 commit 總數 |
| Contributors | 不同 author 數量 |
| LOC +/- | insertions / deletions |
| Test Ratio | test files / total files changed |
| Active Days | 有 commit 的日數 |
| Avg Commits/Day | commits / active days |
| Files Changed | 不重複檔案數 |
| Hotspot Files | 被修改最多次的前 10 檔案 |

## Per-Author 貢獻分析

對每位作者統計：

```bash
# 每位作者的詳細統計
git log --since="7 days ago" --author="<name>" --numstat --format=""
git log --since="7 days ago" --author="<name>" --oneline
```

**輸出**：
```markdown
## 貢獻者分析

| 作者 | Commits | LOC+ | LOC- | 淨增 | 主要模組 | 工作類型 |
|------|---------|------|------|------|---------|---------|
| dev-a | 12 | +850 | -120 | +730 | services/erp | feat (75%) |
| dev-b | 8 | +200 | -400 | -200 | tests/ | refactor (60%) |
| claude | 5 | +300 | -50 | +250 | .claude/ | docs (80%) |
```

## Commit 分類

按 conventional commits 分類：
- `feat:` — 新功能
- `fix:` — 修復
- `refactor:` — 重構
- `test:` — 測試
- `docs:` — 文件
- `chore:` — 維護
- `perf:` — 效能
- `ci:` — CI/CD

**警告信號**: 若 fix 佔比超過 50%，標記為需關注。

## 時間分析

- 每小時 commit 分布直方圖
- 識別高峰時段與低谷

### Session 偵測

根據 commit 時間間隔分類工作 session：

| Session 類型 | 定義 | 說明 |
|-------------|------|------|
| **Deep** | 連續 > 50 分鐘 | 專注深度開發（最有生產力） |
| **Medium** | 20-50 分鐘 | 一般開發工作 |
| **Micro** | < 20 分鐘 | 快速修復或文件更新 |

**判斷邏輯**：
1. 按時間排序所有 commits
2. 相鄰 commit 間隔 > 45 分鐘 → 新 session
3. Session 持續時間 = 最後一個 commit 時間 - 第一個 commit 時間
4. 根據持續時間分類

**輸出**：
```markdown
## 工作模式分析

| 類型 | 次數 | 平均時長 | 佔比 |
|------|------|---------|------|
| Deep | 3 | 2.5h | 45% |
| Medium | 5 | 35min | 35% |
| Micro | 8 | 12min | 20% |

建議: Deep session 比例良好 (45%)，生產力模式健康。
```

## Compare 模式

若使用 `/retro compare`：

1. 讀取上次 JSON 報告（`.claude/retros/` 目錄最新檔案）
2. 計算趨勢差異
3. 輸出比較表：

```markdown
## 趨勢比較 (本週 vs 上週)

| 指標 | 上週 | 本週 | 變化 | 趨勢 |
|------|------|------|------|------|
| Commits | 25 | 32 | +28% | ↑ |
| LOC 淨增 | +1200 | +800 | -33% | ↓ |
| 測試比率 | 35% | 42% | +7% | ↑ |
| Deep sessions | 2 | 4 | +100% | ↑ |
| fix 佔比 | 20% | 15% | -5% | ↑ (改善) |
```

## 版本範圍模式

若使用 `/retro v5.1.14..v5.1.16`：

```bash
git log v5.1.14..v5.1.16 --oneline --format="%H|%an|%ae|%ai|%s"
```

適用於版本發布後回顧特定版本區間的工作成果。

## 輸出格式

```markdown
# 工程回顧 — YYYY-MM-DD (N days)

## 一句話摘要
> [本週最大亮點]

## 指標總覽

| 指標 | 數值 | 趨勢 |
|------|------|------|
| Commits | N | ↑/↓/→ |
| LOC 淨增 | +N/-M | |
| 測試比率 | N% | |
| 活躍天數 | N/7 | |
| Deep sessions | N | |
| 熱點檔案 | top 3 | |

## 貢獻者分析
[Per-author 統計表格]

## Commit 類型分布
[依 feat/fix/refactor/test/chore 百分比]

## 時間模式
[高峰/低谷時段 + session 分析]

## 熱點檔案 (Top 10)
[被修改最多的檔案 — 可能需要重構的信號]

## 本週亮點 (Top 3)
1. [最重要的 feature/改善]
2. [次要亮點]
3. [第三亮點]

## 改善建議 (Top 3)
1. [具體可行動的建議]
2. [建議]
3. [建議]

## 下週習慣建議
1. [基於數據的習慣建議]
2. [建議]
3. [建議]
```

## JSON 持久化

報告儲存至 `.claude/retros/YYYY-MM-DD.json`：
```json
{
  "date": "2026-03-23",
  "window_days": 7,
  "metrics": {
    "commits": 0,
    "loc_added": 0,
    "loc_deleted": 0,
    "test_ratio": 0,
    "active_days": 0,
    "deep_sessions": 0
  },
  "authors": {
    "dev-a": { "commits": 0, "loc_added": 0, "loc_deleted": 0, "primary_type": "feat" }
  },
  "sessions": {
    "deep": 0,
    "medium": 0,
    "micro": 0
  },
  "hotspots": [],
  "commit_types": {},
  "version_range": null
}
```

若有前次報告，自動計算趨勢差異。

## 語氣

鼓勵但坦誠。讚美必須具體、基於實際貢獻。改善建議以投資（而非批評）方式表達。
