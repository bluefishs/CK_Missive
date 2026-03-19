# Code Review — 兩階段結構化審查

> 靈感來源: [gstack/review](https://github.com/garrytan/gstack) — Pre-landing PR review

對未提交或 branch 變更執行結構化兩階段審查。

## 使用方式

```
/code-review            # 審查未提交變更 (git diff HEAD)
/code-review branch     # 審查 branch 與 main 的差異 (git diff origin/main)
```

## Phase 0: 準備

1. **確認 diff 範圍**：
   - 無參數: `git diff --name-only HEAD`
   - `branch`: `git diff --name-only origin/main`
2. **若無變更，中止並提示**
3. **列出所有變更檔案**，按前端/後端/配置分類

## Phase 1: Critical Pass（安全與正確性）

逐檔檢查，任何 CRITICAL 發現都必須個別處理：

| 檢查項 | 嚴重度 | 說明 |
|--------|--------|------|
| 硬編碼密鑰 | CRITICAL | API keys, passwords, tokens |
| SQL 注入 | CRITICAL | 未參數化的查詢 |
| XSS 漏洞 | CRITICAL | 未過濾的 HTML 輸出 |
| 缺少認證/授權 | CRITICAL | API 端點缺少 require_auth |
| LLM 輸出信任 | CRITICAL | 直接使用 LLM 回應而未驗證 |
| 資料刪除無確認 | CRITICAL | DELETE 操作缺少確認機制 |
| 環境變數洩漏 | CRITICAL | .env 內容暴露於前端 |

**每個 CRITICAL finding 獨立詢問用戶**：
- A) 立即修復
- B) 記錄到 TODOS.md（附帶風險說明）
- C) 標記為 false-positive（需說明原因）

## Phase 2: Informational Pass（品質與規範）

| 檢查項 | 嚴重度 | 說明 |
|--------|--------|------|
| 函數 > 50 行 | HIGH | 建議拆分 |
| 檔案 > 800 行 | HIGH | 建議模組化 |
| 巢狀深度 > 4 層 | HIGH | Early return |
| 缺少錯誤處理 | HIGH | try/catch, error boundary |
| console.log | MEDIUM | 清理除錯輸出 |
| TODO/FIXME | MEDIUM | 記錄但不阻擋 |
| 缺少測試 | MEDIUM | 新增程式碼無對應測試 |
| 型別不一致 | MEDIUM | 違反 SSOT（types/ 是唯一來源） |
| Magic numbers | LOW | 提取為常數 |
| 死碼 | LOW | 未使用的 import/函數 |
| a11y 問題 | LOW | 缺少 ARIA 標籤 |

## Phase 3: 專案規範檢查

針對 CK_Missive 專案特有規範：

- [ ] API 端點使用 POST（安全政策）
- [ ] API 路徑使用端點常數（非硬編碼）
- [ ] 前端資料取得使用 useQuery/useMutation（非 useEffect+API）
- [ ] 型別定義在 types/ 目錄（SSOT）
- [ ] 新增路由是否同步三處位置
- [ ] link_id 嚴格檢查（非 `?? id` 回退）

## Phase 4: 報告輸出

```markdown
# Code Review Report — YYYY-MM-DD HH:mm

## 摘要
- 檔案數: N
- Critical: N (已解決/未解決)
- High: N
- Medium: N
- Low: N

## Critical Findings
[已在 Phase 1 逐一處理]

## Informational Findings
[表格：檔案 | 行號 | 嚴重度 | 說明 | 建議修復]

## 規範合規
[專案規範檢查結果]

## 結論
✅ 可安全提交 / ⚠️ 建議先修復 HIGH issues / ❌ 有未解決 CRITICAL
```
