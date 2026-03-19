# Hooks 自動化配置

## 自動觸發 Hooks

### PreToolUse (工具執行前)

| Hook | Matcher | 說明 | 腳本 |
|------|---------|------|------|
| validate-file-location | `Write\|Edit` | 確認檔案位置符合架構規範 | `.claude/hooks/validate-file-location.ps1` |

### PostToolUse (工具執行後)

| Hook | Matcher | 說明 | 腳本 |
|------|---------|------|------|
| typescript-check | `Edit\|Write` | TypeScript 編譯檢查 (.ts/.tsx) | `.claude/hooks/typescript-check.ps1` |
| python-lint | `Edit\|Write` | Python 語法檢查 (.py) | `.claude/hooks/python-lint.ps1` |
| api-serialization-check | `Edit\|Write` | API 序列化問題檢測 (.py, 僅 endpoints/) | `.claude/hooks/api-serialization-check.ps1` |
| performance-check | `Edit\|Write` | N+1 查詢與缺分頁檢測 (.py, 僅 services/endpoints/) | `.claude/hooks/performance-check.ps1` |
| migration-check | `Edit\|Write` | ORM 模型修改提醒建立 Alembic 遷移 (prompt 類型) | settings.json 內嵌 |

### SessionStart (對話開始)

| Hook | Matcher | 說明 | 腳本 |
|------|---------|------|------|
| session-start | `startup` | 自動載入專案上下文 (git/Docker/PM2) | `.claude/hooks/session-start.ps1` |

### PermissionRequest (權限請求)

| Hook | 說明 | 腳本 |
|------|------|------|
| auto-approve | 自動核准唯讀操作 (Read/Glob/Grep 等) | `.claude/hooks/auto-approve.ps1` |

### Stop (回應結束)

| Hook | Type | 說明 |
|------|------|------|
| quality-gate | agent | 自動驗證程式碼修改的品質 |

## Git Hooks (本地 CI)

| Hook | 說明 | 位置 |
|------|------|------|
| pre-commit | Skills 架構驗證 + TypeScript 編譯 + Python 語法 + 敏感檔案偵測 | `.git/hooks/pre-commit` |
| post-commit | 知識地圖增量更新 (`--if-stale`，背景執行) | `.git/hooks/post-commit` |
| post-checkout | 分支切換時自動同步 Skills | `.git/hooks/post-checkout` |
| post-merge | Pull/Merge 後自動同步 Skills | `.git/hooks/post-merge` |

**pre-commit 檢查項目**:
1. 禁止直接修改 `_shared/` 目錄
2. Skills 架構驗證（有 `.claude/skills/` 變更時）
3. 新專案層 Skills 警告
4. TypeScript 編譯 (`npx tsc --noEmit`，有 `.ts/.tsx` 變更時)
5. Python 語法 (`py_compile`，有 `.py` 變更時)
6. 敏感檔案偵測 (`.env`, `credentials.json`, `.pem`, `.key`)

## 手動執行 Hooks

| Hook | 說明 | 檔案 |
|------|------|------|
| route-sync-check | 檢查前後端路徑一致性 | `.claude/hooks/route-sync-check.ps1` |
| link-id-check | 檢查 link_id 使用模式 | `.claude/hooks/link-id-check.ps1` |
| link-id-validation | 後端 link_id 傳遞完整性驗證 | `.claude/hooks/link-id-validation.ps1` |

## Hook 開發協議

所有 hook scripts 透過 **stdin JSON** 接收輸入：

```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": { "file_path": "/path/to/file.ts", "old_string": "...", "new_string": "..." }
}
```

回應方式：
- **exit 0** + stdout JSON → 成功 (可附加 `additionalContext`)
- **exit 2** + stderr → 阻擋操作 (stderr 訊息傳給 Claude)
- **exit 其他** → 非阻擋錯誤
