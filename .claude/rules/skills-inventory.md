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

> 存量 111 支走 `scripts/checks/.declaration_baseline.txt` **逐步清**：
> 每把一支寫進本表就從基線移除一行。閘門每次執行都印剩餘數量 ——
> 數字不動就代表沒有人在清。**新增的腳本不在基線裡，會被真的擋下來。**

| 腳本 | 做什麼 | 誰跑它 |
|---|---|---|
| `scripts/checks/adr_level_audit.py` | ADR 接通完整度自評（MODULARIZATION_STANDARDS §4.3）；2026-05-25 前建立者列為存量不判紅 | weekly 40 |
| `scripts/checks/spec_executor_audit.py` | 規範宣告的腳本，有沒有人在做（含「檔案根本不存在」偵測） | weekly 39 |
| `scripts/checks/cross_repo_work_continuity_audit.py` | 跨 repo／跨 session 工作連續性：未推送（含 push --dry-run 判被擋）、逾期未提交、孤兒腳本 | weekly 34 |
| `scripts/checks/selfaudit_entry_delegation_audit.py` | 走查入口必須委派共用實作，防 copy 式復發 | weekly 33 |
| `scripts/checks/declaration_gate.py` | 腳本強制表態閘門（存量走 .declaration_baseline.txt 逐步清） | 本表守門人 |
| `scripts/checks/sso_coverage_check.py` | ADR-0033 配套：未綁 SSO 者現在就已鎖死（密碼登入回 410） | weekly 35 |
| `scripts/checks/entity_creation_ssot_audit.py` | 業務實體（PMCase／ContractProject／ERPQuotation）只能在授權處建構——防「從標案建案」那種兩份實作各自演化到業務規則相反 | weekly 57 |
| `scripts/checks/enum_storage_convention_audit.py` | 分類／狀態列舉值的守門：寫入端 schema 要有 Literal、表單不得用自由輸入收列舉值（統一帳本就是這樣長出 `billing_payment` 的） | weekly 58 |
| `scripts/checks/schema_ssot_audit.py` | endpoints 不得有本地 BaseModel（規範 §3）——存量 18 項列 baseline 不判紅，新增一律擋 | weekly 59 |
| `scripts/checks/savepoint_autocommit_audit.py` | SAVEPOINT 內不得用 auto_commit=True——會關掉外層交易而使用者只看到「新增失敗」（測試 mock 掉 repo 所以抓不到） | weekly 60 |
| `scripts/checks/model_response_field_reach_audit.py` | ORM 欄位有沒有到達 API 回應——Pydantic 對 schema 沒宣告的欄位是靜默丟棄（quotation_no 就這樣看不到） | weekly 61 |
| `scripts/checks/payable_budget_ceiling_audit.py` | 應付上限：報價單委外經費 vs 應付合計 | weekly 78 |
| `scripts/checks/llm_model_availability_audit.py` | 設定的模型在 provider 那邊還存不存在——**實際打一次**，因為「在清單裡」不等於叫得動（NVIDIA 清單有但呼叫 404） | weekly 79 |
| `scripts/checks/year_convention_audit.py` | 紀年契約：API 查詢參數一律西元（§2.5）。判準是「附近有沒有 logger.warning」——規範要的不是禁止轉換，是**不得靜默轉換** | weekly 80 |
| `scripts/checks/responsive_narrow_convergence_audit.py` | 窄螢幕收斂判準：不得只看 `isMobile`（AntD 的 md 斷點就是 768 ⇒ 平板會走桌面分支） | weekly 81 |
| `scripts/checks/stat_card_denominator_audit.py` | §2.6 列表頁 **①③**：統計卡分母必須是全體不是當頁；年度篩選必須預設當年度**且顯示出來**（篩了卻顯示未選＝隱形篩選，比不篩更糟）。⚠️ ③ 的違規形狀是**那個 key 不存在**，所以判準的進場條件是「有沒有年度 setter」而不是「year 的初始值對不對」——首版問後者，於是對兩個真違規完全是盲的 | weekly 82 |
| `scripts/checks/verify_architecture.py` | 架構完整性 13 項（路由/API 前綴/型別 SSOT/Schema-ORM/棄用模組）。⚠️ 2026-08-29 之前**壞著且沒有人在跑**（L99） | weekly 83 |
| `scripts/checks/lib/ts_source.py` | 給靜態判準用的 TS 讀取器：委派 TypeScript parser 剝掉註解／字串／樣板／JSX 文字。**手寫正則版擋不掉後三者**（L97） | 上列前端類稽核共用 |
| `scripts/checks/runner_flag_drift_audit.py` | 基線鎖有沒有真的被叫到——腳本在、排程在、旗標在，**只是呼叫時少了旗標**（L100） | weekly 84 |
| `scripts/checks/fitness_manual_freshness_audit.py` | 手動月度架構覆盤有沒有真的在跑——它獨佔 57 支檢核卻原本不留任何產出 | weekly 85 |
| `scripts/checks/gate_vs_report_step_audit.py` | weekly 的每一步都必須能紅，否則步驟名要標明「僅報告」——**永遠不可能紅的綠燈與真守門長得一樣**。判準看**程式碼有沒有非 0 退出路徑**，不看檔頭怎麼描述自己（首版掃字樣命中 7 支、**6 支是誤報**）| weekly 89 |
| `scripts/checks/pg_tuning_ssot_audit.py` | postgres 調校參數的跨檔 SSOT：三份 compose ＋規格書＋**執行時**三層比對——`postgresql-tuning.conf` 掛載了卻**從未被讀**（Dead Config），而 dev/infra 定義同一個容器卻給不同的 `max_connections` | weekly 88 |
| `scripts/checks/test_db_schema_drift_audit.py` | 測試庫 schema 不得落後正式庫——測試庫**原本沒有 `alembic_version`**，每支新 migration 都讓它再漂一次，症狀是測試 500 `column X does not exist`，看起來像「測試壞了」 | weekly 87 |
| `scripts/checks/hook_reachability_audit.py` | **hook 有沒有機會被觸發** —— 與 weekly 39 的 `spec_executor_audit` 剛好相反（那支問「規範宣告的腳本有沒有執行者」，執行者來源不含 git hook 與 `.claude/settings.json`，所以在 pre-push 從未執行、secret guard 修在死檔上時仍回 GREEN）。三條機械式判準：①`core.hooksPath` 旁路掉的 `.git/hooks/` 檔 ②husky shim 無實作**且**有一份被擱置 ③`.claude/hooks/*.ps1` 未被 settings 引用。存量 10 筆走基線（帶理由），**新增才判紅**；檔頭寫「不會被 git 執行」即豁免 | weekly 91 |
| `scripts/checks/link_id_fallback_audit.py` | `link_id` 不得用 `??`／`||` 回退到別的 id（§7）——失效的代價是**對錯的紀錄執行操作**而畫面無異狀。豁免 React `key=`（只決定渲染身分）。⚠️ 取代 `.claude/hooks/link-id-check.ps1`：那支**沒有任何 runner 在叫它**，且 `-Path "src\**\*.tsx"` 在 PowerShell 裡的 `**` **不是遞迴 glob** ⇒ 只掃得到 119/604 個檔而照樣印 PASS，另有一條斷言的型別路徑早已過期＝永久假紅 | weekly 90 |
| `scripts/checks/orphan_component_audit.py` | 元件建好了但沒有任何入口渲染它（`dead_ui_detector` 抓不到的第三種形狀）。**基線是問題清單不是刪除清單** | weekly 86 |
