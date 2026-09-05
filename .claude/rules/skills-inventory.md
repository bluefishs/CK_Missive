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
| `scripts/checks/chronic_red_audit.py` | **長期紅燈必須有名字** —— 連續 4+ 輪非綠而未登記 ⇒ RED。實測 11 支慢性紅燈**沒有一支是壞掉的檢核**，全是真發現（合約經費填 $3 而應付 $159,000／2 個 admin 未綁 SSO 現在就登不進來／帳本漏帳），只是沒有人收。⚠️ 登記**不是把紅燈變綠**，它們照樣各自紅著；本支只讓「有多少紅燈沒有人在收」看得見。登記了但已轉綠 ⇒ YELLOW（名冊本身會過期）| weekly 94 |
| `scripts/checks/lib_adoption_audit.py` | **新腳本不得自己重造 paths／docker／db** —— 實測 182 支裡 110 支自算專案根路徑（今天因此出事兩次）、39 支自開 docker exec，而共用層 `lib/` 早就存在、採用率 **3.3%**。⇒ **不是沒有共用層，是共用層沒有成為預設路徑。**存量 134 支走基線（**待清清單不是缺陷清單**），新增或增長才判紅；清的節奏是「因別的原因動到某支時順手改一支」，刻意不專案化（L58／L59 前例）| weekly 93 |
| `scripts/checks/knowledge_base_consistency_check.py` | **四位一體一致性**：ADR × 知識地圖 × 架構圖 × 向量庫。③ 用 `kb_chunks.file_hash` 對照 docs 現檔 MD5，**是精確判準不是啟發式**；連不到 DB 回 exit 2 不回 GREEN。⚠️ ② 原規範說「比對 `code_graph` 表」而**那張表不存在**，改掃原始碼；且**不能拿所有 Mermaid node 比對**（真實圖用縮寫，85 個候選只有 4 個像類別名）—— **收窄之後才有訊號**。⚠️ 首版把 `scripts/` 納入掃描範圍，於是它**找到自己 docstring 裡寫的那個發現**、判定符號存在，把唯一真陽性沖成 0 —— **判準的掃描範圍不得包含描述該判準的文字** | weekly 92 |
| `scripts/checks/hook_reachability_audit.py` | **hook 有沒有機會被觸發** —— 與 weekly 39 的 `spec_executor_audit` 剛好相反（那支問「規範宣告的腳本有沒有執行者」，執行者來源不含 git hook 與 `.claude/settings.json`，所以在 pre-push 從未執行、secret guard 修在死檔上時仍回 GREEN）。三條機械式判準：①`core.hooksPath` 旁路掉的 `.git/hooks/` 檔 ②husky shim 無實作**且**有一份被擱置 ③`.claude/hooks/*.ps1` 未被 settings 引用。存量 10 筆走基線（帶理由），**新增才判紅**；檔頭寫「不會被 git 執行」即豁免 | weekly 91 |
| `scripts/checks/link_id_fallback_audit.py` | `link_id` 不得用 `??`／`||` 回退到別的 id（§7）——失效的代價是**對錯的紀錄執行操作**而畫面無異狀。豁免 React `key=`（只決定渲染身分）。⚠️ 取代 `.claude/hooks/link-id-check.ps1`：那支**沒有任何 runner 在叫它**，且 `-Path "src\**\*.tsx"` 在 PowerShell 裡的 `**` **不是遞迴 glob** ⇒ 只掃得到 119/604 個檔而照樣印 PASS，另有一條斷言的型別路徑早已過期＝永久假紅 | weekly 90 |
| `scripts/checks/dropdown_limit_headroom_audit.py` | **每個下拉還能長幾筆才會靜默截斷** —— 上限不會壞在你改它的那天，會壞在資料長過它的那天（owner 要選的案件排第 144 名，而**前一天排第 93、剛好在界內**）。三種 RED：正在截斷／送出超過端點上限（**422 ⇒ 整個下拉變空，比截斷更糟**）／登記表的資料表不存在。連不到 DB 回 YELLOW 不回 GREEN | weekly 95 |
| `scripts/checks/config_directory_ssot_audit.py` | 專案根只允許 `configs/`（基礎設施）與 `backend/config/`（應用層）—— 第三個目錄就是 `remote_backup.json` 長出三份、內容都不同的來歷。刻意**不管 `shared-modules/`**（每個套件本來就各有 `manifest.yml`，誤報會讓人學會忽略這支） | weekly 96 |
| `scripts/checks/container_restart_loop_check.py` | **容器重啟迴圈偵測**（A66 的守門）——間歇 502 的來源：探針全綠而綠燈之間的空窗才是使用者踩到的。用 `docker events --filter event=die` 現場捕捉，**不用 `docker inspect` 的 ExitCode**（L127：那個欄位不是那個 exit code）。⚠️ 09-01 上線時漏登記表態；且在容器內結構性無效（拿不到 docker socket、`scripts` 為 rw=false 寫不了狀態）＝A68-② | daily 15 |
| `scripts/checks/orphan_component_audit.py` | 元件建好了但沒有任何入口渲染它（`dead_ui_detector` 抓不到的第三種形狀）。**基線是問題清單不是刪除清單** | weekly 86 |
| `scripts/checks/ledger_case_code_reachability_audit.py` | **帳本 `case_code` 必須接得到主表**——08-29 案號收斂做了三張主表（殘留 0）卻沒轉帳本 ⇒ 49 個 `case_code` 只有 5 個接得到、**90% 孤兒**、背後 ~2,000 萬收入。09-02 收斂 43 個後剩 1（`B114-B002`，登記待判）。新孤兒 RED、只剩已知 YELLOW | weekly 97 |
| `scripts/checks/contract_case_quotation_presence_audit.py` | **成案必有報價單，GN 豁免**——請款／發票／應付全掛 `erp_quotation_id`，承攬案件本身沒有金流外鍵 ⇒ 沒有報價單的承攬案在金流上等於不存在。實測 11 件全是 GN 標案（只有投標沒有報價單）⇒ 豁免不補登；**原建議「補登」是錯的，量了才知道** | weekly 98 |
| `scripts/checks/contract_case_pipeline_reconciliation.py` | **以案件為主軸把整條鏈走一遍**（owner：「無法自行檢測整個流程對應數據嗎」）——97–99 各查一個環節，這支問每個承攬案「在 PM／報價／請款／發票／應付／帳本／指派／桃園各環節的數字對不對」。RED 只給**數字互相矛盾**（已收>請款、請款>合約、報價 vs 合約差 >50%、應付>報價）；已結案未收齊／執行中 >365 天 0 請款只 YELLOW（**後者多為小案，很可能是收了沒登**）。⚠️ 桃園 `cumulative_amount` 是全案累計、每張派工單各帶一份，sum 會重複 43 次——只用 `current_amount`。首跑抓到案 189 報價單多打一個 0（四期請款加總正好 = 合約額） | weekly 100 |
| `scripts/checks/case_field_sync_whitelist_audit.py` | **三表共有欄位必須在同步白名單**——09-02 一天踩兩次同型（上午 `status`、晚上 `case_name` 不在 `SYNC_FIELDS` ⇒ 48 筆狀態漂移／109 筆案名三表各改）。第三種形狀：`sync_from_pm` 寫 `ERPQuotation.client_name` 而**模型沒有這個欄位**，`setattr` 靜默不落地——「同步做了」與「同步寫進 DB」在程式碼裡長得一樣。判準③端點不得自抄清單（crud.py 就是抄了第二份讓修法失效）。負向對照：未修前抓到 2 處 | weekly 101 |
| `scripts/checks/case_code_format_consistency_audit.py` | **案號新制統一＋填報編碼同步**（owner 09-02 晚）——三種格式並存：PM 成案「去 `_PM_`」、手動建承攬案原走舊制 `CK{年}_{類}_{性}_{序}`（09-02 晚改為＝GN 制 case_code）。「01」在舊制是類別、在新制是模組，同一個位置兩種意思。存量 23 筆舊制不動（documents／taoyuan 引用），**新建才判** | weekly 102 |
| `scripts/checks/first_billing_presence_audit.py` | **成案即應收**（owner 09-03「非常重要的自動化機制」）——`ERPBillingService.ensure_first_period` 在成案／建報價單／補總額時自動建「一次請領」第一期（金額＝報價總額、pending、請款日＝當天），夜間吹哨者才有東西可催。本支守「有金額的成案報價單必須有請款」；金額 0 的 YELLOW（要人填）。首跑 90 張 3,109 萬 | weekly 103 |
| `scripts/checks/erp_amount_semantics_audit.py` | **金額語意三方對帳**（全景覆盤 A1）——含稅／未稅此前沒有一處寫死，請款一建入 weekly 100 就 RED 87。宣告處＝`FIELD_SEMANTICS.md`，這支照它對帳：RED 只給不可能同時為真的（一次請領≠總價、發票>請款、已收>請款、稅>總價）| weekly 104 |
| `scripts/checks/payable_billing_link_audit.py` | **應付必有 `billing_id`**——欄位存在、47 筆全空，「這筆應付對哪次請款」答不出來。09-02 回填 37 筆（可唯一對上者），10 筆多筆請款走基線待判。可唯一對上卻沒對 ⇒ RED（新建時沒走橋） | weekly 99 |
| `scripts/checks/case_state_consistency_audit.py` | **已承攬 ⇔ 承攬案 ⇔ project_code 三方一致**——匯入服務對總表「已成立」的列只寫 `status=contracted` 而不建承攬案，16 筆 PM 案在承攬列表看不到、報價單沒 `project_code`、損益摘要當未成案、掛著的請款在成案口徑裡消失，**每張表單獨看都正常**。同名待判走基線（登記不是變綠） | weekly 105 |
| `scripts/checks/vendor_association_payable_audit.py` | **指派即應付**——承攬案「協力廠商」分頁寫 `project_vendor_association.contract_amount`，廠商帳款／應付分頁讀 `erp_vendor_payables`，兩表此前沒有橋（16 案有指派 13 案無應付；owner 從 `/contract-cases/191?tab=vendors` 回報）。修法同「成案即應收」：`ensure_from_association` 三處掛點、自動建的帶 `[auto:vendor_association]` 前綴、人工建的不碰。RED＝有金額指派而報價單沒有該廠商應付；YELLOW＝人工應付合計≠指派金額（A96）或 GN 無報價單 | weekly 106 |
| `scripts/checks/name_id_pair_consistency_audit.py` | **名稱欄是快照、鍵欄才是關聯**——`pm_cases.client_name`↔`client_vendor_id`、`contract_projects.client_agency`↔`client_vendor_id`（09-04 新欄，此前承攬案的委託單位沒有 partner_vendors 的鍵、全靠字串對）、`erp_vendor_payables.vendor_name`↔`vendor_id`。RED＝名稱精確對得到主檔卻沒填鍵（自動補鍵沒接到）；YELLOW＝快照漂移（張啟良建築師 vs 事務所）或主檔缺（勤典工程行 ×4，已建） | weekly 107 |
| `scripts/checks/stat_card_filter_wiring_audit.py` | **統計卡點了要真的篩列表**（owner 09-05「統計圖卡對應動態篩選為首要核心」）——逐張卡看 `onClick`：呼叫了會改查詢或路由的 setter＝ok；只設一個沒人讀的 state＝RED（09-04 `/contract-cases`、`/erp/quotations` 四張卡就是這樣，weekly 82 守分母守不到「點了有沒有反應」）；沒有 onClick＝YELLOW 要在檔內登記理由。⚠️ 首版把 `icon={<X />}` 的 `/>` 當卡片結尾，有 onClick 的全報成沒有 | weekly 108 |
| `scripts/checks/rwd_page_overflow_gate.py` | **RWD 整頁溢出閘門**——讀每日 04:30 `ui_page_sweep` 的 `mobile_probe`（41 頁 × 390／768／1024），整頁溢出 ≥ 24px 即 RED。引擎本身「觀測不告警」且門檻是表格外溢 400px，09-04 基準 11 列溢出沒有一列會紅。**表格內橫向捲動刻意不計**（09-05 起窄螢幕保留欄寬改橫向捲動是設計）。不碰 vendored 引擎 | weekly 109 |
| `scripts/checks/assignment_dual_key_audit.py` | **承辦指派必須同時帶 `case_code` 與 `project_id`**——09-05 owner：588 承辦改成賴柏霖後仍顯示兩個名字，因為曾廷睿那筆只綁 `case_code`（PM 頁寫的）、賴柏霖只綁 `project_id`（承攬案頁寫的），承攬案頁看不到前者、報價單取聯集。08-31 改了八個讀取點卻沒改寫入。09-05 回填 69＋24 筆，寫入端改雙鍵；RED＝只綁一邊而另一把解得出來 | weekly 110 |
