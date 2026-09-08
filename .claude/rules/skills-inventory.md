# Skills / Commands / Agents 清單

> 2026-08-27 /doctor 瘦身：檔頭的版本變更史已移入 `.claude/CHANGELOG.md`，
> 可由 `ls` 推導的清單改為指標。**保留下來的是「誰在跑它」這種推導不出來的資訊。**

## v6.9 範本治理體系新增資產（給 lvrland/PileMgmt 等子專案引用）

| FQID | 類型 | 用途 |
|---|---|---|
| `CK_Missive#provider_circuit_breaker_v1.0` | Module L2 | LLM provider 連續失敗自動 skip（5 連敗 → 5min OPEN）|
| `CK_Missive#alias_rls_coverage_audit_v1.0` | Detector L4 | 靜態掃 endpoints 找 ADR-0025 半接通候選 |
| `CK_Missive#domain_score_freshness_check_v1.0` | Detector L4 | L29 watchdog — domain_scores Redis 寫入鏈活體 |
| `CK_Missive#metrics_populate_errors_total_v1.0` | Metric L2 | /metrics endpoint per-scrape silent skip 偵測 |
| `CK_Missive#memory_diary_append_failures_total_v1.0` | Metric L2 | diary fire-and-forget 失敗 4 類別計數 |
| `CK_Missive#L29_lesson_v1.0` | Doc L2 | dict key contract drift × 涵蓋率 × silent except 三重疊加教材 |
| `CK_Missive#telegram_permanent_ban_runbook_v1.0` | Runbook L2 | ADR-0027 後續永封應急（4 plan） |
| `CK_Missive#cloudflare_tunnel_outage_runbook_v1.0` | Runbook L2 | Tunnel 故障 5 plan + Bypass policy 順位陷阱 |
| `CK_Missive#prometheus_alerting_degraded_runbook_v1.0` | Runbook L2 | alerting 失明應急 + §6 緊急降級 |

## v5.10.x 範本治理體系新增資產（給 lvrland/PileMgmt 等子專案引用）

| FQID | 類型 | 用途 |
|---|---|---|
| `CK_Missive#agent_evolution_health_v1.0` | Detector L4 | 坤哥 evolution 引擎健康診斷 |
| `CK_Missive#lessons_drift_check_v1.0` | Detector L4 | LESSONS_REGISTRY 自我保護 |
| `CK_Missive#dead_ui_detector_v1.0` | Detector L4 | 後端有但前端缺 UI 偵測 |
| `CK_Missive#notify_consumers_v1.0` | Detector L4 | Pull-based 升級通知 |
| `CK_Missive#install-template-to_v1.0` | Tool L4 | 跨 repo 一鍵部署 |
| `CK_Missive#LESSONS_REGISTRY_v1.0` | Doc L2 | 22 條 lessons SSOT |
| `CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0` | Doc L2 | 跨 repo 引用治理規範 |
| `CK_Missive#WAVE_1_PLAYBOOK_v2.2` | Doc L2 | 7 SOP + 1 anti-pattern |
| `CK_Missive#WAVE_2_TO_7_RETROSPECTIVE_v1.0` | Doc L2 | 多 Wave 連續執行回顧 |
| `CK_Missive#consumers_v1.0` | Config L4 | 7 consumer registry |
| `CK_Missive#PULL_REQUEST_TEMPLATE_v1.0` | Doc L4 | 範本貢獻 PR 模板 |
| `CK_Missive#AliasIntegrationDrawer_v1.0` | Component L1 | Drawer 雙 Tab 模式範例 |

## Slash Commands (可用指令)

> 指令清單已移除（2026-08-27 /doctor）——`ls .claude/commands/` 直接看得到，
> 每支指令的用途寫在它自己的檔頭。

## 領域知識 Skills (自動載入)

> ⚠️ **2026-08-27 /doctor 實測：這一節描述的機制沒有接通。**
> `.claude/skills/` 底下是 **29 個平鋪 `.md`、0 個 `<name>/SKILL.md`** ——
> 而 Claude Code 只從 `<name>/SKILL.md` 載入 skill
> ⇒ **那 22 份「自動載入」的領域知識檔從來沒有被當成 skill 載入過**，
> 它們是需要時才 Read 的一般文件。
>
> 要真的變成 skill：`mkdir .claude/skills/<name>/ && mv <name>.md $_/SKILL.md`
> 並補上 `name:` / `description:` frontmatter。**先確認真的需要自動載入**——
> 21 個使用者層 skill 在 666 次啟動裡有 20 個是 0 次。

## Agents 代理

> 代理清單已移除——`ls .claude/agents/` 與 `ls .claude/agents/_shared/` 直接看得到，
> 每個代理的職責寫在它自己的 frontmatter `description`。

## 重要規範文件

> 檔案路徑表已移除（原 9,260 字元）——三個權威索引直接查：
> * 檢核腳本 → `scripts/checks/README.md`（按「誰在跑它」分組）
> * 架構決策 → `ls docs/adr/`
> * 架構文件 → `ls docs/architecture/`
> 這與 `CK_Missive/CLAUDE.md` 早先移除同型清單的理由相同：**常駐一份會過期。**

## 自我檢核腳本索引（2026-08-09 起由 `declaration_gate.py` 強制表態）

> **正典＝[`scripts/checks/README.md`](../../scripts/checks/README.md)**，按「誰在跑它」分組，
> 涵蓋 222 支腳本（描述＋執行者），且是 `declaration_gate.py` 的 `INDEX_CANDIDATES[0]`
> —— 容器內讀得到、每天 daily step 0 比對。
>
> 2026-09-08 /doctor：本檔原本抄了其中 57 支（24,727 字元）到這裡，
> **而那份複本每個 session 都要載入一遍**。理由與本檔上方三處移除相同——
> **常駐一份會過期**，且它正是本 repo 反覆付學費的「同一件事兩份宣告」。
> `INDEX_CANDIDATES` 的語意是「任一份登記即通過」（見 `declaration_gate.py` 的註解），
> 所以移除不會讓閘門變紅。移除的原文可從 git 歷史取回。
>
> 存量 111 支走 `scripts/checks/.declaration_baseline.txt` **逐步清**：
> 每把一支寫進 README 就從基線移除一行。閘門每次執行都印剩餘數量 ——
> 數字不動就代表沒有人在清。**新增的腳本不在基線裡，會被真的擋下來。**
