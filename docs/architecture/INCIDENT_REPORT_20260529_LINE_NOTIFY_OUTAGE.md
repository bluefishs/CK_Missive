# INCIDENT REPORT: LINE 通報服務 silent 中斷事件 (L51, 2026-05-29)

> **狀態**: closed (root cause fixed)
> **嚴重度**: P1 — silent failure, 業務推薦完全不通
> **影響時長**: 2h 23min (5/29 09:00 cron 失敗 → 11:23 修復)
> **潛在更長**: 整個 admin push 鏈 LINE channel 自 2026-02-02 docker-compose 建立後即缺 env，
>             只是 5/28 business_recommend cron 落地後才有「應該推但失敗」的可量化基準
> **關聯**: ADR-0046 Phase 4 / L51 task B / cross-file-ssot-governance.md

---

## 1. 事故摘要

L51 task B（LINE 通報觀測閉環）落地 4h 後，立刻觀測閉環本身揭發了一個更深的 silent
failure: backend container **完全沒有任何 LINE_* env**，所有 admin push 透過 LINE channel
一律 silent 失敗（return False），未對 owner 產生任何體感。

---

## 2. 時間軸

| 時間 | 事件 | 來源 |
|---|---|---|
| 2026-02-02 20:15 | docker-compose.production.yml 建立 (commit `1348a913`)，**LINE_* env 從未注入** | git log |
| 2026-05-04 06:17 | `.env` 補齊 LINE_ADMIN_USER_ID 等 8 個 vars (commit `b2aca2ae`)，解 5/04 體感推送事故 | git log |
| 2026-05-28 11:14 | business_recommendation cron 加入 (commit `5a82621b`)，加 cron 每日 09:00 跑 | git log |
| 2026-05-29 09:00 | cron 首次跑，6 筆候選找到，全 push_admin_alert returned False | backend log |
| 2026-05-29 ~10:00 | L51 task B 落地（觀測閉環 + history table） | commit `32712f46` |
| 2026-05-29 ~11:00 | 端對端複查發現 `tender_recommendation_history` 6 筆 status=error | 複查 SQL |
| 2026-05-29 11:23 | docker-compose 補 8 個 LINE_* env → backend recreate → 真實 push True | commit `706b2e22` |

---

## 3. 根因（3 層 silent failure 疊加）

### Layer 1: docker-compose env 缺漏（root cause）

```yaml
# docker-compose.production.yml backend.environment 從建立以來從未注入 LINE_*
environment:
  - DATABASE_URL=...
  - SECRET_KEY=...
  - CK_SSO_ENABLED=...  # SSO 有，因為 L48 上次同樣事故補過
  # ❌ 缺：LINE_BOT_ENABLED / LINE_CHANNEL_* / LINE_ADMIN_USER_ID / ...
```

### Layer 2: `LineBotService` init 不偵測 admin_id

```python
# line_bot.py
self._channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")  # 預設空
self._channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")  # 預設空
self._enabled = os.getenv("LINE_BOT_ENABLED", "false").lower() == "true"  # 預設 false
# init 仍成功（type=LineBotService）但 enabled=False
```

→ `get_line_bot_service()` 不返 None，業務以為「LINE 服務存在」

### Layer 3: `_push_one` 對 admin_id 缺失 silent return False

```python
# messaging_default.py:_push_one (line channel)
admin_id = target or self._get_admin_id("LINE_ADMIN_USER_ID")
if not admin_id:
    return False  # ❌ 沒 log、沒 metric、沒 alert
```

→ 業務只看到 `push_admin_alert returned False`，無法定位是 service 沒 init、admin_id 缺、
還是 push 真失敗

---

## 4. 為何沒早發現（5 個 observability gap）

| Gap | 描述 | 影響 |
|---|---|---|
| 1 | `_get_admin_id` 返 None 時 silent return False，無 log 也無 metric | 沒人知道 admin push 整鏈空轉 |
| 2 | LineBotService init 即使全空 token 也成功（沒 startup validation） | 真活 health probe 永遠 GREEN |
| 3 | 沒 fitness step 驗證「container env vs host env」對齊 | 此類事故反覆發生（L48 SSO 一樣患） |
| 4 | 沒 push_admin_alert 失敗率 metric | 6 筆 / 6 失敗的事實沒 alert |
| 5 | `LINE notify 7d heartbeat watchdog` (fitness step 16) 只看 push 動作有跑，沒驗證 return True | False 結果 silent 通過 |

---

## 5. 為何 L51 task B 揭發了

L51 task B（LINE 通報觀測閉環）的 3 件套之一是 **`tender_recommendation_history` table**：

```sql
-- 每一筆推送結果（含 error）都寫一筆紀錄
INSERT INTO tender_recommendation_history (
  ..., status, error_msg, channel
) VALUES (..., 'error', 'facade.push_admin_alert returned False', 'line')
```

關鍵設計選擇：
- **每筆都寫**（pushed / skipped_duplicate / error 都寫）
- **error_msg 文字級**（不只 boolean）
- **與 Redis 25h 去重 key 分離**（Redis 過期即丟，DB 永久保留）

若仍用舊設計（只 Redis 去重 + Prometheus counter），6 筆 error 會 silent，本事件無從追蹤。

**L51 task B 設計初衷**是「轉換率追蹤」，意外成為**真因偵錯線索**。觀測閉環本身比預期更有價值。

---

## 6. 優化建議（5 條，按優先序）

### P0 — 立即（v6.11 收尾前）

#### 6.1 加 `fitness step 57`: container env vs host env 對齊驗證

