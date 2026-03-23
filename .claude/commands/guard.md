# Guard — 綜合安全防護模式

> 靈感來源: [gstack/guard](https://github.com/garrytan/gstack) — careful + freeze 合一

同時啟用危險命令攔截 (`/careful`) 和編輯範圍鎖定 (`/freeze`)。
適用於重構、偵錯等需要高度安全保障的場景。

## 使用方式

```
/guard backend/app/services/erp/     # 啟用 careful + freeze 到指定目錄
/guard status                         # 查看當前防護狀態
```

## 工作流程

1. **啟用 careful** — 危險命令攔截（透過 PreToolUse hook 自動生效）
2. **啟用 freeze** — 建立 `.claude/freeze-scope.json` 限制編輯範圍
3. **狀態報告**：
   ```
   Guard 模式已啟用:
   - Careful: 危險命令攔截 [永遠啟用]
   - Freeze: 編輯範圍鎖定至 [列出目錄]

   解除方式: /unfreeze（解除 freeze）
   ```

## 適用場景

| 場景 | 建議用法 |
|------|---------|
| 偵錯生產問題 | `/guard backend/app/services/` |
| ERP 模組重構 | `/guard backend/app/services/erp/ backend/app/schemas/erp/ frontend/src/api/erp/` |
| 安全修補 | `/guard backend/app/api/endpoints/auth/ backend/app/core/` |
| 資料庫遷移 | `/guard backend/alembic/` |

## 組成

- **`/careful`** — 攔截 `rm -rf`、`DROP TABLE`、`git push --force` 等危險 Bash 命令
- **`/freeze`** — 限制 Edit/Write 到指定目錄，防止 scope drift
- **`/unfreeze`** — 解除 freeze（careful 始終保持啟用）
