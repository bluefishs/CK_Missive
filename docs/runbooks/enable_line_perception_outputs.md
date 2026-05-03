# 啟用 LINE 體感型輸出 — Runbook v1.0

> **建立**：2026-05-04（v6.7 收尾，回應「沒收到日記與進步紀錄」事件）
> **目的**：說明為何沒收到 LINE 推送 + 如何啟用 v6.3-v6.7 體感型輸出全套
> **跨 repo FQID**：`CK_Missive#enable_line_perception_outputs_v1.0`

---

## 0. 為何沒收到推送（事故分析）

**根因**（2026-05-04 owner 反饋「沒收到日記與進步紀錄」後診斷）：

| 條件 | 預期 | 實況 | 影響 |
|---|---|---|---|
| `LINE_ADMIN_USER_ID` 設定 | `U` + 32 hex | **未設定** | 所有 v6.3-v6.7 LINE 推送 silent skip |
| 後端 cron 含新 jobs | soul_mirror_sync + daily_self_reflection + cron_self_health | **未掛載** | ck-backend uptime 2D > v6.4-v6.7 commit 時間 |
| `LINE_BOT_ENABLED` | true | ✓ | OK |
| `LINE_CHANNEL_ACCESS_TOKEN` | 設定 | ✓ | OK |

**設計原則**（為何 silent skip 而非報錯）：
- ENV gate 是有意設計（避免測試環境 / 部分部署誤推 owner）
- `LINE_ADMIN_USER_ID` 缺 → silent skip + 一行 debug log（不阻塞主流程）
- ADR-0027 + ADR-0028：notify 是 best-effort，不該 break apply / cron 主流程

---

## 1. 啟用步驟（owner 三步）

### Step 1：取得你的 LINE User ID

```bash
# 1.1 確認 LINE Bot 已加你為好友（mobile LINE 用 QR Code 加）
# 1.2 從 LINE 發任何訊息（如「test」）給 Bot
# 1.3 在 ck-backend log 找你的 userId：

cd D:\CKProject\CK_Missive
grep -i "userId" logs/api/api-out.log | tail -3
# 或
grep -E "U[a-f0-9]{32}" logs/api/api-out.log | tail -3
```

或用 LINE Developer Console：
- https://developers.line.biz → Messaging API → Webhook → 最近 events → `source.userId`

複製 `Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`（34 字元）。

### Step 2：寫進 `.env`

```bash
# 編輯 D:\CKProject\CK_Missive\.env
# 加一行（或填補空值）：
LINE_ADMIN_USER_ID=U你剛複製的字串

# 確認下列 key 也都設了（看 .env.example 範本）：
LINE_BOT_ENABLED=true
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_GROWTH_NOTIFY_ENABLED=true       # 預設 true，缺 key 也視為 true
LINE_PROACTIVE_NOTIFY_ENABLED=true    # 預設 true
```

### Step 3：重啟 ck-backend（讓新 cron + env 生效）

```powershell
# PM2 restart with --update-env（讀新 .env）
pm2 restart ck-backend --update-env

# 驗證新 cron 已掛載
curl -s -X POST http://localhost:8001/api/ai/memory/jobs `
  -H "Content-Type: application/json" -d '{}' `
  | python -m json.tool | Select-String -Pattern "id"

# 應看到（除既有 5 個外）：
# - soul_mirror_sync          每日 04:45（v6.4 C1）
# - daily_self_reflection_line_push  每日 22:00（v6.6 B2）
# - cron_self_health_alert    每日 06:30（v6.7 E4）
```

---

## 2. 完整推送清單（驗收用）

啟用後預期收到的 LINE 訊息：

| 觸發事件 | 訊息開頭 | 來源 | 排程 |
|---|---|---|---|
| crystal apply | 🌱 我學到了一條新規則 | crystal_applier | owner approve 即時 |
| crystal rollback | ↩ 我撤回了一條規則 | crystal_applier | owner rollback 即時 |
| 寫 SOUL「我的成長」 | 📜 我的人格更新了一段 | autobiography | 每週日 18:00 後 |
| 週日 18:00 週成長 | 📖 我的週成長 | autobiography | 每週日 18:00 |
| 每日 22:00 反思 | 🌙 我今日的自我反思 | anti_echo summary | 每日 22:00（無事 silent）|
| 每日 06:30 cron 異常 | ⚠ cron 異常通知 | scheduler self-health | 每日 06:30（全綠 silent）|
| proactive 警報 | 📋 系統警報通知 | line_push_scheduler | 每晚吹哨 cron |

