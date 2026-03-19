# Ship — 統一發布工作流

> 靈感來源: [gstack/ship](https://github.com/garrytan/gstack) — 非互動式自動化發布管線

自動化完成從 feature branch 到 PR 的完整發布流程。

## 使用方式

```
/ship              # 完整發布流程
/ship --dry-run    # 僅檢查，不推送
/ship --no-test    # 跳過測試（僅限緊急修復）
```

## 工作流程（按順序執行）

### Phase 1: Pre-flight 檢查

1. **分支驗證** — 確認在 feature branch（非 main/master），否則中止
2. **工作區狀態** — 捕獲所有未提交變更（包含 untracked）
3. **上游同步** — `git fetch origin main`

### Phase 2: Merge & Test

4. **合併 main** — `git merge origin/main`，若有衝突則中止並報告
5. **前端驗證**（並行）：
   - `cd frontend && npx tsc --noEmit` — TypeScript 編譯
   - `cd frontend && npx vitest run` — 單元測試
6. **後端驗證**（並行）：
   - `cd backend && python -m py_compile main.py` — Python 語法
   - `cd backend && python -m pytest tests/unit/ -x --timeout=60` — 單元測試
7. **測試失敗則中止**，報告失敗原因與建議修復

### Phase 3: Pre-Landing Review

8. **結構化審查** — 對 `git diff origin/main` 執行兩階段檢查：
   - **Critical pass**: 安全漏洞、硬編碼密鑰、SQL 注入、缺少認證檢查
   - **Informational pass**: 程式碼品質、TODO/FIXME、console.log、型別一致性

9. **Critical findings 處理**：
   - 每個 Critical issue 使用 AskUserQuestion 獨立詢問
   - 選項: A) 立即修復 B) 記錄到 TODOS.md C) 標記為 false-positive
   - Non-critical findings 記錄到 PR body

### Phase 4: Commit & Push

10. **智慧 commit 分組** — 按邏輯分組（確保每個 commit 可獨立 bisect）：
    - 基礎設施/配置 → 模型/Schema → 服務層 → API 層 → 前端元件 → 測試 → 文件

11. **Commit 訊息格式**：
    ```
    <type>: <description>
    ```
    type = feat/fix/refactor/docs/test/chore/perf/ci

12. **推送** — `git push -u origin <branch>`

### Phase 5: PR 建立

13. **PR 生成** — 使用 `gh pr create`：
    ```
    ## Summary
    - 從 commit history 自動生成摘要 (1-3 bullet points)

    ## Changes
    - 按類別列出所有變更

    ## Test Results
    - TypeScript: ✅/❌
    - Frontend tests: X passed / Y failed
    - Backend tests: X passed / Y failed

    ## Review Findings
    - Critical: N items (全部已解決)
    - Informational: N items

    ## Test Plan
    - [ ] 驗證項目清單
    ```

14. **輸出 PR URL** 作為最終確認

## 中止條件

- 在 main/master 分支
- Merge 衝突
- 測試失敗（除非 --no-test）
- 未解決的 Critical findings

## 不做的事

- 不自動合併 PR
- 不修改版本號（本專案使用 CHANGELOG 管理）
- 不觸碰 CI/CD 配置
