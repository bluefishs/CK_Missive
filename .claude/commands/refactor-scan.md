---
description: "重構掃描 — 超閾值檔案掃描 + 拆分建議"
---

# 重構掃描 (Refactor Scan)

> **版本**: 1.0.0 | **用途**: 掃描超閾值檔案並建議拆分策略

自動掃描前後端程式碼，找出接近或超過行數閾值的檔案。

## 引數

- `quick` — 僅行數掃描 (預設)
- `full` — 行數 + 結構分析 + 拆分建議
- `--threshold N` — 覆蓋預設閾值

## 預設閾值

| 類別 | 閾值 | 來源 |
|------|------|------|
| 前端頁面 (.tsx) | 480L | 500L 規範，留 20L 餘裕 |
| 前端元件 (.tsx) | 480L | 同上 |
| 前端 Hooks (.ts) | 480L | 同上 |
| 後端服務 (.py) | 580L | 600L 規範，留 20L 餘裕 |
| 後端 AI 服務 (.py) | 580L | 同上 |

## 執行項目

### 1. 前端掃描

```bash
echo "=== 前端頁面 >480L ==="
find frontend/src/pages -name "*.tsx" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 480 && !/total/ {printf "  ⚠️ %4dL  %s\n", $1, $2}'

echo "=== 前端元件 >480L ==="
find frontend/src/components -name "*.tsx" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 480 && !/total/ {printf "  ⚠️ %4dL  %s\n", $1, $2}'

echo "=== 前端 Hooks >480L ==="
find frontend/src/hooks -name "*.ts" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 480 && !/total/ {printf "  ⚠️ %4dL  %s\n", $1, $2}'
```

### 2. 後端掃描

```bash
echo "=== 後端根服務 >580L ==="
find backend/app/services -maxdepth 1 -name "*.py" -exec wc -l {} + | sort -rn | awk '$1 > 580 && !/total/ {printf "  ⚠️ %4dL  %s\n", $1, $2}'

echo "=== 後端 AI 服務 >580L ==="
find backend/app/services/ai -name "*.py" -exec wc -l {} + | sort -rn | awk '$1 > 580 && !/total/ {printf "  ⚠️ %4dL  %s\n", $1, $2}'
```

### 3. 接近閾值警告 (80% 門檻)

```bash
echo "=== 前端 >400L (觀察區) ==="
find frontend/src/pages frontend/src/components -name "*.tsx" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 400 && $1 <= 480 && !/total/ {printf "  👀 %4dL  %s\n", $1, $2}' | head -15

echo "=== 後端 >480L (觀察區) ==="
find backend/app/services -name "*.py" -exec wc -l {} + | sort -rn | awk '$1 > 480 && $1 <= 580 && !/total/ {printf "  👀 %4dL  %s\n", $1, $2}' | head -10
```

### 4. 結構分析 (full 模式)

針對每個超閾值檔案：
1. 計算 import 行數佔比
2. 辨識主要區段 (state/handlers/render)
3. 找出最大連續函數區塊
4. 提出拆分建議 (提取 hook / 子元件 / 工具函數)

## 輸出格式

```
REFACTOR-SCAN REPORT
====================

超閾值: N 個 (⚠️)
觀察區: M 個 (👀)
合規: K 個 (✅)

| 類別 | 檔案 | 行數 | 建議 |
|------|------|------|------|
| ⚠️ Page | UnifiedFormDemoPage.tsx | 499L | 提取表單邏輯到 hook |
| 👀 Page | CertificationFormPage.tsx | 469L | 監控，暫不需拆分 |
```

## 相關指令

- `/health-dashboard` — 系統健康報告
- `/code-review` — 結構化審查
- `/verify` — 綜合驗證
