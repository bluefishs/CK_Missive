# scripts/checks/ — 檢核腳本索引

> **重建**：2026-08-10（原版停在 39 支／「run_fitness 6 step」）
> **這份索引是強制的**：`declaration_gate.py`（daily step 0）會比對本檔，
> 新增腳本沒寫進來就擋下。
>
> 理由——本專案反覆發生「腳本寫好了但沒有任何東西會跑它」（lvrland 6 支、pile 6 支、
> `sso_ttl_ssot_audit` 寫好兩週沒接線），而**沒有對應窗口的檢核等於啞巴**：
> 它不會報錯、不會消失，只會安靜地讓人以為有人在看。

## 怎麼讀這份表

按「**誰在跑它**」分組，不是按主題。因為要回答的第一個問題永遠是：
**這支東西壞掉的時候，會有人知道嗎？**

| 分組 | 列數 |
|---|---|
| 🔴 每日（容器內 APScheduler `fitness_daily`） | 13 |
| 🟠 每週（host 排程 `CK_Missive-Fitness-Weekly`，容器端只當接收者） | 86 |
| 🧪 月度架構覆盤（`run_fitness.sh`） | 64 |
| 🖥️ 瀏覽器走查（`run_ui_smoke.sh` / `run_visual_walk.sh`） | 4 |
| ⏰ 後端排程（`backend/app/core/scheduler.py`） | 15 |
| 💓 健康監控（`scripts/health/`） | 1 |
| 🪟 Windows 工作排程器 | 1 |
| ⚪ 無排程（手動／一次性／已被取代） | 25 |

> ⚠️ 上表是**各段的表格列數**（含該段的 runner 本身，且一支可能出現在多段），
> 所以加總會大於下面那個受納管的總數。
> **只有總數由 `doc_baseline_claim_audit` 納管**，分組數字沒有人在看 ——
> 2026-08-15 一次校正就發現每週那格寫 43 而實際 50。
> 若日後再漂，處理方式是重數一次，不是把它當成新增了 7 支。

<!--baseline:check_scripts-->合計 **191** 支（頂層 `*.py` + `*.sh`；子目錄 `.shared-selfaudit/` 由上游同步，不在表態閘門管轄內）。

> 這個數字現在由 `doc_baseline_claim_audit`（weekly 26）納管。
> 2026-08-11 更正：原本寫 164 而實際 156 —— 閘門比對的是「檔名有沒有出現在文件裡」、
> 不看總數，所以數字錯了它一聲都不會吭，而失真的索引會讓人以為還有沒清完的存量。

退出碼三態（全 portfolio 一致）：**0=GREEN／1=YELLOW／2+=RED**。

⚠️ CK_lvrland_Webmap 用的是相反的一套（1=FAIL／2=未驗完），移植時務必先確認 —— 
`db_transaction_health_check` 就曾因此在那邊變成啞的：真的抓到中止交易，卻被印成「SKIP」。

---

## 🔴 每日（容器內 APScheduler `fitness_daily`）

> ⚠️ **這一組跑在容器裡，不是 host。** 寫進這組之前先問：它依賴的東西容器內有嗎？
>
> 容器只掛 `scripts/`、`backend/`、`wiki/`、`docs/`、`backups/`、`logs/`——
> **沒有 docker CLI、沒有 repo 根目錄的 `CLAUDE.md` 與 `.claude/`、沒有 PowerShell、沒有 sibling repo。**
>
> 2026-08-11 一次抓到三支踩到這條，且三支的失敗方式不同：
>
> | 腳本 | 依賴什麼 | 症狀 |
> |---|---|---|
> | `db_transaction_health_check` | docker CLI | 每天 RED，紅的原因不是資料庫有事 |
> | `declaration_gate` | repo 根的 `CLAUDE.md` | 每天 RED，紅的原因不是有人沒表態 |
> | `cron_silent_dormant_check` | `<repo>/backend/...` 路徑 | **靜默**回空 → 38 個 cron 全成 "no threshold" 卻印「✓ all monitored」 |
>
> 前兩支天天紅＝告警疲勞；第三支不出聲＝假綠。**後者危險得多。**
> 判準：這一組的每一支，都必須在容器內實跑驗過，不能只在 host 跑得出綠燈。

