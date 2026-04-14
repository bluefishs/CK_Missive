# Hermes Agent 遷移計畫（取代 OpenClaw）

> **狀態**: active
> **依據**: ADR-0014
> **日期**: 2026-04-14 啟動
> **預計完成**: 2026-05-12（4 週）

---

## 里程碑總覽（合併 ADR-0015 Cloudflare Tunnel）

| Phase | 目標 | 期程 | 可回滾 |
|---|---|---|---|
| P0 | 基線採集 + 環境準備 | Day 0–3 | — |
| P1 | **Cloudflare Tunnel 上線** + Hermes 安裝 + Bridge Tool 就緒 | Day 4–10 | ✅ |
| P2 | Telegram 灰度切換（webhook 走 CF Tunnel） | Day 11–17 | ✅（24h） |
| P3 | Discord 切換 + LINE 下線 | Day 18–24 | ⚠️ LINE 下線不可逆 |
| P4 | OpenClaw 容器歸檔 + **NemoClaw repo 歸檔** | Day 25–28 | — |

---

## Phase 0 — 基線採集（Day 0–3）

### 完成條件
- [x] Shadow Logger 啟用（0.3 採樣）
- [x] PII 遮罩就緒（身分證/電話/email）
- [x] 30 天自動清理
- [x] 測試覆蓋（test_shadow_logger.py）
- [ ] 3 天基線資料累積 ≥ 200 筆
- [ ] 產出 baseline report（`node scripts/checks/shadow-baseline-report.cjs`）

### 關鍵指標（baseline）
- 各通道 p50/p95/max 延遲
- 成功率（目標 ≥ 95%）
- Tool-use 分佈 Top 10
- 錯誤碼分佈

---

## Phase 1 — Hermes 安裝與 Bridge（Day 4–10）

### CK_NemoClaw repo 工作（非本 session 範圍）
```bash
# 預計在 CK_NemoClaw session 執行
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes config set llm.provider ollama
hermes config set llm.endpoint http://host.docker.internal:11434
hermes config set llm.model gemma4:8b-q4
hermes gateway setup telegram
```

### CK_Missive repo 工作
1. **Bridge Skill 規格**: `docs/hermes-skills/ck-missive-bridge/SKILL.md`（本 session 產出）
2. **Bridge Tool 規格**: `docs/hermes-skills/ck-missive-bridge/tool_spec.json`（本 session 產出）
3. **API 合約鎖定**：`/api/ai/agent/query_sync` 視為 public contract，任何 breaking change 需走 ADR

### 驗收
- Hermes CLI 能透過 `query_missive` tool 取得 Missive agent 回應
- Telegram 私訊測試 → Hermes gateway → Missive backend 往返成功

---

## Phase 2 — Telegram 灰度（Day 11–17）

1. **雙跑期**（Day 11–13）
   - Telegram webhook 仍指向 OpenClaw
   - Hermes gateway 另用 test bot 對照測試
   - 每日比對 Shadow Logger trace vs Hermes log
2. **切換**（Day 14）
   - 正式 Telegram bot webhook 改指 Hermes gateway
   - OpenClaw 停止處理 Telegram（config 移除）
3. **觀察**（Day 15–17）
   - 回滾窗口 24h：若 p95 延遲 > 2× baseline 或成功率 < 90% → 回切

### 回滾步驟
```bash
# webhook 回指 OpenClaw
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d url=https://<openclaw-host>/webhook/telegram
```

---

## Phase 3 — Discord 切換 + LINE 下線（Day 18–24）

### Discord
- Interactions Endpoint URL 改指 Hermes gateway `/discord/interactions`
- 同樣 24h 回滾窗口

### LINE 下線（不可逆）
1. **預告**（Day 18）：在 LINE 小花貓 Aroan 發送公告訊息，指引用戶改用 Telegram/Discord/Web UI
2. **移除 webhook**（Day 22）：LINE Developers Console 解除 webhook URL
3. **保留程式碼**：`backend/app/services/line_bot_service.py` 等檔案保留（不刪，視需要復用 LINE Flex 格式化邏輯於他處）
4. **歸檔歷史**：OpenClaw 對話記錄 export → `backups/openclaw-line-history-20260505.json`

---

## Phase 4 — OpenClaw 歸檔（Day 25–28）

1. `CK_NemoClaw/docker-compose.yml` 的 `openclaw` service **註解**（保留 2 週，便於回滾）
2. `C:\Users\User1\.openclaw\` 打包 → `backups/openclaw-config-20260512.tar.gz`
3. Day 42：確認無事故 → 正式刪除 openclaw service
4. Memory 更新：
   - 移除 `line_openclaw_integration.md`
   - 新增 `hermes_agent_runtime.md`
   - `hermes_openclaw_deferred.md` → superseded by ADR-0014
5. CLAUDE.md / rules/skills-inventory.md 同步更新通道章節

---

## 風險登錄

| 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|
| Gemma 4 中文 Tool-Calling 品質不如 Haiku | 中 | 高 | Shadow 對照期延長；備案切 Groq Llama-3.3-70B |
| Hermes skill 學習閉環與 Missive orchestrator 衝突 | 中 | 中 | 職責切分：Hermes = 通道側短期記憶；Missive = 資料側長期圖譜 |
| LINE 用戶抗拒遷移 | 高 | 中 | Telegram bot 提供相同 Skill 集 + 公告 2 週 |
| Hermes 社群/安全更新停滯 | 低 | 中 | MIT 授權可 fork；鎖 pinned commit |
| Telegram webhook HTTPS 憑證問題 | 低 | 低 | Hermes gateway 支援 Let's Encrypt / Cloudflare Tunnel |

---

## 職責切分（雙 Agent 共存）

| 職責 | Hermes (gateway) | Missive orchestrator |
|---|---|---|
| 通道接收 / 格式化 | ✅ | ❌ |
| 使用者短期記憶（session） | ✅（Hermes FTS5） | ❌ |
| 使用者長期 profile | 讀 | ✅ 寫 |
| 文件檢索 / RAG | 呼叫 Missive tool | ✅ |
| 知識圖譜 | 呼叫 Missive tool | ✅ |
| Skill 自我累積 | ✅ | ❌ |
| 審計 trace | 轉發 request_id | ✅ `agent_trace` 寫入 |

---

## 成功條件

- [ ] Phase 4 結束，OpenClaw 已歸檔
- [ ] Haiku API 支出降至 USD 0
- [ ] Telegram/Discord 回覆 p95 < baseline × 1.2
- [ ] 成功率 ≥ 95%
- [ ] 無 P0/P1 級事故 14 天
