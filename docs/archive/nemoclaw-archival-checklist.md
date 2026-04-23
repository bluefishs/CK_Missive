# NemoClaw / OpenClaw 歸檔執行清單

> **Deadline**：2026-05-26（ADR-0015 歸檔日）
> **Status**：進行中（2026-04-22 建立）
> **Owner**：專案 Owner
> **關聯**：ADR-0014（Hermes 取代 OpenClaw）、ADR-0015（NemoClaw 退場）、ADR-0030（Hermes GO/NO-GO）

---

## 總覽

Grep 掃描結果（2026-04-22）：

- **總引用數**：423 處
- **影響檔案**：99 個
- **分類**：5 類（歷史保留、活躍更新、stub 刪除、deprecated 段落清理、測試更名）

```
python -c "print('實際掃描：'); " && grep -rn "nemoclaw\|openclaw" --include="*.{py,ts,tsx,md,yml,yaml,json}" | wc -l
```

---

## 分類與執行計畫

### 類別 A — 歷史紀錄（**保留**，不動）

| 檔案 / 目錄 | 引用數 | 理由 |
|---|---|---|
| `docs/adr/0014-*.md` | 14 | 決策歷史 |
| `docs/adr/0015-*.md` | 15 | 決策歷史 |
| `docs/adr/0016-*.md` | 1 | 決策歷史 |
| `docs/adr/0022-*.md` | 1 | 決策歷史 |
| `.claude/CHANGELOG.md` | 29 | 版本變更歷史 |
| `.claude/retros/*.md` | 3 | 回顧紀錄 |
| `docs/reports/archive/*.md` | 57 | 舊版歸檔報告 |
| `docs/reports/SESSION_20260329_*.md` | 1 | Session 紀錄 |
| `docs/reports/nemoclaw_self_interaction_roadmap.md` | 7 | 歷史路線圖 |
| `docs/reports/Skills_Capability_Map_2026Q1.md` | 3 | 季度快照 |
| `docs/reports/SYSTEM_REVIEW_20260329.md` | 2 | 系統覆盤 |
| `docs/presentations/CK_Missive_Overview.md` | 7 | 對外簡報 |
| `docs/specs/finance_erp_*.md` | 7 | 規格歷史 |
| `docs/specs/invoice_system_*.md` | 6 | 規格歷史 |
| `docs/specs/erp_*.md` | 2 | 規格歷史 |

**合計**：~155 處引用，**不需處理**。

### 類別 B — 活躍文件（**更新**，2026-05-26 前完成）

| 檔案 | 引用數 | 建議動作 |
|---|---|---|
| `CLAUDE.md` | 4 | 確認是否已改為 Hermes + Cloudflare Tunnel 敘述（v5.6 已改，檢查殘留） |
| `docs/HERMES_MIGRATION_PLAN.md` | 16 | 狀態更新（反映 ADR-0030 GO/NO-GO 重訂） |
| `docs/hermes-skills/README.md` | 3 | 確認描述為現況 |
| `docs/openclaw-skill-update.md` | 3 | **加顯眼 deprecated 標頭**（或移入 archive/） |
| `docs/MULTICHANNEL_SETUP_GUIDE.md` | 20 | 移除 OpenClaw 段落，僅保留 LINE / Telegram 直連 |
| `docs/LINE_OPENCLAW_OPERATIONAL_GUIDE.md` | 20 | **整檔標 archived**（移入 docs/archive/） |
| `docs/DOCKER_SECRETS_PHASE1.md` | 1 | 確認描述為現況 |
| `docs/SECRET_ROTATION_SOP.md` | 6 | 移除 OpenClaw token 輪換段落 |
| `docs/SECURITY_THREAT_MODEL.md` | 4 | 更新 Threat Model 移除 OpenClaw component |
| `docs/AUTH_FLOW_DIAGRAM.md` | 2 | 檢查流程圖是否還畫 OpenClaw |
| `docs/CLOUDFLARE_TUNNEL_*.md` | 3 | 確認為現況 |
| `docs/ARCHITECTURE_REVIEW_2026-04-15.md` | 2 | 歷史記錄，標 Snapshot |
| `docs/README.md` | 2 | 移除 OpenClaw 描述 |
| `.claude/rules/skills-inventory.md` | 6 | 移除 OpenClaw 相關 entry |
| `.claude/rules/architecture-backend.md` | 1 | 更新 |
| `.claude/skills/multi-channel.md` | 9 | 更新為 Hermes-centric |
| `.claude/skills/ai-development.md` | 1 | 小改 |