| 腳本 | 用途 |
|---|---|
| `agent_query_starvation_check.py` | Agent query starvation 健康檢查 |
| `compose_dockerfile_healthcheck_ssot.py` | 偵測 docker-compose*.yml healthcheck 與對應 Dockerfile HEALTHCHECK SSOT drift（L45 family） |
| `container_env_alignment_audit.py` | Container env vs host .env 對齊 audit |
| `container_image_freshness_check.py` | Container image freshness check |
| `business_vital_signs.py` | daily 13：**生命跡象**（條目數見腳本輸出，不寫死在這裡 —— 2026-08-26 加第九條時發現腳本自己的文案寫死「八條」而實際已是 **10 條／9 個模組**，漂了很久沒人看；已改為從 `VITALS` 算） —— 問「這個模組今天活著嗎」而非「機制有沒有動」。150 支檢核裡 131 支只看機制，而四個「機制綠、業務停」的實證沒有一支問得到。首月觀測不告警 |
| `cron_silent_dormant_check.py` | Fitness step (v6.12 #2 補完): cron silent dormant 偵測 |
| `dashboard_freshness_check.py` | Fitness step 64: GOVERNANCE_INTEGRATED_DASHBOARD freshness 偵測 |
| `db_transaction_health_check.py` | 資料庫連線狀態健檢 —— 抓「交易中止卻未 rollback」的現行犯 |
| `declaration_gate.py` | 腳本強制表態閘門（CK_Missive 薄包裝）— 2026-08-09 |
| `docker_compose_volume_consistency.py` | 偵測同一專案多個 docker-compose*.yml + backup script 內 volume 命名 drift |
| `governance_dashboard_completeness_audit.py` | Governance Dashboard Completeness Audit |
| `module_import_sweep.py` | 每個模組都必須真的能被匯入 —— 消滅「匯入即失敗但沒有人在匯入它」家族 |
| `run_fitness_daily.sh` | Fitness Tier 1 Daily — 8 critical step (~1 min) |
| `shell_script_eol_audit.py` | shell script 不得帶 CRLF —— 那會讓它在 Linux 容器裡直接無法執行 |

## 🟠 每週（host 排程 `CK_Missive-Fitness-Weekly`，容器端只當接收者）

| 腳本 | 用途 |
|---|---|
| `admin_check_ssot_audit.py` | 管理員判定不得有第二份規則（只看 is_admin 不看 role 會讓 role='admin' 的人看得到卻用不了） |
| `service_port_exposure_audit.py` | 資料層服務埠不得對區域網路無保護開放（綁定位址＋是否需認證＋弱密碼特徵） |
| `pm2_process_liveness_audit.py` | PM2 程序存活 —— 三個排程層裡最後一個補上哨兵的（原本只有「有沒有註冊」沒有「跑完了沒」） |
| `offsite_backup_completeness_audit.py` | 異地備份四類缺一不可（資料庫／里程碑／附件／金鑰）＋dump 尾端截斷偵測 |
| `adr_level_audit.py` | `MODULARIZATION_STANDARDS_v1.md` §4.3 寫著 |
| `agent_evolution_health.py` | Agent Evolution Health Diagnostic — 診斷坤哥進化引擎為何沒跑 |
| `alias_rls_coverage_audit.py` | Alias RLS Coverage Audit |
| `alias_rls_e2e_check.py` | Alias RLS End-to-End Check |
| `api_contract_alignment_audit.py` | 程式 × 頁面 × 服務 三者對應完整性稽核 |
| `capability_usage_snapshot.py` | 能力使用度快照 —— 第 6 階「價值層」的資料收集 |
| `check_effectiveness_report.py` | 檢核有效性報告 —— 哪些從沒紅過（可能是假綠）、哪些紅了沒人處理（噪音） |
| `credential_liveness_audit.py` | 憑證存活稽核 —— 提請複查 |
| `cross_domain_link_audit.py` | Fitness step 71: KG cross-domain 連結率 audit |
| `cross_repo_template_drift_audit.py` | Fitness step 65: 跨 repo 範本漂移 audit |
| `cross_repo_uncommitted_audit.py` | Fitness step 66: 跨 repo 已套用但未 commit staging 偵測 |
| `cross_repo_work_continuity_audit.py` | 跨 repo／跨 session 工作連續性稽核 |
| `diary_density_audit.py` | Diary density audit (L51.7 Sprint 2.P2.11 / |
| `doc_baseline_claim_audit.py` | 文件宣稱數字納管 —— 標記制 |
| `doc_reference_integrity_audit.py` | `docs/architecture/` 已累積 **102 份**文件，但沒有任何檢核在問「它們寫的還算數嗎」 |
| `erp_data_integrity_audit.py` | weekly 55：ERP 帳本收攏／填報推進／案號橋樑／名稱相容字（§1 判 RED＝真漏帳，§2-4 判 YELLOW＝需要人或決策，不是系統壞了） |
| `frontend_design_standard_audit.py` | weekly 56：前端設計規範（列表操作欄收詳情頁／表格須可排序篩選／詳情頁須用 DetailPageLayout 才有分頁深連結）—— 判 YELLOW，因為這些不是故障是規範沒被強制 |
| `facade_adoption_audit.py` | Facade Adoption Audit (P1.7 / |
| `governance_alignment_audit.py` | Fitness step 63: 規範 vs 現況對應檢核 — 程式圖譜 + LLM Wiki 雙源 |
| `graph_domain_tagging_audit.py` | Graph domain tagging audit — entity_type vs graph_domain 一致性 |
| `hermes_baseline_gate_audit.py` | Fitness step 68: Hermes GO/NO-GO baseline gate 自動裁判 |
| `idp_connectivity_check.py` | ADR-0033 配套 — IdP Connectivity Check |
| `kg_embedding_coverage_check.py` | KG pgvector embedding 覆蓋率審計 |
| `job_detail_completeness_audit.py` | 排程 job 算得出數字就該回傳 detail —— 儀器化缺口偵測 |
| `knowledge_dedup_audit.py` | Fitness step 72: KG knowledge domain code entity 重複偵測 |
| `memory_diary_freshness_check.py` | Memory Wiki Freshness Check |
| `ner_relation_regression_check.py` | weekly 54：NER 關係抽取**修法後有無新缺口**（刻意不報 572 筆存量——已知待決的事每週報一次只會被略過） |
| `memory_metrics_alive_check.py` | Memory Wiki metrics alive check |
| `entity_creation_ssot_audit.py` | weekly 57：業務實體（PMCase／ContractProject／ERPQuotation）只能在授權處建構 —— 防「從標案建案」那種兩份實作各自演化到業務規則相反 |
| `enum_storage_convention_audit.py` | weekly 58：狀態值存中文還是英文代碼**只能有一種**（`ENUM_STORAGE_CONVENTION.md`）—— 混存時篩選會靜靜漏掉一半 |
| `payable_budget_ceiling_audit.py` | weekly 78：應付上限（報價單委外經費 vs 應付合計） |
| `llm_model_availability_audit.py` | weekly 79：設定的模型在 provider 那邊還存不存在——**實際打一次**，因為「在清單裡」不等於叫得動（NVIDIA 清單有但呼叫 404；Groq 用 urllib 會被 Cloudflare 擋成 403，要用 httpx） |
| `year_convention_audit.py` | weekly 80：紀年契約一律西元（§2.5）。判準是「附近有沒有 logger.warning」——規範要的不是禁止轉換，是**不得靜默轉換** |
| `responsive_narrow_convergence_audit.py` | weekly 81：窄螢幕收斂判準不得只看 `isMobile`（AntD 的 md 斷點就是 768 ⇒ 平板會走桌面分支拿到桌面的固定 scroll.x） |
| `stat_card_denominator_audit.py` | weekly 82：統計卡分母必須是全體不是當頁（§2.6 ①）——抓的是形狀，不是當下數字對不對 |
| `verify_architecture.py` | weekly 83：架構完整性 13 項。⚠️ 2026-08-29 之前**壞著且沒有人在跑**（根目錄推導在檔案搬家後沒改；白名單裡「由 pre-commit 與 CI 呼叫」是假的，實查各 0 次）——L99 |
| `runner_flag_drift_audit.py` | weekly 84：基線鎖有沒有真的被叫到——腳本在、排程在、旗標在，**只是呼叫時少了旗標**（L100） |
| `schema_ssot_audit.py` | weekly 59：`api/endpoints/` 不得有本地 `BaseModel`（development-rules §3）—— 端點自帶 schema 會與 `app/schemas/` 各自演化 |
| `savepoint_autocommit_audit.py` | weekly 60：`begin_nested()` 內不得呼叫 `auto_commit=True` 的 repo 方法 —— SAVEPOINT 被內層 commit 掉，外層 rollback 就救不回來 |
| `model_response_field_reach_audit.py` | weekly 61：ORM 欄位是否到達 response schema —— Pydantic 對「model 有、schema 沒有」是**靜默丟棄**，API 永遠不回傳而不拋錯（`quotation_no` 就這樣存在資料庫而使用者看不到） |
| `write_payload_schema_audit.py` | weekly 62：前端送出的寫入欄位，寫入端 schema 收得到嗎 —— `extra='forbid'` 之下收不到就是 **422**（不是風險是現行故障）。以端點常數為錨比對 Create/Update，**不用欄位交集猜**（08-17 那次就是猜錯對象而漏掉） |
| `response_frontend_type_audit.py` | weekly 63：後端 Response 的欄位，前端手寫型別宣告了嗎（契約鏈第三面）—— 漏宣告不會壞掉，但**型別檢查守不住那個欄位**；08-18 我在後端補了 `payable_period` 卻漏了前端，而「應收有期別、應付沒有」的不對稱就在前端原封不動 |
| `paths_compose_mount_audit.py` | Fitness step 62 (v6.12, L52 lesson): paths.py PROJECT_ROOT vs docker-compose mount audit |
| `paths_subpath_mount_audit.py` | Fitness step 69: paths.py sub-path vs compose mount sub-path audit |
| `public_exposure_audit.py` | 公網暴露稽核 —— API 文件不得對外開放 |
| `repository_coverage_audit.py` | Fitness step 70: Repository:db_table 覆蓋率 audit |
| `run_fitness_weekly.sh` | Fitness Tier 2 Weekly — 12 trend tracking step (~3 min) |
| `selfaudit_entry_delegation_audit.py` | 走查入口腳本必須委派給共用實作 —— 防止「copy 式」入口再長回來 |
| `service_port_exposure_audit.py` | 服務埠暴露稽核 —— 資料層不得從區域網路無保護連入 |
| `soul_evolution_alive_check.py` | SOUL.md 演化鏈路 alive check |
| `soul_mirror_drift_check.py` | SOUL.md 跨 repo 同步漂移偵測 |
| `spec_executor_audit.py` | owner：「因此要針對既有規範統整複查確認」 |
| `sso_coverage_check.py` | ADR-0033 配套 — SSO 覆蓋率檢查 |
| `sso_ttl_ssot_audit.py` | SSO session TTL 跨 repo SSOT 稽核 |
| `tender_enrichment_freshness_audit.py` | Tender Enrichment Freshness Audit |
| `tender_freshness_audit.py` | 偵測政府標案 tender 資料源 silent dormant（v6.12 P3 forward-looking） |
| `tender_subscription_watchdog_audit.py` | Tender Subscription Scheduler Watchdog |
| `test_suite_health.py` | 測試套件健康檢核 — 「它跑不跑得起來」也要有人問 |
| `visual_walk_freshness.py` | 視覺走查是**唯一**能抓到「斷言全過但畫面是錯的」那一類缺陷的機制 |
| `public_endpoint_auth_audit.py` | **weekly 64**：哪些 API 端點沒有任何認證依賴 —— 用 FastAPI **runtime dependency 樹**，不是 grep。2026-08-21 實測公網未帶憑證可取得 `documents-enhanced/statistics`（回傳公文總數 2017）；根因是 `TUNNEL_GUARD_ENABLED=false`，沒有自帶認證的端點一律對外。既有的 grep 規則「端點缺少認證裝飾器」產生 **122 個誤判**（真問題的 6 倍），認不出 `Depends(require_auth())`。baseline 內已知項不判紅，**新增一律 RED**；探測不到就 exit 2 不下結論 |
| `router_level_auth_mixing_audit.py` | **weekly 65**：router 層加認證有沒有**誤擋公開端點**（C2）。CK_PileMgmt 2026-08-24 指出這是 08-21 那個修法的反面風險 —— 同一個 router 檔案裡可能混雜真公開端點（他們的 `gislayers` 一半是管理 CRUD、一半是公開地圖互動），router 層加認證會把公開那半一起擋掉，而**那種失敗只有真的打開那一頁才看得見**（tsc／py_compile／以管理員身分跑的走查都看不到）。現況 16 檔 86 端點、12 條公開路由全是認證流程 ⇒ GREEN。⚠️ 它看不到**非瀏覽器消費者**，那一面由 `integration_e2e_validation` 負責 |
| `http_method_convention_audit.py` | **weekly 66**：規範 §24「所有 endpoint POST」有沒有人在管。2026-08-24 盤點發現 **175 支腳本裡沒有一支驗 HTTP 方法** —— 規範只是散文（CK_AaaP 同日：「散文不帶設定」）。實測 21 條純 GET 裡 16 條是外部工具強制（healthcheck 只發 GET／SSE 的 EventSource 只能 GET／Swagger 是瀏覽器導覽），**5 條真違反**，已改 4 條（scheduler_events，後端＋前端常數＋呼叫端三處一起）。剩 `/api/ai/memory/digest` 消費端在 CK_Hermes ⇒ 走協作 |
| `vendor_identity_ssot_audit.py` | **weekly 70**：廠商**身分**的源頭是不是同一個（69 管金額，這支管身分）。owner 2026-08-27「避免委託與協力帳款不一致，以及統一源頭數據」—— 查證後**兩端用兩套完全不同的機制**：委託靠 `PMCase.client_vendor_id`（掛邀標案件，覆蓋 102/253＝40%），協力靠 `erp_vendor_payables.vendor_id`（掛應付單）**外加一份冗餘的 `vendor_name` 文字**，再加第三處 `project_vendor_association`。⇒ **已有 3 筆同一張單兩個名字**，其中「林晉廷」vs FK 指向的「林宥廷測量技師事務所」**是不同的人 ⇒ 那筆錢會算到別人頭上**。判準只管矛盾：FK 與文字名不同 → RED（那不是還沒填，是兩個地方對同一件事給出不同答案）／只有文字沒 vendor_id → YELLOW（無法跨案件彙總）／委託覆蓋率只報數字不判級 |
| `year_convention_audit.py` | **weekly 74**：紀年契約——API 查詢參數一律西元（`development-rules` §2.5，owner 2026-08-29 裁示「系統統一採西元年建置資料與查詢服務」）。⭐ 起因：同一天抓到**四個「年度篩選從未生效」**（委託單位帳款／廠商帳款／財務總覽／發票彙總），形狀完全相同——前端送民國 115、後端比對西元 2026，**兩邊各自用自己的紀年而沒有一方會報錯**。土壤是契約不統一：同一支 service 裡 `get_company_overview` 收民國而 `get_all_projects_summary` 收西元，兩種寫法都「對」。⚠️ **判準的關鍵在分辨「靜默轉換」與「轉換並出聲」**——首跑 12 處全是誤判（外部資料解析＋相容告警），因為原判準只看有沒有 `+1911`。現改為「附近有 logger.warning 即豁免」，抓的正是規範真正要求的東西。負向對照已驗（注入違規即紅、還原即綠）|
| `llm_model_availability_audit.py` | **weekly 73**：`ai_connector.py` 設定的 LLM 模型在 provider 那邊**還存不存在**。owner 2026-08-29「防呆機制」。⭐ 起因是 A31：Groq 與 NVIDIA 的設定模型雙雙下架，agent 在本地 ollama 上跑了約 27 天沒人知道 —— 而 `llm_quota_check` 每 6 小時都在跑且一路是綠的，**因為它量的是用量配額**，而模型不存在會讓用量變低、反而讓它更綠（`proxy_metric_looks_good` 的教科書案例）。三態刻意分清：成功取得清單且模型不在＝RED；查詢 403/逾時＝**YELLOW 不下結論**（實測 Groq 回 403 而 NVIDIA 回 83 個模型，把「查不到」當「下架」會製造假警報）。⚠️ 模型名是**模組級常數不是 env**（compose 只傳 API key），修法要改程式碼。⚠️ 若 owner 決定長期就用本地 ollama，這支應改為基線接受而不是放著長紅 —— 長紅與沒有訊號是同一個下場 |
| `payable_budget_ceiling_audit.py` | **weekly 72**：應付帳款有沒有「上限」在管——報價單 `outsourcing_fee` vs 應付合計。owner 2026-08-29 於財務域複查 P1-4（5 張報價委外經費 0 但應付>0，最大 350 萬）後裁示「防呆預警」。與 weekly 69 同族第三對（69 看 per 廠商的合約經費，本支看 per 報價單的委外總預算）。判準：經費**有填**而應付超 110% → RED（上限被突破）；經費未填而應付>0 → YELLOW（還沒填不是填錯——存量 5 筆天天報紅只會訓練人忽略）。收入端對稱防呆是 `billing_service._guard_billing_within_contract`（寫入時直接擋，同 110% 容差） |
| `vendor_contract_payable_consistency.py` | **weekly 69**：協力廠商 tab 的「合約經費」與應付帳款 tab 的「分期應付」對不對得起來。owner 2026-08-27 問「如何對應管控避免兩端不一致」—— 查證後**問題比不一致更基本：兩端幾乎沒有交集**（33 筆協力廠商登記裡**只有 1 筆**填了合約經費、28 組應付完全沒登記過廠商）。而不一致**已經真實發生**：`CK2026_PM_01_005` 政威資訊，協力廠商填 $2,000,000 而應付合計 $1,000,000，**差 100 萬且沒有任何東西在報**。⚠️ 兩端沒有共同外鍵，只能經 `case_code` 三跳相接 —— 漏掉那一跳會**回 0 筆而不是報錯**，看起來像完全一致。判準：兩端都有值且差 > 1 元 → RED（那是矛盾）／只有一端 → YELLOW（那是還沒填，把 29 筆未填報成紅色只會訓練人忽略它）。三個修法方案見 `VENDOR_FUND_CONTROL_PLAN.md` |
| `admin_action_visibility_audit.py` | **weekly 68**：管理動作有沒有給一般同仁看見（`OPEN_ITEMS` B7）。判準三條件同時成立才 RED：**被路由掛載的頁面**＋**路由沒有 roles 限制**＋**檔內消費管理端點卻無身分守衛**。⚠️ 這支自己踩了兩個坑才有鑑別力：①第一版只比對**字面路徑**，而規範 §1 要求走端點常數 ⇒ 路徑根本不在頁面檔裡，把 ERPGraphPage 的守衛**完全移除**它仍回 GREEN（首跑那兩個命中剛好都是假陽性）；②改用常數後又用**裸常數名**，`CREATE`／`DELETE`／`LIST` 在四個 endpoints 檔裡都有，於是 `API_ENDPOINTS.USERS.CREATE` 被對到 backup 的 `CREATE` —— **同一個坑 08-20 掃全管理員端點時已踩過一次**。用完整限定名後 14→2，兩個都是真的。鑑別力實測 0→1→0 |
| `probe_fingerprint_guard.py` | **weekly 67**：公網探測的**客戶端指紋**。Cloudflare 依 User-Agent 擋 —— 實測同一條已知未受保護的端點：`curl` 預設 UA **200**／`urllib` 預設 UA **403**／`urllib` 帶瀏覽器 UA **200**。⇒ 用 Python 預設 UA 探公網，每一條都回 403，**而那個 403 長得正好像「認證有效」**。本專案 08-21 因此四次得出「已經擋住了」的錯誤結論；CK_AaaP 08-24 在 pile 一個**進行中的 P0 外洩**上重現同一件事。⚠️ 本 repo 三支端點稽核**不對外打 HTTP**（讀容器內 runtime tree）故免疫，這支守的是臨時探測腳本 。**2026-08-26 補第二種指紋＋反向案例**（CK_AaaP 建議）：本站 **SPA catch-all 讓任意路徑回 200 + text/html**，只有 `/api/*` 回 404 JSON ⇒「200 就是通過」會把 catch-all 讀成認證繞過，**兩個方向都會錯**（誤判有洞／漏掉真的洞）。反向案例＝打一條已知回 JSON 的 `/api/*`：連它都被判成 catch-all 就是 **content-type 沒在讀**，exit 2 不下結論。鑑別力實測：寫死 content-type 即 **EXIT=2**、還原即 0。⚠️ 我的第一版自己就壞了（`via_urllib` 寫死打 `CONTROL_URL` ⇒ catch-all 根本沒被測到，而且同一段輸出印 `→ 200` 又說「打不到」還 exit 0）——**新寫的檢核第一次跑出來的結果，最該懷疑的是檢核本身**（CK_AaaP 的判準；他們有結構相同的案例：守門測試造的反向告警自己滿足了守門正則因而通過）|
| `wiki_kg_link_audit.py` | Wiki ↔ KG 雙向引用率審計 |
| `windows_task_liveness_audit.py` | Windows 排程存活稽核 |
| `pm2_declared_vs_running_audit.py` | **PM2 宣告 vs 實際在跑**（weekly 71）。2026-08-27 人工盤點才發現 `ecosystem.config.js` 宣告三支而 pm2 上一支都沒在跑；其中 `health-watchdog` 的「假死自動復原」**沒有等價物** —— Docker 不會因為 unhealthy 就重啟容器。刻意不設 baseline：兩個方向（跑起來／從設定移除）都會讓它變綠，用 baseline 反而讓「還沒決定」看起來像已處理 |
| `work_record_chain_semantics_audit.py` | 作業紀錄鏈的語意檢核：完成的成果不該是新事件的前序 |

> ⚠️ **2026-08-27 校正**：下面四支先前列在「⏰ 後端排程（`scheduler.py`）」底下，
> 而 `scheduler.py` **一次都沒提到它們**。真正的執行者設計上是 `.git/hooks/pre-commit`，
> 而那支 hook 裡**一支都沒有**（檔案自 2026-05-27 未再更動）。
> orchestrator 有一步正是要抓這件事，但它跑在容器裡而 `.git/` 刻意不 mount
> ⇒ 自 2026-05-31 起每天回 `info: skipped`。**能抓到的地方它不跑，跑的地方它抓不到。**
> 已改接 weekly（host 端、進版控、不增加提交延遲）。

| `async_session_race_guard.py` | 並行 DB session 競態（ADR-0021／`development-rules.md` §5.1 **強制規範**）—— 靜態檢查 asyncio.gather 不得共用 db session | weekly 72 |
| `sse_headers_guard.py` | SSE 端點必須顯式 `Content-Encoding: identity` | weekly 73 |
| `schema_lazy_load_guard.py` | Pydantic Schema 不得訪問 ORM lazy-relationship | weekly 74 |
| `pattern_yaml_type_guard.py` | 掃 memory/patterns/failures/proposals 等 YAML frontmatter 的 id-like 欄位型別 | weekly 75 |
| `governance_enforcement_coverage.py` | ADR／教訓有沒有人在強制 —— 只報數字與斷鏈，不判斷「該不該有」 ｜weekly 51（⚠️ 2026-08-27 校正：原列在「月度架構覆盤」底下，實際跑它的是 weekly） |
| `declared_runner_truth_audit.py` | **本表自己的守門人** —— README 宣告的執行者是不是真的在跑它。`declaration_gate` 只驗「有沒有宣告」，宣告是不是真的先前沒有人驗：2026-08-27 首跑抓到 **7 支宣告錯了**，其中四支守的是強制規範（ADR-0021 等），真正的執行者設計上是 pre-commit hook 而那支 hook 裡一支都沒有 | weekly 76 |
| `case_award_pipeline_audit.py` | **成案程序管控** —— 報價/標案 → 承攬 → 成案編碼 → 金流，逐段報件數與**金額**。實查：已承攬無編碼 176 件／1,273 萬／請款 0；有編碼 51 件／48 有請款。⚠️ 只對惡化報紅（棘輪基線），存量不報紅 —— 它負責的是「不讓第 177 件靜靜發生」 | weekly 77 |

## 🧪 月度架構覆盤（`run_fitness.sh`）

| 腳本 | 用途 |
|---|---|
| `adr_lifecycle_check.py` | ADR Lifecycle Check — 列出所有 ADR 並統計 active_count |
| `auth_deeplink_returnurl_audit.cjs` | 寫死的「登入後目的地」常數（這些是 returnUrl 該覆寫的預設值，不該直接 navigate） |
| `auth_state_ssot_audit.cjs` | auth 基礎設施 — 唯一被允許「推導登入 + 導向認證頁」之處（相對 frontend/src，POSIX 斜線） |
| `autobiography_freshness_check.py` | Autobiography Scheduler Freshness Check (v6.10.2 B 配套) |
| `calendar_sync_reconciliation_audit.py` | Calendar Sync Reconciliation Audit — runtime 狀態對賬 |
| `calendar_title_standard_audit.py` | Calendar Title Standard Audit — 命名標準 SSOT 強制 |
| `capability_usage_audit.py` | Capability Usage Audit |
| `code_duplication_audit.py` | Code Duplication & Competing-Standard Audit — 全專案重複樣態 |
| `code_graph_orphan_audit.py` | 程式圖譜 orphan 偵測（Code-Graph Stale-Orphan Detector）— DRY-RUN 只報不刪 |
| `code_semantic_duplication_audit.py` | 程式圖譜語意異質同工偵測（Code-Graph Semantic Heterogeneous-Work Detector） |
| `config_dead_reader_scan.py` | Dead Config Reader 偵測 |
| `config_settings_drift_audit.py` | Config Settings Drift Audit — AST 衍生全域版 |
| `container_host_dependency_audit.py` | from __future__ import annotations |
| `container_lifecycle_audit.py` | 偵測 docker container image tag drift（next_session_resume 8 大根因 #4） |
| `contract_case_code_coverage_audit.py` | 承攬案件 case_code 橋接覆蓋率審計 |
| `contracts_only_import_guard.py` | Contracts Only Import Guard |
| `cron_external_binary_guard.py` | cron 外部執行檔依賴「沉默跳過」護欄 |
| `cron_health_check.py` | Cron 健康度（v6.2 Phase C2） |
| `cross_repo_auth_state_audit.py` | fitness step 42 (L44 配套) |
| `cross_repo_secret_audit.py` | fitness step 41 (L41 配套) |
| `csrf_service_drift_audit.py` | CSRF Service Drift Audit — pile ↔ lvrland csrf_service 單一源守門（Tier2 / L80） |
| `db_pool_exhaustion_audit.py` | **兩個維度**：① 應用自己的池（原有）② **伺服器端 `max_connections` 額度**（2026-08-27 加）—— 兩者會完全背離：實測應用池 15/35 報 GREEN 2.9%，而伺服器 49/50 正在拒絕每一個新連線。②**刻意不靠 DB 連線量**（需要它的時候正是連不進去的時候），退回 postgres 容器的 `/proc/net/tcp` |
| `db_schema_drift_audit.py` | 偵測 SQLAlchemy 模型 vs Alembic migration drift（next_session_resume #1） |
| `dead_ui_detector.py` | Dead UI Detector — PLAYBOOK §6.5 Anti-pattern 落實 |
| `dialogue_learning_coverage_audit.py` | Dialogue Learning Coverage Audit — 對話學習真實覆蓋率 |
| `dispatch_cache_contract.sh` | 派工 cache 契約 lint |
| `domain_score_freshness_check.py` | Domain Score Freshness Watchdog |
| `facade_consumer_audit.py` | 偵測 v6.10 P1 抽象層（contracts/facades/ + contracts/ports/）的零 caller 反模式 |
| `facade_only_check.py` | Facade Only Check |
| `frontend_api_wiring_audit.py` | Frontend API Wiring Audit — 導覽鏈 page→endpoint 接線治理 |
| `frontend_bundle_size_drift_audit.py` | 偵測 frontend Vite build artifact 是否 silent 膨脹超過閾值 |
| `generic_filter_audit.py` | Generic Filter Audit |
| `heterogeneous_work_audit.py` | 異質同工防增量審計（Heterogeneous-Same-Work Anti-Regrowth Audit） |
| `integration_e2e_validation.py` | Integration E2E Validation |
| `integration_liveness_check.py` | F14 (5/04 v3.0 覆盤洞察 11) — 整合鏈活體驗證 |
| `lessons_drift_check.py` | Lessons Drift Check — 防 LESSONS_REGISTRY 成為 dead doc |
| `line_notify_heartbeat_check.py` | F15 (5/04 v3.0 覆盤洞察 15) — LINE notify 7 天 heartbeat watchdog |
| `module_portability_audit.py` | Module Portability Audit |
| `naming_convention_audit.py` | Naming Convention Audit |
| `navigation_live_integrity_audit.py` | 導覽列 live 完整性稽核 |
| `network_audit.py` | 跨 repo Docker Network Standard 驗證 |
| `paths_sloppy_calc_guard.py` | Paths Sloppy Calc Guard |
| `powershell_bom_audit.py` | PowerShell UTF-8 BOM Audit |
| `producer_output_watchdog.py` | Producer 產出自我檢核 watchdog（Silent-Success Detector）— 行為層 SSOT ★標準化架構 |
| `queryKey_drift_audit.py` | React Query queryKey 一致性（兩種形態）：**漂移**＝invalidate 的 key 沒有人在用（L39）；**撞號**＝同一個 key 對到不同資料源，誰先載入誰決定快取內容（2026-08-20 新增） |
| `role_permissions_consistency_check.py` | 角色權限一致性（ADR-0034）。2026-08-27 加第 5 項：**端點 `require_permission` 與前端 `hasPermission` 要求的權限，有沒有角色拿得到** —— 前四項只比對 nav ↔ roles ↔ 手維護的 `_BUSINESS_PERMISSIONS`，於是 4 個權限結構上無人可得而它回全綠。已知的走 `permission_unreachable_baseline.json`（每條註明理由），新出現的判紅 |
| `run_fitness.sh` | Architecture Fitness Functions — 本地月度覆盤腳本（零 CI 費用） |
| `scheduler_liveness_audit.py` | Scheduler Liveness Audit — 排程真活對賬 |
| `service-line-count-check.py` | 後端服務行數監控 — CI 自動警告 |
| `service_dir_entropy.py` | services/ 頂層散戶比例 |
| `signal_consumer_lint.sh` | Memory Signal Producer-Consumer 治理 lint |
| `sso_autoload_completeness_audit.py` | 驗證 consumer repo frontend SSO autoload 完整接通（next_session_resume #7） |
| `sso_bridge_conformance_audit.py` | SSO Bridge Conformance Audit — 跨 repo sso_bridge 安全契約守門（Tier2 / L80） |
| `startup_dependency_race_audit.py` | 偵測 docker-compose depends_on 缺 condition: service_healthy 的 startup race 風險 |
| `stub_import_lint.sh` | 禁止直接 import 已遷移的 stub 模組（DDD 遷移期護欄） |
| `subdomain_registry_audit.py` | 偵測 subdomain registry SSOT drift（next_session_resume 8 大根因 #3） |
| `synthetic_baseline_freshness_audit.py` | 偵測 synthetic_baseline_inject scheduler job 是否陷入 silent dead loop |
| `tier1_shared_package_audit.py` | Tier 1 共享套件版本偏移 + 消費模式稽核 |
| `toolkit_sync_audit.py` | Toolkit Sync Audit |
| `transaction_pollution_audit.py` | Transaction Pollution Audit — 偵測「吞錯不 rollback 污染共用 session」反模式 |
| `transitive_deps_audit.py` | Transitive Deps Audit |
| `uncommitted_work_audit.py` | Session 收尾完整性審計 — 未提交工作 × host↔容器部署對賬 |
| `wiki_unicode_dup_check.py` | Wiki Unicode 重名偵測（v6.2 Phase C3） |

## 🖥️ 瀏覽器走查（`run_ui_smoke.sh` / `run_visual_walk.sh`）

| 腳本 | 用途 |
|---|---|
| `run_ui_smoke.sh` | 自我檢核入口（CK_Missive） |
| `run_visual_walk.sh` | 瀏覽器視覺走查入口（逐頁截圖，供人工複覽版面） |
| `ui_smoke_auth.py` | 為 UI 自我檢核簽發臨時 admin session |
| `ui_smoke_data_guard.py` | 走查不得改變業務資料 —— 前後列數比對守衛 |

## ⏰ 後端排程（`backend/app/core/scheduler.py`）

| 腳本 | 用途 |
|---|---|
| `critique_health_audit.py` | Critique Health Audit |
| `daily_self_retrospective.py` | Daily Self-Retrospective |
| `generate_governance_dashboard.py` | Governance Integrated Dashboard Generator |
| `producer_registry.py` | Producer 產出判定的**單一實作** |
| `proposal_aging_alert.py` | Proposal Aging Alert |
| `run_fitness_weekly_host.sh` | Tier 2 Weekly fitness — host 端執行器 |
| `shadow-baseline-report.cjs` | 用 better-sqlite3 若可用，否則 fallback node sqlite3 package |
| `synthetic-baseline-inject.py` | Synthetic Baseline Inject — 注入模擬查詢到 /api/ai/agent/query_sync 以加速 Hermes 基線採集 |
| `weekly_evolution_generator.py` | Weekly Evolution Generator |

## 💓 健康監控（`scripts/health/`）

| 腳本 | 用途 |
|---|---|
| `config-persistence-check.py` | 系統重啟後配置持久化檢查工具 |

## 🪟 Windows 工作排程器

| 腳本 | 用途 |
|---|---|
| `run_capability_snapshot.sh` | 能力使用度快照入口（須在 host 跑：Prometheus 綁 127.0.0.1:19090） |

## ⚪ 無排程 —— 手動／一次性／已被取代

**每一支都必須寫明理由**。沒有理由的腳本就是孤兒，而孤兒會被後人當成「還在用」
而不敢動，或當成「沒人用」而誤刪 —— 兩種都是成本。

| 腳本 | 用途 | 為什麼沒有排程 |
|---|---|---|
| `admin_backup_smoke_test.py` | Admin Backup Smoke Test (L49 配套 — owner 要求「自我瀏覽器複查」) | 手動｜備份/還原端點煙霧測（L49 配套），owner 要求複查時跑 |
| `check-config.ps1` | 本機埠與服務配置速查（PowerShell） | 手動｜本機埠與路徑速查 |
| `check-ollama.ps1` | Ollama 服務健康檢查腳本 | 手動｜Ollama 服務健檢（推論異常時） |
| `check_consistency.py` | 前後端一致性檢查（早期版本，已被 api_contract_alignment_audit 取代） | **已被取代**｜api_contract_alignment_audit（weekly 25）涵蓋更廣的三方對照 |
| `code_graph_orphan_prune.py` | 程式圖譜 orphan 安全 prune（保守子集：真刪除 = symbol 全專案都不存在） | 一次性授權清理（2026-07-17 owner 選 A）；orphan 現為 0，保留供未來授權使用 |
| `config-check.py` | 系統配置檢查工具 - 簡化版本 | **已失效**｜指向的 docker-compose.unified.yml / port-config.json 皆已不存在（2026-03 佈局） |
| `cron_liveness_snapshot.py` | cron 真活快照 — 透過 /health/scheduler 取 SchedulerTracker + APScheduler  | **已被取代**｜scheduler_liveness_audit 已在 run_fitness |
| `doc-sync-check.cjs` | (a) CLAUDE.md 版本 | 手動｜文件版本同步速查 |
| `frontend_backend_endpoint_audit.py` | Fitness step 67: 前後端 endpoint 一致性 audit | **已被取代**｜api_contract_alignment_audit 涵蓋更廣 |
| `hermes-checkpoint-report.cjs` | 1. 解析 plan.md → phases | 一次性｜Hermes 遷移進度報告，遷移已結案 |
| `jwt_debug.py` | Debug JWT sign + decode inside container | 除錯工具（容器內簽/驗 JWT），非檢核 |
| `manifest_drift_audit.py` | Manifest Drift Audit | 手動｜shared-modules manifest 中繼資料完整性 |
| `notify_consumers.py` | Notify Consumers — CROSS_REPO_REFERENCE_GUIDE v6.0 通知 detector | 手動｜跨 repo 範本升級通知（pull-based），見 REFERENCE_FOR_OTHER_SYSTEMS.md |
| `security-config-check.py` | 生產環境安全配置檢查（讀 host .env，會誤報；暴露面改看 service_port_exposure_audit） | ⚠️ 讀 host .env 而非容器實際值，會誤報；且印 CRITICAL 仍回 exit 0。真實暴露面改由 service_port_exposure_audit（weekly 42）負責 |
| `skills-sync-check.ps1` | Version: 1.0.0 | 手動 / pre-deploy｜Skills 42 項同步驗證 |
| `soul-fidelity-eval.py` | SOUL.md Fidelity Eval — 跨 provider 人格遵循度評估 | 手動｜換模型時跑，程序見 docs/runbooks/hermes-model-swap.md |
| `soul-fidelity-multi-baseline.sh` | soul-fidelity-multi-baseline.sh — 多 provider × 多 model 批次 fidelity | 手動｜同上，多 provider 批次版 |
| `sso_entry_smoke.cjs` | Anonymous-load smoke test for SessionGate / EntryPage on public si | 手動｜SSO 匿名載入煙霧（日常已由走查涵蓋） |
| `sso_race_repro.cjs` | SSO bootstrap-race 真實瀏覽器重現 | 一次性｜SSO bootstrap race 重現（L74 已修） |
| `synthetic-baseline-loop.sh` | Synthetic Baseline Loop — 常駐執行合成流量注入，累積 Hermes Phase 0 shadow base | **已被取代**｜PM2 於 2026-05-27 廢除；改由 FastAPI scheduler 的 synthetic_baseline_inject job |
| `tender_ezbid_pcc_match_audit.py` | Tender ezbid ↔ PCC Match Audit (ADR-0046 Phase 2 ROI 試算) | 一次性｜ADR-0046 Phase 2 ROI 試算，決策已定 |
| `v6_8_acceptance.sh` | v6.8 Acceptance Test — 一鍵驗證 5/04 交付的所有 32 commits 真活 | 一次性｜v6.8 交付驗收（11/11 已通過） |
| `verify_ai_stubs.py` | AI re-export stub 一致性驗證 | 一次性｜DDD 遷移期 AI re-export stub 驗證，遷移已完成 |
| `verify_architecture.py` | CK_Missive 架構驗證腳本 | 手動 / CI｜架構 7 項自動化驗證 |
| `wiki-orphan-classify.cjs` | 讀取全部 wiki pages | 手動｜wiki 孤兒分類輔助 |
| `admin_endpoint_ui_consumers.py` | **人工觸發、刻意不接排程**：需要管理員的端點被哪些非管理頁面消費。2026-08-20「同仁變成代碼」修完後的掃全結果＝無第二例；剩下的是「頁面只要登入但頁內含管理動作」，403 部分屬刻意 ⇒ 接排程只會每天報同樣 4 個已知項。它是 `OPEN_ITEMS` **C5**（走查永遠以最高權限跑）收束時的盤點素材 ⚠️ 2026-08-27 校正：原列在「每週」底下，而它自己的說明就寫著「刻意不接排程」——**同一列裡兩件事互相矛盾**。 |
| `skill_value_audit.py` | 技能系統真價值稽核（Skill-System Value Audit）— 誠實化「技能演化」KPI ⚠️ 2026-08-27 校正：原列在「後端排程」底下，而 `scheduler.py` 一次都沒提到它。 |
| `v7_metrics_report.py` | M1 (5/04 v3.0 覆盤洞察 14) — v7.0 新指標 lite 報表 ⚠️ 2026-08-27 校正：原列在「後端排程」底下，而 `scheduler.py` 一次都沒提到它。 |
| `deploy_verify.py` | 部署後驗證（L76 三層＋**L93 ORM／認證層**）—— 2026-08-16 事故：三層全 200 而登入是死的，因為 /health 不觸發 ORM mapper。第 4 層用 **POST** /api/auth/check，401 是正確答案、500 才是壞了 ⚠️ 2026-08-27 校正：原列在「每日 fitness_daily」底下而它一次都沒被呼叫。**已改由 `scripts/deploy/deploy-public.sh` 第 7 步呼叫**——它的用途本來就是「部署後」，不是每日。 |

---

## 相關

- 檢核階梯與可信度規則：`docs/architecture/SELF_AUDIT_EVOLUTION_STANDARD.md`
- 盲區分類與提問法：`docs/architecture/BLIND_SPOT_STRATEGY.md`
- 共享引擎（**禁手改**，改回上游）：`scripts/checks/.shared-selfaudit/` ← `shared-modules/selfaudit/src/`
- 教訓登錄：`docs/architecture/LESSONS_REGISTRY.md`
