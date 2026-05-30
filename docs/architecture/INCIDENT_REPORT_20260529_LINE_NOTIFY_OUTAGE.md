# INCIDENT REPORT: LINE 通報服務 silent 中斷事件 (L51, 2026-05-29)

> **狀態**: closed (root cause fixed)
> **嚴重度**: P1 — silent failure, 業務推薦完全不通
> **真實影響時長**: **40h 23min** (5/27 19:00 PM2 廢除引爆 → 5/29 11:23 修復)
> **首次校正**: 原報告寫「3 個月 27 天」(自 docker-compose 建立)，**錯誤**。
>             Owner 5/29 12:30 提供 5/25 / 5/27 / W21 LINE 訊息範例證明 PM2 模式下真活，
>             正確引爆點是 PM2→docker 流量切換 (commit `ed81bf87` / `1ea91196`)。
> **關聯**: ADR-0046 Phase 4 / L51 task B / cross-file-ssot-governance.md / **OA-3 PM2 廢除**

---

## 1. 事故摘要

L51 task B（LINE 通報觀測閉環）落地 4h 後，立刻觀測閉環本身揭發了一個更深的 silent
failure: backend container **完全沒有任何 LINE_* env**，所有 admin push 透過 LINE channel
一律 silent 失敗（return False），未對 owner 產生任何體感。

**Owner 5/29 12:15 後續追問「派工 LINE 通知也中斷？」**揭發影響範圍 **遠超出 business_recommendation**：

| LINE Push 鏈 | docker 模式下狀態 (5/27 19:00 ~ 5/29 11:23) | 修法後驗活 |
|---|---|---|
| `LineBotService.enabled` | False（env 缺）| **True** |
| `push_admin_alert` (any admin push) | return False | **True**（驗活訊息已送達） |
| `push_dispatch_progress` (派工進度 Flex 每日 00:30) | return `disabled` silent | **sent=1/1, overdue=3** |
| `morning_report` LINE 推送 (每日 08:00) | LINE channel 跳過 | channel ready=True |
| `scan_and_push` (夜間吹哨警報) | enabled=False return | recovers |
| `business_recommendation` (每日 09:00) | found=6 pushed=0 err=6 | dry-run 6/6 OK |

### 真實影響時長 — **40 小時 23 分**（不是 3 個月 27 天）

Owner 提供 4 種 LINE 訊息範例（5/25 / 5/27 / W21 / W21）反證 PM2 模式下 LINE 鏈真活：

```
PM2 模式 (2026-02-02 ~ 2026-05-27 19:00)
  → 流量 cloudflared → host:8001 命中 PM2 native uvicorn
  → 從 host .env 直接讀 LINE_* 真活推送 ✓

5/27 19:04 commit ed81bf87: refactor(pm2): remove ck-backend + ck-frontend
5/27 19:09 commit 1ea91196: OA-3 階段 2-3 完成 (L43 路由迷宮解開)

docker 模式 (2026-05-27 19:00 ~ 2026-05-29 11:23 = 40h 23min)
  → 流量 cloudflared → docker container
  → container 內 docker-compose env 缺 LINE_* → enabled=False
  → 全鏈 silent disabled ✗

5/29 11:23 commit 706b2e22: docker-compose 補 8 個 LINE_* env
  → 真活恢復 ✓
```

**根因**：OA-3 PM2 廢除（v6.11 治理）切換流量入口時，未察覺 docker-compose 缺 LINE_*
env，導致整個 LINE 通知生態從 host env 真活 → container env silent disabled。**這是
治理動作引發的回退**，非新功能 bug。

---

## 2. 時間軸（2026-05-29 12:30 校正版）

