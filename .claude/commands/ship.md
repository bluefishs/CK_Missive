---
description: "統一發布工作流 — 測試歸因 + review 就緒 + bisectable commits"
---

# Ship — 統一發布工作流

> 靈感來源: [gstack/ship](https://github.com/garrytan/gstack) — 非互動式自動化發布管線
> **版本**: 2.0.0 (v1→v2: 測試歸因 + review 就緒 + bisectable 強化)

自動化完成從 feature branch 到 PR 的完整發布流程。

## 使用方式

```
/ship              # 完整發布流程
/ship --dry-run    # 僅檢查，不推送
/ship --no-test    # 跳過測試（僅限緊急修復）
/ship --fast       # 快速模式（跳過 review，保留測試）
```

## 工作流程（按順序執行）

### Phase 1: Pre-flight 檢查

1. **分支驗證** — 確認在 feature branch（非 main/master），否則中止
2. **工作區狀態** — 捕獲所有未提交變更（包含 untracked）
3. **上游同步** — `git fetch origin main`
4. **Review 就緒檢查** — 驗證是否已完成必要前置工作：
   - 是否有 commit history（空 branch 警告）
   - 是否有對應的測試檔案變更（新功能必須有測試）
   - 是否有文件更新（大型功能必須有 CHANGELOG 或 ADR）

   ```markdown
   ## Review 就緒檢查
   - [x] 有 commit history (12 commits)
   - [x] 有測試變更 (tests/unit/test_expense.py)
   - [ ] 缺少文件更新 — 建議更新 CHANGELOG.md
   ```

### Phase 2: Merge & Test

5. **合併 main** — `git merge origin/main`，若有衝突則中止並報告
6. **前端驗證**（並行）：
   - `cd frontend && npx tsc --noEmit` — TypeScript 編譯
   - `cd frontend && npx vitest run` — 單元測試
7. **後端驗證**（並行）：
   - `cd backend && python -m py_compile main.py` — Python 語法
   - `cd backend && python -m pytest tests/unit/ -x --timeout=60` — 單元測試

### Phase 2.5: 測試失敗歸因 (Test Failure Blame)

**若有測試失敗**，執行歸因分析：

```bash
# 在 main 分支執行相同測試
git stash
git checkout main
# 執行失敗的測試
git checkout -
git stash pop
```

**分類**：

| 類型 | 定義 | 動作 |
|------|------|------|
| **In-branch** | 只在本 branch 失敗 | 必須修復才能繼續 |
| **Pre-existing** | main 也失敗 | 記錄但不阻擋，標記為 known issue |
| **Flaky** | 重跑後通過 | 記錄，標記為 flaky |

```markdown
## 測試失敗歸因
| 測試 | 類型 | 動作 |
|------|------|------|
| test_expense_create | In-branch | 🔴 必須修復 |
| test_flaky_timeout | Pre-existing | 🟡 已在 main 失敗 |
| test_race_condition | Flaky | 🟡 重跑通過 |
```

**In-branch 失敗 → 中止發布，報告失敗原因與建議修復**

### Phase 3: Pre-Landing Review

8. **結構化審查** — 對 `git diff origin/main` 執行兩階段檢查：
   - **Critical pass**: 安全漏洞、硬編碼密鑰、SQL 注入、缺少認證檢查
   - **Informational pass**: 程式碼品質、TODO/FIXME、console.log、型別一致性

9. **Critical findings 處理**（Fix-First 模式）：
   - **AUTO-FIX**: 死碼、console.log、多餘空白 → 自動修復
   - **ASK**: 安全漏洞、設計問題 → 批次詢問用戶
   - 選項: A) 立即修復 B) 記錄到 TODOS.md C) 標記為 false-positive

10. **Scope drift 快速檢查**：
    - 比對 branch 名稱/commit messages 與實際變更
    - 若有 > 3 個 drift 檔案，建議拆分 PR

### Phase 4: Commit & Push

11. **智慧 commit 分組** — 按邏輯分組（確保每個 commit 可獨立 bisect）：

    **分組規則**（越上面越先 commit）：
    ```
    1. 基礎設施/配置 (.env, docker-compose, package.json)
    2. 資料庫遷移 (alembic/)
    3. ORM 模型 (models/)
    4. Schema 定義 (schemas/)
    5. Repository 層 (repositories/)
    6. Service 層 (services/)
    7. API 層 (endpoints/)
    8. 前端型別 (types/)
    9. 前端 API 層 (api/)
    10. 前端 Hooks (hooks/)
    11. 前端元件/頁面 (components/, pages/)
    12. 測試 (tests/, *.test.*)
    13. 文件 (.md, docs/)
    ```

    **Bisectable 驗證**：每個 commit 分組後，確認：
    - 不會引入編譯錯誤（後面的 commit 不依賴前面未 commit 的程式碼）
    - 依賴關係正確（先 model → 後 service → 再 endpoint）

12. **Commit 訊息格式**：
    ```
    <type>: <description>
    ```
    type = feat/fix/refactor/docs/test/chore/perf/ci

13. **推送** — `git push -u origin <branch>`

### Phase 5: PR 建立

14. **PR 生成** — 使用 `gh pr create`：
    ```
    ## Summary
    - 從 commit history 自動生成摘要 (1-3 bullet points)

    ## Changes
    - 按類別列出所有變更（依 Phase 4 分組）

    ## Test Results
    - TypeScript: ✅/❌
    - Frontend tests: X passed / Y failed
    - Backend tests: X passed / Y failed
    - Pre-existing failures: N (not blocking)
    - Flaky tests: N (noted)

    ## Review Readiness
    - Tests: ✅/❌
    - Docs: ✅/❌ (if applicable)
    - Scope: Clean / N drift files noted

    ## Review Findings
    - Critical: N items (全部已解決)
    - Auto-fixed: N items
    - Informational: N items

    ## Test Plan
    - [ ] 驗證項目清單
    ```

15. **輸出 PR URL** 作為最終確認

## 中止條件

- 在 main/master 分支
- Merge 衝突
- In-branch 測試失敗（除非 --no-test）
- 未解決的 Critical findings

## 不做的事

- 不自動合併 PR
- 不修改版本號（本專案使用 CHANGELOG 管理）
- 不觸碰 CI/CD 配置
- 不將 pre-existing 測試失敗歸咎於當前 branch