**首日**（restart 後當天）大概率收到：
1. **22:00**「🌙 我今日的自我反思」（如有反思事件）
2. **次日 06:30**「⚠ cron 異常通知」（restart 後可能多數 never_run）

**首週**（週日 18:00）：
3. 「📖 我的週成長 2026-WXX」
4. 「📜 我的人格更新了一段」（autobiography 寫 SOUL 後）

---

## 3. 即時測試（不等 cron）

### 3.1 手動觸發 22:00 反思 LINE 推送
```bash
cd D:\CKProject\CK_Missive\backend
python -c "
import asyncio
from app.core.scheduler import daily_self_reflection_line_push_job
asyncio.run(daily_self_reflection_line_push_job())
"
# 預期：
# - 今日 diary 有事 → LINE 收到「🌙 我今日的自我反思」
# - 今日 diary 無事 → log 「skip LINE push」（不推雜訊）
```

### 3.2 手動觸發 cron 健康檢查
```bash
python -c "
import asyncio
from app.core.scheduler import cron_self_health_alert_job
asyncio.run(cron_self_health_alert_job())
"
```

### 3.3 直接測 LINE 連通性（最簡）
```bash
python -c "
import os, asyncio
os.environ['LINE_ADMIN_USER_ID'] = 'U你的_id'  # 或 .env 已設可省
from app.services.integration.line_bot import LineBotService
async def go():
    bot = LineBotService()
    print('enabled:', bot.enabled)
    if bot.enabled:
        ok = await bot.push_message(os.getenv('LINE_ADMIN_USER_ID'), '測試訊息 from runbook')
        print('push result:', ok)
asyncio.run(go())
"
```

---

## 4. 故障排除

| 症狀 | 檢查 | 解法 |
|---|---|---|
| 完全沒收到 | `.env` 有 `LINE_ADMIN_USER_ID`？| Step 1+2 |
| `pm2 restart` 後仍沒 | restart 用 `--update-env`？| `pm2 restart ck-backend --update-env` |
| 部分有部分沒 | 該事件 ENV 子開關？| `LINE_GROWTH_NOTIFY_ENABLED` / `LINE_PROACTIVE_NOTIFY_ENABLED` |
| 22:00 沒推 | 今日無 anti_echo 觸發 + 無失敗 query | 設計如此（silent 避免雜訊）— 先試 3.1 手動推驗證 |
| 06:30 沒推 | 全綠時 silent | 設計如此 — 先試 3.2 手動推驗證 |
| 推了但沒看到 | LINE Bot block / 群組 mute | 檢查 LINE App 設定 |
| log 顯示 `push returned False` | LINE access token 失效 | 重新生 token + 更新 `.env` |
| log 顯示 `enabled is False` | `LINE_BOT_ENABLED=false` 或 token 缺 | 補 token |

---

## 5. 與 Telegram 的關係（ADR-0027 切換後）

| 通道 | 角色 | 主動 push 預設 |
|---|---|---|
| **LINE** | **owner 主推送（v6.3-v6.7）** | ✅ 啟用 |
| Telegram | 個人號封禁，僅備援 | ❌ 預設 disabled（需顯式開）|
| Discord | 業務命令通道 | — 不推 owner notification |

每個體感事件（5a/5b/5c/proactive）都優先 LINE。Telegram 只在某些舊邏輯（如 weekly autobiography 的 push_to_telegram）作為次推（並推 LINE，與 LINE 共用 best-effort）。

---

## 6. 預防再事故

**架構級**：
- 啟動時做「ENV self-check」— 缺 `LINE_ADMIN_USER_ID` 寫一行 WARNING log（已有，但 owner 看不到）
- ✅ 加 fitness step 15「LINE notify env presence check」（v6.8 候選）

**流程級**：
- 任何 v6.x 加新 cron 時，commit message 注明「需 PM2 restart 才生效」
- README 加「啟用體感型輸出」section 連結本 runbook

**體感級**：
- LINE 推送本身就是體感反饋；如連續 7 天 0 推送，應觸發 owner alert（v6.8 候選）

---

## 7. 關聯文件

- ADR-0027：Telegram → LINE 主推送通道切換
- v6.3 commit `8367af64`：crystal/cross_session/autobiography 體感三件組
- v6.4 commit `caf814de`：C1 cron + A1 channel + I3 critique entity
- v6.6 commit `21d77d70`：A3 SOUL changelog + rollback notify
- v6.6 commit `5cfad746`：B2 每日 22:00 反思
- v6.7 commit `3894cfb3`：E3+E4+E5（含 cron_self_health_alert）

---

> **體感 ≠ dev metrics。**
> **能推到 LINE 才算數。**
> **ENV gate 是設計選擇；事故是設計選擇的代價。**
