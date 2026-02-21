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

## 手動執行 Hooks

| Hook | 說明 | 檔案 |
|------|------|------|
| route-sync-check | 檢查前後端路徑一致性 | `.claude/hooks/route-sync-check.ps1` |
| api-serialization-check | 檢查 API 序列化問題 | `.claude/hooks/api-serialization-check.ps1` |
| link-id-check | 檢查 link_id 使用模式 | `.claude/hooks/link-id-check.ps1` |
| performance-check | 效能問題檢測 (N+1, 未分頁查詢) | `.claude/hooks/performance-check.ps1` |

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
