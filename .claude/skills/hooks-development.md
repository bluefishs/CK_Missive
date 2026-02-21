---
name: hooks-development
description: Claude Code Hooks 開發指南
keywords: hook, hooks, 鉤子, automation, 自動化
---

# Claude Code Hooks 開發指南

## Hook 事件類型

| 事件 | 觸發時機 | matcher 匹配 | 可阻擋 |
|------|---------|-------------|--------|
| `SessionStart` | 對話開始/恢復 | `startup`, `resume`, `clear`, `compact` | 否 |
| `UserPromptSubmit` | Claude 處理前 | 無 matcher | 是 |
| `PreToolUse` | 工具執行前 | tool name: `Bash`, `Edit\|Write`, `mcp__.*` | 是 |
| `PostToolUse` | 工具成功後 | tool name | 是 |
| `PostToolUseFailure` | 工具失敗後 | tool name | 是 |
| `PermissionRequest` | 權限對話框 | tool name | 是 (allow/deny) |
| `Stop` | Claude 回應結束 | 無 matcher | 是 |
| `Notification` | 系統通知 | notification type | 否 |

## 三層巢狀結構

```json
{
  "hooks": {
    "事件名": [          // Level 1: 事件
      {
        "matcher": "regex",  // Level 2: 匹配器 (regex, 匹配 tool_name)
        "hooks": [           // Level 3: 處理器陣列
          {
            "type": "command",   // command | prompt | agent
            "command": "...",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

## Hook Type 說明

| Type | 用途 | 特有欄位 |
|------|------|---------|
| `command` | 執行 shell 命令 | `command`, `async` |
| `prompt` | 送給 Claude 評估 (快速) | `prompt`, `model` |
| `agent` | 產生子代理 (有工具存取) | `prompt` |

## Stdin JSON 協議

所有 hook 透過 stdin 接收 JSON：

```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.ts",
    "old_string": "...",
    "new_string": "..."
  },
  "cwd": "/project/root"
}
```

## 回應方式

### Exit Codes
- `0` → 成功，解析 stdout JSON
- `2` → 阻擋操作，stderr 訊息傳給 Claude
- 其他 → 非阻擋錯誤

### Stdout JSON 回應

```json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "提供給 Claude 的補充資訊"
  }
}
```

### PermissionRequest 決策

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow"
    }
  }
}
```

## PowerShell Hook Template

```powershell
# Hook Template (v2.0.0)
$ErrorActionPreference = "SilentlyContinue"

# 讀取 stdin JSON
$rawInput = ""
try {
    while ($line = [Console]::In.ReadLine()) {
        $rawInput += $line
    }
} catch { }

if (-not $rawInput) { exit 0 }

$hookInput = $rawInput | ConvertFrom-Json
$filePath = $hookInput.tool_input.file_path
$toolName = $hookInput.tool_name

# 根據 file_path 副檔名過濾
if ($filePath -and $filePath -notmatch '\.py$') {
    exit 0  # 不處理
}

# 執行檢查...
# exit 0 = 通過
# exit 2 + stderr = 阻擋
```

## 測試 Hook

```powershell
# 模擬 PostToolUse 輸入
$testInput = '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"frontend/src/App.tsx"}}'
echo $testInput | powershell -File .claude/hooks/typescript-check.ps1
```

## 環境變數

| 變數 | 說明 |
|------|------|
| `$CLAUDE_PROJECT_DIR` | 專案根目錄 |
| `$CLAUDE_ENV_FILE` | SessionStart 專用: 持久化環境變數檔案 |

## 注意事項

1. `matcher` 是 **regex**，匹配 `tool_name`，不是檔案路徑
2. 檔案類型過濾需在 script 內部做（從 `tool_input.file_path` 判斷）
3. `async: true` 的 hook 不能阻擋操作
4. Stop hook 的 agent 若觸發修改可能導致無限迴圈 — 保持唯讀
5. Windows PowerShell 需加 `-ExecutionPolicy Bypass`