| 時間 | 事件 | 來源 |
|---|---|---|
| 2026-02-02 20:15 | docker-compose.production.yml 建立 (commit `1348a913`)，LINE_* env 從未注入。**但流量仍走 PM2，無影響** | git log |
| 2026-05-04 06:17 | `.env` 補齊 LINE_ADMIN_USER_ID 等 8 個 vars (commit `b2aca2ae`)，解 5/04 體感推送事故 | git log |
| 2026-05-25 | LINE 推送「每日巡檢 Pipeline RED 報告」(owner 提供範例) — **PM2 模式真活** | owner 證據 |
| 2026-05-27 早上 | LINE 推送「05/27 晨報」派工預警 3 筆 + 會議 4 場 (owner 提供範例) — **PM2 模式真活** | owner 證據 |
| 2026-05-27 19:04 | commit `ed81bf87`: refactor(pm2): remove ck-backend + ck-frontend | git log |
| 2026-05-27 19:09 | commit `1ea91196`: OA-3 階段 2-3 完成，**流量切到 docker container** | git log |
| 2026-05-27 22:00 | (應推) daily_self_reflection_line_push — silent skip | 推算 |
| 2026-05-28 00:30 | (應推) push_dispatch_progress 派工進度 Flex — silent skip | 推算 |
| 2026-05-28 08:00 | (應推) morning_report 每日晨報 LINE — silent skip | 推算 |
| 2026-05-28 11:14 | business_recommendation cron 加入 (commit `5a82621b`) | git log |
| 2026-05-28 22:00 | (應推) daily_self_reflection_line_push — silent skip | 推算 |
| 2026-05-29 00:30 | (應推) push_dispatch_progress — silent skip | 推算 |
| 2026-05-29 08:00 | (應推) morning_report — silent skip | 推算 |
| 2026-05-29 09:00 | business_recommendation cron 首次跑，6 筆全 push_admin_alert returned False | backend log |
| 2026-05-29 ~10:00 | L51 task B 落地（觀測閉環 + history table） | commit `32712f46` |
| 2026-05-29 ~11:00 | 端對端複查發現 `tender_recommendation_history` 6 筆 status=error | 複查 SQL |
| 2026-05-29 11:23 | docker-compose 補 8 個 LINE_* env → 真活恢復 | commit `706b2e22` |
| 2026-05-29 12:15 | Owner 追問「派工 LINE 通知也中斷？」→ 5 鏈擴大盤點 + 派工 Flex sent=1/1 | 對話 |
| 2026-05-29 12:30 | **Owner 提供 4 種 LINE 訊息範例反證 PM2 模式真活 → 校正時長為 40h 23min** | owner 證據 |

### 期間漏推清單 (5/27 19:00 ~ 5/29 11:23，共 12 條訊息)

| # | 時間 | 訊息類型 |
|---|---|---|
| 1 | 5/27 22:00 | 每日反思 (daily_self_reflection) |
| 2 | 5/28 00:30 | 派工進度 Flex (push_dispatch_progress) |
| 3 | 5/28 08:00 | 每日晨報 (morning_report) |
| 4 | 5/28 22:00 | 每日反思 |
| 5 | 5/29 00:30 | 派工進度 Flex |
| 6 | 5/29 08:00 | 每日晨報 |
| 7-12 | 5/29 09:00 | 業務推薦 × 6 筆 (揭發者) |

---

## 2.5 真正引爆點：OA-3 PM2 廢除（治理動作引發的回退）

校正版時間軸揭示**真根因不是「docker-compose 沒注入 env」這個 3 個月舊問題**，而是
**OA-3 PM2 廢除這個治理動作切換流量時未察覺 env 依賴**：

```
[Before PM2 廢除]
  cloudflared → host:8001 (PM2 native uvicorn)
              → 直接讀 host /home/.../.env LINE_* ✓ 真活

[After PM2 廢除 commit ed81bf87 / 1ea91196]
  cloudflared → ck_missive_backend (docker container)
              → 讀 container env LINE_* 全空 → enabled=False ✗ silent disabled
```

### 為何 OA-3 廢除時沒察覺

1. **OA-3 廢除 pre-flight checklist** (commit `5e4f7650` / `553d159d`) 沒檢查 LINE_* env 對齊
2. **同治理動作 L48** (5/27) 補了 CK_SSO_* env，因為 SSO 失敗會 hard-fail（用戶報「無法登入」），
   立即被發現