```bash
# scripts/checks/container_env_alignment_audit.py
# - 讀 .env LINE_* / TELEGRAM_* / CK_SSO_* 等 critical secrets
# - 對比 docker-compose.production.yml backend.environment 區塊
# - 若 .env 有但 compose 沒注入 → RED
```

防同型事故（L48 SSO 已患過、L51 LINE 又患）。

#### 6.2 `_get_admin_id` 返 None 時記 warning + metric

```python
# messaging_default.py
@staticmethod
def _get_admin_id(env_key: str) -> Optional[str]:
    import os
    val = os.getenv(env_key)
    if not val:
        # L51 加：silent fail 升級為 warning + metric
        logger.warning(f"[Messaging] admin_id env '{env_key}' missing, channel push will skip")
        try:
            from app.services.tender.metrics import get_tender_metrics
            # 或加新 Prometheus counter: messaging_missing_admin_id_total{env_key}
        except Exception:
            pass
    return val
```

### P1 — 兩週內

#### 6.3 LineBotService startup validation

```python
# line_bot.py:LineBotService.__init__
def __init__(self):
    self._channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    # L51 加：critical config 缺失即 raise，不要 init 成「假可用」
    if self._enabled and not (self._channel_secret and self._channel_access_token):
        raise RuntimeError(
            "LINE_BOT_ENABLED=true 但 CHANNEL_SECRET/ACCESS_TOKEN 缺失 — "
            "拒絕假裝 ready (L51 lesson)"
        )
```

#### 6.4 加 Prometheus alert: `messaging_push_failure_rate > 50% over 1h`

對應 dashboard panel + Alertmanager rule，避免 silent fail 再發生 2h+。

#### 6.5 業務推薦 cron 對「pushed=0 但 found>0」單獨告警

```python
# business_recommendation.py
if stats["found"] > 0 and stats["pushed"] == 0:
    logger.error(
        "[CRITICAL] business recommend: found=%d but pushed=0 — "
        "messaging chain may be broken",
        stats["found"],
    )
    # 額外推 admin 用 Telegram fallback（避免依靠壞掉的同一鏈報自己壞）
```

### P2 — 月底前

#### 6.6 寫進 `cross-file-ssot-governance.md`

擴大規範範圍：**host .env vs container env** 列為「跨檔資源不一致」第 6 類（既有 5 類為
secrets / volumes / ports / endpoints / network names）。

---

## 7. 程序：新 env var 三同步檢查清單

加 env var 時，**三處必須同步**（檢查清單）：

| # | 位置 | 檢查 |
|---|---|---|
| 1 | `.env` | 加實際值 |
| 2 | `.env.example` | 加範本（無值，註解說明用途） |
| 3 | `docker-compose.production.yml` backend.environment | 加 `- VAR=${VAR:-}` |
| 4 | `docker-compose.dev.yml` 若有獨立 | 同 #3 |
| 5 | container 內驗證 | `docker exec backend env \| grep VAR` 應有值 |
| 6 | 程式碼 startup probe | 若 critical，加 raise RuntimeError 防假可用 |

**新增 PR template 一行**：
```markdown
- [ ] 若新增 env var：已同步 .env / .env.example / docker-compose / startup probe
```

---

## 8. 連帶事件對照

L51 LINE 事件**並非孤例**，同型事故已發生過：

| Lesson | 事件 | 同型「.env vs compose 不同步」 |
|---|---|---|
| L48 (2026-05-27) | SSO `CK_SSO_*` env 未注入 container | ✓ 已修，加 5 個 vars |
| L51 (2026-05-29) | LINE_* env 未注入 container（本次） | ✓ 已修，加 8 個 vars |
| ???（潛伏）| Telegram / Discord env？ | 待 audit step 57 揭發 |

→ 強烈支持 P0.6.1（fitness step 57 自動 audit），避免反覆發生。

---

## 9. 度量改善（修法後）

| 指標 | 修法前 | 修法後 |
|---|---|---|
| LINE push 成功率 | 0% (6/6 fail) | 100% (dry-run 6/6 pushed) |
| Admin 體感推送 | silent fail | 已收到驗證訊息 |
| Silent fail 時長 | 2h+（cron 落地後）| < 5min（observability 揭發） |
| Root cause 追蹤線索 | 無 | `tender_recommendation_history.error_msg` |

---

## 10. Refs

- **修法 commit**: `706b2e22` (docker-compose LINE_* env 注入)
- **揭發機制**: L51 task B `tender_recommendation_history` (commit `32712f46`)
- **觀測閉環 SOP**: `.claude/rules/adr-anti-half-wired-sop.md` (ADR L1→L2 升級)
- **同型事故**: L48 SSO env 配套 (commit `4872ce7f`)
- **跨檔 SSOT 規範**: `.claude/rules/cross-file-ssot-governance.md`
- **PCC 評估 doc**: `docs/architecture/TENDER_PCC_COVERAGE_AUDIT_20260529.md`

---

## 11. 對 Owner 的關鍵啟示

1. **觀測閉環不是「補洞」，是「揭發器」**
   L51 task B 設計初衷是業務轉換率追蹤，意外揭發了一個 4 個月潛伏的 silent failure。
   未來新功能落地時，**先想「如果這個失敗了，下一個人怎麼知道」**，這個問題會節省幾天 debug。

2. **silent return False 是技術債**
   `_get_admin_id` 缺失時 return False 看似「優雅 fallback」，實則消滅了所有 debug 線索。
   產品設計上應「不可用即叫」（raise）或「可用但記錄」（log + metric），不應「假裝可用」。

3. **跨檔資源治理是反覆痛**
   L48 / L51 / L52(?) 同型「.env vs compose 不同步」事故，需要自動化 audit 終結反覆。
