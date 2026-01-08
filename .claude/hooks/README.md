# Claude Code Hooks 配置

> **版本**: 1.0.0
> **用途**: 定義 Claude Code 自動化鉤子

---

## Hooks 類型

### 1. PreToolUse (工具執行前)
在 Claude 執行工具之前觸發，可用於：
- 驗證危險命令
- 檢查檔案位置合規性
- 注入額外上下文

### 2. PostToolUse (工具執行後)
在工具執行完成後觸發，可用於：
- 自動格式化程式碼
- 執行語法檢查
- 觸發測試

### 3. UserPromptSubmit (使用者提交提示時)
在使用者提交訊息時觸發，可用於：
- 注入專案上下文
- 提供相關文件路徑
- 自動載入 Skills

---

## 配置方式

### 方式 1: 在 settings.json 中配置 (推薦)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "script": ".claude/hooks/validate-bash-command.sh"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "file_pattern": "*.ts|*.tsx",
        "script": ".claude/hooks/typescript-check.sh"
      }
    ]
  }
}
```

### 方式 2: 獨立腳本檔案

將腳本放置於 `.claude/hooks/` 目錄。

---

## 本專案 Hooks

### validate-bash-command.sh
驗證 Bash 命令是否安全執行。

```bash
#!/bin/bash
# 檢查危險命令
DANGEROUS_COMMANDS=("rm -rf /" "DROP DATABASE" "format")

for cmd in "${DANGEROUS_COMMANDS[@]}"; do
  if [[ "$TOOL_INPUT" == *"$cmd"* ]]; then
    echo "BLOCKED: 偵測到危險命令: $cmd"
    exit 1
  fi
done

exit 0
```

### typescript-check.sh
TypeScript 編譯檢查。

```bash
#!/bin/bash
cd frontend
npx tsc --noEmit
exit $?
```

### python-lint.sh
Python 語法檢查。

```bash
#!/bin/bash
cd backend
python -m py_compile "$EDITED_FILE"
exit $?
```

---

## 使用範例

### 自動 TypeScript 檢查

當修改前端 TypeScript 檔案後，自動執行編譯檢查：

1. 配置 PostToolUse hook
2. 匹配 Edit/Write 工具
3. 篩選 .ts/.tsx 檔案
4. 執行 `npx tsc --noEmit`

### 危險命令阻擋

當 Bash 工具嘗試執行危險命令時：

1. 配置 PreToolUse hook
2. 匹配 Bash 工具
3. 檢查命令內容
4. 若危險則阻擋執行

---

## 注意事項

1. **腳本權限**: Unix 系統需 `chmod +x` 賦予執行權限
2. **路徑處理**: 使用相對於專案根目錄的路徑
3. **退出碼**: 0 = 成功, 非 0 = 失敗/阻擋
4. **環境變數**: 可使用 TOOL_NAME, TOOL_INPUT, EDITED_FILE 等

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `.claude/settings.local.json` | 本地配置 |
| `CLAUDE.md` | 主配置文件 |
| `@AGENT.md` | 開發代理指引 |
