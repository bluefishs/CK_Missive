---
description: "危險命令攔截模式 — 啟用 PreToolUse hook 攔截破壞性操作"
---

# Careful — 危險命令攔截模式

> 靈感來源: [gstack/careful](https://github.com/garrytan/gstack) — 破壞性操作防護

啟用後，所有 Bash 命令會經過 `careful-guard.ps1` hook 檢查，攔截潛在危險操作。

## 使用方式

```
/careful              # 查看當前狀態與攔截規則
/careful status       # 同上
```

## 攔截規則

### CRITICAL（直接阻擋）

| 模式 | 說明 |
|------|------|
| `rm -rf /` / `~` / `..` | 刪除根目錄/家目錄/上層 |
| `DROP TABLE/DATABASE` | SQL 刪除表/庫 |
| `TRUNCATE TABLE` | SQL 清空表 |
| `DELETE FROM x;` | 無 WHERE 全表刪除 |
| `git push --force main` | Force push 到主分支 |
| `git reset --hard origin` | Hard reset 到遠端 |
| `chmod -R 777` | 遞迴開放全部權限 |
| `mkfs.*` | 格式化磁碟 |

### WARNING（阻擋並提示確認）

| 模式 | 說明 |
|------|------|
| `rm -rf` | 遞迴刪除（非根目錄） |
| `git push --force` | 非主分支 force push |
| `git reset --hard` | Hard reset |
| `git branch -D` | 強制刪除分支 |
| `git checkout -- .` | 放棄所有變更 |
| `git clean -fd` | 清除未追蹤檔案 |
| `docker rm/rmi -f` | Docker 強制刪除 |
| `ALTER TABLE DROP` | SQL 欄位刪除 |
| `alembic downgrade` | 遷移降級 |
| `kill -9` | 強制殺進程 |

## 配置

此功能透過 `settings.json` 的 PreToolUse hook 自動啟用，無需手動操作。

hook 位置: `.claude/hooks/careful-guard.ps1`

## 與 /freeze 搭配使用

- `/careful` — 攔截危險 **命令**
- `/freeze` — 限制 **編輯範圍**
- `/guard` — 同時啟用兩者（重構/偵錯推薦）
