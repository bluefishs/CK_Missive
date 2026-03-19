# QA Smart — Diff-Aware 智慧測試

> 靈感來源: [gstack/qa](https://github.com/garrytan/gstack) — 系統化 QA 測試

自動分析 git diff 識別受影響的路由和元件，針對性執行測試。

## 使用方式

```
/qa-smart              # diff-aware 模式（自動偵測變更）
/qa-smart full         # 完整測試（所有頁面）
/qa-smart quick        # 快速 smoke test（30 秒）
/qa-smart regression   # 與基線比較
```

## 模式說明

### Diff-Aware 模式（預設）

1. **分析變更**：
   ```bash
   git diff --name-only origin/main
   ```

2. **識別受影響路由**（載入 `.claude/qa-route-map.json`）：
   - 比對變更檔案與 `trigger_patterns` 映射
   - 若命中 `global_triggers`，標記為全量測試
   - 變更的頁面元件 → 直接受影響
   - 變更的共用元件 → 查找所有引用它的頁面
   - 變更的 API 層 → 對應的前端頁面
   - 變更的 hooks → 使用該 hook 的所有頁面
   - 自動選擇對應的 E2E spec (`e2e/*.spec.ts`)

3. **生成測試計畫**：
   ```markdown
   ## 受影響路由分析
   | 變更檔案 | 影響類型 | 受影響頁面 | 建議測試 |
   |---------|---------|-----------|---------|
   | components/ai/RAGChatPanel.tsx | 直接 | KnowledgeGraphPage | E2E + 單元 |
   | hooks/business/useDocuments.ts | 間接 | DocumentPage, DocumentDetailPage | 單元 |
   ```

4. **執行測試**：
   - 單元測試：`npx vitest run [受影響的測試檔案]`
   - TypeScript：`npx tsc --noEmit`
   - E2E（若有對應 spec）：`npx playwright test [受影響的 spec]`

### Quick 模式（30 秒 smoke test）

1. TypeScript 編譯檢查
2. 核心頁面 import 驗證
3. API client 健康檢查

### Full 模式

1. 完整 TypeScript 檢查
2. 所有單元測試
3. 所有 E2E 測試
4. Bundle size 檢查

### Regression 模式

1. 載入基線（`.claude/qa-baseline.json`）
2. 執行完整測試
3. 比較差異：新增失敗 / 修復的測試 / 新增測試

## 8 維度健康度評分

| 維度 | 權重 | 扣分規則 |
|------|------|---------|
| TypeScript | 20% | 每個 error -5 分 |
| 單元測試 | 20% | 每個 fail -3 分 |
| E2E 測試 | 15% | 每個 fail -5 分 |
| 安全性 | 15% | 每個 CRITICAL -20 分 |
| 效能 | 10% | Bundle 超標 -10 分 |
| 可及性 | 5% | 每個 a11y issue -2 分 |
| 程式碼品質 | 10% | ESLint errors 每個 -1 分 |
| 覆蓋率 | 5% | 低於 40% 時 -10 分 |

**評分標準**:
- 90-100: 優秀 (可發布)
- 70-89: 良好 (建議修復)
- 50-69: 需改善 (不建議發布)
- <50: 需修復 (禁止發布)

## 輸出格式

```markdown
# QA Report — YYYY-MM-DD HH:mm

## 模式: [diff-aware/full/quick/regression]
## 健康度: [分數]/100 [優秀/良好/需改善/需修復]

## 受影響路由 (diff-aware)
[路由分析表格]

## 測試結果
| 類型 | 通過 | 失敗 | 跳過 |
|------|------|------|------|
| TypeScript | ✅/❌ | - | - |
| 單元測試 | N | N | N |
| E2E 測試 | N | N | N |

## 各維度評分
[8 維度評分明細]

## 失敗詳情
[每個失敗的測試案例]

## 建議
[基於結果的具體改善建議]
```

## 基線儲存

```bash
# 儲存當前結果為基線
# 自動儲存至 .claude/qa-baseline.json
```
