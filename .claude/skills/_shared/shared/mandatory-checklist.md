---
name: 跨專案強制性開發規範檢查清單
description: 所有開發任務啟動前必須檢視的強制性規範清單
version: 1.0.0
category: shared
triggers:
  - /mandatory-checklist
  - 開發規範
  - checklist
  - 強制檢查
updated: 2026-01-28
---

# 跨專案強制性開發規範檢查清單

> **版本**: 1.0.0
> **建立日期**: 2026-01-22
> **狀態**: 強制執行 - 所有開發任務啟動前必須檢視
> **來源**: 整合自 CK_Missive MANDATORY_CHECKLIST v1.8.0

---

## 重要聲明

**本檢查清單為強制性文件。任何開發任務開始前，必須先完成相關規範檢視。**

違反規範可能導致：

- 程式碼審查不通過
- 前後端資料不同步
- 系統運行異常
- 維護成本增加

---

## 一、開發任務類型判斷

根據任務類型，選擇對應的檢查清單：

| 任務類型              | 適用專案         | 對應檢查清單                   |
| --------------------- | ---------------- | ------------------------------ |
| **前端組件/頁面開發** | React 專案       | [清單 A](#清單-a前端開發)      |
| **後端 API 開發**     | Python/Node 專案 | [清單 B](#清單-b後端-api-開發) |
| **型別定義變更**      | 全部             | [清單 C](#清單-c型別管理ssot)  |
| **Bug 修復**          | 全部             | [清單 D](#清單-d-bug-修復)     |
| **效能敏感操作**      | 全部             | [清單 E](#清單-e效能檢查)      |
| **安全相關變更**      | 全部             | [清單 F](#清單-f安全檢查)      |
| **資料庫變更**        | 後端專案         | [清單 G](#清單-g資料庫變更)    |
| **跨專案同步**        | Skills/Agents    | [清單 H](#清單-h-skills-同步)  |

---

## 清單 A：前端開發

### 必讀技能

- [ ] `@react-ui-patterns` - React 與 Ant Design 最佳實踐
- [ ] `@code-standards` - 程式碼標準（ESLint、Hook 順序、Import 排序）
- [ ] `@testing-patterns` - 測試模式（組件測試、Hook 測試）

### 開發前檢查

- [ ] 確認組件職責單一（Single Responsibility）
- [ ] 確認 Hook 順序正確（useState → useEffect → useCallback → useMemo）
- [ ] 確認使用統一的錯誤處理模式

### 開發後檢查

- [ ] TypeScript 編譯通過：`npx tsc --noEmit`
- [ ] ESLint 檢查通過：`npm run lint`
- [ ] 組件有對應的測試用例

### 禁止事項

- [ ] 禁止在組件內直接使用 `fetch`，使用統一的 API 服務
- [ ] 禁止重複定義已存在的型別
- [ ] 禁止在 useEffect 中直接修改非相關 state

---

## 清單 B：後端 API 開發

### 必讀技能

- [ ] `@api-development` - API 開發規範
- [ ] `@postgres-patterns` / `@express-api-patterns` - 後端模式
- [ ] `@security-patterns` - 安全模式（認證、授權、輸入驗證）

### 開發前檢查

- [ ] 確認使用統一回應結構（ServiceResponse 模式）
- [ ] 確認使用 POST 方法進行資料修改操作
- [ ] 確認輸入使用 Schema 驗證（Pydantic / Zod）

### 開發後檢查

- [ ] 語法檢查通過
- [ ] API 端點有對應文件更新
- [ ] 前端 API 服務同步更新

### 禁止事項

- [ ] 禁止在 API 中直接操作資料庫而不經過服務層
- [ ] 禁止返回未經序列化的資料庫對象
- [ ] 禁止在回應中暴露敏感資訊

---

## 清單 C：型別管理 (SSOT)

### 核心原則：Single Source of Truth

**後端優先架構：**

```
Database Models
    ↓
Backend Schemas (Pydantic / Zod)
    ↓ (OpenAPI 生成)
Frontend Types
```

### 開發前檢查

- [ ] 確認型別來源正確（後端 Schema → 前端型別）
- [ ] 確認不重複定義已存在的型別
- [ ] 確認使用 `import type` 語法導入型別

### 開發後檢查

- [ ] 確認前後端型別一致
- [ ] 確認 API 回應符合型別定義
- [ ] 確認無任何 `any` 型別洩漏

### 禁止事項

- [ ] 禁止在前端重新定義後端已有的型別
- [ ] 禁止使用 `as any` 繞過型別檢查
- [ ] 禁止型別斷言繞過編譯錯誤

---

## 清單 D：Bug 修復

### 必讀技能

- [ ] `@systematic-debugging` - 系統化除錯
- [ ] `@test-driven-development` - TDD 修復流程

### 修復流程（強制）

1. [ ] **先寫失敗測試** - 重現 Bug 的測試用例
2. [ ] **確認測試失敗** - 執行測試，確認 FAIL
3. [ ] **最小修復** - 只修改導致 Bug 的程式碼
4. [ ] **確認測試通過** - 執行測試，確認 PASS
5. [ ] **回歸測試** - 確認其他測試不受影響

### 禁止事項

- [ ] 禁止在沒有測試的情況下修復 Bug
- [ ] 禁止修復 Bug 時順便重構
- [ ] 禁止修復 Bug 時新增功能

---

## 清單 E：效能檢查

### 必讀技能

- [ ] `@code-standards` - 效能相關標準

### 前端效能檢查

- [ ] 大型列表使用虛擬化（react-window）
- [ ] 圖片使用懶加載
- [ ] 避免不必要的重渲染（React.memo、useMemo）
- [ ] Bundle 大小在合理範圍

### 後端效能檢查

- [ ] 資料庫查詢有適當索引
- [ ] 避免 N+1 查詢問題
- [ ] 大量資料使用分頁
- [ ] 耗時操作使用異步處理

---

## 清單 F：安全檢查

### 必讀技能

- [ ] `@security-patterns` - 安全模式
- [ ] `@security-audit` - 安全審計
- [ ] `@dangerous-operations-policy` - 危險操作策略

### 輸入驗證

- [ ] 所有用戶輸入經過驗證
- [ ] SQL 查詢使用參數化
- [ ] 檔案上傳驗證類型與大小

### 輸出處理

- [ ] HTML 輸出經過 XSS 防護
- [ ] 敏感資料不寫入日誌
- [ ] 錯誤訊息不暴露系統資訊

### 認證授權

- [ ] API 端點有適當的認證保護
- [ ] 權限檢查在服務層執行
- [ ] Token 有適當的過期機制

---

## 清單 G：資料庫變更

### 必讀技能

- [ ] `@postgres-patterns` - 資料庫模式
- [ ] `@dangerous-operations-policy` - 危險操作策略

### 開發前檢查

- [ ] 確認有完整的資料備份
- [ ] 確認 Migration 腳本正確
- [ ] 確認變更不影響現有資料

### 開發後檢查

- [ ] Migration 在測試環境執行成功
- [ ] 相關 ORM 模型已更新
- [ ] 相關 API Schema 已更新

### 禁止事項

- [ ] **絕對禁止** 在生產環境直接執行 DROP/TRUNCATE
- [ ] **絕對禁止** 沒有備份的情況下修改結構
- [ ] **絕對禁止** 未經測試直接上線

---

## 清單 H：Skills 同步

### 必讀技能

- [ ] `@skills-management` - Skills 管理規範
- [ ] `GOVERNANCE.md` - 治理規範

### 同步前檢查

- [ ] 確認變更不影響其他專案
- [ ] 確認無專案特定資訊洩漏
- [ ] 確認相似度檢查通過

### 同步流程

1. [ ] 更新中央 Skills 庫（`GeminiCli/.claude/skills/`）
2. [ ] 執行同步腳本（`sync-skills.ps1`）
3. [ ] 驗證各專案同步狀態
4. [ ] 更新 `skills-index.json`

### 提取到共用層的條件

- [ ] 至少 2 個專案可受益
- [ ] 無專案特定硬編碼
- [ ] 已通過相似度檢查

---

## 二、Superpowers 工作流（推薦）

### 標準開發流程

```
1. brainstorming        → 需求精煉與設計
2. using-git-worktrees  → 建立隔離工作區
3. writing-plans        → 撰寫詳細計畫
4. executing-plans      → 執行計畫（含檢查點）
5. test-driven-development → TDD 實作
6. requesting-code-review  → 程式碼審查
7. finishing-a-development-branch → 收尾與合併
```

### 除錯流程

```
1. systematic-debugging → 4 階段根因追蹤
2. test-driven-development → 測試驗證修復
3. verification-before-completion → 完成前驗證
```

---

## 三、自動化驗證工具

### 執行方式

```powershell
# 驗證 Skills 架構
powershell -ExecutionPolicy Bypass -File .claude\scripts\validate-skills.ps1

# 同步所有專案
powershell -ExecutionPolicy Bypass -File .claude\sync-skills.ps1

# TypeScript 檢查
npx tsc --noEmit

# Python 檢查
python -m py_compile *.py
```

---

## 四、違規處理

| 違規等級 | 說明                   | 處理方式           |
| -------- | ---------------------- | ------------------ |
| **嚴重** | 安全漏洞、資料遺失風險 | 立即回滾，事後檢討 |
| **中等** | 型別不一致、測試缺失   | 程式碼審查不通過   |
| **輕微** | 程式碼風格、文件缺失   | 補充後通過         |

---

_版本：1.0.0 | 最後更新：2026-01-22 | 整合自乾坤測繪開發規範_