3. **LINE 失敗是 silent skip**（return False，沒 error 也沒 alarm），所以同時期 PM2 廢除引入
   的回退沒被同時揭發
4. 無對應的 fitness audit 自動掃描「治理切換後 env 對齊」（fitness step 57 是事後補的）

### 治理動作回退模式

這次事件**不是新功能 bug**，是「治理動作（PM2 廢除）切換 runtime context 但未同步配置」
反模式。同型事故（L48 SSO env 配套）已在同 PM2 廢除期間發生過一次（已修），但 LINE_*
這 8 個 env 漏掉了。

**寫進 cross-file-ssot-governance.md** 應有「治理動作 checklist」一節：
- runtime context 切換時，列出**所有從 host env 讀的服務**
- 對比 target runtime（container/PM2/其他）是否能獲得同樣 env
- 若不能，新增 env 注入或 secret mount

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

## 10.5 受影響鏈擴大盤點（2026-05-29 12:15 owner 追問後追加）

Owner 提問「派工 LINE 通知也中斷？」促使全面排查。**5 條 LINE push 鏈一次性驗活**結果：

```
[修法後 5/29 12:15 驗活]
1. LineBotService.enabled = True
2. LINE_ADMIN_USER_ID env exists: True
3. _get_push_targets returns: 1 users (owner 自己)
4. morning_report LINE channel ready: True
5. push_admin_alert: True
```

**Owner 5/29 12:15 ack 收到 [L51 audit] 驗活訊息** + 派工進度 Flex（3 筆 overdue）。

### 為何沒一次發現？

我前一輪修法時**只看 business_recommendation 那條鏈**，沒做擴大盤點。Owner 一句反問
立即揭發**整個 LINE 通報生態**都被同一個 env 缺漏影響。

**教訓**：silent failure 修復時，**不只修觸發者那條鏈，要排查所有依賴同 root cause 的鏈**。
本次 root cause 是「LINE_BOT_ENABLED env 缺」，影響範圍是「所有讀此 env 的 service」。

### 後續行動（v6.11 收尾前必補）

1. **fitness step 57 已落地** — 防同型事故反覆
2. **加 admin LINE bind 真活 startup probe**：
   ```python
   # main.py startup hook
   if settings.ENVIRONMENT == "production":
       svc = get_line_bot_service()
       admin_id = os.getenv("LINE_ADMIN_USER_ID")
       if not (svc.enabled and admin_id):
           logger.error("[STARTUP] LINE notify chain not ready in production "
                        "(enabled=%s, admin_id=%s)", svc.enabled, bool(admin_id))
           # 不 raise（避 hard-fail prod），但發 alarm metric
   ```
3. **每週 cron 跑活體確認**：發一條 "LINE healthcheck pulse" 給 admin，連續 N 週 silent 才算真活

---

## 10.6 L51 5 防護層 silent regression 揭發（2026-05-30 10:25 loop 複查）

L51.7 Sprint 1 完成後 ScheduleWakeup 複查發現 `v7_channel_diversity` 仍為 0
（期望 ≥1 因 LINE 真活）。深入追查揭發**新 silent regression**：

```
container 內 grep MESSAGING_PUSH_TOTAL → 0 matches!
→ messaging_default.py 是舊版（L51 task e 5 防護層的 Counter 沒到 container）
```

**真因**：
- 5/29 commit `5d03562f` 加 messaging_default.py Counter + main.py eager import
- 部署用 `docker cp` 修法到 container（不 rebuild image）
- 後續某次 `docker compose restart` 或 `up -d` 重起時，docker cp 修法**遺失**
- 結果：image 內 messaging_default 仍是 5/28 以前的版本（無 Counter）

**確認時序**：09:00 business_recommendation cron 跑了 6 筆 pushed=6（從
`tender_recommendation_history` 表確認真活）但 `/metrics` 完全沒
`messaging_push_total` — Counter 從未在主進程內被 import 過。

**修法**：`docker compose build backend && up -d backend`（force rebuild image）
- container 內 grep `MESSAGING_PUSH_TOTAL` 返 7 ✓
- `/metrics` 15 labels 預宣告 ✓
- 5 防護層真活恢復

