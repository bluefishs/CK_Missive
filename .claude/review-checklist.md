# Code Review Checklist — CK_Missive 專案

> 本檔案供 `/code-review` 指令載入，定義專案特有的審查規則。
> 可根據需求新增/修改規則，每次 `/code-review` 執行時自動載入。

---

## Critical 規則（必須通過）

### 安全性
- [ ] 無硬編碼密鑰 (API keys, passwords, tokens)
- [ ] SQL 查詢使用參數化 (SQLAlchemy ORM 或 text() bind params)
- [ ] 前端無直接 innerHTML / dangerouslySetInnerHTML 使用
- [ ] API 端點有認證保護 (require_auth / require_admin)
- [ ] LLM 輸出不直接用於 SQL/HTML/shell 命令
- [ ] .env 內容不暴露於前端 bundle

### 資料安全
- [ ] DELETE 操作有確認機制
- [ ] 批量操作有數量限制
- [ ] 敏感欄位 (password, token) 不出現在 API 回應

---

## High 規則（強烈建議修復）

### 架構合規
- [ ] API 端點使用 POST 方法 (POST-only 安全政策)
- [ ] API 路徑使用端點常數 (`ENDPOINTS.XXX`，非硬編碼字串)
- [ ] 前端資料取得使用 `useQuery` / `useMutation` (非 useEffect + API)
- [ ] 型別定義在 `types/` 目錄 (SSOT 原則)
- [ ] 新增路由同步三處: `router/types.ts` + `AppRouter.tsx` + `init_navigation_data.py`

### 程式碼品質
- [ ] 函數長度 ≤ 50 行
- [ ] 檔案長度 ≤ 800 行
- [ ] 巢狀深度 ≤ 4 層
- [ ] 錯誤處理完整 (try/catch, error boundary)
- [ ] `link_id` 使用嚴格檢查 (非 `?? id` 回退)

---

## Medium 規則（建議修復）

### 清潔度
- [ ] 無 `console.log` 殘留
- [ ] 無未使用的 import
- [ ] TODO/FIXME 有對應 issue 或時間限制
- [ ] Magic numbers 提取為命名常數

### 測試
- [ ] 新增程式碼有對應測試
- [ ] 測試使用 mock 而非真實 API 呼叫
- [ ] 測試覆蓋 happy path + error path

---

## Low 規則（可選修復）

- [ ] ARIA 標籤完整 (a11y)
- [ ] 變數命名語意清晰
- [ ] 註解適量（解釋 why 而非 what）
- [ ] import 排序一致

---

## 抑制規則

> 以下情境為已知可接受的例外，審查時不需標記：

- `as never` 用於 react-force-graph 等庫邊界橋接
- `eslint-disable-next-line` 有對應註解說明原因
- `@ts-expect-error` 用於已知的第三方型別問題
- `noUnusedLocals: false` 在 tsconfig.json (legacy cleanup pending)