**合計**：~109 處引用，**需逐檔編輯**。

### 類別 C — Re-export / Stub（**刪除**，Hermes GO 後）

| 檔案 | 引用數 | 建議動作 | Blocker |
|---|---|---|---|
| `backend/app/services/ai/misc/nemoclaw_agent.py` | 3 | 刪除（`MissiveAgent` 已取代） | Hermes GO 後 + 所有 import 遷移完畢 |
| `backend/app/services/ai/misc/__init__.py` 的 NemoClawAgent re-export | 2 | 刪除 | 同上 |
| `backend/app/api/endpoints/ai/agent_nemoclaw.py`（若存在） | 檢 | 已 renamed to agent_capability | 驗證 routes.py |

### 類別 D — Deprecated 段落清理（**清理**，低風險）

| 檔案 | 引用數 | 建議動作 |
|---|---|---|
| `docker-compose.multichannel.yml` | 7 | **移除 openclaw service 整段**（profiles: ["deprecated"] 6 週未啟動） |
| `docker-compose.dev.yml` | 1 | 檢查 openclaw 引用是否殘留 |
| `docker-compose.production.yml` | 1 | 同上 |
| `docker-compose.infra.yml` | 1 | 同上（應僅註解） |
| `backend/config/inference-profiles.yaml` | 1 | 檢查是否 NemoClaw profile 殘留 |
| `backend/config/agent-policy.yaml` | 1 | 檢查 routing rule 殘留 |
| `backend/mcp_server.py` | 3 | 檢查是否 MCP tool 定義含 nemoclaw |

### 類別 E — 程式碼引用（**重點檢查**，可能需改名或調整）

| 檔案 | 引用數 | 建議動作 |
|---|---|---|
| `backend/app/services/ai/federation/federation_discovery.py` | **14** | 檢查是否是 domain name 用詞，改為 `missive_domain` |
| `backend/app/services/ai/federation/federation_client.py` | 8 | 同上 |
| `backend/app/services/ai/federation/federation_delegation.py` | 4 | 同上 |
| `backend/app/services/ai/tools/tool_definitions.py` | 5 | 檢查是否仍定義 openclaw 相關 tool |
| `backend/app/services/ai/agent/shadow_logger.py` | 1 | 檢查 provider label |
| `backend/app/services/ai/agent/provider_resolver.py` | 1 | 檢查 provider mapping |
| `backend/app/services/ai/proactive/proactive_triggers.py` | 1 | 檢查 channel |
| `backend/app/services/skill_evolution_service.py` | 4 | 檢查 ref |
| `backend/app/services/sender_context.py` | 1 | 檢查 channel enum |
| `backend/app/services/line_flex_builder.py` | 1 | 檢查文案 |
| `backend/app/services/tender_subscription_scheduler.py` | 1 | 檢查推播通道 |
| `backend/app/services/ai/core/token_usage_tracker.py` | 1 | 檢查 provider name |
| `backend/app/services/ai/domain/digital_twin_service.py` | 1 | 檢查 |
| `backend/app/services/ai/misc/skill_scanner.py` | 1 | 檢查 |
| `backend/app/schemas/ai/rag.py` | 1 | 檢查 enum 值 |
| `backend/app/api/endpoints/ai/__init__.py` | 1 | 檢查 import |
| `backend/app/api/endpoints/ai/digital_twin.py` | 4 | 檢查 endpoint |
| `backend/app/api/endpoints/ai/agent_query.py` | 1 | 檢查 |
| `backend/app/api/endpoints/ai/agent_query_sync.py` | 3 | 檢查 |
| `backend/app/api/endpoints/ai/agent_capability.py` | 1 | 檢查（本就 renamed from nemoclaw） |
| **測試檔案（7 個）** | 55 | 隨實作調整；已廢 test 可 skip 或更名 |
| **前端檔案（8 個）** | 18 | JSDoc / 字串 / 類型 — 可批次 rename |

---

## 執行順序（Sprint Plan）

### Sprint 1（本週，2026-04-22 ~ 04-28）：文件批次

