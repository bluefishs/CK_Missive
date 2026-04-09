---
description: "編輯範圍鎖定 — 限制 Edit/Write 到指定目錄"
---

# Freeze — 編輯範圍鎖定

> 靈感來源: [gstack/freeze](https://github.com/garrytan/gstack) — 防止偵錯/重構時的 scope drift

鎖定編輯範圍到指定目錄，防止修改無關程式碼。適用於偵錯或定點重構場景。

## 使用方式

```
/freeze backend/app/services/erp/              # 鎖定到單一目錄
/freeze backend/app/services/ frontend/src/api/ # 鎖定到多個目錄
/freeze status                                  # 查看當前鎖定狀態
```

## 工作流程

### 啟用 Freeze

1. **解析用戶指定的路徑** — 接受 1~N 個目錄路徑（以空格分隔）
2. **建立 `.claude/freeze-scope.json`**：
   ```json
   {
     "allowed_paths": ["backend/app/services/erp/", "backend/app/schemas/erp/"],
     "reason": "用戶手動設定的編輯範圍限制",
     "created_at": "2026-03-23T14:00:00",
     "created_by": "user"
   }
   ```
3. **確認訊息** — 列出允許的編輯範圍
4. `.claude/` 目錄永遠允許（用於管理 freeze 本身）

### 查看狀態

```
/freeze status
```

讀取 `.claude/freeze-scope.json` 並顯示：
- 允許的編輯路徑
- 設定原因
- 設定時間

若檔案不存在，回報「未啟用 freeze」。

### 解除 Freeze

使用 `/unfreeze` 指令（見下方）。

## 機制

透過 `freeze-scope.ps1` PreToolUse hook 實現：
- 攔截所有 `Edit` 和 `Write` 工具呼叫
- 檢查目標檔案是否在 `freeze-scope.json` 的 `allowed_paths` 中
- 不在範圍內 → exit 2 阻擋並提示

## 適用場景

| 場景 | 建議範圍 |
|------|---------|
| 偵錯特定服務 | 該服務的目錄 + 對應測試目錄 |
| ERP 模組重構 | `backend/app/services/erp/` + `backend/app/schemas/erp/` + `frontend/src/api/erp/` |
| 前端元件修復 | 該元件所在目錄 |
| 安全修補 | 受影響的端點 + 中間件目錄 |

## 注意事項

- Freeze 僅影響 Edit/Write，不影響 Read/Grep/Glob
- `.claude/` 目錄永遠不受限制
- 若需同時攔截危險命令，搭配 `/careful` 或使用 `/guard`
