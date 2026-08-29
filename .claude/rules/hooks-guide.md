# Hooks 自動化配置

## 自動觸發 Hooks

### PreToolUse (工具執行前)

| Hook | Matcher | 說明 | 腳本 |
|------|---------|------|------|
| validate-file-location | `Write\|Edit` | 確認檔案位置符合架構規範 | `.claude/hooks/validate-file-location.ps1` |
| freeze-scope | `Write\|Edit` | 編輯範圍鎖定（需 freeze-scope.json） | `.claude/hooks/freeze-scope.ps1` |
| careful-guard | `Bash` | 危險命令攔截（rm -rf, DROP, force push 等） | `.claude/hooks/careful-guard.ps1` |

### PostToolUse (工具執行後)

> ⚠️ **2026-08-26：`typescript-check` 已從 PostToolUse 移除**（腳本保留，可手動跑）。
>
> 起因是 CK_Website 回報他們的 `PostToolUse:Edit` 平均 8.4 秒；量本 repo 更嚴重 ——
> 近 30 個 session 裡 `PostToolUse:Edit` **3,315 次 × 5.9 秒 = 5.4 小時**，
> 加 Write 共約 **6.6 小時**純阻塞等待。逐支量測後元兇是它：改一個 `.tsx`
> 要 **28.8 秒**（`npx tsc --noEmit` 全專案 600+ 檔；`--incremental` 也只降到 15.1 秒）。
>
> 而真正的問題不是慢，是**同一件事有三份，最貴的那份跑得最頻繁**：
>
> | 層 | 做什麼 | 頻率 |
> |---|---|---|
> | ~~`PostToolUse`~~ | `npx tsc --noEmit` | **每次 Edit** —— 平均 4.3 次／turn，最多 39 次 |
> | `Stop` quality-gate | prompt 明寫「執行 `npx tsc --noEmit`」 | 每 turn 1 次 |
> | `pre-commit` | TypeScript 編譯檢查 | 提交時 |
>
> 近 10 個 session 有 366 個 turn 動到檔案 ⇒ 每 turn 多跑 3.3 次無用的全專案編譯。
> 而且一次修改往往要多次 Edit，**中間狀態的型別錯誤是「還沒改完」不是「改錯了」**。
>
> 移除後保護沒有變薄：Stop（每 turn）與 pre-commit（提交時）兩層都還在，
> 而後者實測會擋（本輪提交時印出「[Pre-commit] TypeScript 編譯通過」）。
> 若日後覺得少了即時回饋，加回一行即可 —— 這個取捨是可逆的。

| Hook | Matcher | 說明 | 腳本 |
|------|---------|------|------|
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

> ⚠️ **2026-08-30 實測：`git config core.hooksPath = frontend/.husky/_`**
> ⇒ git **只**執行 `frontend/.husky/` 底下的 hook，**`.git/hooks/` 整個目錄不會被執行**。
> 下表原本把位置寫成 `.git/hooks/`，那是**錯的**（已更正）。
>
> | hook | `.git/hooks/`（死） | `frontend/.husky/`（活） |
> |---|---|---|
> | pre-commit | 9,674 B、6 項檢查 | ✅ 已於 08-30 補上 secret guard 與 destructive ops |
> | **pre-push** | **7,787 B、3 階段守門包** | **❌ 不存在 ⇒ 從來沒有跑過一次** |
> | post-commit | 5,736 B（知識地圖增量更新）| ❌ 不存在 |
> | post-checkout / post-merge | 有 | ✅ 有 |
> | commit-msg | 無 | ✅ commitlint |
>
> **要改 pre-commit 行為請改 `frontend/.husky/pre-commit`。**
> pre-push 要不要接上見待辦 A46（實跑 467 秒、且會因別的 repo 服務掛掉而擋住本 repo 的 push）。

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
| ~~link-id-check~~ | ⚠️ **已被 `scripts/checks/link_id_fallback_audit.py`（weekly 90）取代**。它從 2026-01-21 起沒有任何 runner 在叫它，而且跑起來會給錯的答案：`-Path "src\**\*.tsx"` 在 PowerShell 裡的 `**` **不是遞迴 glob**（等同 `*`），實測只掃得到 **119/604** 個 `.tsx` 而照樣印 `[PASS]`；另有一條斷言 `BaseLink` 必須在 `types/api.ts`，而它實際在 `types/taoyuan.ts:53` ⇒ **永久假紅**。檔案保留待 owner 裁示刪除（A42） | `.claude/hooks/link-id-check.ps1` |
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
