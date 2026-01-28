# Claude Code Hooks 配置

> **版本**: 1.2.0
> **用途**: 定義 Claude Code 自動化鉤子
> **最後更新**: 2026-01-28

---

## 快速參考：Hooks 執行方式

| Hook 腳本 | 執行方式 | 觸發條件 | 說明 |
|----------|---------|---------|------|
| `typescript-check.ps1` | 🤖 自動 | 修改 .ts/.tsx | TypeScript 編譯檢查 |
| `python-lint.ps1` | 🤖 自動 | 修改 .py | Python 語法檢查 |
| `validate-file-location.ps1` | 🤖 自動 | Write/Edit 前 | 驗證檔案位置符合架構 |
| `route-sync-check.ps1` | 📋 手動 | /route-sync-check | 前後端路由一致性 |
| `api-serialization-check.ps1` | 📋 手動 | /api-check | API 序列化問題檢查 |
| `link-id-check.ps1` | 📋 手動 | 需要時 | 前端 link_id 使用檢查 |
| `link-id-validation.ps1` | 📋 手動 | 需要時 | 後端 link_id 傳遞檢查 |
| `performance-check.ps1` | 📋 手動 | /performance-check | 效能診斷檢查 |

**圖例**：🤖 自動 = 由 settings.json 配置自動觸發 | 📋 手動 = 搭配 Slash Command 或手動執行

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

### api-serialization-check.ps1 (v1.0.0 - 2026-01-21)
API 序列化問題檢查。

**用途**: 檢查 API 端點是否可能直接返回未序列化的 ORM 模型

**檢查項目**:
1. `.scalars().all()` 後直接返回（未經 `model_validate` 或字典轉換）
2. datetime 欄位未使用 `.isoformat()` 序列化

**使用方式**:
```powershell
# 檢查單一檔案
.\.claude\hooks\api-serialization-check.ps1 -FilePath "backend/app/api/endpoints/dashboard.py"

# 檢查所有 API 端點
.\.claude\hooks\api-serialization-check.ps1
```

**相關文件**:
- `.claude/skills/api-serialization.md`
- `docs/specifications/SCHEMA_DB_MAPPING.md`

### route-sync-check.ps1 (v1.0.0 - 2026-01-12)
前後端路由一致性檢查。

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

## 完整 Hooks 清單

### 自動執行 Hooks (settings.json 配置)

這些 hooks 已在 `.claude/settings.json` 中配置，會自動觸發。

#### 1. typescript-check.ps1
- **觸發時機**: PostToolUse (Edit/Write .ts/.tsx)
- **功能**: 執行 `npx tsc --noEmit` 檢查 TypeScript 編譯
- **失敗處理**: 顯示錯誤，阻止繼續

#### 2. python-lint.ps1
- **觸發時機**: PostToolUse (Edit/Write .py)
- **功能**: 執行 Python 語法檢查
- **失敗處理**: 顯示錯誤，阻止繼續

#### 3. validate-file-location.ps1
- **觸發時機**: PreToolUse (Write/Edit)
- **功能**: 驗證新建/修改的檔案位置符合架構規範
- **失敗處理**: 阻止在錯誤位置建立檔案

### 手動執行 Hooks

這些 hooks 需要透過 Slash Command 或手動執行。

#### 4. route-sync-check.ps1
- **搭配指令**: `/route-sync-check`
- **功能**: 檢查前後端路由定義一致性
- **檢查項目**: ROUTES 常數、AppRouter、導覽配置

#### 5. api-serialization-check.ps1
- **搭配指令**: `/api-check`
- **功能**: 檢查 API 端點是否有序列化問題
- **檢查項目**: ORM 直接返回、datetime 未序列化

#### 6. link-id-check.ps1
- **用途**: 檢查前端 JSX 中的 link_id 使用
- **檢查項目**: 是否誤用 `.id` 而非 `.link_id`

#### 7. link-id-validation.ps1
- **用途**: 檢查後端 Python 中的 link_id 傳遞
- **檢查項目**: API 回應是否包含 link_id

#### 8. performance-check.ps1
- **搭配指令**: `/performance-check`
- **功能**: 效能診斷檢查
- **檢查項目**: N+1 查詢、未使用索引、大量資料載入

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `.claude/settings.json` | Hooks 自動觸發配置 |
| `.claude/settings.local.json` | 本地覆蓋配置 |
| `CLAUDE.md` | 主配置文件 |
| `docs/SYSTEM_OPTIMIZATION_REPORT.md` | 系統優化報告 |
