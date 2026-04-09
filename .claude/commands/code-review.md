---
description: "結構化程式碼審查 — Scope Drift 偵測 + Fix-First 策略"
---

# Code Review — 結構化審查 + Scope Drift 偵測 + Fix-First

> 靈感來源: [gstack/review](https://github.com/garrytan/gstack) — Pre-landing PR review
> **版本**: 2.0.0 (v1→v2: scope drift + Fix-First 模式)

對未提交或 branch 變更執行結構化審查，自動偵測 scope drift 並分類修復建議。

## 使用方式

```
/code-review            # 審查未提交變更 (git diff HEAD)
/code-review branch     # 審查 branch 與 main 的差異 (git diff origin/main)
/code-review --plan     # 搭配計畫意圖比對 scope drift（讀取最近 TodoWrite 或 commit messages）
```

## Phase 0: 準備 + 意圖收集

1. **確認 diff 範圍**：
   - 無參數: `git diff --name-only HEAD`
   - `branch`: `git diff --name-only origin/main`
2. **若無變更，中止並提示**
3. **列出所有變更檔案**，按前端/後端/配置分類
4. **收集意圖**（用於 scope drift 偵測）：
   - 讀取 branch 名稱推斷意圖（`feat/erp-expenses` → 費用報銷功能）
   - 讀取 commit messages 提取主題
   - 若有 `--plan` 參數，讀取最近的 TodoWrite 任務清單

## Phase 1: Scope Drift 偵測

**比對計畫意圖 vs 實際變更，識別無意的 scope 膨脹。**

分析每個變更檔案是否屬於計畫意圖範圍：

| 分類 | 定義 | 動作 |
|------|------|------|
| **On-scope** | 直接相關的變更 | 正常審查 |
| **Adjacent** | 相鄰但合理的變更（如更新 import） | 標記但不阻擋 |
| **Drift** | 與意圖無關的變更 | 警告，建議拆分 |

**輸出**：
```markdown
## Scope Drift 分析

Branch: feat/erp-expenses
意圖: ERP 費用報銷功能

| 檔案 | 分類 | 說明 |
|------|------|------|
| backend/app/services/expense_invoice_service.py | On-scope | 費用服務 |
| frontend/src/pages/ERPExpenseListPage.tsx | On-scope | 費用頁面 |
| frontend/src/components/common/PageLoading.tsx | Adjacent | 共用元件微調 |
| backend/app/services/ai/agent_tools.py | **Drift** | 非費用相關修改 |

建議: 1 個 drift 檔案應拆分為獨立 commit 或獨立 PR
```

## Phase 2: Critical Pass（安全與正確性）

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

## Phase 3: Fix-First 分類審查（品質與規範）

**核心改進**: 將每個發現分類為 AUTO-FIX 或 ASK，減少審查摩擦。

### AUTO-FIX（自動修復，不詢問用戶）

以下類型的問題**直接修復**，在報告中記錄但不阻擋：

| 類型 | 說明 | 自動修復動作 |
|------|------|-------------|
| 死碼 | 未使用的 import | 移除 |
| console.log | 遺留除錯輸出 | 移除 |
| 多餘空行 | 連續空行 > 2 | 壓縮為 1 |
| 尾隨空白 | 行末空格 | 移除 |
| 型別導入格式 | `import type` | 統一格式 |

### ASK（批次詢問用戶）

以下需要判斷的問題**彙整為一次性提問**：

| 類型 | 嚴重度 | 說明 |
|------|--------|------|
| 函數 > 50 行 | HIGH | 建議拆分 |
| 檔案 > 800 行 | HIGH | 建議模組化 |
| 巢狀深度 > 4 層 | HIGH | Early return |
| 缺少錯誤處理 | HIGH | try/catch, error boundary |
| TODO/FIXME | MEDIUM | 記錄但不阻擋 |
| 缺少測試 | MEDIUM | 新增程式碼無對應測試 |
| 型別不一致 | MEDIUM | 違反 SSOT（types/ 是唯一來源） |
| Magic numbers | LOW | 提取為常數 |
| a11y 問題 | LOW | 缺少 ARIA 標籤 |

**批次提問格式**：
```
以下 N 個發現需要您的判斷：

1. [HIGH] backend/services/x.py:45 — 函數 process_data 有 62 行，建議拆分
   → A) 修復  B) 跳過  C) 記錄到 TODO

2. [MEDIUM] frontend/pages/Y.tsx:120 — 新增元件無對應測試
   → A) 補測試  B) 跳過

請回覆選擇（如: 1A 2B）
```

## Phase 4: 專案規範檢查

針對 CK_Missive 專案特有規範：

- [ ] API 端點使用 POST（安全政策）
- [ ] API 路徑使用端點常數（非硬編碼）
- [ ] 前端資料取得使用 useQuery/useMutation（非 useEffect+API）
- [ ] 型別定義在 types/ 目錄（SSOT）
- [ ] 新增路由是否同步三處位置（types.ts + AppRouter.tsx + init_navigation_data.py）
- [ ] link_id 嚴格檢查（非 `?? id` 回退）
- [ ] 後端 Schema 在 schemas/ 目錄（非 endpoints 內本地 BaseModel）
- [ ] 費用/帳本金額使用 Decimal（非 float）

## Phase 5: 報告輸出

```markdown
# Code Review Report — YYYY-MM-DD HH:mm

## 摘要
- 檔案數: N
- Scope: N on-scope / N adjacent / N drift
- Critical: N (已解決/未解決)
- Auto-fixed: N items
- Ask (待決): N items

## Scope Drift 分析
[Phase 1 結果 — 若有 drift 則顯示警告]

## Critical Findings
[已在 Phase 2 逐一處理]

## Auto-Fixed Items
[表格：檔案 | 行號 | 類型 | 修復動作]

## Pending Decisions
[Phase 3 ASK items — 用戶已回覆的決定]

## 規範合規
[專案規範檢查結果]

## 結論
✅ 可安全提交 / ⚠️ 建議先修復 HIGH issues / ❌ 有未解決 CRITICAL
```
