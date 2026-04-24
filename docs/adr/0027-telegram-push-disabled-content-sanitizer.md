# ADR-0027：Telegram 主動推播關閉 + 內容敏感詞過濾

- **狀態**：Accepted
- **日期**：2026-04-21
- **作者**：CK 助理（坤哥意識體）
- **相關**：ADR-0023（坤哥意識體上線）、MEMORY `access_urls.md`

---

## 背景

2026-04-21 用戶 `@Aaron_ckbot` 所屬的 Telegram **個人帳號**被 Telegram 官方
永久封禁。申訴已於 2026-04-21 被駁回：

> The team's supervisors have reviewed your appeal and all relevant materials.
> We regret to inform you that your appeal has been denied and the restrictions
> have not been lifted.

推測根因：bot 主動推播的 admin 訊息（晨報 / 告警 / 結晶提案）中，含有大量
類詐騙格式內容：

- **身分證 / 統編樣式**：`AB12345678`
- **金額樣式**：`NT$ 50,500`
- **長串連續數字**：11+ 位派工文號 / 案號

這些內容在 Telegram 反詐騙系統中觸發高風險標記，導致帳號受限。

---

## 決策

### 雙層防護

#### 層 1：主動推播 gate（`TELEGRAM_ADMIN_PUSH_ENABLED`）

- 新增獨立環境變數 `TELEGRAM_ADMIN_PUSH_ENABLED=false`（預設關閉）。
- 保留 `TELEGRAM_BOT_ENABLED=true` 讓 webhook 被動回覆可用
  （用戶發訊 → bot 回覆）。
- `TelegramBotService.push_message()` 先檢查 `push_enabled`，
  若關閉直接 return False 並 log，不發 API request。
- 所有 scheduler 呼叫 `push_message()` 的地方
  （晨報 / LLM 配額告警 / 結晶提案 / autobiography）
  **不需改動**，由 gate 統一控制。

#### 層 2：內容 sanitizer（`telegram_content_sanitizer`）

- 新增 `backend/app/services/common/telegram_content_sanitizer.py`：
  - `[A-Z]{1,2}\d{7,10}` → `[識別碼]`
  - `(NT\$|NTD|NT|\$)\s?數字(,000)*(.xx)?` → `[金額]`
  - `\d{10,}` → `[編號]`
- `send_message()` / `_send_and_get_id()` / `_edit_message()` 在送出前
  自動套用 `sanitize()`，被動回覆也包含在內，徹底阻絕風險內容外洩。

### 主要 admin 通道切換

- **LINE** 成為主要 admin push 通道（晨報 / 告警）。
- Telegram 維持被動回覆備援（問答用途，不含敏感格式）。

---

## 後果

### 正面

1. 避免 bot 訊息再次觸發 Telegram 反詐騙，保護新帳號（若未來切換）。
2. 被動回覆仍可用，用戶可在 Telegram 繼續和 bot 對話（SOUL 坤哥人格）。
3. Sanitizer 提供系統級別的內容衛生，對所有 outbound Telegram 訊息一致套用。
4. 環境變數 gate 可快速開關，不需重新部署程式碼。

### 負面

1. Admin 晨報暫時失去 Telegram 推播通道，轉為 LINE 單通道
   （LINE 推播目前仍正常）。
2. Sanitizer mask 後可讀性下降（如 `派工單 [編號]_測量工程`），
   需在 UI / email 補呈現原始案號。

---

## 驗證

```bash
# Sanitizer 單元測試
cd backend && python -m pytest tests/unit/test_telegram_content_sanitizer.py -v

# push_message gate
python -c "
import asyncio, os
os.environ['TELEGRAM_ADMIN_PUSH_ENABLED'] = 'false'
os.environ['TELEGRAM_BOT_ENABLED'] = 'true'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test'
from app.services.telegram_bot_service import TelegramBotService
svc = TelegramBotService()
assert svc.enabled is True       # 被動 webhook 仍可用
assert svc.push_enabled is False # 主動 push 關閉
print('✅ push gate works')
"
```

---

## 狀態記錄

- `.env`：`TELEGRAM_ADMIN_PUSH_ENABLED=false`
- `MEMORY.md`：note「Telegram 個人號 2026-04-21 封禁 (申訴駁回)，系統 push 關閉」
- 後續：若啟用 bot 新帳號，先以 sanitize 過的 synthetic push 測 7 天再開 gate

## 配套延伸（2026-04-22 P0/P1 落地）

為根治「push 通道單點失效」與「silent failure 邊界層」：

| 層級 | 項目 | 狀態 |
|---|---|---|
| P0-1 | Synthesis timeout 60s→35s；quality review 15s→10s；防 silent gap | ✅ |
| P0-2 | `admin_push_metrics.py` — LINE/Telegram push 成功失敗 counter + 連續失敗 3 次 error log + `logs/admin_push_failures.log` 獨立記錄 | ✅ |
| P0-3 | `tests/integration/test_sse_agent_stream.py` — 活體驗證 `Content-Encoding: identity` + 10s 內首 event + 30s 內 done | ✅ |
| P1-4 | `scripts/checks/schema_lazy_load_guard.py` — 靜態檢查 `schemas/*.py` 不得 `getattr(obj, <relationship>)`；CI / pre-commit 可直接接 | ✅ |
| P1-5 | `synthetic-baseline-inject.py` — 每批注入加 `content_risk_hits` / `scam_keyword_hits` / `risky_samples` 3 欄；擊中 → warn log 提醒 | ✅ |
