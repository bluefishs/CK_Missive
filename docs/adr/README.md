# Architecture Decision Records (ADR)

本目錄記錄 CK_Missive 專案的重要架構決策。每筆 ADR 回答三個問題：
**為什麼做這個決定？做了什麼？帶來什麼後果？**

## 狀態說明（ADR-0029）

| 狀態 | 含義 |
|------|------|
| `proposed` | 提案中，尚未實作 |
| `accepted` | 決策已確定，正在影響當前開發 |
| `deprecated` | 已排定移除 |
| `superseded` | 被新的 ADR 取代 |
| `archived` | 決策穩定 > 6 個月，已融入日常；歷史沉澱，僅供考古 |
| `removed` | 程式碼已從專案移除 |
| `rejected` | 考慮過但未採用 |

**Active = proposed + accepted**，健康區間 ≤ 15；>20 觸發瘦身 sprint；>25 必須開 session review。

## 當前統計（自動產生）

```bash
python scripts/checks/adr_lifecycle_check.py
```

最近一次執行：Active 17 / Archived 10 / Removed 1 — **[GREEN-]** 接近健康區間。

---

## 活躍 ADR（current）

| # | 標題 | 狀態 | 日期 |
|---|------|------|------|
| [0011](0011-ai-config-db-crud-removed.md) | AI 配置 DB CRUD 移除（超前開發教訓） | removed | 2026-02-27 |
| [0012](0012-tender-search-module.md) | 標案搜尋模組 | accepted | — |
| [0013](0013-unified-coding-system.md) | 統一編碼系統 | accepted | 2026-04-02 |
| [0014](0014-hermes-replace-openclaw.md) | Hermes Agent 取代 OpenClaw | accepted | 2026-04-14 |
| [0015](0015-retire-nemoclaw-cloudflare-tunnel.md) | 廢止 NemoClaw，Cloudflare Tunnel 取代 | accepted | — |
| [0016](0016-multi-project-platform-subdomain.md) | 多專案平坦分域 | accepted | — |
| [0019](0019-structlog-unified-logging.md) | structlog 統一 JSON 日誌 | accepted | — |
| [0021](0021-asyncpg-concurrent-session.md) | asyncpg 並行 session 隔離 | accepted | 2026-04-19 |
| [0022](0022-memory-wiki-self-evolving-assistant.md) | Memory Wiki 自進化助理 | accepted | — |
| [0023](0023-kunge-consciousness-launch.md) | 坤哥意識體上線 | accepted | 2026-04-20 |
| [0024](0024-calendar-visibility-case-collaborator.md) | Calendar Visibility 承辦同仁 | accepted | — |
| [0025](0025-user-identity-unification.md) | Identity Unification 分身合併 | accepted | — |
| [0026](0026-work-record-calendar-sync.md) | WorkRecord ↔ Calendar Sync | accepted | — |
| [0027](0027-telegram-push-disabled-content-sanitizer.md) | Telegram 主動推播關閉 + sanitizer | accepted | 2026-04-21 |
| [0028](0028-error-contract-silent-failure-policy.md) | 錯誤合約化 + Silent Failure 政策 | accepted | 2026-04-22 |
| [0029](0029-adr-lifecycle-policy.md) | ADR Lifecycle Policy | accepted | 2026-04-22 |
| [0030](0030-hermes-go-no-go-revision.md) | Hermes GO/NO-GO 決策重訂 | accepted | 2026-04-22 |
| [0031](0031-frontend-page-consolidation.md) | Frontend Page Consolidation v6.0 | accepted | 2026-04-22 |
| [0032](0032-tender-multi-source-identifier-unification.md) | 標案多源識別統一 | accepted | 2026-04-24 |
| [0033](0033-disable-password-authentication.md) | 關閉帳密登入 | accepted | 2026-04-24 |
| [0034](0034-dynamic-role-permissions.md) | 動態角色權限 | accepted | 2026-05-07 |
| [0035](0035-gitnexus-bridge-agent-tool.md) | GitNexus Bridge — Agent Code Intelligence | proposed | 2026-05-16 |

---

## 歷史 ADR（archived — 首波 2026-04-22）

決策已穩定執行 > 6 個月、融入日常開發、不再是「活的」辯論。
檔案位於 `archived/` 子目錄，保留作為考古與 onboarding 教材。

| # | 標題 | 原狀態 | 歸檔理由 |
|---|------|------|------|
| [0001](archived/0001-groq-primary-ollama-fallback.md) | Groq 為主、Ollama 本地 fallback | accepted | 已被 Token Tracker + 5 provider routing (v5.5.x) 取代 |
| [0002](archived/0002-httponly-cookie-csrf-auth.md) | httpOnly Cookie + CSRF + Token Rotation | accepted | 2026-01 交付，穩定 3+ 月 |
| [0003](archived/0003-internal-network-auth-bypass.md) | 內網 IP 免認證策略 | accepted | 2026-01 交付，穩定 3+ 月 |
| [0004](archived/0004-ssot-type-architecture.md) | 前後端型別 SSOT 架構 | accepted | 已全面落地，不再辯論 |
| [0005](archived/0005-mixed-mode-deployment.md) | 混合部署模式 | accepted | 2026-02 交付，穩定運行 |
| [0006](archived/0006-pgvector-document-embeddings.md) | pgvector 768D 文件向量搜尋 | accepted | 穩定運行；若升 1024D 開新 ADR |
| [0007](archived/0007-four-layer-ai-architecture.md) | AI 四層架構 | accepted | 已演進為 Agent + Orchestrator（見 ADR-0022） |
| [0008](archived/0008-repository-flush-only-strategy.md) | Repository flush-only 交易策略 | accepted | 規範已融入日常開發 |
| [0009](archived/0009-agent-rule-based-self-correction.md) | Agent 規則式自動修正 | accepted | 被 ADR-0022 Memory Wiki 進化機制取代 |
| [0010](archived/0010-qwen3-4b-local-llm.md) | qwen3:4b 本地模型 | accepted | 被 ADR-0023 坤哥 + Gemma 4 取代 |

---

## 建立新 ADR

1. 複製 [TEMPLATE.md](TEMPLATE.md)
2. 命名為 `NNNN-short-title.md`（四位數序號 + kebab-case）
3. 填寫背景、決策、後果；**必須**標明 `狀態` 與 `日期`
4. 若取代既有 ADR，顯式標記 `superseded by ADR-XXXX`
5. 更新本 README 的索引表
6. 或使用 `/adr new "標題"` 命令自動建立

## ADR 治理自動化

- `scripts/checks/adr_lifecycle_check.py` — 統計 active_count 與狀態分佈
- 建議加入 `scripts/checks/verify_architecture.py` 作為 CI 檢查項
- 半年一次 review（下次：2026-10-22）— 判斷是否可再 archive 一批