**連帶教訓 (#8)**：
- **docker cp 修法不可持久** — 只能用於緊急驗證，必須跟 rebuild image
- 每次新功能上 production 應有 SOP：
  1. commit code
  2. docker compose build {service}
  3. docker compose up -d {service}（不只 restart）
  4. 驗 container 內 file mtime + content
- **fitness step 應加 image_freshness_check**：對比 image build 時間 vs 最後 commit
  時間，>24h 即 warning（image 比 code 舊）

**潛伏影響盤點（過去 ~36h）**：
- 5/29 12:00 ~ 5/30 09:30 期間（rebuild 前），所有理論上應 inc 的 push 都
  沒寫進 messaging_push_total Counter
- LINE push 仍真活（owner 收到訊息），但「observability 觀測」silent disabled
- 這正是「修法部署成功」假象 — 真正生效需要 image 包含

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

4. **silent failure 修復必排查同 root cause 全鏈**
   Owner 5/29 12:15 反問「派工 LINE 通知也中斷？」一句揭發影響範圍從「1 條鏈 6 筆 error」
   擴大到「5+ 條鏈 3 個月 27 天從未真實推送」。下次修法應**先列受影響鏈清單**再修。

5. **觀測閉環設計的「邊際價值」遠超預期**
   L51 task B history table 設計初衷是業務轉換率追蹤，連帶揭發了：
   - business_recommendation cron silent fail (直接揭發)
   - admin push 整鏈中斷 (root cause 追蹤)
   - 派工 LINE Flex / 早報 LINE / 夜間吹哨 LINE 全部中斷 (擴大盤點)
   - L48 同型事故仍在反覆 (寫進 audit 發現)
   單一 design choice 連帶解了 4 個潛伏問題。

6. **錯誤分析比 silent fail 本身更危險**
   2026-05-29 12:00 我寫「3 個月 27 天 silent disabled」是**未經驗證的擴大推論**。
   Owner 12:30 提供 5/25 / 5/27 / W21 LINE 訊息範例**反證 PM2 模式真活**，
   迫使重新校正為「40h 23min」。錯誤分析會誤導後續決策（例如：
   若 owner 相信 3 個月時長，可能會懷疑 morning_report 整體設計
   有問題；實際只需修 PM2→docker 切換配套）。

   **教訓**：時長/影響範圍宣稱前**必須**列證據鏈，不要從「.env 沒注入」直線推到
   「從建立以來都壞」。應該問「過去真的有推過嗎？如何證明？」（5/25 訊息證據）。

7. **治理動作（PM2 廢除）回退是隱性風險源**
   v6.11 OA-3 PM2 廢除（治理收斂動作）的副作用引爆本次事件。
   未來治理動作（v6.12 規劃）應有「runtime context 切換 checklist」前置：
   - 列出所有從 host env 讀的服務
   - 對比 target runtime 是否能讀同樣 env
   - 主動推 startup self-test 訊息（活體確認）

   未做這個 checklist，就會反覆發生「修了 A 但無心壞了 B」。

8. **docker cp 修法不可持久 — 部署 SOP 必須含 image rebuild**
   L51 5 防護層 5/29 commit + docker cp 「驗證 OK」假象，實際 image 內
   仍是舊版 messaging_default.py（無 Counter）。後續 docker compose 重起
   時 docker cp 修法遺失，但因「部署成功」感覺良好沒去複查。

   5/30 ScheduleWakeup 複查才發現 36h 期間 messaging_push_total **從未真實 inc 過**。
   LINE 還在推（owner 收訊息），但「失敗率監控」觀測 silent disabled。

   **教訓**：每次新功能部署應有 SOP checklist：
   - [ ] commit code
   - [ ] `docker compose build {service}`
   - [ ] `docker compose up -d {service}`（不只 restart）
   - [ ] 驗 container 內 file mtime 在合理範圍
   - [ ] grep 關鍵新字串確認進 image
   - [ ] fitness step 加 image_freshness_check：image 比 commit 舊 >24h 即 warning