- [ ] 類別 B：更新 17 份活躍文件（低風險）
  - 把 `LINE_OPENCLAW_OPERATIONAL_GUIDE.md` 整檔加 `> **ARCHIVED**：此文件已被 Hermes 取代，見 docs/HERMES_MIGRATION_PLAN.md` 標頭
  - 移除 `docs/openclaw-skill-update.md` 或移入 `docs/archive/`
  - 更新 `HERMES_MIGRATION_PLAN.md` 反映 ADR-0030

### Sprint 2（第 2 週，2026-04-29 ~ 05-05）：Deprecated 段落清理

- [ ] 類別 D：刪除 7 處 deprecated yaml / config 段落
  - 移除 `docker-compose.multichannel.yml` 的 `openclaw:` 整個 service block
  - 清理 `docker-compose.{dev,prod,infra}.yml` 的註解殘留
  - 刪除 `inference-profiles.yaml` / `agent-policy.yaml` 的 openclaw rule
  - 清理 `mcp_server.py` 的 nemoclaw tool

### Sprint 3（第 3 週，2026-05-06 ~ 05-12）：程式碼引用審計

- [ ] 類別 E：針對 31 處程式碼引用逐一檢查
  - 多數是字串 label / enum 值，可直接 rename
  - `federation_*.py`：確認 domain 命名是否需遷移為 `missive_*`
  - 前端 JSDoc / 字串批次 rename

### Sprint 4（Hermes GO 後）：Stub 刪除

- [ ] 類別 C：刪除 re-export stubs
  - `nemoclaw_agent.py` 刪除
  - `__init__.py` 的 re-export 移除
  - 所有 `from ...nemoclaw_agent import` 遷移為 `from ...missive_agent import`

### Sprint 5（2026-05-20 ~ 05-26）：Repo Archive

- [ ] 整個 `CK_NemoClaw/` repo 標 archived（GitHub level）
- [ ] 整個 `CK_OpenClaw/` repo 標 archived（GitHub level）
- [ ] 在兩 repo 各放一份 `ARCHIVED.md` 說明後繼者

---

## 驗收條件（2026-05-26）

- [ ] `grep -r "nemoclaw\|openclaw" backend/app/ | grep -v -E '(\.pyc|\.md|#)'` 只剩 test 的 legacy name
- [ ] `grep -r "nemoclaw\|openclaw" frontend/src/ | grep -v '\.md'` 清空或僅剩註解
- [ ] docker-compose *.yml 中無啟動路徑依賴 OpenClaw
- [ ] 所有 active 文件（類別 B）已更新完畢
- [ ] CK_NemoClaw + CK_OpenClaw repo GitHub archived

---

## 風險與回滾

| 風險 | 緩解 |
|---|---|
| 測試 break | 每個 sprint 結束跑 `cd backend && python -m pytest`；失敗立刻 revert |
| Hermes GO 延遲 → stub 無法刪除 | Sprint 4 不是硬 deadline；GO 後再執行 |
| 文件讀者誤解「已歸檔」 | 每個 archived 檔案加顯眼 `> **ARCHIVED**` 標頭 |
| Federation 命名遷移 break 聯邦 | Sprint 3 程式碼遷移配合 regression test；需先審計跨 repo 契約 |

---

## 狀態追蹤

| Sprint | 狀態 | 完成日 | Notes |
|---|---|---|---|
| 1（文件） | 🟡 部分完成 | 2026-04-22 | LINE_OPENCLAW_OPERATIONAL_GUIDE + openclaw-skill-update 加 ARCHIVED 標頭 |
| 2（deprecated 段落） | ✅ 完成 | 2026-04-23 | docker-compose.multichannel.yml openclaw service 移除；mcp_server.py docstring 通用化 |
| 3（程式碼引用） | ⬜ pending | — | 31 處 federation_* / test 檔案 / 前端 JSDoc 待審計 |
| 4（stub 刪除） | ⬜ blocked on Hermes GO | — | 等 ADR-0030 決策（2026-05-20）|
| 5（repo archive） | ⬜ pending | — | 需 GitHub admin，2026-05-26 deadline |

---

## 備註

- 本 checklist 由 session 2026-04-22 產生（v5.9 整合優化 sprint）
- 若 Hermes NO-GO（ADR-0030），整個 checklist 時程保留但 stub 刪除（Sprint 4）暫緩
- 最終檢核 2026-05-26，若未達 100% 則延期至 v6.0
