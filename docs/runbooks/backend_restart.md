# Backend 重啟 Runbook

> **適用情境**：pm2 restart ck-backend（程式碼變更 / 環境變數變更 / 卡死自救）
> **建立日期**：2026-05-07
> **觸發事件**：5/06 用戶報「未預期錯誤」+ ERR_CONNECTION_REFUSED — pm2 restart 期間 10-15s downtime + 前端 retry 7s 不夠涵蓋

---

## 0. 為什麼需要這份 runbook

| 維度 | 現況 |
|---|---|
| 環境 | Windows + Python uvicorn 單實例 + pm2 fork mode |
| 重啟 downtime | ~12 秒（startup.py + alembic upgrade + uvicorn 啟動） |
| 前端 retry 退避 | 1+3+9 = **13 秒**（P-42 已調整，理論可涵蓋） |
| zero-downtime 可行性 | **❌**（cluster mode 不適用 Python；gunicorn 不支援 Windows） |

**結論**：純技術上無法 zero-downtime。**體感優化策略**：
1. 拉長前端 retry（已做，13 秒）
2. **重啟前 LINE notify**（本 runbook 主旨）
3. **重啟後健康輪詢回報**

---

## 1. 一般情境：用 safe-restart 腳本

### Windows（推薦）
```powershell
.\scripts\dev\safe-restart.ps1
# 預設提前 5 秒通知，pm2 restart，輪詢 /api/health 至 ready，發恢復通知
```

### 自定 grace period
```powershell
.\scripts\dev\safe-restart.ps1 -GraceSeconds 10 -Reason "deploy v6.9 commit abc"
```

### 緊急（不發通知）
```powershell
.\scripts\dev\safe-restart.ps1 -SkipNotify -Reason "緊急修復 bug"
```

## 2. 流程細節

```
[T=0s]   Pre-notify LINE: 「將於 5 秒後重啟，預計 downtime ~12 秒」
[T=5s]   pm2 restart ck-backend --update-env
[T=5~17s] backend 啟動中（用戶看到 ERR_CONNECTION_REFUSED；前端 retry 退避中）
[T=17s]  /api/health 200 OK
[T=17s]  Post-notify LINE: 「已恢復（用時 12 秒）」
```

## 3. 用戶體感對照

| 情境 | Without safe-restart | With safe-restart |
|---|---|---|
| 操作中遇到 restart | 突然錯誤訊息 | 提前 5 秒收到 LINE，可暫停操作 |
| 重啟期間 retry | 看到「重試耗盡」紅字 | 知道是 deploy 進行中 |
| 恢復後 | 自己重新試 | 收到 LINE 主動告知可繼續 |

## 4. 緊急回退

如 safe-restart 卡住或 backend 30 秒內未 ready：

```powershell
# 強制 restart
pm2 restart ck-backend --update-env

# 看 log 找根因
pm2 logs ck-backend --lines 100 --nostream

# 若啟動失敗（ImportError / migration 失敗）
cd backend
python startup.py 2>&1 | head -100   # 直接看錯誤
```

最壞情況：rollback 到上一個 commit
```bash
git log --oneline -5
git revert HEAD            # 或 reset --hard <previous>
.\scripts\dev\safe-restart.ps1
```

## 5. 何時不該用 safe-restart

| 情境 | 直接 pm2 restart 即可 |
|---|---|
| 開發機本地測試（無外部用戶） | ✅ |
| 半夜無使用者時段（< 6:00 / > 22:00） | ✅ |
| backend log 卡住 / OOM | 直接 `pm2 restart`（不需 grace） |

## 6. 監控與配套

| 工具 | 用途 |
|---|---|
| `health-watchdog`（pm2 cron 2 min） | 健康檢查失敗自動 restart |
| `synthetic-baseline`（pm2 cron 4 hr） | 注入測試流量，驗證可用 |
| `idp_connectivity_check`（fitness step） | 確認 Google/LINE OAuth 可達 |
| **本 runbook safe-restart** | 主動 / 計劃性 restart |

## 7. 後續優化方向（非阻擋）

| 方向 | ROI | 工程量 |
|---|---|---|
| 雙 backend instance + nginx 切換 | 高（真 zero-downtime） | L (3 day) |
| LINE notify endpoint 化（背後 service） | 中 | M (4 hr) |
| Restart 計劃排程（cron + admin 預先批） | 低 | S (1 hr) |
| 前端 ChunkLoadError boundary 自動 reload | 中（解 stale bundle 自動恢復） | S (2 hr) |

---

## 附：LINE Notify Endpoint 實作（待補）

`safe-restart.ps1` 預期呼叫 `POST /api/admin/system/notify` 推 LINE。
若該 endpoint 尚未實作，腳本會 best-effort 跳過（不阻擋重啟）。

實作參考：
```python
# backend/app/api/endpoints/admin/system_notify.py（規劃中）
@router.post("/system/notify")
async def system_notify(request: SystemNotifyRequest, current_user: User = Depends(require_admin())):
    """推 LINE/Telegram 給所有 admin，告知系統事件（restart / deploy / outage 等）。"""
    from app.services.integration.line_bot import push_to_admins
    await push_to_admins(f"[{request.event_type}] {request.message}")
    return {"success": True}
```

---

## 變更歷史

- 2026-05-07：建立（v1.0），P-44 任務交付
- 觸發事件：5/06 ERR_CONNECTION_REFUSED 事故
