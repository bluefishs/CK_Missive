# Governance Lessons Registry — 治理教訓單點 SSOT

> **建立**：2026-04-28（v5.10.1）
> **目的**：解決「對策散落 commit/ADR/PLAYBOOK，新人需從 git log 重建脈絡」痛點
> **狀態**：accepted（單點查詢 SSOT，每月覆盤時更新）
> **適用對象**：當前/未來 Claude session、新進 owner、跨 repo 引用者
>
> **Why this exists（v5.10.1 owner 觀察）**：
> > 「我做了 R1→R7，每輪都是『發現 → 對策』，但對策都散落在 commit messages，
> > 沒有一個單點查詢的 lessons SSOT。下次 Claude session 接手，得從 git log 重建脈絡。」

> **⚠️ 編號缺口（2026-08-03 查證）**：本檔自稱「單點 SSOT」但 **L42–L48 從缺**
> （L41 之後直接跳 L49），而其他檔仍在引用那幾號 —— 例如 L49 family 的 Refs 就寫著
> 「同類 L41 跨環境 secret drift + L43 volume mount drift」。
> **那一段的內容沒有遺失**，在 `.claude/rules/cross-file-ssot-governance.md` 的
> L41–L45 family 表（含修法 commit / audit step / 對應 ADR）。
> 記憶索引原本指向 `L43_*.md`、`L44_*.md` 等**從不存在的檔案**，已於同日改為文字引用。
> 補寫 L42–L48 進本檔屬歷史重建，需 owner 決定是否要做。

每條 Lesson 含 5 欄位：
- **Trigger**：什麼情境會踩到（What to look for）
- **Cause**：根因（Why it happened）
- **Fix**：當時怎麼修（How it was fixed）
- **Prevention**：未來怎麼防（Don't repeat）
- **Refs**：commit / ADR / PLAYBOOK / FQID

跨 repo 引用 FQID：`CK_Missive#LESSONS_REGISTRY_v1.0`

---

## L01 — SSOT 聲明 vs 實作斷鏈（Dead Doc 反模式）
<!--enforced-by: scripts/checks/adr_lifecycle_check.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | ADR / 設計文件承諾「將實作 X」但實際從未建檔；scanner 報 dead config |
| **Cause** | PR 拆分後文件先 merge code 後做，PR 卡住 → ADR 變 dead doc |
| **Fix** | v5.9.9：補建 `backend/app/core/timeouts.py` SSOT（兌現 ADR-0028 承諾） |
| **Prevention** | ADR 必附 commit hash 證明已落地；ADR Lifecycle Check 加「文件提到的檔案不存在」detector |
| **Refs** | ADR-0028 / commit `284ef07e` / PLAYBOOK §4.9 |

## L02 — Yaml config 聲明卻 0 reader（Dead Config）
<!--enforced-by: scripts/checks/config_dead_reader_scan.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | yaml schema 寫了某欄位但 production code 0 呼叫點，scanner 報 dead |
| **Cause** | feature 設計時想到要支援，但實作 fallback 仍走 hardcoded |
| **Fix** | 兩種：(a) 真接線（`should_prefer_local` 案例）(b) 標 deferred marker（`inference_profiles` 案例） |
| **Prevention** | scanner v3 識別 `Status: pending integration` docstring → SKIP；新增 yaml 欄位需附 integration test 鎖定鏈路 |
| **Refs** | ADR-0030 patch A 案例 / commit `f0a3dc5a` / PLAYBOOK §4.9 |

## L03 — Mock.patch 路徑遷移（Wave 1 sub-batch B）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | service 從 `services/foo_service.py` 搬到 `services/foo/core.py` 後，test 內 `patch("services.foo_service.X")` 完全失效 |
| **Cause** | mock.patch 替換的是「使用該名稱的 namespace」，不是定義位置 |
| **Fix** | sed 批次更新所有 patch 字串到新路徑 |
| **Prevention** | 每個 sub-batch 完成 git mv 後立即 `rg --multiline 'patch\(\s*["\x27]app\.services\.<old>\.'` 預掃 + 修 |
| **Refs** | commit `173230f1` / PLAYBOOK §4.3 |

## L04 — Multi-line patch sed 失效（Wave 4 tender）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | sed 替換 patch 路徑後，test 仍 fail；`grep` 同行模式找到 0 處但實際有殘留 |
| **Cause** | Python 慣用法 `patch(\n  "..."\n)` 跨行，sed line-based 漏抓 |
| **Fix** | 必用 `rg --multiline`，殘留逐個 manual Edit（不用 sed） |
| **Prevention** | PLAYBOOK §4.3 補強 — 兩種格式都掃 |
| **Refs** | commit `74b3d262` / PLAYBOOK §4.8 |

## L05 — Class name collision（Wave 1 sub-batch C notification）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 子包多個模組定義同名類別（`notification.service.NotificationType` vs `notification.template.NotificationType`），`__init__.py` wildcard re-export 互相覆蓋 |
| **Cause** | 不同 service 各自演化出同名 type，未察覺衝突 |
| **Fix** | `__init__.py` 改 explicit re-export 主類別，子類型從具體 submodule import |
| **Prevention** | sub-batch C 設計時先 grep `^class ` 找重名 |
| **Refs** | commit `b106cc3a` / PLAYBOOK §4.4 |

## L06 — 內部循環 import → relative import（Wave 1 sub-batch A document）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | sub-batch 包含互相 lazy import 的 service（如 Facade pattern），stub 載入時造成循環死鎖 |
| **Cause** | stub 機制 + lazy circular import 互動 — stub 載入觸發 __init__.py 載入 import_facade，import_facade 又 lazy import stub → 死鎖 |
| **Fix** | 子模組間互引用必改 relative import (`from .core import X`)，完全不經過 stub |
| **Prevention** | sub-batch git mv 後跑 `grep -rn "from app\.services\.<old>" backend/app/services/<context>/` 找出所有內部 stub 引用，批次改 relative |
| **Refs** | commit `33d23776` / PLAYBOOK §4.5 |

## L07 — Private function (`_` 開頭) re-export（Wave 2 ERP）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | test 嘗試 `from app.services.<old> import _parse_head_qr` 等私有函數失敗，wildcard 不 export |
| **Cause** | Python `from module import *` 預設不 import 底線開頭名字 |
| **Fix** | stub 補 explicit re-export 私有函數清單 |
| **Prevention** | stub 建立後，grep `from app.services.<old> import _` 找出所有私有 import，補 explicit |
| **Refs** | commit `e1641e05` / PLAYBOOK §4.6 |

## L08 — Production caller 路徑同步（Wave 3 integration）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 大量 mock.patch 的 service（如 line_bot），即使 patch 路徑改了，仍多個 regression — 因 production caller 仍走舊 stub |
| **Cause** | stub 機制下 patch 失效 — patch 命中 `integration.line_bot.X` 但 dispatcher import 走 stub namespace 的 reference |
| **Fix** | sub-batch 完成後**production code 也批次 sed 改用新路徑**（不再走 stub） |
| **Prevention** | Wave 3+ 必做 `grep -rl "from app\.services\.<old>" backend/app/ backend/main.py` + sed |
| **Refs** | commit `bd5baeba` / PLAYBOOK §4.7 |

## L09 — Async mock 斷鏈（pre-existing test failures）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | pytest 報 `'coroutine' object is not iterable` / `StopAsyncIteration` |
| **Cause** | test 用 `MagicMock` 而非 `AsyncMock` 包 async function；或 side_effect iterator 被消耗完 |
| **Fix** | 個案修；本 session 多為 pre-existing，stash 對比證實非新 regression |
| **Prevention** | 每個 sub-batch git stash + 跑同套 test，確保 baseline 失敗清單與遷移後完全相同 |
| **Refs** | 多處：test_case_code / test_pm_case / test_agency_statistics 等 |

## L10 — Dead UI（後端實作但前端缺 UI）
<!--enforced-by: scripts/checks/dead_ui_detector.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶反映「某功能仍無法操作」，但 grep 後發現後端 endpoints 早已實作 |
| **Cause** | 後端先做 PoC + ADR 寫 routes 但前端 PR 卡住、或 ADR 沒寫 UI 需求 |
| **Fix** | v5.10.1：建 `AliasIntegrationDrawer` + 加 endpoints 常數 + UserManagementPage 觸發按鈕 |
| **Prevention** | 規劃 dead_ui_detector.py（cross-check `routes.py` 後端 endpoints vs `frontend/src/api/endpoints/`）；ADR 模板加 `## UI Integration` 段 |
| **Refs** | commit `03963499` / PLAYBOOK §6.5 |

## L11 — React Query staleTime + 0 invalidate = 60s 不刷新
<!--enforced-by: scripts/checks/queryKey_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶反映「狀態更新後頁面沒及時刷新」 |
| **Cause** | useQuery `staleTime: 60_000` + 沒有任何 mutation `invalidateQueries(queryKey)` |
| **Fix** | 雙管齊下：(a) `refetchOnMount: 'always'` + 短 staleTime (b) 所有相關 mutation 加 invalidate |
| **Prevention** | 每個 useQuery 設計時即列「哪些 mutation 會影響此 cache」清單；invalidate 集中於 mutation hook（非 caller） |
| **Refs** | commit `244593d0` / 派工總覽 morning-status 案例 |

## L12 — Stub 算散戶 → entropy 短期不會降
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | DDD 遷移 N 檔到子包後，service entropy 短期沒降反升 |
| **Cause** | scanner 把頂層 stub 也算 orphan；entropy = top_level / total，stub 仍佔分子 |
| **Fix** | 預期接受短期不降；待 v6.0 stub 移除後（grep 確認 0 caller）才會大幅降 |
| **Prevention** | retrospective / CHANGELOG 明確寫「stub 算散戶 → entropy 短期不變是預期」避免誤判 |
| **Refs** | PLAYBOOK §6 / WAVE_1_RETROSPECTIVE.md / 整體 entropy 29.4% → 23.5% 軌跡 |

## L13 — sed 替換漏掃 cross-cutting test 檔（Wave 8）
<!--not-enforceable: 這是 Wave 1-8 服務遷移期的一次性操作程序（掃 patch 路徑／私有 import／test 檔）。遷移已於 2026-08-13 隨最後 32 個 stub 清除而結束，沒有持續適用的規則可強制。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | sub-batch sed 跑完跑 target service 的 test 全綠，但全套件 pytest 報 N 個 regression |
| **Cause** | sed 只掃對應 test file（如 `test_system_health_service.py`），漏掃跨服務的 test（如 `test_agent_tools.py`）|
| **Fix** | sed 後跑 `grep -rln "app\.services\.<old>\." backend/tests/` 全掃 |
| **Prevention** | sub-batch 完成必跑全套件 pytest（不只跑 target test） |
| **Refs** | commit `bf69487c` |

## L14 — GitHub Actions 自動觸發產生雲端費用
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | GitHub Actions push trigger 自動跑，每月累積費用 |
| **Cause** | CI workflows 預設綁 push event |
| **Fix** | 全 workflow 改 `workflow_dispatch` 唯一觸發 |
| **Prevention** | 所有檢查走本地 hook + monthly cron；新 workflow 預設手動 |
| **Refs** | feedback memory `feedback_no_github_actions_cost.md` / `.github/workflows/ci.yml` |

## L15 — Telegram 個人號當主推播通道（ADR-0027）
<!--enforced-by: scripts/checks/credential_liveness_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 主推播通道突然全斷（Telegram 個人號封禁） |
| **Cause** | admin push 全靠 Telegram 個人號 |
| **Fix** | 切 LINE；Telegram 維被動 bot；加 PII sanitizer |
| **Prevention** | 通道應**多供應**設計，從 day 1 用 `notification_dispatcher` 抽象至少 2 通道 |
| **Refs** | ADR-0027 / `telegram_content_sanitizer` |

## L16 — 一個 dataclass 塞 100+ 設定欄位
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 修一個 config 值找半天；dataclass 行數失控 |
| **Cause** | `AIConfig` 累積 50+ 欄位涵蓋 LLM / search / agent / pattern / compaction |
| **Fix** | （規劃）按 bounded context 拆 config — `AIConfig` / `SearchConfig` / `AgentConfig` |
| **Prevention** | 新 repo 從 day 1 即按 context 拆 config |
| **Refs** | TEMPLATE_EXTRACTION.md §3.6 |

## L17 — DDD 遷移看職責邊界不看行數
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | service 行數 > 600 line 觸發拆分提醒，但內容單一 domain 完整實作 |
| **Cause** | 早期定義「行數驅動拆分」規則 |
| **Fix** | 改「職責驅動」— 1074 行單一 domain 不拆，200 行混三 domain 必拆 |
| **Prevention** | feedback memory 永久標 `feedback_ddd_over_line_count.md`；service-line-count-check.py 改僅警告不阻擋 |
| **Refs** | feedback memory / WAVE_1_RETROSPECTIVE.md |

## L18 — Wiki dispatch backfill 不需 fuzzy match
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | wiki↔KG link 30%（dispatch 0% linked），假設需 fuzzy match |
| **Cause** | 假設錯誤 — backfill 腳本根本沒跑過 |
| **Fix** | 直接跑現有 exact match backfill → 100% |
| **Prevention** | 任何「現況很差」的指標**先試現有工具是否曾跑過**，再考慮新工具 |
| **Refs** | commit `a0dc6901` / v5.9.9 KG 100% 達成 |

## L19 — KG embedding 維護需週期性 backfill

| 欄位 | 內容 |
|---|---|
| **Trigger** | DDD 遷移後新增 ~700 entity 進 code-graph，KG embedding 從 100% 降到 96% |
| **Cause** | code-graph 自動採集新 service entity 但 embedding 未自動跟進 |
| **Fix** | 跑 `backfill_kg_embeddings_all.py --apply --all`（17 秒 / 674 筆 / zero cost） |
| **Prevention** | fitness step 5 月度跑；考慮 nightly cron auto-trigger 若 coverage < 95% |
| **Refs** | v5.10.1 fitness 後 996% → 100% / Ollama nomic-embed-text |

## L21 — Agent evolution scheduler 整合斷鏈（redis counter 卡 0）
<!--enforced-by: scripts/checks/agent_evolution_health.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | `agent_evolution_history` 14d+ 0 新增；`crystals/` 持續空 |
| **Cause** | **2026-04-29 v5.10.2 根因確認 — 兩個 silent failure 疊加**：(1) `agent_post_processing.py:144` 用 `from app.core.redis import get_redis`，正確 module 是 `app.core.redis_client` → ImportError → 被 `except Exception: pass` 吞掉（違反 ADR-0028）→ `redis=None` → `should_evolve()` line 92 直接 return False → counter 永不 incr → evolution 永不跑 (2) `agent_evolution_health.py:44` 寫 `agent:evolution:query_counter`（多 `er`），scheduler 實際用 `agent:evolution:query_count` → health script 永遠報 counter=0 誤導 owner 判斷。crystallizer 鏈路（pattern→proposal）正常跑因為走別的路徑 |
| **Fix** | **v5.10.2** (1) `agent_post_processing.py:144` 改用 `app.core.redis_client` + silent `except` 改 `logger.error(exc_info=True)`（ADR-0028 合規）(2) `agent_evolution_health.py:44` 修 key 名稱對齊 scheduler。**實證**：fix 後送 1 次 agent query → counter `0 → 1` ✓，`agent:evolution:signals` + `eval_history` keys 出現 ✓ |
| **Prevention** | (a) Module 名稱以 string import 時加 unit test 驗 module 真實存在（避免 ImportError 被當例外吞）(b) Redis key 常數**集中到單一 const module** 供 scheduler + health script 共用，避免 typo 漂移(c) ADR-0028 守護擴大：silent `except: pass` 在 fitness 加 lint(d) Integration test 鎖定 `should_evolve()` 鏈路（avoid dead integration） |
| **Refs** | v5.10.2 fix commit pending / `agent_post_processing.py:144` / `agent_evolution_health.py:44` / `agent_evolution_scheduler.py` / 同類 L01 dead integration / **這是「silent failure × silent failure」疊加經典反例**（ADR-0028 教材） |

## L24 — Self-evaluator 標準過鬆 / Pattern 門檻過緊（雙重失衡）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | v5.10.2 #4 evolution 修復後審 Redis pattern 分布：53 個 pattern 全部 success_rate ≥ 0.95（無一例外），但 hit 分布偏低（23 筆 hit 1-2 / 5 筆 hit 3-4），結晶 candidates 累積太慢 |
| **Cause** | (a) `MIN_HIT_FOR_CRYSTAL=5` + `MIN_SUCCESS_RATE_FOR_CRYSTAL=0.95` 雙閘設計，預期「高成功 + 高頻」才結晶。實測 success_rate 全卡頂 → success 閘形同虛設，hit 閘變成唯一瓶頸 (b) self_evaluator 給分過鬆：每次 query 後評，但「能回應 = 高分」沒區分 hallucination / 找不到 / 完美回答（04-23 列無關公文 hallucination 仍評高分案例佐證） |
| **Fix** | （v5.10.2 評估記錄，未即刻 apply）門檻 5→3 立即解鎖 5 筆候選（+10%）。但更根本是修 self_evaluator 區分度 — 增加 negative-test hallucination 偵測規則 |
| **Prevention** | (a) Pattern 門檻調整前 dry-run，評估「會新增多少 promotion」(b) self_evaluator 應有 calibration test：人工標注 20 筆 query，看評分 vs 標注一致率，<70% 即報警 (c) success_rate 分布 entropy 監測 — 若全卡 1.0 即評分機制失效信號 |
| **Refs** | v5.10.2 Phase 4.1 評估 / `agent_evolution_scheduler.py:78-79` 門檻常數 / synthetic-baseline-inject.py 修正後仍 100% 高分問題 |

## L25 — 鏈路驗證 vs 鏈路盤點（grep 關鍵字陷阱）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 驗證「坤哥自我學習進化」鏈路 2（Failure → Defense rule → Planner prompt）時，初判 `load_active_defenses` 0 caller 即斷定 dead integration |
| **Cause** | 用了原始函式名稱關鍵字 grep，但實際 export 是包裝過的便捷函式 `get_defensive_rules_block`（agent_planner.py 用後者，不直接用 load_active_defenses）。「grep 找不到 caller」≠「沒有 caller」 |
| **Fix** | v5.10.2 KUNGE_LEARNING_VERIFICATION 救：補做 Phase C 直接呼叫該模組任一 export 函式看輸出，**1136 chars defense block 證實鏈路活著**。原判斷 dead 改為閉環 ✓ |
| **Prevention** | (a) 鏈路驗證**必跑實際呼叫**（asyncio.run + module call），不能只靠 grep (b) grep 時應掃整個模組所有 public export，不只 1 個關鍵字 (c) 對 dead integration 判斷加二次驗證——真試呼叫看輸出 |
| **Refs** | KUNGE_LEARNING_VERIFICATION.md §1 鏈路 2 / `auto_defense.py:97 get_defensive_rules_block` / 同類 L01（dead integration 判斷需證據而非假設） |

## L20 — Lessons 散落 commit/ADR/PLAYBOOK → 需 SSOT
<!--enforced-by: scripts/checks/lessons_drift_check.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner / 新 Claude session 接手時，需從 git log + 7 份 doc 重建 incident 脈絡 |
| **Cause** | 對策淬鍊散在 commit messages（R1~R7）+ ADR 章節 + PLAYBOOK §4.x + RETROSPECTIVE 等 |
| **Fix** | v5.10.1：建本檔 `LESSONS_REGISTRY.md` 為單點查詢 SSOT |
| **Prevention** | 任何「發現 → 對策」必新增 L## entry 在本檔；commit message 末尾加 `Refs: L##`；`lessons_drift_check.py` (commit `2cee9943`) detector 月度跑防 dead doc |
| **Refs** | 本檔自身 / commit `3fd04734` / `lessons_drift_check.py` |

## L23 — 領域驅動拆分 vs 行數驅動拆分（拒拆判準）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 維護者看到「1000 行檔案」直覺反應「該拆」，提案把 morning_report_service.py (1,074L) / agent_orchestrator.py (642L) 拆成多檔 |
| **Cause** | 行數本身不是 DDD 邊界依據（feedback_ddd_over_line_count）：「1000 行單一領域不拆，200 行混三領域必拆」。但人對「大檔案」有本能厭惡，容易誤把行數當拆分理由 |
| **Fix** | **v5.10.2 評估後拒拆**（兩件案例驗證判準）：(1) `morning_report_service.py` 1,074L — 4 主題 sections（派工/會議/現勘/遺漏建檔）是「晨報生成」**單一領域內的層次分解**，`_get_*` (queries) / `_format_*` (formatting) / `_compute_*` (純函數) 是領域內 helper，不是混多領域。`morning_report_queries.py` (27L) 是 Phase 1 標記檔已預留 future 遷移路徑，但時機應在「新增領域邏輯時自然發生」(2) `agent_orchestrator.py` 642L — 7 個 method 全是 agent loop 不可分割環節（stream/tool loop/wiki ingest/trace flush）。原規劃「抽 plugin contract」評估後不必要：plugin pattern 已分散在 `agent_tools/` 子包、`agent_self_evaluator.py`、`agent_pattern_learner.py` 等別處 |
| **Prevention** | (a) 提案拆分時必先回答 3 個問題：① 內部方法是否屬不同 bounded subdomain？② 拆完後跨檔呼叫多還是單檔內呼叫多？③ 是否有外部消費者目前需要的 pattern？三題若無一個 yes → 不拆 (b) 對比範例：v5.10.2 #1 拆 `ai_stats.py` 692L (混 7 領域 → 拆) vs 本 lesson 不拆 morning_report 1,074L (單一領域) — 領域邊界才是判準 (c) 「行數是結果，不是目標」每次拆分後 commit message 要說明「拆出哪 N 個 bounded subdomain」 |
| **Refs** | v5.10.2 #6 評估 / `morning_report_service.py` (kept 1,074L) / `agent_orchestrator.py` (kept 642L) / 對比 `ai_stats.py` (拆 692L → 7 檔) / `feedback_ddd_over_line_count.md` |

## L26 — Half-Wired Anti-Pattern Stacking（多層 bug 疊加遮蔽）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶報告「一般使用者看到不該看的選單」，連續 3 次「修了 → 仍可看 → 再修」；單一現象背後 4 層獨立 bug 疊加（P-57 backend schema / P-58 frontend dev mode / P-59 NavTree UX / P-60 DB 資料漂移）。任一層沒修都看到「以為修了仍復現」假象。 |
| **Cause** | 多層獨立 bug 同時存在時，外層 bug 會 mask 內層 bug。修第一層後外觀沒變不代表沒修，而是被第二層遮住。維護者容易誤判為「上一個 fix 沒生效」而回滾，反而退步。 |
| **Fix** | v6.8+：建立「**穿透式驗證**」debug 邏輯。每修完一層，以 query「這層的修法在 unit test 通過了嗎」確認 → 若通過但用戶仍復現 → **下一層必有 bug**，繼續挖。將 `failure-sidebar-perm-4layer-stack.md` 立成範本案例。 |
| **Prevention** | (a) 大 incident debug 必有 task list 標記每層修法獨立 (b) 每修完一層立即 unit test + 文字描述「這層改了什麼會 affect 用戶看到什麼」(c) 用戶仍復現時不要回滾，假設「下一層仍有 bug」繼續挖 (d) 任一層修法都附 regression test 防回退 |
| **Refs** | `wiki/memory/failures/failure-sidebar-perm-4layer-stack.md` / commits P-57~P-60 / 同類 ADR-0025 13-day dormant |

## L27 — Dev Mode Override Trap（VITE_AUTH_DISABLED 強制覆蓋真實用戶）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | dev 內網 `VITE_AUTH_DISABLED=true` 為求方便，但 `usePermissions.fetchUserPermissions()` 看到此 flag 後直接覆蓋真實 user_info 為 mock superuser → 即使 user 已登入，他們的 role / permissions 也被無視 → dev 永遠以 superuser 視角操作系統，無法測試其他 role |
| **Cause** | 早期 dev mode 設計目標是「跳過登入流程」但實作為「跳過所有權限檢查」。兩個目標被合併在同一個 flag — 結果 dev mode 不只跳過 login，連身份本身也被改寫。 |
| **Fix** | P-58（5/07）：新 helper `shouldUseDevMockUser()` — 只在「`VITE_AUTH_DISABLED=true` 且 localStorage 沒真實 user_info」時才回 true。修 7 處 `isAuthDisabled()` 短路 + `useNavigationData` 對應切換 + 4 regression test 鎖定 4 種 case（公網/dev 無登入/dev 有登入/localStorage throw）。 |
| **Prevention** | (a) 所有 frontend dev override 都採「opt-in fallback」原則：只在沒有真實 state 時介入 (b) 「跳過登入」與「跳過權限」必須是兩個獨立 flag (c) 長期願景：移除 dev short-circuit，改為 dev 內網提供 5 個固定 quick-login 按鈕（superuser / admin / staff / user / unverified）走真實 permission flow |
| **Refs** | `failure-sidebar-perm-4layer-stack.md` §層 2 / commit P-58 / `shouldUseDevMockUser.test.ts` |

## L29 — Domain score 寫入鏈再次中斷（dict key bug + 涵蓋率不足）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶反映「坤哥自我成長又中斷」。L21 已修 redis import + key typo，但 v6.9 evolution_health 報告 counter=224 累積 OK / 14d 13 次觸發 ✓，**但 domain_scores Redis 全 (no data)** → domain-aware evolution trigger（5 連續低分）永遠不觸發 → 即使某 domain 持續弱仍不會被識別。 |
| **Cause** | **雙重 silent gap 疊加**：(1) `agent_self_evaluator.evaluate_and_store` L257-258 用 `tool.get("name")` 但 `agent_tool_loop.py:312/381` 實際 append 的 dict key 是 `"tool"` → 永遠拿空字串 → domain 永遠 None (2) `TOOL_DOMAIN_MAP` 只有 19 entries（涵蓋率 < 25% 的 98 個 tool）→ 即使 key 對也大量 tool 無法歸類 (3) `except Exception: pass` silent skip 違反 ADR-0028 → 失敗 0 可見性 |
| **Fix** | **v6.9 三件組**：(a) `tool.get("tool") or tool.get("name") or ""`（雙 key 容錯，"tool" 優先）(b) 擴 `TOOL_DOMAIN_MAP` 19 → 47 entries 補高頻業務 tool + 引入 `_DOMAIN_PREFIX_RULES` prefix fallback（如 `search_dispatch_*` → dispatch）(c) `silent pass` → `logger.error(..., exc_info=True)` + 新建 `resolve_tool_domain` 統一 resolver。**實證**：8 regression tests 鎖定 `tool` key 契約 + prefix fallback + silent except 防回退 + domain_scores 真活寫入。 |
| **Prevention** | (a) 跨模組 dict key 必有 contract test 鎖定（避免一邊改 key 另一邊不知）— 本案 `test_tool_loop_appends_with_tool_key` 偵測 source code (b) Static map（如 TOOL_DOMAIN_MAP）必有最低涵蓋率 test — `test_tool_domain_map_has_minimum_coverage` 鎖定 ≥ 40 entries (c) **Domain scores 累積 health check**：擬建 fitness step 22 — 7 天滑動窗 0 domain_scores 寫入 → 警報（這是 L29 真活第一發）(d) silent except 全面 lint（grep `except Exception:\s*pass` 在 services/ai/）月度跑 |
| **Refs** | v6.9 commit pending / `agent_self_evaluator.py:259-285` / `agent_capability_tracker.py:31-90 + resolve_tool_domain` / 同類 L21（兩次 silent failure 疊加）+ L01（dead integration）+ L25（鏈路驗證需穿透式）/ **這是「dict key contract drift × static map 涵蓋率不足 × silent except」三重疊加教材** |

## L28 — JSON-as-TEXT Schema Drift（DB Text 存 JSON 但忘 parse）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | `site_navigation_items.permission_required = TEXT` 存 JSON 字串如 `'[]'`、`'["x:y"]'`，但 `_item_to_dict` / `nav_repo.get_children_recursive` 直接回傳字串。前端 `'[]'.length === 2 ≠ 0` → filter 失效以詭異方式破壞權限過濾。 |
| **Cause** | DB 用 TEXT 存 JSON 是常見折衷（避免 JSONB 跨 DB 相容性問題），但 endpoint 沒對應 parse helper → ORM column 型別與 API 對外型別不一致。新加的 `/admin/role-permissions/nav-tree` endpoint **正確** parse，但舊 `/secure-site-management/navigation/action` 漏 parse — schema drift 在 endpoint 層產生。 |
| **Fix** | P-57（5/07）：endpoint + repo 兩端對齊新增 `_parse_permission_required` helper（None / "" / "[]" / valid JSON / list / 損壞 → 安全 fallback []）。19 unit test 含 alignment test（兩 helper 對相同輸入產出相同結果）。前端 `useNavigationData` fallback 也改為「**只**放行真正空陣列」防禦式雙保險。 |
| **Prevention** | (a) 所有 `Column(Text, comment="JSON")` 在 dict 化前都過 helper parse + 加 unit test 鎖定型別轉換 (b) 任何 TEXT-as-JSON 欄位寫進 ER diagram comment 並警告「endpoint 必 parse」 (c) Schema drift 偵測：fitness step 加「同一 column 在不同 endpoint 是否型別一致」 (d) 長期願景：能用 JSONB 就不用 Text |
| **Refs** | `failure-sidebar-perm-4layer-stack.md` §層 1 / commit P-57 / `test_nav_permission_required_parse.py` (19 tests) / 對比正確 implementation：`role_permissions_admin.py` nav-tree endpoint |

## L30 — Pipeline Integration as Priority（環節不連通就是浪費）
<!--enforced-by: scripts/checks/capability_usage_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | v6.10 retro 揭發：crystals 開了沒人看每日產出 / fitness 跑了沒推 owner / capability_audit 寫了沒接 cron / metrics 暴露了沒人開 dashboard。10 條優化環節有 5 條 RED — 50% dis-integrated。 |
| **Cause** | 散修文化 — 每次 /loop 修個別零件，沒人負責「上游餵入 + 下游推出」完整性。建好的環節不等於連通的環節。**根因 = 缺中央 Orchestrator + push channel + 視覺化 dashboard**。 |
| **Fix** | 建 `docs/architecture/OPTIMIZATION_PIPELINE.md` 把 10 條環節畫成連通圖（每節標上下游 + dead segment）+ `backend/app/services/optimization_pipeline_orchestrator.py` 每日 cron 03:00 跑 5 step（fitness / capability_audit / memory_loop / shadow_baseline / precommit_hook）合成 digest + 寫 `wiki/memory/pipeline-reports/YYYY-MM-DD.json`。下一階段接 LINE/Telegram push owner + `/kunge/ops` 加 tab pipeline-health。 |
| **Prevention** | (a) 任何新 capability 上線前必標明「上游 trigger + 下游 consumer」 — 否則自動視為 dis-integrated 候選 (b) 月度 retro 強制跑 orchestrator + 檢視 daily digest 7d 趨勢 (c) 任何「結果」都不可只停在 stdout / file / DB — 必有 push channel 或 dashboard panel (d) 範本擴增 `install-template-to.sh --include=pipeline,capability` 讓子專案一鍵部署。 |
| **Refs** | v6.10 retro / `OPTIMIZATION_PIPELINE.md` / `optimization_pipeline_orchestrator.py` / `capability_usage_audit.py` / diary 2026-05-16 owner addendum / 同類 L01 dead integration + L22 跨 repo 引用治理 |

## L31 — ROI = entities × usage_rate（建表不等於用表）

| 欄位 | 內容 |
|---|---|
| **Trigger** | v6.10 retro 揭發：22,000 KG entities + 117,980 mentions 建好，但 agent 90% query 只用 `search_entities` 一個工具。`search_across_graphs` / `navigate_graph` / `search_tender` / `wiki_*` 全 7d 0% — 4 個 graph tool 完全沒被觸發過，14 個 KG entity_type 0% mention 命中。 |
| **Cause** | 「建表」與「用表」是兩件事，但日常維護只關注建表（每 sprint 都在加新 entity / endpoint / tool），沒人量測 usage_rate。傳統 ADR-0029 lifecycle 只管 ADR 數量、ADR-0028 silent failure 只管 error 路徑，**沒有任何規範管「建好沒人用」的死投資**。 |
| **Fix** | (a) 建 `scripts/checks/capability_usage_audit.py`（fitness step 23）— 偵測 tools / KG entity_types / memory loops / ADRs 4 類資產的 7d / 30d usage = 0 (b) 建 `docs/architecture/CAPABILITY_GOVERNANCE.md` — 三層健康度模型（Existence × Usage × Outcome）+ 8 狀態分類 + A/B/C 決策矩陣（Activate / Block-deprecate / Catch-rescue）(c) 對 12 dead capability 立刻分類處置（本 session 啟動 3 改善：cross-graph router rule / CRYSTAL_AUTO_APPLY=live / 條件式 KG 注入）。 |
| **Prevention** | (a) 任何新 capability 必有 Prometheus counter 確保 usage 可量測（`MODULARIZATION_STANDARDS_v1` §2 強制規範）(b) 月度 ROI 復盤強制執行 — 對 dormant 30d+ capability 必走 A/B/C 決策 (c) 任何「真活宣告」7 天後自動跑 capability audit 驗證 (d) ROI 量化指標：healthy ratio > 80% / dormant > 30d 數 < 20 / 上月決策落實率 > 70%。 |
| **Refs** | v6.10 retro / `CAPABILITY_GOVERNANCE.md` / `capability_usage_audit.py` / `MODULARIZATION_STANDARDS_v1.md` §2 / diary 2026-05-16 owner addendum / 同類 L20 dead doc 預防 + L01 dead integration |

## L32 — Frontend UI Component 不適合 packaging（LR-015 終局教訓 / 2026-05-18）

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v1.0 ship 14 frontend components (Header/Sidebar/SidebarContent) + 8 hooks → consumer install 後 19 TS errors → 5 層 transitive deps 全部要拷貝 → useMenuItems hardcoded 30+ Missive ROUTES |
| **Cause** | Frontend UI 強耦合 design system / route schema / permission model — 表面是 UI shell 但實際拉整個 repo 結構假設。step 30 audit 看 keyword 不看 import 鏈，portability score 1.000 ≠ self-contained。 |
| **Fix** | v2.0 backend-only：刪 frontend layout 全部，只保留 backend 6 檔 + 1 TS type definition (NavigationItem)。lvrland 真採用 → npx tsc exit 0 ✓ |
| **Prevention** | (a) PACKAGING_PATTERN Rule 9：Frontend UI Component 慎重模組化 (b) fitness step 34 transitive_deps_audit AST-based import 鏈偵測 (c) Frontend artifact 限 type definitions / pure utility hooks (d) 業務 UI shell 由 consumer 自寫 |
| **Refs** | ADR-0036 §Lessons / PACKAGING_PATTERN.md Rule 7/8/9 / step 34 transitive_deps_audit.py / lvrland Webmap 真採用 evidence (2026-05-18) |

## L33 — Transitive Deps 缺失必致 Half-Wired（LR-015/016 配套）
<!--enforced-by: scripts/checks/manifest_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | install.sh 拷 N 個檔，但每個檔 `import` 的真實依賴未在 manifest 列出 → consumer build/runtime fail |
| **Cause** | manifest.yml 設計時只列「主要安裝檔」，未追蹤每檔的 transitive deps (env.ts / authService / logger / hooks / common components / utility) — install.sh 機械拷貝主檔，consumer 揭發 5 層 deps 缺失 |
| **Fix** | (a) manifest schema v1.1 加 `transitive_dependencies` 欄位（framework_deps / schema_deps / runtime_deps）(b) install.sh 加 6-stage 守門：baseline → deps check → dry-run → install → verify build → smoke test (c) step 34 transitive_deps_audit AST 解析 import 鏈交叉驗證 manifest |
| **Prevention** | (a) 任何新 ck-* package manifest 強制 list transitive_deps (b) step 34 在 fitness gate 阻擋 unlisted_dep > 0 (c) install.sh `--strict` 模式跑 consumer 端 tsc + py_compile 驗證才報 install 成功 (d) 真採用嚴格定義 4 件齊備（install + 編譯 + 啟動 + hook 通過）|
| **Refs** | LR-015 / LR-016 lvrland session feedback / ADR-0036 §Lessons / manifest.yml v2.0 ck-navigation / step 34 transitive_deps_audit.py |

## L34 — 業務 specific 不可進 shared package（lvrland LR-020 對應 / 2026-05-18）
<!--enforced-by: scripts/checks/module_portability_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v1.0 ship 業務 ROUTES (DOCUMENTS / AGENCIES / DISPATCH) hardcoded 在 useMenuItems.tsx → consumer 完全無對應路由 → install 後立即 19 TS errors |
| **Cause** | 模組化過程未區分「框架可移植」vs「業務專屬」— useMenuItems 表面是 hook 但實際是業務 navigation tree builder，30+ 個 ROUTES 寫死。lvrland LR-020 揭發：shared package 內絕不可有業務 specific 內容（route / enum / API path / business magic number） |
| **Fix** | (a) ck-navigation v2.0 完全移除 useMenuItems.tsx (b) PACKAGING_PATTERN Rule 8 No Business Constants Hardcoded (c) 業務 specific items 改 consumer 端 init script seed 入 DB / config |
| **Prevention** | (a) shared-modules/ 內絕不 import `*ROUTES*` / `*API_ENDPOINTS*` / 業務 enum (b) step 30 keyword audit + step 34 transitive deps audit 雙重 gate (c) 新 package 必過 portability score ≥ 1.000（無 critical / high）才能 release (d) PR review 強制 grep 業務 keyword in shared-modules/ |
| **Refs** | lvrland LR-020 / PACKAGING_PATTERN.md Rule 8 / step 30 module_portability_audit / ck-navigation v2.0 changelog |

## L35 — 採納前必過 baseline TS check（lvrland LR-019 對應 / 2026-05-18）
<!--enforced-by: scripts/checks/cross_repo_template_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v1.0 install 標榜「14/14 100% PORTABLE 0 conflicts」→ consumer 真 install 後 19 TS errors → revert 才回 0 errors。dry-run conflicts 0 ≠ runtime 可運作 |
| **Cause** | 「真採用」評估只看 file write + conflict count，**未跑 consumer 端 build/runtime 驗證**。lvrland LR-019 揭發：採納前必須先 npx tsc / py_compile 驗證 baseline，否則 install 是半接通 |
| **Fix** | (a) ADR-0036 §Lessons 立「真採用嚴格定義」4 件齊備（install + 編譯 + 啟動 + hook 通過）(b) install.sh 加 verify build stage（6-stage 守門）(c) lvrland 揭發 Webmap TS baseline = 0 — 純基線 forward (d) ck-navigation v2.0 在 lvrland 達 TS exit 0 (件 2 通過) |
| **Prevention** | (a) install.sh `--strict` 模式跑 consumer 端 tsc + py_compile + smoke test 才報 install 成功 (b) consumers.yml `real_adoption_criteria.criteria_met` 必 4/4 才可標記 verified (c) 任何 partial < 4/4 一律標 INSTALLED_PARTIAL_N_OF_4 不可誤稱 VERIFIED |
| **Refs** | lvrland LR-019 / ADR-0036 §Lessons / consumers.yml v6.10 P1 / install.sh 6-stage 守門（待 v1.1 升級）|

## L36 — Repo Structure Assumption（install.sh 寫死目標路徑 / 2026-05-18）
<!--enforced-by: scripts/checks/module_portability_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v2.0 install.sh 寫死 `backend/app/api/endpoints/`，但 lvrland 用 `backend/app/api/v1/endpoints/` → 檔放錯位置 → 件 3 runtime smoke 失敗（Missive source 內 OK 但 consumer 結構差異）|
| **Cause** | Package source repo（Missive）的 backend structure 不等於所有 consumer 結構。lvrland 用 `v1/endpoints/` 規約 (API versioning)，pile/AaaP/hermes 可能各自不同。install.sh 不能寫死單一 target path |
| **Fix** | (a) install.sh 加結構偵測（Option A）：先掃 consumer 是否有 `backend/app/api/v1/endpoints/` 否則 fallback `backend/app/api/endpoints/` (b) manifest.yml 加 `target_patterns` 可配置欄位 (c) 補登 L36 入 LESSONS_REGISTRY (d) 加 PACKAGING_PATTERN Rule 10 「Target Path 必須可配置」 |
| **Prevention** | (a) install.sh 強制偵測 consumer 結構（不再寫死路徑）(b) 新 ck-* package 必加 target_patterns 多模式 (c) step 35 manifest_drift 加偵測 target_pattern 欄位是否存在 (d) consumer 採納前 owner 確認結構符合任一 target_pattern |
| **Refs** | lvrland P220 件 3 失敗 evidence (2026-05-18) / ck-navigation v2.0 install.sh / PACKAGING_PATTERN.md Rule 10（待補） |

## L22 — 範本資產缺跨 repo 引用治理規範
<!--enforced-by: scripts/checks/cross_repo_template_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 範本資產（playbook / lesson / detector / component）數量爆炸性增長（27+），但 consumer repo 不知如何引用、升級、回饋 |
| **Cause** | CK_AaaP/CONVENTIONS §1.3 只涵蓋 ADR FQID（`Repo#NNNN`），沒涵蓋範本資產的 FQID 命名 / 版本管理 / 引用模式 / 升級通知 / 貢獻回流規範 |
| **Fix** | v5.10.1：建 `CROSS_REPO_REFERENCE_GUIDE.md` 補完規範 — 5 大類別 FQID + 3 引用模式 + SemVer + 月度健檢 SOP + 27 範本資產目錄 + 4 個 consumer anti-pattern |
| **Prevention** | (a) 新增範本資產時必加 FQID 至 §6 目錄 (b) 升 minor/major 必更新 CHANGELOG `Note for consumers` 段 (c) `notify-consumers.py` (v6.0 規劃) |
| **Refs** | commit `b3112a9d` / `CROSS_REPO_REFERENCE_GUIDE_v1.0` / 同類 L20 dead doc 預防 |

## L37 — 覆盤報告自身也是「真活宣告 vs 真接通」候選（2026-05-19）
<!--enforced-by: scripts/checks/doc_reference_integrity_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 寫策略級覆盤時，自然會在 §結論 / §演進方向 提出新標準 / 新 ADR / 新原則；但覆盤本身是 day-1 產出，未經 dogfood 即標榜「策略級體檢」。如 RETRO_20260519 §5 提 3 個 ADR 候選 vs §7.4「禁做新建抽象層 / 守護腳本 / 標準文件」自相矛盾，是 LR-015 同型反模式（建好門面 + 自評通過 + 無 dogfood）。|
| **Cause** | 覆盤代理 / 寫手對自身產出無 ROI 量測機制，傾向「結論越多越專業」。Effort 估計常 3-4 倍樂觀（如 §6 列 5h 但實際 10-13h）。風險分級易用 hyperbole（如 R1「隨時觸發」缺實際 user base 量測）。ROI 量化常混淆「使用率」與「ROI」（前者是分母，後者是分子÷分母）。|
| **Fix** | v6.10 P1：(a) 覆盤報告必附 `§自我檢視` 段落，列出至少 5 個自己看到的弱點（如 RETRO_20260519 §9 列 7 缺陷）(b) Effort 估計 × 2-3x 緩衝後再對外宣告 (c) 「真活定義」不可依賴掛了的監督機制（如 capability_usage_audit JSON parse fail 期間不可用作真活判定）(d) §禁做 原則必檢查與 §策略提議 自洽 |
| **Prevention** | (a) 覆盤報告必有「P0 半天可做」清單 + Effort 估計 × 2-3x 緩衝 + 與 §禁做 原則自洽性校驗 (b) §風險 R1-R6 等級宣告必附「實際引爆率量測待補」(c) ROI 量化嚴格區分「使用率」「成本投入」「outcome 量」三維 (d) 報告產出後 7 天 owner check-in：本報告自己有沒有變 dead doc |
| **Refs** | `docs/architecture/RETRO_20260519_strategic_health_check.md` §9（自我檢視 7 缺陷）/ ADR-0036 §Lessons LR-015 / 同類 L30/L31 dead investment / 覆盤工具自身也犯反模式 = 元教訓 |

## L39 — QueryKey Drift（React Query invalidate silent dead）（2026-05-20）
<!--enforced-by: scripts/checks/queryKey_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶報「派工 158 公文對照僅 1 筆又出現 2 筆紀錄（類似問題已多次發生）」。DB + Redis cache 都實際 1 筆，但 UI 顯示 2 筆 — frontend React Query cache stale。深掘揭發：真實 list query 用 `queryKeys.taoyuanDispatch.orders(params)` = `['taoyuan-dispatch-orders', params]`，但所有 mutation invalidate 寫 `['dispatch-orders']` —— **兩個 key 完全不重疊**！5/18 第一次案例已加 invalidate 但 silent dead（永不生效），用戶 5/20 第二次踩 = 慢性 bug 真因。|
| **Cause** | **與 L29 dict-key drift 同型反模式**：A 邏輯寫 key X、B 邏輯讀 key Y、X≠Y 但兩端都以為對齊 → silent failure 累積。React Query `invalidateQueries({ queryKey: ['dispatch-orders'] })` 對 `useQuery({ queryKey: ['taoyuan-dispatch-orders', ...] })` 不起作用（prefix 不同）。命名漂移源：早期可能用 `['dispatch-orders']`，後改 `queryKeys.taoyuanDispatch.orders()` SSOT 但 invalidate 路徑沒同步更新。5/18 第一次 fix 又再次用舊散戶 key 寫死，沒走 SSOT。|
| **Fix** | v6.10.1 (5/20): (a) `useDispatchCacheInvalidator.ts`：DISPATCH_ORDERS_KEY 改用 `['taoyuan-dispatch-orders']` + 保留 legacy `['dispatch-orders']` 防其他散戶 query (b) `useDocuments.ts:176`：invalidate 改用 `queryKeys.taoyuanDispatch.all` SSOT + 仍保留 legacy key (c) 清 Redis backend cache `cache:dispatch:list:*` (d) 用戶 Ctrl+Shift+R 後 UI 應變 1 筆。|
| **Prevention** | (a) 任何 `invalidateQueries({ queryKey: [...] })` 必引用 `queryKeys.<module>.<entity>` SSOT，**禁止散戶手寫字串陣列** (b) 加 fitness step `queryKey_drift_audit.py`：grep 全 codebase invalidate keys vs useQuery keys 做交集 — 任何 invalidate key 未對應任一 query key 即報 (c) `useCacheInvalidator` 類 helper 集中所有 invalidate 入口，禁止 component 內直接呼叫 `invalidateQueries` (d) 任何 chronic bug「類似問題已多次發生」**第一個假設就是 silent dead invalidate / drift / wiring**，不要假設 backend bug |
| **Refs** | 用戶 5/20 報案（image dispatch=158）/ `frontend/src/hooks/taoyuan/useDispatchCacheInvalidator.ts:36` / `frontend/src/hooks/business/useTaoyuanDispatch.ts:48` / `frontend/src/config/queryConfig.ts` queryKeys.taoyuanDispatch.orders / 同類 L29 dict-key contract drift + L21 redis key 名稱漂移 + L28 JSON-as-TEXT schema drift（drift 反模式三件套）|

## L38 — 平時保險（cron / 異地備份）也是 LR-015 反模式高發區（2026-05-19）
<!--enforced-by: scripts/checks/offsite_backup_completeness_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶 5/19 指出「Docker Desktop 升級會清 volume．．．不可發生之錯誤」。盤點發現 CK_Missive 三重風險：(1) Windows Task Scheduler 無 `CK_Missive_Daily_Backup` 任務（5/16 後完全沒跑），但 setup_scheduled_task.ps1 寫了；(2) `backend/config/remote_backup.json` 14 天 `sync_enabled: false`，異地備份 0 次；(3) docker-compose.infra.yml 全用 named volume — Docker Desktop reset / WSL distro unregister 會**全清**。5/12 `ck_missive_backup_20260512_020000.sql` size=0（pg_dump 失敗仍 touch 檔）— 是 ADR-0028 silent failure 的備份版。|
| **Cause** | 過去討論 LR-015 都聚焦「**新建抽象層 + 自評通過**」（如 ck-navigation v1.0 標榜 portability 1.000 後爆 19 TS errors），但平時保險也是同型反模式：(a) 「排程應該在」≠「排程真在」(b) 「sync_enabled 該 true」≠「實際是 true」(c) 「named volume 可用」≠「升級後仍可用」(d) 「backup 跑完」≠「backup 檔有效」。共同病灶：機制建好後**從未驗證 wiring 真活**。|
| **Fix** | v6.10 P1（2026-05-19，1.5h 內）：(a) `scripts/backup/pre_upgrade_backup.sh`（96 行）4 層緊急備份（PG custom dump + PG SQL.gz + Redis rdb + 2 個 volume tar）+ NAS 異地同步 (b) `scripts/backup/restore_from_volume_tar.sh`（102 行）bit-perfect 還原 (c) `docs/runbooks/docker-desktop-upgrade-sop.md`（9 段）升級前 / 中 / 後 SOP (d) 立即跑 emergency backup 269MB 本機 + 272MB NAS Z 異地 — pg_dump 79MB / SQL.gz 76MB / Redis rdb 380KB / PG volume tar 193MB / Redis volume tar 149KB |
| **Prevention** | (a) 所有「保險機制」必每月跑一次 **real restore drill**（非假設）才算真活；本月 5/19 危機即 first drill (b) backup script 必加 `[[ -s "$file" ]]` 0B 檢查 + 失敗 Telegram alert（防 5/12 同類）(c) 用 `Get-ScheduledTask` / cron 真活 probe 補進 `optimization_pipeline_orchestrator` 環節（pipeline-reports JSON 每日記錄 last_run_time）(d) named volume → host bind mount 結構性升級（停機 5min，根除 Docker Desktop reset 風險）(e) `remote_backup.json sync_enabled` 改 true 後加 `sync_status alert`（連續 24h idle → red）|
| **Refs** | `scripts/backup/pre_upgrade_backup.sh` / `scripts/backup/restore_from_volume_tar.sh` / `docs/runbooks/docker-desktop-upgrade-sop.md` / `RETRO_20260519` §10 / 同類 L01 dead integration + L30 pipeline integration + L37 覆盤自身反模式 |

## L41 — JWT Secret Drift Silent Fail（4 重疊加 / 2026-05-21）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 員工 SSO Phase 1.5 整合 missive 時 `verify_ck_sso_jwt` 持續回 401，owner 花 6 小時逐項排除才找到「`.env` CK_SSO_JWT_SECRET hex 與 CF Pages JWT_SECRET 打錯一字元」。四重反模式疊加：(1) secret drift（手動 copy 失誤）(2) silent fail（`logger.debug` 在 prod INFO level 永不輸出）(3) 異常吞噬（單一 `except JWTError` 不分 SIGNATURE/EXPIRED/ISSUER/MISSING_CLAIM 四種子型）(4) 缺真 E2E（CI 用 mock JWT 全綠，從未跑「真 CF Pages 簽 → 真 backend 驗」端到端）|
| **Cause** | 每個反模式單獨都不致命，**疊加構成驗證永遠失敗、永遠靜默的死區**。與 L37 同型「平時看不到反模式」家族 — verify 失敗本是高頻事件，但被降級為 debug 後等於沒發生。與 L29 dict-key drift 同型 cross-side mismatch，但 L41 是「兩 hex string 跨環境同步」非「dict key 同 codebase 漂移」。|
| **Fix** | (a) 全 4 種 JWT exception 分別 `logger.warning` + 區分子型訊息 (b) `verify` 失敗 log 含 expected_issuer / hex_length（不漏 secret 本體）(c) `ck-sso-py/install.sh` v1.0 內建 4 acceptance check 強制 (Check 1 grep `.env`、Check 2 grep `logger.warning`、Check 3 bridge endpoint health、Check 4 owner 真 E2E) (d) Check 1+2 自動，3+4 必手動 — 自動 fail 拒絕 install，提示 owner 不可省 Check 4 |
| **Prevention** | (a) 任何「跨環境 secret 同步」流程加 hex 比對 self-test（不洩漏內容但比較 hash 前 8 chars） (b) 任何「驗證型」endpoint 預設 `logger.warning` 失敗、單元測試 cover 4+ 種失敗子型 (c) 跨 repo 共用模組必走 `install.sh` 含「真接通」自動 check + owner manual gate (d) 「採用」定義升級：程式進 repo + import 不報錯 + owner E2E pass = 真採用 |
| **Refs** | `D:/CKProject/CK_Missive/shared-modules/ck-sso-py/install.sh` v1.0 (4 acceptance check) / `D:/CKProject/CK_Website/docs/SSO-IMPLEMENTATION-STATUS.md` v1.2 / 真採用範本 `CK_lvrland_Webmap/backend/app/core/ck_sso.py` + `CK_PileMgmt/backend/app/core/ck_sso.py` / 獨立 lesson 檔 `wiki/memory/lessons/L41_jwt_secret_drift_silent_fail.md` / 同類 L37 silent-debug + L29 contract drift + L21 silent-fail 累積元教訓 |

---

## L77 — 標案 enrichment 死結：openfun 需 org_id、org_id 只在被反爬限流的 PCC 詳情頁（勿重試爬蟲路徑 / 2026-06-17）
<!--not-enforceable: 這是領域判斷的結論（資料源限制／相關性判準），不是可用機器驗證的規則。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 反映業務推薦特例無窮（隧道式電子血壓計命中「隧道」等），擬以 PCC 詳情 enrichment 取「採購性質/標的分類」做可靠職能篩選（財物=儀器可靠排除）。 |
| **Cause** | 資料死結：①openfun API（不限流、回乾淨採購性質/預算/底價/廠商）只能用「點分 org_id」查；②點分 org_id **僅在 PCC 詳情頁** `searchTenderDetail?pkPmsMain=`，今日清單頁(prkms/today)/ezbid/openfun-by-date 皆無；③PCC 詳情頁對我方伺服 IP **端點層反爬限流**——早上前幾次回完整 123KB(含 org_id)，密集除錯後即回 13–49KB stub(無 org_id)，curl/httpx/補 headers/換 UA/session+Referer/原始= 皆無效。⇒ 採購性質 server 端無法穩定取得。我方 `unit_id` 實為 PCC `pkPmsMain`。 |
| **Fix** | (1) **不投入 server 端 PCC 爬蟲 enrichment**（已徹底驗證死結，繼續＝沉沒成本）。(2) 官方直連修：`searchTenderDetail?pkPmsMain=<unit_id>`，base64 尾 `=` 須原樣(`quote(safe='=')`；`%3D` 落 stub)；使用者瀏覽器(他 IP)不受限。(3) 篩選以**確定性自維 UI**（關鍵字+排除+承攬史建議，即時生效）為可靠引擎，特例由 owner 自加排除。(4) DB enrichment 欄位(遷移 20260617a001)無害備用、服務 best-effort 不掛 cron。 |
| **Prevention** | (a) 外部資料源 enrichment 先做 spike 驗「id 格式映射 + 反爬/限流」再規劃管線（本案 P0 spike 即揭露 id 不匹配，P2 揭露限流）。(b) **非全面 IP 封**：限流為端點層、速率型——`prkms/today` 爬蟲資料源正常(200/1439 筆)、推薦/篩選不受影響，勿誤判為系統壞。(c) 密集除錯外部站點要節流(我方密集打 searchTenderDetail 觸發升級限流)。(d) 採購性質自動化唯一正解＝付費/官方開放資料授權或合法代理 API，非爬蟲（採購決策）。 |
| **Refs** | `docs/architecture/TENDER_RECOMMENDATION_FLOW.md` 附錄 B / `detail_enrichment.py`(best-effort,blocked) / 遷移 20260617a001 / commit `5ec45d7c` / 同族 healthcheck≠functional、外部依賴 spike 先行 |

---

## L76 — Windows Docker backend recreate/restart 易留殭屍埠轉發 socket → 公網 502（部署後必驗 host→8001 / 2026-06-16）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 為部署 tender 修法 `docker compose up -d --no-deps backend`（rebuild+recreate）後約 30 分鐘，owner 報「無法 Google 登入」；查證＝公網 `missive.cksurvey.tw` 全 **502 Bad Gateway**。 |
| **Cause** | backend 容器**內部健康**（`localhost:8001/health`=200、docker 埠映射 `0.0.0.0:8001` 正常），但 **host→localhost:8001 = 連線失敗(000)** → cloudflared 經 `host.docker.internal:8001` 撞死 socket → `EOF / Unable to reach origin` → 502。根因＝**Windows Docker Desktop 的埠轉發 proxy（vpnkit/port-proxy）在容器 recreate/restart 後成殭屍**（docker 層顯示綁定正常，但 host 側轉發已死）——CLAUDE.md 既列「Windows 殭屍 socket」Docker 陷阱。屬 backend 程式碼 baked image（非 bind-mount）→ 任何後端修法部署都需 recreate → 在 Windows host 上即觸發此風險（rebuild churn 的隱性代價）。 |
| **Fix** | `docker restart ck_missive_backend` 重建埠轉發 → host→8001 立即回 200、公網 `/`+`/api/health`+`/entry` 全 200、SSO 競態瀏覽器複驗 finalPath=/dashboard PASS。（cloudflared 端無需動；問題在 origin 側埠轉發。若 restart 無效需 `--force-recreate` 或重啟 Docker Desktop。） |
| **Prevention** | (a) **後端任何 rebuild/recreate/restart 後，必跑公網可達性驗證**（`curl host localhost:8001/health` + `curl https://missive.cksurvey.tw/api/health` 應 200），不可只看容器 health（容器內健康 ≠ 公網可達，同 healthcheck≠functional 元教訓）。(b) 納入 `deployment-effect-ssot.md` 與重啟 runbook 的後端部署 SOP。(c) 「健康但公網 502」黃金訊號＝先測 `host→localhost:8001`：通則查 cloudflared，不通則 backend 埠轉發殭屍→restart。(d) 考慮把 cloudflared origin 由 `host.docker.internal:8001` 改為**同 docker network 直連 `backend:8001`**（繞過 Windows 埠轉發層，根治此族；需評估 cloudflared 與 backend 是否同網）。 |
| **Refs** | commit（無 code，運維事件）/ `docs/runbooks/deployment-effect-ssot.md`（待補後端部署後公網驗證步驟）/ CLAUDE.md「Docker 陷阱：Windows 殭屍 socket」/ 同族 healthcheck≠functional（L43 §規則3、feedback_pre_demo_functional_verification）+ feedback_rigor_no_self_inflicted_instability（rebuild churn） |

---

## L75 — 推薦相關性：機關關係 ≠ 工項相關；粗放機關信號 + 粗粒度（府級）比對＝噪音源（標案業務推薦 / 2026-06-16）
<!--not-enforceable: 這是領域判斷的結論（資料源限制／相關性判準），不是可用機器驗證的規則。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 反饋每日業務推薦推 10 案「公司皆無涉略」（護岸災修/排水/道路改善/漁港疏浚/學生團體保險/地磅勞務委外）。 |
| **Cause** | 兩層根因：(1) **機關信號可「粗放獨立入選」**——推薦把「合作/承攬機關」當獨立入選路徑（OR），但機關（即使精準）會發包大量公司不做的工項；查證 10 案**零個命中訂閱關鍵字**，全靠機關信號入選。(2) **機關比對粒度過粗（府級）**——`南投縣政府/嘉義縣政府/苗栗縣政府` 等裸府級同時在合作/承攬名單，導致該府**任何**標案都命中；但公司真實承攬關係是**局/所級**（`桃園市政府工務局`/`地政事務所`）。另有 unicode 髒資料（`桃園市政府⼯務局` 用 U+2F37 部首字非正常「工」）使精準比對失準。本質＝**把「與誰有關係(機關)」誤當「做什麼工項(相關性)」**。 |
| **Fix** | Option B「關鍵字優先＋機關窄通道」：(a) 關鍵字（=工項）命中→一律入選且權重 10（遠高於機關 2/1，關鍵字案恆排最前）；(b) 機關信號改**精準局/所級**——排除裸府級（`NOT LIKE '%政府'`）+ 正規化 unicode（`⼯`→`工`）；(c) 機關獨立入選額外限**工程類**（`NOT IN 財物/勞務`），測量/技服（PCC 常歸勞務）改靠關鍵字路徑接。驗證（rebuild live）：days_back=8 → 0（噪音全濾、裸府級殘留 0）；days_back=60 → 15（關鍵字 4 + 精準局處工程 11）。 |
| **Prevention** | (a) 推薦/匹配系統區分「關係信號」與「相關性信號」——關係（機關/歷史）只能加權，不能粗放當入選門檻；真正相關性需「工項/內容」層級訊號（關鍵字/分類）。(b) 機關/組織比對須對到**實際承攬單位粒度**（局/所/科），勿用上級機關（府/部）粗匹配——上級會發包大量無關工項。(c) 名稱比對前先 unicode 正規化（部首字/全半形/異體字），髒資料使精準比對 silent 失準。(d) 推薦相關性決策樹須文件化（見 `TENDER_RECOMMENDATION_FLOW.md` 評估基準對照流程圖），便於調參與覆盤。 |
| **Refs** | `backend/app/services/tender/business_recommendation.py` v2.0.0（find_business_recommendations SQL）/ `docs/architecture/TENDER_RECOMMENDATION_FLOW.md`（流程+評估基準+Mermaid）/ commit `2fef0161` / 同族 L51.4/L51.6（推薦雜訊前案）+ L48.1（unicode BOM 髒資料 silent fail）+ ADR-0046 |

---

## L74 — 單一狀態欄被多個 async 來源 last-writer-wins 競寫 + 破壞性副作用＝經典 race（SSO「第一次停 entry、重刷才好」/ 2026-06-16）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 重開機後從 `www.cksurvey.tw` SSO 進 `missive.cksurvey.tw`，**第一次仍停在 /entry，重刷才登入**。此症狀已被「修」多次（L66 self-heal / `a66d410b` retry / `9e229a36` 宣告式導向），皆未根治。 |
| **Cause** | SSO 治本後 `sessionStore.status` 是唯一真相，但它被**兩個獨立 async 解析器 last-writer-wins 競寫**：(1) `bootstrap()`——重開機後 localStorage.user_info 磁碟持久殘留（cached≠null）→ 走 `validateTokenOnStartup`，舊 token 失效時**內部 `clearAuth()` 清資料** + 回 false → `anonymous`；(2) EntryPage `ssoBridge()`——用 ck_employee cookie 建立**全新 session** → `markAuthenticated` → `authenticated` → `<Navigate>` dashboard。**競態時序**：ssoBridge 先贏設 authenticated → bootstrap 的 validate（含 600ms retry，較慢）**遲到失敗**，(a) `clearAuth` 清掉剛建立的新 session、(b) status 覆寫回 anonymous → ProtectedRoute 把 dashboard 踢回 entry。**「重刷才好」的精確解釋**＝前次 clearAuth 已清 user_info → 重刷 cached=null → bootstrap 走 early-return（不 validate、不 clobber）→ ssoBridge 乾淨贏。歷次修法都只動「導向機制」，沒人看見「雙寫競態 + 破壞性 clearAuth」這層。 |
| **Fix** | SSOT 層（非再補 EntryPage）：① `authService.validateTokenOnStartup` 改**非破壞性**——不再內部 `clearAuth`（唯一 production caller 是 bootstrap，清除決策上收）。② `sessionStore.bootstrap` 加**競態防護**——`await validate` 後 `if getState().status==='authenticated' return`（已被 ssoBridge/login 升級則尊重、不降級不清）；只有真失效（無競態升級）才 `clearAuthData()`+anonymous。規則＝**markAuthenticated（明確成功事件）優先於被動舊 token 檢查**。驗證：sessionStore 競態 regression + useAuthGuard 19 綠 / tsc 0 / build 部署 / 匿名煙霧 resolved+entryRendered+0 fatal。 |
| **Prevention** | (a) 任一「單一狀態欄」被 2+ 個 async 來源寫入時，須明確定義**優先序**（明確事件 > 被動檢查），不可任由 last-writer-wins。(b) **破壞性副作用（clearAuth/清資料/刪檔）必須收歸唯一決策點**，不可埋在被動驗證函式裡，否則競態下會誤毀另一來源剛建立的有效狀態。(c)「第一次失敗、重刷成功」是 race 的招牌徵狀——優先懷疑「持久化殘留 × 啟動時序」而非導向機制。(d) **結構性護欄**：`auth_state_ssot_audit.cjs`（fitness step 64）禁新元件自行『推導登入+導向認證頁』，防 SSOT 再被打散（治本之後立 audit 鎖定，對齊「防護腳本存在≠生效」須掛 fitness）。 |
| **07-03 續集（第 N+1 次復發，owner「今日 OK 明日又壞」）** | 前述 audit 有盲點＝allowlist **完全信任 auth 基礎設施內部**，但真正破口都在基礎設施檔內：① `api/interceptors.ts` 的 `attemptSSOBridge()`（401 觸發）只 POST sso-bridge 設 cookie 就 `location.replace('/dashboard')`，**從不寫 user_info** → 重載後 bootstrap 讀 user_info=NULL → anonymous → 停登入頁（後端 cookie 有效故 /auth/me 仍 200 = 假象）；② `services/authService.ts` **獨立 axios 實例**的 401 攔截器無守衛 `clearAuth+location.href='/login'`（bootstrap 期間 /auth/check race 瞬態 401 搶在 600ms retry 前清 user_info+硬跳）。修＝attemptSSOBridge 200 補存 user_info；兩 axios 實例 401 都加 `getSessionStatus()==='anonymous'` 才破壞性清除。**audit 強化**：step 64 新增 **Rule C（401 破壞性動作須有 session 狀態守衛）+ Rule D（sso-bridge POST+reload 路徑須持久化 user_info）**，直掃基礎設施內部（受控測試證實會標紅修法前、通過修法後）。commit `79e36c4d`。 |
| **Refs** | `frontend/src/store/sessionStore.ts` / `frontend/src/services/authService.ts`（401 守衛 + validateTokenOnStartup 非破壞性）/ `frontend/src/api/interceptors.ts`（attemptSSOBridge 存 user_info + 兩實例守衛）/ `frontend/src/services/__tests__/authService.interceptor401.regression.test.ts` / `scripts/checks/auth_state_ssot_audit.cjs`（step 64 + Rule C/D）/ **`docs/architecture/SSO_RECURRING_REGRESSION_RETROSPECTIVE.md`（跨專案元覆盤 + 六不變式 + 驗證協定）** / commit `b2b6ae26`+`1dc75776`+`52053913`+`79e36c4d` / 同族：L66/L68/L69 + 見 L78 |

---

## L90 — 一次異常關機讓 12 個排程整批沒跑，而三層存活稽核沒有一層問「這一次它跑了沒有」（2026-08-12）

| 欄位 | 內容 |
|---|---|
| **Context** | 08-12 凌晨本機異常關機：cron 事件從 **02:52 斷到 05:43**，容器 05:43 才被拉起。當日覆盤時所有既有訊號都是綠的。 |
| **What happened** | 三件事一起發生：<br>① **Windows 排程整批漏跑且不補**：03:30–05:30 之間到期的 **12 支**（含 **異地備份**、四個 repo 的走查、能力使用快照）全部沒跑，`NextRunTime` 直接跳過當天排到隔天。**當晚的 DB dump 與金鑰因此只留在本機一顆磁碟上**。<br>② **`StartWhenAvailable=True` 沒有兌現**：這 12 支全部設了 True（08-02 就是為了「機器關機整個跳過」而補的），實測到當日 10:30 一支都沒補跑。<br>③ **稽核全綠**：`windows_task_liveness_audit` 唯一的時間判準是「上次執行超過 **8 天**」，每日排程漏一天的 age 只有 ~48h，離門檻差得遠。 |
| **Root cause** | 8 天門檻要抓的是「**整支停擺**」，抓不到「**這一次沒跑**」——兩件事需要兩個判準，而只寫了一個。更根本的是 ①：把「設定允許補跑」當成了「會補跑」，是 L84「設定寫得很嚴謹 ≠ 它跑得起來」的又一例，而且這次是**我們自己在 08-02 下的結論被實測推翻**。 |
| **Fix** | 稽核加「錯過未補跑」判準，**不另建頻率表**（那正是該檔開宗明義拒絕的第二份事實）：上一個應執行時點 = 作業系統自己給的 `NextRunTime` − 該排程自己的 trigger 週期；`LastRun` 落在那之前就是這一輪沒跑到。**鑑別力對照成立**：實跑抓出 11 支（第 12 支異地備份因已手動補跑而正確不報），而窗口外的（02:00／02:30 跑過的、05:45 後跑的、週排程、登入觸發型）一支都沒誤報——邊界恰好等於關機窗口。 |
| **Prevention** | (a) **「排程有沒有停擺」與「這一次有沒有跑到」要分開判**，前者用長門檻、後者用 `NextRunTime` 反推，缺一個就會有一整類漏跑看不見。(b) 任何「設定了就沒事」的結論都要有一次真實情境的驗證，否則它只是宣告。(c) 漏跑的後果不對稱：走查漏一天隔天自己會補，**備份漏一天是那一天的資料只有一份**——同一次漏跑要按後果分級處理。 |
| **Refs** | `scripts/checks/windows_task_liveness_audit.py`（`NextRun`／`IntervalDays` + `MISSED_GRACE_HOURS`）/ 同族：L84（設定嚴謹≠跑得起來）、L83（狀態與退出碼要一致）、`check_runs_in_which_environment` |

---

## L117 — `misfire_grace_time` 防的是「忙過頭」，不是「重啟」（2026-08-30）
<!--enforced-by: scripts/checks/cron_silent_dormant_check.py（job 停止觸發時判紅，不論成因是重啟或別的）-->

| 欄位 | 內容 |
|---|---|
| **Context** | watchdog 報 `優化管線報告 55h 前 > 門檻 30h（產出 stale）`。追下去：`optimization_pipeline`（每日 03:00）最後執行是 08-28 03:00，之後兩天完全沒有 cron_events 紀錄。 |
| **先排除「容器沒開」** | 那兩天 02:30–03:30 窗口分別有 **49／55 筆**其他 job 的事件 ⇒ 排程器活著，是**這一支自己沒被觸發**。 |
| **根因** | 08-30：`scheduler_start` 在 **03:00:19**，重啟正好撞在觸發時刻。08-29：標記當天 14:35 才加、看不到，但 `health_check_broadcast` 的 5 分鐘固定節奏在 **03:03 缺席**（02:58:11 → 03:05:11）⇒ 同一時段重啟過。 |
| **為什麼 grace time 救不了** | 該 job **有** `misfire_grace_time=600`，全域 `job_defaults` 也有 3600。但 `AsyncIOScheduler(...)` **沒有指定 jobstore ⇒ 預設 `MemoryJobStore`** —— 重啟後 job 是全新註冊的，**根本不存在「錯過的觸發」這筆紀錄**。grace time 的語意是「排定時刻到了但排程器忙，允許晚 N 秒才跑」，前提是排程器**當時活著**。⇒ **兩個機制防的是不同的事，而它們的名字讓人以為是同一件。** |
| **與 L72 的關係** | L72（02:00 壅塞 misfire skip）修的是**真的**壅塞，補 grace time 是對的。本條是**另一種**空窗，補再多 grace time 也沒有用 —— 把兩者混為一談會讓人以為「已經修過了」。 |
| **規模** | cron_events 顯示 **28 次 `scheduler_start`**（約 20 小時內，多為開發期 rebuild）。每日排程撞上重啟窗口不是罕見事件。同日的 `llm_quota_check`（6h 週期）也是被同一個機制餓死的（L109）。 |
| **Prevention** | ⚠️ 看到排程沒跑時，**先問「那個時刻排程器在不在」**，再問「它為什麼沒排到」——兩者的修法完全不同。⚠️ 以及：**一個參數有沒有設，不代表它防得了你眼前這件事**；要對照它的語意前提（此例＝排程器當時必須活著）。 |
| **Fix（owner 同日裁示採選項 ①，已辦）** | ⚠️ **而我當時的建議只對了一半 —— 光加持久化不夠。**讀 APScheduler 3.11.1 `BaseScheduler._real_add_job` 確認：`if not hasattr(job,'next_run_time')` 時會重算成**未來**，接著 `except ConflictingIdError: if replace_existing: store.update_job(job)` **用剛算的值覆蓋掉存起來的** —— 而本檔 56 處 `add_job` **全部**帶 `replace_existing=True` ⇒ 每次重啟照樣沖掉，持久化等於白做。<br><br>⇒ 實際修法是**三件事**：①持久化 jobstore（既有 Postgres，零費用）②`_RecoveringAsyncIOScheduler._real_add_job` **只接回已經過去的** `next_run_time`（未來的讓 trigger 重算，改 cron 排程才會生效）③啟動後清理「程式碼已移除但 DB 還留著」的殘留 job。<br><br>容器內對照實測（真 DB、複製正式程式的順序）：**修法版執行 1 次／原生版 0 次**。⚠️ 這個對照做了三次才做對 —— 前兩次被「排程器自己把到期 job 跑掉」與「我寫成 start() 再 add_job，與正式順序相反」污染，兩組都『有跑』而分不出差別。**負向對照要複製正式程式的呼叫順序，不是只複製它的元件。** |
| **推薦一個修法時，要確認它單獨成立** | 我 08-30 上午寫「建議持久化 jobstore」時，**沒有讀 `_real_add_job` 就下了建議**。它聽起來完全合理、方向也對，但少了第二件事就是無效的。⇒ **在建議裡寫「這樣做就會解決」之前，先把那條路走到底**；只走到「機制存在」就停手，正是本 repo 反覆記過的形狀（只是這次發生在建議階段而不是實作階段）。 |
| **Refs** | `backend/app/core/scheduler.py`（`_scheduler` 初始化／`optimization_pipeline` add_job）／A50／同族：L72、L109（同一機制餓死 `llm_quota_check`）、`observed_span()`（本次 08-29 那段正是「我看不到那麼遠」） |

---

## L116 — 同一天內我兩次從「沒有人在看」出發，而兩次鏈路都是通的（2026-08-30）

| 欄位 | 內容 |
|---|---|
| **第一次** | 走查抓到的 HTTP 400 —— 我寫「沒有人看那份產出」。實查：registry 已登記 `fail_key`、watchdog exit 2、**02:02:25 queued「🚨 每日檢核 RED」、07:30:14 隨晨報送出**。已於同日更正（見 L115）。 |
| **第二次（本條）** | watchdog 報「帳本對帳 ar_diff=0 非合理零 reason=mismatch」，我一路推到「AP 差額 100 萬沒有人在看」。實查：`system_notifications` 有 **144 則 `reconciliation_alert`**，今天 05:00 那則寫著「已付應付總額 4174372.00 vs 帳本支出 3174372.00，差額 1000000.00」。**系統偵測到了、也建立了通知**（未讀，但那是收件匣不是系統故障）。 |
| **我的推理偏誤** | **我預設「沒有接收者」**。這個 repo 的歷史裡確實有很多「訊號存在但沒有接收者」（L109／A37／signal_without_receiver），於是它變成我的第一假設 —— 而**一個曾經反覆為真的模式，會讓人停止驗證它這一次是否為真**。⇒ 凡是要下「沒有人在看 X」這種結論，**先沿鏈路取證**（登記 → 判準退出碼 → 通知落地 → 送出紀錄），四段都要有證據才說得出口。 |
| **過程中三次表名踩空** | `erp_expense_invoices`（實為 `expense_invoices`）／`finance_ledger`（實為 `finance_ledgers`）／`notifications`（實為 `system_notifications`，前者是 0 筆的殘留表）。最後那次差點讓我做出「通知管道全死」的相反結論。⇒ **查資料前先 `information_schema` 對一次表名**，代價一次查詢，錯了的代價是整條推論。 |
| **真正的發現（收窄後）** | ① **業務資料**：`erp_vendor_payables` id=72／73（政威資訊顧問，各 500,000）標記 `paid` 但 `paid_date`／`invoice_number`／帳本分錄全空，id=72 建立時就是 paid ⇒ AP 差額正好 1,000,000（A49，待 owner 判斷）。② **訊息指錯數字**：watchdog 說「ar_diff=0 非合理零」而真正非零的是 `ap_diff` —— **判準正確，而人讀到的摘要說了別的事**。 |
| **Fix** | `producer_registry.judge()` 的 `cron_detail` 訊息**只改措辭不改裁決**：把 detail 裡其他非零數值一併列出 ⇒ 現在顯示「…reason=mismatch（沉默成功）（detail 另有 ap_diff=1000000.0）」。複驗：RED 數與 exit code 不變（4 RED / exit 2）。 |
| **⚠️ 刻意不做的** | 不把 `ap_diff` 另立一筆 registry —— `cron_detail` 的 judge 是**值為 0 時判紅**（設計目的是抓「不合理的零＝沉默成功」），那個登記管的是**對帳有沒有跑**，不是差額對不對；差額的正確性由 job 自己的通知負責，而那條路是通的。**把 liveness 的判準拿去做 correctness，兩件事都會做不好。** |
| **Refs** | `scripts/checks/producer_registry.py`／`backend/config/producer_outcome_registry.json`／A49／同族：L115（同日第一次）、`my_tool_behaviour_is_not_the_finding`、`signal_without_receiver`（正是被我過度套用的那個模式） |

---

## L115 — 走查昨晚就記下了那個 400，而沒有人看那份產出（2026-08-30）

| 欄位 | 內容 |
|---|---|
| **Context** | 把「反方向」問法套到排程層（註冊了的 job 有沒有機會被觸發）——結果**乾淨**：1 個條件註冊（`einvoice_sync` 卡 `MOF_APP_ID`，08-12 已記載為刻意停用）、4 個旗標閘門（3 個預設開啟；唯一關閉的 `tender_business_recommend_job` **回傳 `{"pushed":0,"reason":"line_push_disabled"}`，不是沉默成功**）。轉去跑既有的 `windows_task_liveness_audit`（weekly 28），**RED 6 項，其中兩項是本 repo 的頁面層真實故障。** |
| **走查抓到的三件事，沒有一件有人看過** | ① `quotation-expense`：報價單「費用核銷」列點不進詳情頁。② `receipt-image`：核銷收據影像載不出來（**owner 回報過「看不到」**）。③ `/erp/einvoice-sync` console error **HTTP 400**。產出時間是 **08-29 20:41／21:14**。 |
| **①② 是系統行為正確，走查設定錯了** | 兩者都只在 `role: user` 失敗、admin 20/20 全過。實查 `role_permissions`：`user` 只有 `documents:read／projects:read／agencies:read／vendors:read／calendar:read`，**沒有 `reports:erp:view`**，而 `expenses`／`expenses_io` 兩個 router 在 `erp/__init__.py` 被該權限包住 ⇒ 一般同仁本來就拿不到資料。⇒ **把它弄綠（給 user ERP 權限）才是錯的**（`red_light_is_not_a_repair_order`）。修法＝在 `selfaudit.config.json` 補 `roles: ["admin"]` + `roles_why`，與既有 5 個項目同一慣例。數字也對得上：20 − 5 admin 專屬 = 15 = user 那次跑的項目數。 |
| **③ 是真的 bug，而且是我昨天弄壞的** | 08-29 做 §2.6 ①（統計卡分母）時，`total_amount` 被**同時加到兩個 repo 方法**：`get_pending_receipts`（對的，端點解三個）與 `get_sync_logs`（**錯的，端點只解兩個**）⇒ 每次呼叫都 `too many values to unpack (expected 2)`，電子發票同步頁的歷史清單自那天起整個壞掉。而那個多出來的值**沒有任何消費端**（前端讀的是另一支的 `totals.pending_amount`）。 |
| **三個地方同時說謊而沒有一個報錯** | repo 的型別註解寫 `tuple[list[...], int]`（兩個）／service 的註解也是兩個／端點解兩個 —— **只有執行時才炸**。Python 不驗註解，而 CI 的 MyPy 是 soft-fail 且 GitHub Actions 自 2026-03-09 全面停用。 |
| **⚠️ 元教訓已於同日推翻（2026-08-30 09:xx）** | 我原本寫「產出存在、內容正確，缺的只是有人讀它」——**那是錯的，閉環是完整的**。逐段實查：`producer_outcome_registry` 對 `ui-sweep.json`／`ui-flow.user.json` **已登記 `json_result` + `fail_key`**（08-04／08-27 補的，`_why` 就寫著「若 fail 由 0 變 25，watchdog 仍全綠」）；`producer_output_watchdog` 實跑 **exit 2**，抓到的正是那兩項；容器日誌顯示 **02:02:25 `Fitness Tier 1 Daily RED rc=1，queueing digest` → `[line-digest] queued topic=🚨 每日檢核 RED len=1319`**；**07:30:14 `Morning digest tail attached (1792 chars)`** ⇒ 已隨晨報送達。<br><br>**真正的形狀是延遲不是缺席**：bug 08-29 進版 → 走查 20:41 抓到 → daily 02:02 判紅 → 07:30 送出，端到端約 10.5 小時；而我 09:xx 手動跑 weekly 28「發現」它時，它已經在 owner 當天的晨報裡。<br><br>⇒ **我把「我還沒讀到」寫成了「沒有人讀」** —— 這正是 `my_tool_behaviour_is_not_the_finding` 的變形，而且我用它推導出一個關於系統的錯誤結論並提交進版控。**下結論說某個機制沒有接收者之前，要沿著鏈路每一段都拿到證據**（registry 登記 → watchdog 退出碼 → 通知佇列 → 送出紀錄），不能因為「我是手動跑才看到的」就推論沒有人在跑。 |
| **Fix** | ① `get_sync_logs` 移除多餘回傳值，回到註解宣告的形狀。② 新增 `backend/tests/test_einvoice_sync_arity_regression.py` —— **AST 比對 repo 的 return 元素數 × 端點的解包數**，不需 DB、不受測試庫 schema 漂移影響；負向對照：把修法還原 ⇒ **精確地只有那一組紅**（另一組仍綠）。③ `selfaudit.config.json` 補兩個 `roles: ["admin"]`。<br>⚠️ 全庫掃同型「repo 回 N、端點解 M」共 **0 個**，是孤例 ⇒ 配回歸鎖而非新開檢核。 |
| **待辦** | `backend/app` 非 bind mount ⇒ **③ 的修法要 rebuild 才在容器內生效**（A48）。另：`selfaudit.config.json` 的 `$schema` 指向 `scripts/checks/selfaudit.schema.json` 而**該檔不存在**（懸空引用）。 |
| **Refs** | `backend/app/repositories/erp/einvoice_sync_repository.py`／`backend/tests/test_einvoice_sync_arity_regression.py`／`selfaudit.config.json`／同族：A37、L109（產出端有了消費端沒有）、`red_light_is_not_a_repair_order`、`audit_runs_as_admin_only` |

---

## L114 — 我能證明的是「PreToolUse 的訊息到得了」，不是「PostToolUse 的到不了」（2026-08-30）

| 欄位 | 內容 |
|---|---|
| **Context** | 續 L112：驗**掛在 settings.json 上**的 PostToolUse hook。`api-serialization-check`／`performance-check` 手動餵違規輸入 → **判準都正確**（N+1、缺 limit、ORM 直接回傳、datetime 未 isoformat 全抓到，乾淨檔通過）。 |
| **問題不在判準，在通道** | 三支都用 `Write-Host` + `exit 0` —— 而協議記載的到達通道是「`exit 0` + stdout **JSON** 的 `additionalContext`」或「`exit 2` + stderr」。**兩條都不是。** |
| **測到哪裡為止（重要）** | 我**實測 PreToolUse 的 `exit 2` + stderr 確實到得了**：Write 一個 `frontend/**.py` 當場被 `validate-file-location` 擋下，訊息出現在我眼前。<br>而 PostToolUse 的 `additionalContext` —— **扁平與巢狀兩種形狀都沒有可觀察到的輸出**。<br>⇒ **我不能宣稱「那四支 remind-* 從來沒送達過」** —— 我只能說**我驗不到**。無法區分「沒送達」與「送達了但不以我看得見的形式呈現」。 |
| **確實查到的不一致** | 四支 `remind-*.ps1` 用**扁平** `@{hookEventName; additionalContext}`，而同目錄**實際運作中**的 `auto-approve.ps1` 與 `CK_DigitalTunnel/.agents/skills/claude-code-setup/hooks-reference.md` 都是**巢狀在 `hookSpecificOutput` 底下**。⇒ 已對齊（形狀更正 ≠ 已證實送達，兩件事分開講）。 |
| **⚠️ 我在修的過程中親手重演了 careful-guard 的 BOM bug** | `remind-type-sync.ps1` 原本**無 BOM 且純 ASCII**，我加了中文註解 ⇒ PowerShell 以 cp950 誤讀 ⇒ **`運算式或陳述式中有未預期的 '}'`，整支掛掉**。當場被我的手動測試抓到。另三支我改時**刻意只動 JSON 結構、註解用英文**，維持純 ASCII 就不需要 BOM。 |
| **守門已經存在而且有效** | `scripts/checks/powershell_bom_audit.py`（daily fitness step 54，L49 family #11）—— 38 個含中文 .ps1、0 個無 BOM。它會抓到我那個破壞，只是要等 02:00 的排程。⇒ **這一格是好消息：規範有守門、守門是活的。** |
| **Prevention** | ⚠️ **在 .ps1 裡寫中文之前，先確認它有 BOM**（或把註解寫成英文）。⚠️ **報告「送不到」與「我驗不到」要分開** —— 前者是對系統的斷言，後者是對我的觀測能力的陳述，而我今天只證得了後者。 |
| **Refs** | `.claude/hooks/remind-*.ps1`（四支已對齊巢狀）／`.claude/hooks/auto-approve.ps1`（正確範本）／`scripts/checks/powershell_bom_audit.py`（daily 54）／A47／同族：L112、L113、`my_tool_behaviour_is_not_the_finding` |

---

## L113 — 我昨天「修好」的守衛，修在一個 git 從不執行的檔案上（2026-08-30）
<!--enforced-by: scripts/checks/hook_reachability_audit.py（判準 ①② —— .git/hooks 被 core.hooksPath 旁路、husky shim 無實作）-->

| 欄位 | 內容 |
|---|---|
| **Context** | 2026-08-29 發現 pre-commit 的 secret 掃描依賴一個**不存在**的 `scripts/check-secrets.cjs`，`[ -f ]` 為 false ⇒ 整段靜靜跳過。我改用 repo 裡已寫好的 `pre-commit-secret-guard.sh`，並讓「守衛不見時**出聲**」。改的是 `.git/hooks/pre-commit`。 |
| **What happened** | `git config core.hooksPath` = **`frontend/.husky/_`** ⇒ git **只**執行 husky 底下的 hook，`.git/hooks/pre-commit` **從不執行**。那支 193 行、6 項檢查（destructive ops／`_shared`／Skills／secret guard／backend 長度閘門）**全是死的**。<br><br>2026-08-30 實測：把一個含私鑰的 `.pem` 加進暫存 → 實際跑的 hook 回 **exit 0 並印「全部檢查通過」**。 |
| **辨識的線索** | 我幾次 commit 看到的輸出是 `[Pre-commit] 驗證 CK_Missive...`，而我改的那支印的是 `[Skills Hook] 驗證完成` —— **兩段文字不一樣**。線索一直在畫面上，我讀了好幾次都沒對照。⇒ **改一個 hook 之前，先確認它印的字就是你實際看到的那些字。** |
| **根因** | 兩套 hook 系統並存，**較新的那套靜默勝出**：husky 在 `frontend/` 底下 npm install 時設了 `core.hooksPath`，把 `.git/hooks/` 整個旁路掉，沒有任何警告。 |
| **修好之後才看得見的第二層** | 接上 secret guard 後實測，它的「內容層」**只警告不阻擋**，且必須有 `password\|secret\|api_key\|token` 這類關鍵字接 `[:=]` ⇒ **裸字面完全無聲**：`X = "sk-ant-api03-…"`／`ghp_…`／`AKIA…` 全部通過。**最高信心也最傷的那種形狀，正好是它看不見的那種。** |
| **Fix** | ① `frontend/.husky/pre-commit`（真正會跑的那支）補上 destructive ops 與 secret guard 兩段。② secret guard 新增**供應商前綴阻擋層**（`sk-ant-`／`sk-proj-`／`ghp_`／`AKIA`／`xox?-`／`AIza`＋長度下限），出口是同行加 `pragma: allowlist secret`。③ `.git/hooks/pre-commit` 加警示標頭寫明「**這個檔案不會被 git 執行**」，免得下一個人（或我）再修一次。 |
| **判準先量誤報再上線** | 新前綴樣式對**全 repo 追蹤中的檔案**掃描，命中 **1 個** —— `test_autobiography.py` 的測試用假金鑰（已加 allowlist 標記）。佔位字串 `sk-proj-xxxxx` 因長度下限而正確不命中。7/7 正負向控制通過。 |
| **Prevention** | ⚠️ **改任何 hook 之前先 `git config core.hooksPath`。** 更一般地：**在「修好」一個機制之後，要用它真正的觸發路徑驗一次，而不是直接執行那個檔。** 直接跑 `.git/hooks/pre-commit` 會通過，而那不是 git 走的路。 |
| **Refs** | `frontend/.husky/pre-commit`／`scripts/hooks/pre-commit-secret-guard.sh`／`.git/hooks/pre-commit`（警示標頭）／A45（長度閘門要不要接）／同族：L112、L111、L109（都是「機制在，但不是你以為的那條路徑」） |

---

## L112 — 掛上去、會執行、也真的擋過東西的 hook，仍有一半的規則從未命中（2026-08-30）
<!--not-enforceable: 規則會不會命中取決於真實 payload 形狀，靜態分析正則字面會退化成猜測。防線是改 hook 規則時跑正負向控制（本條修法留下 14/14）。-->

| 欄位 | 內容 |
|---|---|
| **Context** | L111 查的是**沒有人在跑**的 hook。這次查**真的掛在 settings.json 上**的 12 支 —— 先驗 BOM（`careful-guard` 曾因缺 BOM 而 12,491 次呼叫一次都沒攔到），結果 12 支全部正常。於是改問：**餵它違規輸入，它會不會有反應？** |
| **What happened** | `validate-file-location.ps1` 是活的（它正確擋下 `frontend/src/foo.py`），**但 6 條規則裡有 3 條從未命中過**：`^[^/]+\.md$`／`^temp_`／`^test_` 都帶 `^` 錨點，比對的是完整路徑，而 **Claude Code 的 Write/Edit 要求絕對路徑** ⇒ 字串一律以 `D:/…` 開頭 ⇒ 三條全部落空。實測同一支 hook：餵絕對路徑 exit 0、餵相對路徑 exit 2。**而另外三條會命中，所以它一直看起來是正常的。** |
| **同一支還缺一條** | `backend/.env` 放行 —— 而 development-rules §2 明文「**禁止存在**」。CI 的 `config-consistency` job 自 2026-03-09 起全面停用（收費），這支不查它 ⇒ **那條規範零強制**。已補。 |
| **修的時候差點放寬成另一個 bug** | 我第一版把 `^test_` 從「路徑」改套到「檔名」—— 那會把 `backend/tests/test_foo.py` 這種**合法的 pytest 檔全部擋掉**。原意是「不應在**根目錄**」。⇒ 改成先判斷「父目錄 == repo 根」再套檔名規則。**修一條沒生效的規則時，很容易順手把它放寬成另一個 bug**；負向控制必須包含「原本就該放行的東西」。 |
| **另一個發現（未自行修）** | `careful-guard` 的 CRITICAL／WARNING 分級**只存在於資料裡**：兩層都 `exit 2`。例行操作（`docker system prune`／`kill -9`／`git clean -fd`）被硬擋而非提醒。協議有非阻擋通道（`exit 0` + `additionalContext`）。**放寬安全護欄屬 owner 決定，列 A43 不自行改。** |
| **Prevention** | ⚠️ **一支 hook「有在擋東西」不代表它的每條規則都在擋。** 驗 hook 要逐條給違規輸入，而不是看它整體會不會動。⚠️ 特別留意**錨點與輸入形態的假設**（相對 vs 絕對路徑）—— 這類失效不報錯、不留痕，只是安靜地放行。 |
| **Refs** | `.claude/hooks/validate-file-location.ps1`（`$RootOnlyForbiddenNames` + `$RepoRoot`）／A43／同族：L111（沒人跑的三支）、L109（路徑深度 off-by-one）、`arch_pattern_script_existence_not_enforcement` |

---

## L111 — 沒有人在跑的檢核不是「沒用」，是**會腐爛，而且腐爛的方式你猜不到**（2026-08-30）

| 欄位 | 內容 |
|---|---|
| **Context** | 複查六條沒有守門的核心規範（§1／§2／§5.1／§6／§7／§8），8 個候選逐一核實後 **0 個真違規**。轉去查記憶裡標記「同一件事被發現兩次」的模式 —— `.claude/hooks/` 底下標為「手動執行」的三支。 |
| **What happened** | 三支都**沒有任何 runner／settings／git hook 在叫它們**，而且**三支各自壞成不同的樣子**：<br>① `link-id-check.ps1`：`Select-String -Path "src\**\*.tsx"` —— **PowerShell 的 `**` 不是遞迴 glob**，等同於 `*`。實測掃得到 **119/604** 個 `.tsx`（20%）**而照樣印 `[PASS]`** ⇒ 假綠。同檔另有一條斷言 `BaseLink` 必須在 `types/api.ts`，而它實際在 `types/taoyuan.ts:53` ⇒ **永久假紅**。<br>② `route-sync-check.ps1`：專案根用了**三層** `Split-Path`（應為兩層）⇒ 算到 monorepo 根、找不到路由檔、每次 exit 1。<br>③ `link-id-validation.ps1`：跑得動、報 7 個警告，**但 exit 0** ⇒ 接進 runner 也永遠不會紅；抽查第一個是假陽性。 |
| **重點不是「它們沒被跑」** | 而是**如果今天有人照著文件把它們接進 runner，拿到的是一個永久紅燈加一批假綠**。⇒ 「腳本存在 ≠ 有在強制」還要再加一句：**「腳本能跑 ≠ 它說的是真的」**。接一支久未執行的檢核之前，先跑它、並**確認它報的東西真的存在**。 |
| **修好之後才看得見的第二層** | `route-sync-check` 修好路徑後給出「前端 144 條 vs 後端白名單 41 條」，看起來像大規模漂移 —— 實際那份白名單只收**導覽選單**的路徑，本來就不該等於全部路由；而反方向的 `/admin/` 是把 `navigation_validator.py:127` 的**字串常數** `.replace("/admin/", "/")` 當成白名單項（同 L97）。⇒ **修好一支壞掉的檢核，不等於得到一支正確的檢核。** 故它已修好但**刻意不接進 weekly**。 |
| **Fix** | §7 改寫為 `scripts/checks/link_id_fallback_audit.py`（走 `lib/ts_source` 剝註解／字串，掃 **805** 個檔，豁免 React `key=` —— 它只決定渲染身分不決定操作對象），接為 **weekly 90**。負向對照：把 `key=` 的回退改成 `unlinkDispatchMutation.mutate(link_id ?? other)` 與 `\|\|` 兩種形式，皆 GREEN→RED（行號正確）→還原後 GREEN。`route-sync-check` 路徑已修但不接。舊 PS1 保留待裁示＝A42。 |
| **本支自帶的解析度證據** | 新檢核印「掃描 N 個前端原始檔」，且 `N < 400` 直接回 2 不視為通過 —— 因為舊版正是**掃得少而印 PASS**。**凡是掃描型檢核，掃了幾個必須說出來，並為它設下限。** |
| **Refs** | `scripts/checks/link_id_fallback_audit.py`（weekly 90）／`.claude/rules/hooks-guide.md`（已標記取代）／A42／同族：`arch_pattern_script_existence_not_enforcement`、L97（判準命中字串）、L109／L110（同日的兩個路徑與欄位盲區） |

---

## L110 — 判準去問「那個欄位長什麼樣」，而違規是「那個欄位不存在」（2026-08-30）

| 欄位 | 內容 |
|---|---|
| **Context** | owner 2026-08-29 裁示的 §2.6 列表頁三要素，① 有 weekly 82 守門，③「預設當年度」沒有。補守門前先量現況。 |
| **What happened** | 判準寫成「有年度 state 的頁面，其初始值必須是 `getFullYear()`」，量出 **0 違規**。而真正的違規形狀是 **params 物件裡根本沒有 `year` 這個 key** —— `ERPInvoiceSummaryPage`（`{skip:0,limit:20}`）與 `ERPOperationalListPage`（`fiscal_year` 未設），兩頁的年度 Select 開場都是空的 ⇒ **歷年混算**，而畫面毫無異狀。**一個去找欄位的判準，看不見欄位的缺席。** |
| **修法的通則** | 進場條件改成「**有沒有人在寫入年度**」（setter 存在＝這一頁有年度篩選），再問「預設值在不在」。⇒ **用「有沒有人要改它」證明欄位該存在，比用「欄位長什麼樣」可靠。** 這個形狀可以直接套到其他「應該有但可能沒有」的欄位稽核。 |
| **判準校準了三次，前兩次都在過寬方向** | ①`\byear\b` 出現即算 ⇒ 誤報 2 個長條圖頁（`year_trend` 的 X 軸）。②初始值必須字面是 `getFullYear()` ⇒ 誤報 3 個用 `const currentYear` 別名的。③找 `'all'` 字樣當「可切全部年度」⇒ 實際是用 `allowClear` 實作。**三次都是實測才發現，沒有一次是想出來的。** |
| **修的過程差點造出更糟的東西** | `ERPOperationalListPage` 的年度 Select **只有 `onChange`、沒有 `value` 綁定**。我加了預設年度 ⇒ 資料被篩而畫面顯示「未選」＝**隱形篩選**，使用者不知道自己看到的是子集 —— 比不篩更糟。⇒ 「補了預設值」要連著問「它顯示得出來嗎」，並把 `value` 綁定一併納入判準（其餘 8 個 Select 掃過，都已有）。 |
| **Prevention** | ⚠️ 寫「某某必須設定」這類判準時，先問：**沒設定的時候，程式碼長什麼樣？** 若答案是「什麼都沒有」，那判準就不能從那個東西出發，要從**它的使用痕跡**出發。 |
| **Refs** | `scripts/checks/stat_card_denominator_audit.py`（`YEAR_SETTER` 為進場條件）／weekly 82／同族：L109（把「沒有資料」讀成「沒有發生」）、`proxy_metric_looks_good`、`verification_signal_too_coarse` |

---

## L109 — 同一個檔案裡已經有人解過這題，而我自己又解了一次、解錯了（2026-08-30）

| 欄位 | 內容 |
|---|---|
| **Context** | `cron_silent_dormant_check.py` 判斷排程是否停擺時，用容器 uptime 扣除重啟時間，而它自己的註解指出 uptime「只反映**最後一次**重啟」。2026-08-29 加的 `scheduler_start` 事件正好記著每一次啟動 —— 產出端有了、消費端沒有（同日 `csp_violations_total` 的形狀）。於是我寫了 `count_restarts_within()` 去消費它。 |
| **What happened** | 我在那支新函式裡**自己寫了一份路徑推導**：`parents[2] / "logs" / "cron_events.jsonl"`。而**同一個檔案第 268 行就有 `_cron_events_path()`**，它的註解寫著這個路徑是錯的（compose 掛的是 `./backend/logs:/app/logs`）、repo 根那份是舊的、「**讀到了、有資料、看起來很正常**」。⇒ 我在同一個檔案裡，重現了那個 helper 專門要防的 bug。 |
| **兩次失敗的形狀不同，第二次危險得多** | ① 首版用了個不存在的 `ROOT` 常數 ⇒ `NameError`，會吵，看得見。② 二版指到 repo 根 ⇒ 那個檔案**真的存在** ⇒ 不報錯、不回 `None`，**安靜地讀了錯的檔案回 0**，而 0 會被讀成「期間沒有重啟」。⚠️ **語法檢查與「有沒有拋例外」都攔不到第二種。** |
| **它接著造成一個錯誤的診斷** | 我據此寫出「重啟太密所以 job 結構上跑不到」—— 一個能解釋症狀的合理故事。實查才發現 repo 根那份**不是舊檔**，是 pytest 在 host 上跑時寫的（`CK_LOGS_DIR` 未設 ⇒ 落到 repo 根），504 筆、當天還在更新、連 detail 格式都是真的，破綻只有 `test_obs_job` 這個 job_id。⚠️ **假的事件流比沒有事件流更糟：它讓你做出有信心的相反結論。** |
| **第三個錯：拿 13 小時的證據解釋 69 小時的空窗** | `scheduler_start` 前一天才加，觀測窗只有 13h，而空窗 69.8h。我第一版把整段都歸因於部署節奏。⇒ 補 `observed_span()`，任何用重啟史做的歸因都要先講「我看得到多遠」。 |
| **Root cause** | 重複實作。**同一份知識在兩處各寫一次，錯的那一份不會告訴你它是錯的** —— 而正確的那一份就在同檔上方 100 行。 |
| **Fix** | ① `_restart_stamps_within()` 改用既有的 `_cron_events_path()`。② `longest_uptime_within()` 排除「事件流開始之前」那段（那是**未觀測**不是連續存活；首版把 24h 窗算成 10.87h 而真值 2.80h）。③ 窗口內 0 筆事件回 `None` 不回 `seconds`。④ `backend/tests/conftest.py` 在 import `main` **之前**設 `CK_LOGS_DIR`，讓測試不再污染 repo 根（實測 504 行 → 504 行未動，隔離檔收到寫入）。 |
| **Prevention** | ⚠️ **寫任何「路徑推導／環境判別」之前，先在同一個檔案裡 grep 一次有沒有人做過。** 這類邏輯是本 repo 最常被重複實作、也最常靜默出錯的一類（L52／L57／`windows_container_path_trap` 同族）。⚠️ 以及：**讀到資料不等於讀對檔案** —— 對事件流做結論前，先確認它的 job 種類數與時間範圍合理（本例 5 種 vs 57 種、504 筆 vs 87,677 筆，一眼可辨）。 |
| **Refs** | `scripts/checks/cron_silent_dormant_check.py`（`_cron_events_path` / `_restart_stamps_within` / `longest_uptime_within` / `observed_span`）／`backend/tests/conftest.py`（A44）／同族：L52、L57、`windows_container_path_trap`、`symptom_is_not_the_cause`（能解釋症狀就停手）、`proxy_metric_looks_good` |

---

## L108 — 為了看見一種訊號而加的旗標，把另一種訊號整批關掉了（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | 發現測試基線只解析 `failed`、不看 `skipped`／`xfailed`（那讓 11 支 xfail 隱形 4.5 個月），於是擴充它一併棘輪未執行的測試。 |
| **What happened** | 為了讓 skip 的**理由**印出來，我在 pytest 加了 `-rs`。**而 pytest 的 `-r` 是「取代」不是「附加」** —— 預設的 `fE`（failed+error）被換成只有 `s` ⇒ **FAILED 行整批不印** ⇒ 解析到 0 個失敗 ⇒ **基線被寫成 0 項，而該次實際有 36 failed**。 |
| **後果的形狀** | 下一次執行會把 36 個既有失敗全部報成「新增」⇒ 一片紅 ⇒ 而處理方式多半是「重錄基線」，於是**真正的新增失敗會混在裡面一起被吸收**。⚠️ **一個為了增加可見度而加的旗標，差點讓失敗偵測整個失效。** |
| **為何沒被立即發現** | 輸出裡**兩個數字同時存在**：pytest 摘要說 `36 failed`，而腳本印「基線已更新：**0 項**」。兩行相距三行，而我當時在看的是 skip 與 xfail 的數字 —— **我驗的是我剛加的東西，沒有看我可能弄壞的東西。** |
| **Root cause** | 對一個「修改既有行為」的旗標，我只想到它**增加**什麼，沒問它**取代**什麼。同族：本日 `docker inspect .Config.Labels` 回空字串（我只想到它會給值，沒想到它對不存在的 key 不報錯）。 |
| **Fix** | 改為 `-rfEs`（failed + error + skipped，三者都要），並在該行寫明「必須是 `fEs` 不能只寫 `s`」與這次的代價。重建基線。 |
| **Prevention** | ⚠️ 改動一個既有指令的旗標時，**除了驗新增的訊號，也要驗原本的訊號還在**。本次的具體檢查是：基線項數不應從 37 掉到 0。⚠️ 更一般地：**擴充一個機制之後，先確認它原本在做的事還在做。** |
| **Refs** | `scripts/checks/test_suite_health.py`／同族：L104（同一小時內漏掉第二處）、待辦 A35 |

---

## L107 — 外層 rollback 擋不住內部自己 commit 的函式，而我把「已回滾」寫進了回報（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | owner 問「91 件已承攬但未成案的案子是不是被什麼擋著」。為了不真的改資料，我寫了一段外層包 `db.rollback()` 的測試去呼叫 `promote_to_project`。 |
| **What happened** | **`promote_to_project` 內部自己 `await self.db.commit()`** ⇒ 外層 rollback 對已提交的交易無效。**3 件真的成案了**，而且正是 owner 刻意撤回、標記「待判讀」的那批（`8b5acc26`：85 筆成案＋91 筆撤回）。我還在同一段對話裡說「刻意不批次成案，成案不可逆，那是 owner 的決定」。 |
| **發現它的唯一原因** | **weekly step 28 的基線比對**：「已承攬但無成案編碼 **91 → 88**」。那個數字不該變。若不是那支在盯基線，這件事不會被發現。 |
| **Root cause** | 錯的不只是技術細節（沒查被呼叫的函式會不會自己 commit），是**我用一個沒有驗證過隔離性的方法，然後把「已回滾」當成事實寫進回報**。回報裡的每一句斷言都會變成別人的判斷依據。 |
| **Fix** | 依 owner 裁示還原：先查所有指向 `contract_projects` 的外鍵（6 張表，除我造成的 3 筆指派外全為 0），再於單一交易內逐表撤銷（`project_id`→NULL／兩處 `project_code`→NULL／DELETE 三筆）。**指派本身不刪** —— NULL 才是它的原狀。基線檔也還原（weekly 已把它棘輪到 88，**否則會把一個錯誤狀態記成新常態**）。`promote_to_project` 的 docstring 加上「本方法內部會 commit」的警告。 |
| **Prevention** | ⚠️ 對**不可逆**函式做試算前，先 `grep self.db.commit()`。有的話外層 rollback 是假的。⚠️ 沒把握就用**唯讀方式**推導（讀它的驗證條件），不要真的呼叫。⚠️ **驗收要驗系統狀態，不是驗自己的輸出** —— 「我做了 X 而狀態沒變」與「我以為狀態沒變」是兩件事。 |
| **Refs** | `backend/app/services/contract/case_code.py` docstring／memory `rollback_did_not_roll_back`／同族：L101（量測工具）、`my_tool_behaviour_is_not_the_finding` |

---

## L106 — 公網探的那支 health 根本不查 DB，而 L43 的防禦做在另一條路徑上（2026-08-29）
<!--enforced-by: scripts/checks/integration_e2e_validation.py（實打 health 端點並要求 business_data.ok，端點若退回靜態 dict 會失敗）-->

| 欄位 | 內容 |
|---|---|
| **Context** | 為了套用 `max_connections` 而重建 postgres 後做驗證，注意到公網 `/api/health` 的回應**沒有 `business_data` 欄位**。 |
| **What happened** | 系統有**兩個** health 端點：`/health`（main.py，DB ping + 業務量 + pool）與 `/api/health`（endpoints/health.py，**靜態 dict、完全不碰 DB**）。**公網探的是後者** ⇒ postgres 掛掉它一樣回 `healthy`。 |
| **為何嚴重** | L43（2026-05-21 volume mount drift）的修法白紙黑字寫著「面向公網的 `/health` **必須**包含業務量檢查」，機制是「healthcheck fail → 流量不打進空殼 instance」。**那個防禦只做在 `/health` 上** ⇒ 同一個事故形態在真正對外的那條路徑上原封不動地留著。 |
| **它騙過的不只是監控** | **我自己整天用 `/api/health` 當部署後的驗證** —— 那個 200 比我以為的弱得多。這一整天的「公網 200」證據強度因此要打折。 |
| **Root cause** | 同一件事有兩份實作，而**規範只約束了其中一份**。規範說的是「/health」這個名字，沒有說「所有對外的健康端點」。 |
| **Fix** | 業務量檢查抽成 `app/core/health_probe.py`，兩個端點共用同一份實作；`/api/health` 現在做 DB ping + 業務量檢查，不通過回 **503**。⚠️ **`/health/liveness` 維持不碰 DB** —— 那是故意的：「程序活著嗎」與「系統可用嗎」是兩個問題，合併會讓重啟中的程序被誤判。 |
| **Prevention** | ⚠️ 寫「必須有 X」的規範時，要問**有幾個地方在做同一件事**，而不是只約束你當時看到的那一個。用執行時路由表（不是 grep）掃同名端點：本次掃 748 條路由找出 3 組根路徑與 `/api` 的碰撞。 |
| **Refs** | `backend/app/core/health_probe.py`／`cross-file-ssot-governance.md` 規則 3／L43 |

---

## L105 — 「我這條路徑找不到」不等於「資料不存在」，而那句結論寫進了文件（2026-08-29）
<!--not-enforceable: 「我這條路徑找不到」與「資料不存在」的差別要靠追第二條路徑，機器不知道還有哪條路徑沒走。防線是下否定結論前先問「我試過幾種取法」。-->

| 欄位 | 內容 |
|---|---|
| **Context** | owner 問「為何承攬報價紀錄皆未對應承辦同仁」。257 張報價單中 122 張的服務人員欄是空的。 |
| **What happened** | 2026-08-20 我從彙整表的**工作表名稱**取承辦（原始／老闆／慶忠／元宏／其他），115 檔只有一個「工作表1」⇒ 我下了結論並寫進 commit：「115 檔沒有承辦人資訊 —— **那是資料本身沒有**，不是漏掉。」**那個結論是錯的。** |
| **資料一直都在** | 在 `legacy_quotation_no` 裡：`B115-**A**001-0A`／`B115-**B**003-0`。第一段 `B115` 是年度前綴（那個 B 不是人），**人的代碼是第二段開頭那個字母**。owner 說「A坤樹 B慶忠 C元宏 D廷睿」**已多次提出**，而系統一直沒有記下來。 |
| **Root cause** | 我讀了**一個**來源、讀不到，就宣告來源不存在 —— 而那筆記錄還有其他欄位我沒看過。更糟的是那句結論寫進了 commit 訊息與文件，成了後面所有人判斷的依據。 |
| **Fix** | 依代碼回填 115 件案號（張坤樹 5／洪慶忠 61／邱元宏 49），報價單有承辦 **135 → 250 張**。解碼規則**先在已知答案上驗證**才用（A/C/D 零反例、B 有 2 筆反例 ⇒ 已有指派一律不覆蓋）。代碼表寫進 `quotation_legacy_import._LEGACY_CODE_TO_NAME` 且**代碼優先於工作表名稱**。 |
| **Prevention** | ⚠️ 宣告「資料不存在」之前，先列出**這筆記錄還有哪些欄位沒看過**。⚠️ owner 講過的領域知識要**寫進程式常數**，不是寫進當次的 commit 訊息 —— 訊息不會被下一次執行讀到，常數會。 |
| **Refs** | `backend/app/services/erp/quotation_legacy_import.py`／`scripts/init/backfill_quotation_staff_from_legacy_code.py`／memory `quotation_legacy_staff_code` |

---

## L104 — 註解指名了來源檔，不代表值是從那裡來的（2026-08-29）
<!--not-enforceable: 目前沒有機械判準，防線是 review。可能的判準是「複本有沒有宣稱自己是別處的鏡像」（預設參數不算），但誤報率未測，寫成檢核前不宣稱它存在。-->

| 欄位 | 內容 |
|---|---|
| **Context** | 後端把報價單明細上限從 5 提到 10（範本本來就有 10 列，卡住的只是備註列的位置）。 |
| **What happened** | 前端有一份**手抄的**：`/** 正式範本的明細容量（quotation_document.py ITEM_LAST_ROW） */ const TEMPLATE_ITEM_CAPACITY = 5;`。註解**自己指名了來源檔**，值卻是手抄的 ⇒ 第 6 項起畫面警告「僅容 5 項，超出的需先合併」——**叫使用者去手動合併後端其實輸出得出來的工項**，而真正的邊界（第 11 項才 400）從來沒出現在畫面上。 |
| **為何沒被發現** | **`npx tsc --noEmit` 是綠的。型別檢查看不出一個過期的字面值。** 失敗形態是「畫面說一套、後端做另一套」，兩邊都不會報錯。 |
| **同一小時內犯了第二次** | 我修完建單頁那一份、commit 訊息寫著「容量只留一個家」，**而同一個功能的另一個檔案裡還有第二份 `>= 5`**（`QuotationItemsTab.tsx`）。⇒ **宣稱的範圍大於實際做到的範圍，比沒修更糟** —— 它會讓下一個人不再去找。 |
| **Fix** | 容量只留一個家：`ITEM_LAST_ROW - ITEM_FIRST_ROW + 1` → `ERPQuotationTemplateMeta` schema → `/erp/quotations/template-meta` → 前端 `useQuery`。前端留的 fallback 在註解寫明**偏哪一邊比較安全**（取偏小只多提醒一次，取偏大會讓人填到輸出才被擋）。 |
| **Prevention** | ⚠️ 改任何後端邊界值（上限／門檻／容量）前，先 grep 前端有沒有同名或同義常數。⚠️ **同族修法要先數清楚有幾處再動手**，不是修掉眼前這個就宣稱收斂完成。⚠️ 判準：**那份複本有沒有宣稱自己是別處的鏡像** —— 預設參數（如 `maxFileSizeMB = DEFAULT_MAX_FILE_SIZE_MB`）不算，它沒有宣稱自己是鏡像。 |
| **Refs** | `frontend/src/pages/erpQuotation/QuotationTemplateCreatePage.tsx`／memory `hand_copied_constant_across_layers`／同族：L99、L100 |

---

## L103 — 我把 runner 改壞、提交進版控，而它印著 GREEN 與退出碼 0（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | 同一天為 weekly runner 新增 8 支檢核（78–86），並為既有兩步補 `--ci` 旗標。 |
| **What happened** | 補旗標時字串替換把註解插進「步驟名」與「腳本路徑」之間，路徑掉到下一行變成獨立語句 ⇒ `run_step "64" "名稱"` 只有兩個參數 ⇒ `set -u` 下 `$3` unbound **直接致命** ⇒ **第 64~86 步一步都沒跑**，包含我當天新增的全部 8 支。**而它已經被提交進版控。** |
| **為何沒被發現** | **它看起來像跑完了**：前 63 步逐一印 GREEN、退出碼 **0**，只有輸出末尾夾一句 `line 76: $3: unbound variable`。⇒ 這是本 repo 反覆記過的「訊號存在但沒有接收者」的**自身版本**：訊息印出來了，而它被埋在 63 步綠燈之後。 |
| **發現它的唯一原因** | 我為了確認「今天加的 8 支能不能跑」而**實跑了一次完整 weekly**。在那之前我每支都單獨驗過負向對照 —— **卻從沒讓它們跟其餘 78 支一起跑**。 |
| **Root cause** | 我為別人建的判準（「能力做好了不等於有人在跑它」「腳本存在 ≠ 有在強制」）沒有套用在**我自己剛做的改動**上。單元驗證通過 ≠ 整體還能跑。 |
| **Fix** | 修兩處損壞；runner 開頭加 `_self_check`：任何 `run_step` 少於三個帶引號參數即 exit 2 並指名行號，**放最前面且不可跳過**。負向對照：注入壞步驟 → exit 2 並印行號；還原 → 正常進入第 1 步。 |
| **Prevention** | ⚠️ **改了 runner 就要跑一次完整的 runner**，不能只跑自己新增的那幾步。⚠️ **退出碼 0 不代表全部跑完** —— 要另外確認「跑了幾步」等於「宣稱有幾步」。本次守門只擋語法形態，**跑完的步數對不對仍需人看**。 |
| **Refs** | `scripts/checks/run_fitness_weekly.sh` `_self_check` / 同族：`arch_pattern_script_existence_not_enforcement`、L99、L100 |

---

## L101 — 量測工具的解析度比事件粗，而它交回的數字是對的（2026-08-29）
<!--not-enforceable: 「這個量測工具對這個事件夠不夠細」是判讀，機器無從得知被量測事件的真實粒度。防線是動手量之前先問一次解析度。-->

| 欄位 | 內容 |
|---|---|
| **Context** | CK_Website 回報跨平台 sso-bridge 每天約 15% 的 502，追 missive 這一側。 |
| **What happened** | 我用 `health_check_broadcast`（**每 5 分鐘一次**）的空窗推算部署造成的中斷窗口，得到「每次 5–6 分鐘 × 8 次 ≈ 45 分鐘」。實測真值：容器 `StartedAt 05:10:00.35` → app ready `05:10:32.03`＝**32 秒**；該次部署的 cloudflared 錯誤只有 **8 行、橫跨 18 秒**。**估計錯了 10 倍。** |
| **Root cause** | 5 分鐘週期的訊號漏掉一次，看起來就像 6 分鐘的空窗 —— 無論真實事件是 30 秒還是 5 分鐘。**量測沒有失效、數字是對的，錯的是我從它推出來的時間結構。** |
| **同日的對照組** | CK_Website 用 **15 分鐘**一次的探針看 **5–6 分鐘**的叢發，得出「零星、不連續」——而 cloudflared 的每分鐘日誌顯示母體是叢發的（單分鐘最高 76 筆）。他們的「零星」同樣是取樣的產物。**兩個獨立的人、同一天、同一個錯誤形態各犯一次。** |
| **Fix** | 直接量事件本身（容器啟動時戳、cloudflared 逐秒日誌），不從週期性訊號推。 |
| **Prevention** | ⚠️ **要描述一個事件的「時間結構」（多久、多頻繁、連續還是叢發）之前，先問「我的取樣間隔比這個事件短嗎」。** 不短的話，能得到的只有「有沒有發生」，得不到「怎麼發生」。⇒ 這與「驗證訊號的粒度比被驗證的性質粗」是同一族，但這一支特別難察覺：**訊號本身完全正常，沒有任何東西看起來壞掉。** |
| **Refs** | 同族：`verification_signal_too_coarse`、`proxy_metric_looks_good` / CK_Website 同日獨立案例 |

---

## L102 — 修法的首版把「不存在」偽裝成「用錯」，正是它要修的東西的反面（2026-08-29）
<!--enforced-by: scripts/checks/runner_flag_drift_audit.py（旗標在呼叫端漏掉時判紅）-->

| 欄位 | 內容 |
|---|---|
| **Context** | 跨 repo 探針量到同一端點的 GET：missive 回 **404**，lvrland／pilemgmt／digitaltwin 都回 **405**。而 404 有兩種意思、處置相反（路徑存在但方法不符／端點根本不存在），於是對方的探針**把 404 歸類成「正常」**——理由正是「有平台會正常回 404」⇒ **端點整個消失也不會被發現**。 |
| **What happened** | 我改 SPA fallback：攔到 `/api/*` 時先掃 `app.routes` 找同路徑的其他方法，有就回 405 + `Allow`。**首版是壞的**：沒有排除 catch-all 自己（`/{spa_path:path}` 匹配所有 GET）⇒ `allowed` 永遠非空 ⇒ **連真的不存在的路徑也回 405**。 |
| **Root cause** | 掃描集合裡包含了「正在執行這段程式碼的那條路由」。 |
| **為何差點沒發現** | **只驗「方法錯」那一個案例會看到 405，看起來就是成功了。** 五個案例逐一實測才抓到：①方法錯 ②真的不存在 ③正確 POST ④SPA 路徑 ⑤既有 GET API。 |
| **Fix** | 掃描時只看 `route.path.startswith("/api/")`，排除 catch-all。五案例全對。 |
| **Prevention** | ⚠️ **修一個「兩種情況被混為一談」的缺陷時，兩種情況都要驗** —— 只驗你想修的那一種，很容易做出一個把另一種也吞掉的版本，而那比原本更糟（原本至少誠實地說「或」）。⇒ 一般化：**收斂型修法的驗收案例數 ≥ 被收斂的情況數 + 1**（多的那個是「不該被影響的」）。 |
| **Refs** | `backend/main.py` spa_fallback / 前一版修法 2026-07-30（GET /api/* 回 200 HTML → 404，方向對但併成一個碼） |

---

## L100 — 執行者在、腳本在、旗標也在，只是呼叫時少了那個旗標（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | CK_AaaP 提出 L72（豁免是一筆待驗的斷言，需要可求證的理由**和**到期日），據此回掃本 repo 的 8 份基線與白名單。 |
| **What happened** | 兩份三個多月沒動的基線，逐一判型後**不是**「暫時容忍變成永久」—— 它們是**棘輪基線**（禁淨增），沒動代表沒變糟。但 `alias_rls_baseline` 有兩個真問題：① 鎖在 **29** 而實測 risks=**0**（棘輪從沒往下轉 ⇒ 天花板高於地板 29 格，可以靜靜新增 29 個未稽核 user filter 而檢核照過）；② **那個鎖從未被執行過** —— 基線比對整段包在 `if args.ci:` 裡，而唯一的自動排程 `CK_Missive-Fitness-Weekly` 跑的 weekly 第 7 步**沒帶 `--ci`**（帶 `--ci` 的 `run_fitness.sh` 是手動月度觸發、不在 Windows 排程裡）。 |
| **Root cause** | 能力與啟用分離：腳本有那個能力，但能力藏在旗標後面，而排程用的是不帶旗標的那條路徑。 |
| **為何沒被發現** | **三者分開看都是綠的**：排程存在（`Get-ScheduledTask` 看得到）、腳本存在且會跑（weekly 每週真的執行第 7 步）、旗標存在且正確（負向對照證明鎖本身有效）。L99 那種「宣告的執行者不存在」`grep -c` 就抓得到；這一種要比對的是「腳本的哪個模式才有那個能力」與「排程實際傳了什麼」，沒有窗口在問。 |
| **Fix** | baseline 29→0；weekly 7 改帶 `--ci`；另外兩支「新增缺口即 exit 2」且有基線檔的（`public_endpoint_auth_audit`／`http_method_convention_audit`）也補上 —— 新增一個無認證的公開端點是**回歸**不是漂移，應該是 RED。配套 **weekly 84** `runner_flag_drift_audit`。 |
| **Prevention** | ⚠️ **判準必須窄。** 首版粗判準（「支援嚴格旗標但沒帶」）實測 28 個命中，逐一判型後真問題只有 1 個 —— **誤報率 96%**，因為 `run_fitness_weekly.sh` 檔頭明文「刻意不傳 `--strict`」（2026-08-03 決定，避免把 YELLOW 升成 RED）。那是**政策不是疏漏**，一併判紅會讓人開始無視這支檢核。收窄成「基線比對被旗標包住」後命中 1、誤報 0。⇒ **這支的價值全在判準的窄度上。** |
| **Refs** | `scripts/checks/runner_flag_drift_audit.py`（weekly 84）/ `scripts/checks/alias_rls_baseline.json` / 同族：L99（宣告的執行者不存在）、`arch_pattern_script_existence_not_enforcement`、CK_AaaP#L72 |

---

## L99 — 壞掉的腳本＋假的執行者宣告＋文件把它列為驗證命令（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | owner 要求「複查確認前後端服務與涉及架構設計完整性與標準化」，照 `CLAUDE.md`／`ci-cd.md` 寫的命令跑 `verify_architecture.py`。 |
| **What happened** | 一啟動就 `[FATAL] 前端目錄不存在: .../scripts/frontend/src` —— 根目錄推導寫的是 `Path(__file__).resolve().parent.parent`，而本檔在某次整理中**被移進 `scripts/checks/`**，於是它把 `scripts/` 當成專案根。修好之後又發現兩處讀單檔（`api/endpoints.ts`、`extended/models.py`）而那兩個**早已拆成目錄**，那兩項自拆分起就一直是 ERROR、實質沒有驗過。 |
| **Root cause** | 檔案搬家與模組拆分都沒有同步更新引用它們的腳本；而**沒有任何人在跑它**，所以壞了也沒有人知道。 |
| **為何沒被發現** | `spec_executor_audit`（專門查「規範宣告的腳本有沒有人在做」）的白名單裡寫著「由 pre-commit hook 與 CI 呼叫」—— **實查 `.git/hooks/pre-commit` 提及 0 次、三支 workflow 各 0 次**，而 CI 本身早在 2026-03-09 全面停用（收費）。⇒ **那句宣告讓專門抓這件事的稽核放過了它。** 白名單裡的理由沒有人驗證過。 |
| **Fix** | 修根目錄（`parents[2]`）＋兩處改讀目錄；更正 `spec_executor_audit` 的宣告；接進 **weekly 83**。跑起來後真的抓到東西：**前端型別 SSOT 違規 4 檔 12 個 interface**（`development-rules` §3 明文禁止 `api/*.ts` 定義業務型別，而**前端一直沒有機制在強制** —— 後端 2026-08-17 才補上 weekly 59，當時累積 18 個違規無人知曉；前端是同一個故事的另一半）。已全數搬入 `types/` 並 re-export，違規歸零。 |
| **Prevention** | ⚠️ **豁免／白名單裡的「理由」本身要被驗證。** 「由 X 呼叫」是一句可以求證的斷言（`grep -c` 就夠），而它一旦是假的，就同時關掉了守門與守門的守門。⇒ 凡是白名單條目寫著「由某某執行」，稽核應**實際確認那個執行者提到它**，而不是相信欄位內容。 |
| **Refs** | `scripts/checks/verify_architecture.py` / `scripts/checks/spec_executor_audit.py` / weekly 83 / 同族：`arch_pattern_script_existence_not_enforcement`、L98（修法只擴散到一半） |

---

## L97 — 判準命中的是註解不是程式碼，而註解寫得越用心它越容易被騙（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | owner 裁示「響應式頁面排版檢視與調整優化」，為 RWD 缺口寫稽核（weekly 81）並複查既有的 weekly 56。 |
| **What happened** | 兩支稽核的判準都是**字串比對檔案內容**（有沒有 `isTablet` / 有沒有 `EnhancedTable`），而兩支都被**註解**騙過：① weekly 81 的負向對照——把 `isNarrow` 改回 `isMobile` 注入回歸，它**仍然回綠**，因為該檔的說明註解裡就寫著「isTablet」；② weekly 56 放過 `MorningReportTrackingTable`（16 欄、實測 768px 外溢 580px），因為它的註解寫著「刻意不改用 **EnhancedTable**」。 |
| **Root cause** | 靜態判準把「檔案文字」當成「程式碼行為」。**說明為什麼不用某個東西的那句話，在字串比對眼裡等於用了它。** |
| **為何沒被發現** | 兩者都回綠，而綠燈沒有人會去追。①靠負向對照當場揭穿；②靠「稽核說 0，但我實測這頁確實有一張原生 Table」的**矛盾**發現——與 L83 家族同一個救援機制。 |
| **Fix** | 兩支都改成 `re.sub(r"/\*[\s\S]*?\*/\|//[^
]*", "", src)` 先去註解再比對。weekly 81 的負向對照在去註解後才成立（GREEN→RED→GREEN）。 |
| **Prevention** | **凡是用字串比對判斷「程式碼有沒有做某件事」，一律先去註解。** 且新稽核**必須跑負向對照**——沒有這一步，分不出它是綠的還是瞎的。本則的①正是負向對照唯一一次真的擋下東西。 |
| **Refs** | `scripts/checks/responsive_narrow_convergence_audit.py` / `scripts/checks/frontend_design_standard_audit.py` / 同族：`verification_signal_too_coarse`（第八型）、L83 |

---

## L98 — 修一個共用元件不會讓它的同類變好，而它們的症狀一模一樣（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | 行動版面走查回報 768px 下多頁表格外溢 ~580px。 |
| **What happened** | 根因是 `useResponsive` 的 `isMobile = !screens.md`，而 AntD 的 md 斷點**就是 768** ⇒ **恰好 768px 時 isMobile 為 false**，平板（768–991）走桌面分支，拿到為桌面挑的固定 `scroll.x`（呼叫端傳 1100/1530，元件內建 `md: 900`）。**設定本身就在製造橫向捲動。** 而這個 bug `EnhancedTable` **2026-08-15 就修過了**（改判 `isMobile \|\| isTablet`）——只是沒有擴散到 `ResponsiveTable`（23 個檔在用）與四個自己寫 RWD 的頁面。 |
| **Root cause** | 同一個角色有多份實作：表格包裝三份（EnhancedTable／ResponsiveTable／UnifiedTable）＋散在頁面裡的 `scroll={isMobile ? ... : {x:N}}` 四處。修一份時沒有人問「還有幾份」。 |
| **為何沒被發現** | 08-15 修完當下量測確實改善了（那次量的頁剛好都用 EnhancedTable），**看起來就是修好了**。而行動量測只涵蓋 18/125 條路由，`/pm/cases` 列表根本沒被量、只量了它的詳情頁。 |
| **Fix** | 五處全改 `isNarrow = isMobile \|\| isTablet`；量測路由由 13 條擴到 31 條業務頁。實測表格外溢 9 筆／8 頁 → 4 筆／3 頁。配套 weekly 81 掃**全前端**（不只共用元件）的 `scroll={isMobile ? …}` 形狀。 |
| **Prevention** | **修共用元件時先問「同一個角色還有幾份實作」**（`grep -rl` 找同類）。⚠️ 並問「量測涵蓋到哪裡為止」——擴大路由後，`/document-numbers`(612px)／`/projects`／`/staff`／`/taoyuan` 立刻全部上榜，先前的「只有 8 頁溢出」答的是比問題更窄的範圍。 |
| **Refs** | `frontend/src/components/common/ResponsiveTable.tsx` / `scripts/checks/responsive_narrow_convergence_audit.py`（weekly 81）/ `selfaudit.config.json` `page_sweep.mobile_probe` / 同族：`proxy_metric_looks_good`、`arch_pattern_script_existence_not_enforcement` |

---

## L96 — 取走資料的動作與送出的動作之間，只要有失敗的可能，就必須有回填路徑（2026-08-29）
<!--enforced-by: backend/tests/test_line_digest_restore_regression.py（取走後送出失敗必須回填，回歸測試守著）-->

| 欄位 | 內容 |
|---|---|
| **Context** | LINE 免費月配額 200 則，各主題 job 改走 `queue_digest` 暫存、每日晨報一次帶走合併推播（2026-07-07 落地）。 |
| **What happened** | `drain_digest()` 是「`lrange` 讀取後立刻 `redis.delete`」，而真正的送出在 scheduler 幾十行之後。中間失敗——**最現實的是 LINE 月配額用罄**（`_call_line_api` 對 429 monthly limit 有短路旗標，配額用盡直接回 False 不送）——那批主題摘要**已經從 Redis 刪掉了，永久遺失且沒有任何痕跡**。不是延遲送達，是消失。 |
| **Root cause** | dequeue 與 deliver 之間沒有事務性。而「送出成功」是**我方單方面判定**的：呼叫返回被當成對方收到。 |
| **為何沒被發現** | 佇列空了與「本來就沒有告警」長得一模一樣。且 LINE 送出鏈的其餘部分都是對的（檢查 status_code、非 200 回 False、記 `admin_push_metrics.record_failure`、`log_delivery` 依 ok 記 success/failed、連續失敗 2 天 streak 告警）——**缺的只有 drain 與 send 之間那一段，而那一段剛好是唯一沒有人在看的地方**。 |
| **Fix** | 保留 drain 出來的原始條目；一個管道都沒送成功時 `restore_digest()` 放回佇列（rpush 維持時序、重置 TTL）。判準＝digest 是同一份內容送給多人 ⇒ **至少一個管道成功即算送出，全部失敗才回填**。另加 `logs/digest_history.jsonl` append-only 持久紀錄（跨 repo 治理告警的唯一入口只活在 48h TTL 裡，事後無從回答「上週有沒有人通報過什麼」）。 |
| **Prevention** | **任何 dequeue／claim 語意的操作，寫的時候就要同時寫回填路徑**，不要等到需要時才有。⚠️ 實證：`restore_digest` 寫完當天就攔下我自己的清理動作——drain 出來的 18 則真實告警（含 3 則跨 repo 送來的）差點被吃掉。**那類佇列的日常操作（清理、除錯、手動 drain）本身就是資料遺失的主要來源，不是罕見路徑。** |
| **Refs** | `backend/app/services/integration/line_digest_buffer.py` / `backend/tests/test_line_digest_restore_regression.py` / 同族：CK_Website `flushDigest` 的 cursor 無條件前進、L83（送出的與收到的不一致） |

---

## L95 — 排程紅燈有四種型態，而稽核上長得一模一樣（2026-08-29）

| 欄位 | 內容 |
|---|---|
| **Context** | 排程存活稽核只能看到「這支紅了」（`LastTaskResult != 0`），看不到紅的原因屬於哪一類。 |
| **What happened** | `CK_Missive_AutoStart` 永遠 `result=1`，而 `autostart.log` 顯示**所有容器都正常啟動**。根因：PowerShell 對 native 指令用 `2>&1`，每行 stderr 被包成 ErrorRecord 使 `$?` 為 false，即使 exe 退出碼是 0——而 `docker compose` 的進度訊息**本來就走 stderr**。 |
| **Root cause** | 「動作成功但退出碼騙人」。與同日處理的 A39（`CK_Missive_Daily_Backup` 指向搬家前舊路徑、連續失敗 171 天）合起來，可歸納為四型。 |
| **四型** | ① **路徑不存在**＝真失敗但沒人看（A39，171 天）② **工作已被別人接手**＝假失敗，該刪（A39 的備份已由容器內 asyncio task 承擔）③ **動作成功但退出碼騙人**＝假失敗，該修（本例）④ **真失敗但已知有界**＝該豁免但仍要出聲（CK_Website 的 NAMELEN）。**四者在稽核輸出上完全相同。** |
| **Fix** | 改 `exit $LASTEXITCODE`（native 的真實退出碼，不受 ErrorRecord 影響）；端到端觸發實測 `result` 1→0，稽核 RED 7→6。 |
| **Prevention** | (a) PowerShell 排程呼叫 native 指令時用 `exit $LASTEXITCODE`，不要依賴 `$?`。(b) ⚠️ **rc=0 沒有鑑別力**（CK_Website 的兩個反例：bat 整體退出碼掩蓋段內 robocopy rc=11、PM2 autostart rc=0 而 9 條 cron 缺席 37 分鐘）——**rc≠0 是訊號，rc=0 什麼都不證明**；單段指令才可把 rc 當主判準。(c) 判型必須由人做過一次才能進豁免白名單，**白名單為空是「還沒有人判過型」而非「還沒填」**。 |
| **Refs** | 排程 `CK_Missive_AutoStart` / `scripts/checks/windows_task_liveness_audit.py` / 同族：A28（被停用正是對的）、L38（平時保險反模式） |

---

## L94 — 把觀測者的回報路徑接到被觀測的系統上，就是讓它們共用失敗模式（2026-08-29）
<!--not-enforceable: 「這兩條路徑共不共用失敗模式」要知道系統的相依拓樸，是架構判讀不是字串比對。防線是整併監測前先問「被監測的系統掛掉時這條回報路徑還在嗎」。唯一可機械化的 (c)【部署後公網驗證多次抽樣】已於 2026-08-30 實作於 scripts/deploy/deploy-public.sh Step 6（在那之前註解宣稱已改而程式碼從未改）。-->

| 欄位 | 內容 |
|---|---|
| **Context** | CK_Website 的 CF edge Worker 持續監測四個 SSO 消費端；另有 PM2 端治理 cron 走本 repo 的 `/api/notify/digest` → 晨報 → LINE。兩條鏈送到同一個 LINE、共用同一個月配額，看起來重複。 |
| **What happened** | 提議把 Worker 也改走 `/api/notify/digest`（好處真實：長期記憶、配額只算一次、集中在會被讀的地方）。而那 38 則告警裡**最有價值的一筆是「四站同時 530」——正是本機重啟 37 分鐘、PM2 鏈整個死掉的時刻**。合一之後 Worker 會投遞到 `missive.cksurvey.tw`，**那個域名在該事件中也是 530** ⇒ 告警記錄的正是那次失敗，而它會因為那次失敗而送不出去。 |
| **Root cause** | 外部監測的價值來自**它不共用被監測系統的失敗模式**。任何「合併以節省成本」的優化都可能在無意間消滅這個性質，而收益（配額、集中化）是立即可見的，代價只在故障時才顯現。 |
| **Fix** | 合一可行，但**直接推送的路徑必須保留為 fallback，這是條件不是選項**（我方端點回非 2xx 時才走）。 |
| **Prevention** | (a) 評估任何監測整併前先問：**「被監測的系統掛掉時，這條回報路徑還在嗎？」** (b) 同理適用於容器內 metrics／`cron_events.jsonl`——它們在容器不可達時什麼都證明不了，而那正是最需要證據的時刻。**「看守者掛掉的那一段，只有站在它外面的東西看得見。」**(c) 我方實例：兩筆公網 502 期間 `cron_events` 顯示排程照跑無異常空窗 ⇒ backend 活著、CF 打不進來＝L76 殭屍埠——**這是 L76 第一次有外部證據**，而 `deploy-public.sh` 的公網驗證是單次 curl，間歇性殭屍埠會讓那次剛好通過 ⇒ **部署後的公網驗證要多次抽樣** —— 2026-08-30 實作三次抽樣（任一次非 200 即失敗）。⚠️ 在此之前 `deploy-public.sh` 有一句註解宣稱「前幾天才把單次 curl 改成三次抽樣」，而全 repo grep 只命中那句註解本身 —— **宣稱的改動從未發生**（L104 形狀，且就在防線上）。 |
| **Refs** | `docs/architecture/OPEN_ITEMS_20260819.md` 結案總表 / 跨 session：CK_Website `ck-sso-edge-cron` / 同族：L76（殭屍埠）、L84（設定嚴謹≠跑得起來） |

---

## L93 — ORM mapper 初始化失敗＝整個系統無法登入，而 /health 仍是 200（2026-08-16）

<!--not-enforceable: 部分可檢核（test_orm_mappers_configure 已鎖 mapper 可初始化），但「改 ORM 要重建不能只 docker cp」是行為準則-->

| 欄位 | 內容 |
|---|---|
| **Context** | 為核銷審核加 `approved_by` 欄位後，`ExpenseInvoice` 有兩個外鍵指向 `users`（`user_id`＝送出者、`approved_by`＝核准者）。 |
| **What happened** | SQLAlchemy 無法判斷 `User.expense_invoices` 該走哪一條 → `AmbiguousForeignKeysError` → **mapper 初始化失敗** → 所有碰到 User 的查詢爆掉 → `POST /api/auth/google` 回 **500**，owner 回報「系統無法登入」。 |
| **Root cause** | ① 加第二個指向同一張表的外鍵時，**兩端的 relationship 都必須指明 `foreign_keys`**。② 事故被放大的原因是**我修好程式碼後只做 `docker cp` 沒有重建** —— `docker cp` 不會重載已匯入的模組，行程仍載著舊 mapper，所以「程式碼是新的、行為是舊的」。 |
| **為何沒被發現** | **`/health` 與公網首頁全程 200** —— 它們不觸發 ORM mapper 設定。L76 的三層驗證（host:8001／公網首頁／公網 API）**全部通過**，而登入是死的。又一次「服務層綠、業務層死」，而這次連我剛建的八條生命跡象也照不到（它們查資料不走 ORM relationship）。 |
| **Fix** | 兩端 relationship 指明 `foreign_keys`；重建容器（非 docker cp）；新增 `test_orm_mappers_configure`（一次觸發全部 mapper 設定，負向測試：拿掉 foreign_keys 即紅）。 |
| **Prevention** | (a) **改 ORM 一律重建容器**，`docker cp` 只對 bind-mount 的 `scripts/` 有效。(b) 加外鍵時問「這張表已經有幾個外鍵指向同一個目標」。(c) L76 的部署驗證應**加一條會觸發 ORM 的端點**（如 `/api/auth/check`），否則 200 只證明靜態層活著。 |
| **Refs** | `backend/app/extended/models/{core,invoice}.py` / `backend/tests/unit/test_orm_mappers_configure.py` / 同族：L45（healthcheck 綠而服務死）、L90（檢核跑在哪個環境） |

---

## L92 — 檢核在「要報問題的那一刻」崩掉，而平常看起來好好的（2026-08-15）

<!--enforced-by: scripts/checks/governance_alignment_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Context** | 做架構標準化複查時跑 `governance_alignment_audit`，它把 ADR/教訓/SOP/腳本數全都算完印出來了，最後卻退出 1。 |
| **What happened** | 它在印最後那句「✓ 規範 vs 現況 完全對齊，無缺口」時 `UnicodeEncodeError` —— **全綠的時候反而退出 1**。往下掃，19 支檢核腳本 print 了 cp950 編不出來的符號（`✅🔴⚠✓❌🟡🟢` 等）且沒有 `sys.stdout.reconfigure`。host 上隨機挑 6 支實測，**5 支真的崩**。 |
| **Root cause** | weekly 的 54 步跑在 **host（cp950）**，容器則有 `ENV PYTHONIOENCODING=utf-8` 所以不受影響 —— 這是 L90「檢核跑在哪個環境同樣重要」的又一例。而真正危險的是崩潰**路徑相依**：平常走 GREEN 分支沒事，偏偏走到 🔴 分支才倒。`hermes_baseline_gate_audit` 印 `✅🔴🟡`，而 🔴 那條正是有問題時才會走的。**「它平常好好的，只在要報問題時壞掉」比一直壞更難發現**，因為前者不會累積出任何可疑的紀錄。 |
| **Fix** | 19 支補上標準 preamble（`sys.stdout.reconfigure(encoding="utf-8")`，try/except 包住），重測 0 支再崩。 |
| **Prevention** | (a) **判準要用「實際做得到嗎」而不是「看起來像不像」**：我第一版用「有沒有 print 中文」當判準得到 28 支，**那是錯的** —— 中文在 cp950 本來就編得出來，崩的是符號；改用 `ch.encode('cp950')` 實測才收斂到真正的 19 支。(b) **批次改寫腳本時，「最後一個 import」不一定在頂層**：`knowledge_dedup_audit` 的 import 出現在要送進容器執行的字串裡，preamble 被塞進字串中（語法沒錯、跑起來仍崩）。(c) 同 L49.8（`.ps1` 缺 BOM 在 PowerShell 5.1 下整支解析失敗）家族：**看不見的編碼問題，症狀是整支不執行或在錯的地方倒下，而不是報錯**。 |
| **Refs** | `scripts/checks/governance_alignment_audit.py` 等 19 支 / 同族：L49.8（BOM）、L90（環境差異）、`SELF_AUDIT_EVOLUTION_STANDARD.md` §3 #22 |

---

## L91 — 在 Windows 上執行帶容器絕對路徑的程式碼不會失敗，它會靜靜讀寫 `D:\app\`（2026-08-12）

| 欄位 | 內容 |
|---|---|
| **Context** | 修 `cron_silent_dormant_check` 時，替它加了一條「/metrics 沒有指標就改讀持久的 `cron_events.jsonl`」的退路，候選路徑沿用既有慣例寫成 host 與容器各一條。 |
| **What happened** | host 候選我寫錯了（compose 掛的是 `./backend/logs:/app/logs`，不是 `<repo>/logs/`），於是往下試容器候選 `Path("/app/logs/cron_events.jsonl")`。**在 Windows 上這條路徑不會失敗**——`/app` 被當成磁碟根相對路徑解析成 `D:\app\`，而**那個目錄真的存在**（過去某次在 host 執行帶容器路徑的程式碼時被靜靜建出來的），裡面躺著一份 **08-10 的舊 `cron_events.jsonl`**。結果：讀到了、有資料、格式正確，然後據此把 36 個健康的排程判成「從未執行」、把一個正常的判成 dormant。**檢核給出了精確而完全錯誤的結論。** |
| **Root cause** | 在 Linux 上路徑寫錯會 `FileNotFoundError`（吵、但安全）；**在 Windows 上會讀到一份看起來很正常的假副本**（安靜、但有毒）。L52 家族一直談的是「路徑對不對」，這一層是「**路徑錯了卻仍然成功**」。 |
| **Fix** | ① 容器絕對路徑候選**只在非 Windows 採用**（`os.name != "nt"`）；host 一律走 compose 掛載的真實位置。② 加**新鮮度守衛**：backend 明明在跑（拿得到 /metrics）卻讀到一份 6 小時以上沒增長的紀錄檔，就不是權威來源而是某個副本，**寧可說「沒有依據」也不據此判定**。 |
| **Prevention** | (a) host 端腳本列容器路徑候選時，一律加平台判斷——否則 Windows 會替你「找到」它。(b) 對照組：`scheduler_liveness_audit` 沒被騙到，因為它要求**成對的兩個檔案同時存在**才採用該組候選；單一路徑命中就採信，缺的正是這個交叉條件。(c) 讀到的資料要能自證新鮮，不能只驗「檔案存在」。(d) `D:\app\`（5 個檔案，最新 08-10）是這個 bug 的殘留物，仍在原地——它下次還會騙到人。 |
| **Refs** | `scripts/checks/cron_silent_dormant_check.py`（`_cron_events_path` 平台判斷 + `fetch_last_event_ages` 新鮮度守衛）/ `scripts/checks/scheduler_liveness_audit.py`（成對候選的正面對照）/ 同族：L52（host↔container 路徑）、L43（掛錯 volume 也是「成功但錯」） |

---

## L89 — 跨 repo 共用腳本帶著自己的退出碼約定進到別人的 runner，會被靜靜降級成「未驗完」（2026-08-09）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Context** | 2026-08-08 lvrland 後端 hang 住、API 對真實使用者完全不可用而公網首頁仍 200，唯一線索是 DB 的 `idle in transaction (aborted)`。為防再犯，把 `db_transaction_health_check.py` 部署到四個 repo。 |
| **What happened** | 該腳本依 portfolio 標準寫（**0=GREEN／1=YELLOW／2+=RED**），但 lvrland 的 `run_checks.sh` 用的是另一套：**1=FAIL／2=未驗完**，而且它的其他 13 支檢核都遵守後者。於是若中止交易再度發生，該檢核會 exit 2 → runner 印「**SKIP（未驗完）**」→ `UNVERIFIED=1` → `static-checks.json` 寫 **`fail: 0`** → `OVERALL=YELLOW`。**為了防止那次停機而寫的檢核，在那個 repo 是啞的。** |
| **Root cause** | 兩套約定都自洽，但**共用腳本沒有在呼叫點宣告自己用哪一套**，靜靜取了預設值。這不是誰對誰錯——`2` 在一邊是「最嚴重」、在另一邊是「沒驗到」，語意剛好相反。而「沒驗到」與「嚴重故障」在輸出上長得完全不同，卻被對應到同一個數字。 |
| **Fix** | 腳本加 `--red-exit {1,2}`（預設 2＝portfolio 標準），**由呼叫端明示**；lvrland 的 runner 傳 `--red-exit 1`，並把 `run_py` 改吃 `"$@"` 以容納參數。**實測驗證**：以可逆方式在 lvrland DB 注入真實的中止交易 → runner 印 `FAIL`、`OVERALL=RED`（先前會是 SKIP／YELLOW／fail=0）；注入解除後回 0。 |
| **Prevention** | (a) **跨 repo 移植腳本時，先讀目標 repo 的 runner 怎麼解讀退出碼**——這比讀腳本本身更重要，因為腳本再對，解讀錯就等於沒有。(b) 有歧義的約定要讓**呼叫點明示**，不要靠預設值：預設值出錯時是安靜的。(c) 驗證共用檢核不能只跑 `--self-test`，要在**目標 repo 的 runner 裡**用真實故障注入一次。 |
| **Refs** | `CK_lvrland_Webmap/scripts/checks/run_checks.sh`（`run_py` 吃 `"$@"` + `--red-exit 1`）/ `*/scripts/checks/db_transaction_health_check.py`（`--red-exit`）/ 同族：L83（印出狀態與退出碼必須一致）、L88（檢核把自己的退出碼判成異常） |

---

## L87 — 「多給一種憑證」不是保險，是多開一條會失敗的路；而剛上線的檢核最不該被信任（2026-08-09）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Context** | 導入第 5 個 repo（CK_DigitalTunnel）的瀏覽器走查。DT 是**第一個 token 型**：認證走 `Authorization: Bearer`，token 存 localStorage 且經 XOR+base64 混淆，與前四個 cookie/session 型 repo 的典範不同。 |
| **What happened** | 三件事，全部是「新加的東西自己出問題」：<br>① **保險反而致命**：adapter 為求穩妥同時種了 cookie 與 localStorage（後端 `verify_jwt_token` 兩種都收）→ **27 頁全部 403**。三向對照才看出：cookie-only 403（走 cookie 路徑會觸發 CSRF 檢查而瀏覽器沒有 CSRF token）、Bearer 200。多給的那一種把請求推上一條**必然失敗**的路。<br>② **新診斷製造假缺陷**：08-08 為追 pile 503 加的「回應層 4xx 診斷」一律報 4xx，於是 Missive `/reports` 被報 403 —— 實測同端點帶正確 CSRF 回 **200 且有真實資料**（走查全站共用一個 browser context，單次性 CSRF token 被前面的頁面用掉）。根因是**同一類事件被兩套標準處理**：console 層的 NOISE_RE 明確排除 401/403，回應層用另一種訊息格式繞過了它。<br>③ **新格式打破既有降級規則**：Missive 早已登記 `/admin/deployment` 的 `match: "status of 503"`，但降級要求「**所有**問題都符合」，新增的 `HTTP 503 <url>` 格式不符 → 已登記的已知限制**失效**、變回 FAIL。 |
| **Root cause** | 三者共通：**新增一條路徑時，只驗了它自己會不會動，沒問它與既有機制的接縫**。①多一條認證路徑 ②多一種錯誤訊息格式 ③而既有比對規則是按舊格式寫的。與 L81「換了出口就要換整條鏈」同構，差別在這次是**加**而不是換 —— 加同樣會斷鏈。 |
| **Fix** | ① token 型 repo **只給 token**，adapter 明確不輸出 cookie 並寫明理由。② 回應層診斷排除 401/403（與 console 層一致），**保留 404 與 5xx** —— 判準是「401/403 有正當的良性解釋（權限探測、刻意不對外），404 沒有」；代價寫進註解：pile 那種刻意安全 403 改由 `public_exposure_audit` 管（它問「該不該對外」，才是對的提問層級）。③ 比對規則涵蓋兩種格式。另把兩支引擎**各自一份且已漂移**的 NOISE_RE 收斂進 `_bootstrap`。 |
| **Prevention** | (a) **「為了保險兩種都給」是反模式**——每多一種憑證/路徑就多一條可能失敗的分支，且失敗時症狀相同無從區分（同 08-08 那次「把所有 cookie 一律設 httpOnly」）。(b) **新增訊號格式時，回頭檢查所有按舊格式寫的比對規則**（豁免、降級、告警過濾）——它們會靜靜失效，而症狀是「本來綠的變紅」或更糟的「本來會紅的變綠」。(c) **剛上線的檢核最不該被信任**：它還沒有任何一次「已知結果」可對照，本輪 §3 可信度表新增的 3 條（#15/#16/#17）全是我同一輪自己新加的機制造成的。 |
| **Refs** | `CK_DigitalTunnel/scripts/checks/selfaudit_auth.py`（bearer 型 adapter + 混淆往返 self-test）/ `CK_DigitalTunnel/selfaudit.config.json` / `shared-modules/selfaudit/src/_bootstrap.cjs`（LOCAL_STORAGE + 共用 NOISE_RE）/ `shared-modules/selfaudit/src/ui_page_sweep.cjs`（4xx 判準 + 判 FAIL 前重跑）/ `SELF_AUDIT_EVOLUTION_STANDARD.md` §3 #15–#17 / 同族：L81（換出口斷鏈）、L86（讓工具說出它看到什麼） |

---

## L88 — 檢核把自己的退出碼判成異常：自我循環讓 weekly 永遠不可能綠（2026-08-09）

| 欄位 | 內容 |
|---|---|
| **Context** | `windows_task_liveness_audit`（weekly step 28）直接問作業系統有哪些 CK 排程，判 State／未宣告的失敗碼／`StartWhenAvailable`／逾期。 |
| **What happened** | 它把 `CK_Missive-Fitness-Weekly` 的 `LastTaskResult=1` 判成「未宣告的失敗碼」＝RED。但 weekly runner 的三態約定是 **0=GREEN／1=有 RED step／2+=執行失敗**，1 是**正常且已宣告的語意**。於是形成閉環：稽核判它異常 → 自己成為 weekly 的一個 RED step → weekly 因此退出 1 → 下次稽核再判它異常。**weekly 在結構上永遠不可能綠。** |
| **Root cause** | 稽核問的是「任務有沒有跑完」（存活層），卻拿**內容層**的退出碼當存活訊號。它對 `SelfAudit-*` 任務已經做對了這個區分（「有失敗＝任務跑完了，內容另判」），只是沒套用到 weekly runner 自己。而 `ALLOWED_NONZERO` 這個宣告機制**存在但從未被使用**（空 dict）。 |
| **Fix** | 宣告 `CK_Missive-Fitness-Weekly: {1: "有 RED step＝跑完了、紅的是內容"}`。**刻意只宣告 1、不宣告 2** —— 2 代表 runner 自己執行失敗（argparse 錯、腳本不存在），那是真的要出聲的。內容另有接收者（weekly 自己推 digest）。RED 由 5 降為 2，剩下兩條都是真實且已知的頁面故障。 |
| **Prevention** | (a) **「永遠是紅的」與「連 9 週 RED 無人知」下場相同**——訊號失去意義。看到某項長期紅，先問它有沒有可能在結構上不可能綠。(b) 存活層與內容層必須分開判：「跑完了但結果是紅的」和「根本沒跑」的處置完全不同。(c) 空的宣告機制（allowlist / registry）是個訊號：要嘛沒人用、要嘛用錯地方。 |
| **Refs** | `scripts/checks/windows_task_liveness_audit.py`（`ALLOWED_NONZERO`）/ `wiki/memory/fitness_weekly_last_run.json` / 同族：fitness_self_false_green.md（weekly 連 9 週 RED 無人知）、L83（印出狀態與退出碼必須一致） |

---

## L86 — 連續猜錯五次之後：讓工具「說出它看到什麼」，比再猜第六次有效（2026-08-08）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | pile 走查 12 條路由全報「被導回登入頁」，而同一條路由用視覺走查單獨開卻完整渲染、已登入為超級管理員。 |
| **Cause** | 真因是**我自己**：修 cygpath 路徑問題時把註解插進了 `COOKIE="..." USER_INFO="..." \` 的續行中間——反斜線後面接註解，**環境變數指派完全沒有套用到 node**。cookie 因此從未被加進瀏覽器；localStorage 有種（那是另一條路徑），所以看起來「像是登入了但被踢出來」。**追這一個問題我連續猜錯五次**：種錯 store（改了→沒變）／重導時間窗口（只解釋 1 頁）／角色欄位缺失（真缺陷但非根因）／掃描自我限流（只解釋 FAIL 半邊）／cookie 屬性（**改成 httpOnly 反而把 Missive 走查從 17 PASS 弄成 1 PASS**，因為 csrf_token 必須可被 JS 讀取）。每一個都是真實缺陷，但都不是根因。 |
| **Fix** | 停止猜測，改讓檢核**輸出它實際看到的狀態**，三個維度逐一補：①重導時的實際 URL（立刻揭露 `/admin/login-history` 這種**路由名本身含 login** 的假陽性）②localStorage 有哪些 key ③cookie 有哪些。最後補上**開場診斷** `[auth] 起始 cookie:` —— 一行就分辨出「從沒加成功」而非「加了又被清掉」，當場定位。結果：PASS 13 → **33**、SKIP 12 → **0**。 |
| **Prevention** | (a) **同一個問題猜錯兩次以後，就不要再猜第三次**——改成讓工具說出它看到什麼。診斷輸出是一次性投資、長期資產；猜測是每次都要重付的成本。(b) 「A 說有效、B 說沒有」時（後端說憑證有效、瀏覽器說沒有），要補的是**中間那段的可觀測性**，不是對兩端再做假設。(c) 登入態有**三個載體**（localStorage / cookie / 後端 session），診斷少報一個就會卡在無法判斷。(d) **共享引擎的改動要在多個消費端驗**——只驗一個會像這次一樣修好 A 弄壞 B。 |
| **Refs** | `shared-modules/selfaudit/src/_bootstrap.cjs`（開場 cookie 診斷）/ `src/ui_page_sweep.cjs`（重導判定 + 三維診斷）/ `CK_PileMgmt/scripts/checks/run_selfaudit.sh`（續行註解的真因）/ 同族：§3 可信度規則（先懷疑檢查、再懷疑系統） |

---

## L85 — 破壞性指令的作用範圍必須先確認；而且答案往往早就寫在文件裡（2026-08-08）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 修 pile 前端時撞到「port 13000 already allocated」。我用 `docker ps -aq --filter publish=13000` 找出佔用者並 `rm -f` —— **那個埠是 `ck-platform-grafana` 在用**，我把觀測棧的 Grafana 刪掉了。它與我正在處理的事情完全無關。 |
| **Cause** | 兩層。①**過濾條件不等於目標**：`--filter publish=13000` 回傳的是「所有發佈該埠的容器」，我卻預設它只會是我要處理的那個。破壞性指令前沒有先看清單、沒有排除非目標。②**答案早就寫在 repo 裡**：pile 有前端部署專用 SOP 與腳本（`scripts/redeploy-frontend.sh`、`docker-compose.frontend-prod.yml`、port **3005**），註解白紙黑字寫著「**override 主 compose 的 13000 衝突（ck-platform-grafana 已占 13000）**」，日期 **2026-05-27**。我沒查就自己下 `docker compose build/up`，才製造出埠衝突、殘缺容器（無網路 → `host not found in upstream "backend"`）與這次誤刪。 |
| **Fix** | Grafana 以既有資料 volume（`observability_platform_obs_grafana_data`）重建，`/api/health` 回 `database: ok`、儀表板與帳密沿用、埠 13000 恢復。pile 改用既有 SOP 腳本部署 —— 它自帶部署後新鮮度複驗（image git_commit ⊇ 最新 frontend commit）並通過。 |
| **Prevention** | (a) **`rm -f` / `docker compose down` / 任何依「條件」選目標的破壞性指令，先印出清單並確認每一項都是目標**；跨 stack 的資源（埠、volume、network）尤其危險，因為條件會撈到別人的東西。(b) **動一個 repo 的部署前，先找它自己的部署 SOP/腳本**——這個專案幾乎每個 repo 都有，且通常記著你正要踩的那顆雷。查一次的成本遠低於踩一次。(c) 症狀是「埠被占」時，先問**誰在占、那是不是該讓的**，而不是直接讓它讓開。 |
| **Refs** | `CK_PileMgmt/scripts/redeploy-frontend.sh`（正確做法）/ `CK_PileMgmt/docker-compose.frontend-prod.yml:47`（2026-05-27 就寫著這個衝突）/ `CK_AaaP/platform/observability/docker-compose.yml`（Grafana）/ 同族：feedback_rigor_no_self_inflicted_instability（禁自造不穩定） |

---

## L84 — 「設定寫得很嚴謹」與「它跑得起來」是兩件事：從未啟動成功過的服務，會逼出一條更差的替代路徑（2026-08-08）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | `digitaltwin.cksurvey.tw` 由 host 的 Vite **dev server** 對外提供，實測 `/src/App.tsx` 回 200、**92,129 bytes 完整原始碼公開可讀**。而該專案的正式路徑（builder → volume → nginx）其實早就定義好。 |
| **Cause** | **nginx 從來沒有啟動成功過**（`frontend-dist` volume 是空的即為佐證），逐層追出**三個獨立阻斷**，任一個都足以 `[emerg]`：①acute3d NAS 掛載失敗（`key has been revoked`）—— **掛載失敗會讓整個 nginx 起不來**，不是只有該功能不可用；②`default.conf` 帶 UTF-8 BOM → `unknown directive "﻿#"`；③`cap_drop: ALL` 與自身 `nginx.conf` 不相容（`user nginx;` 需 SETUID/SETGID 降權、`proxy_cache_path` 需 CHOWN/DAC_OVERRIDE）。另有健檢**從來不可能通過**（用映像檔裡沒有的 `curl`；用 `localhost` 而 nginx 只 listen IPv4 → `::1` refused），容器長期標 unhealthy 而服務其實健康。**這些全部是「寫好了但沒人驗過它跑不跑得起來」**。而當正式路徑不可用，人就會找一條跑得動的替代路徑 —— 那條路徑（dev server）帶著遠更嚴重的問題。 |
| **Fix** | 移除 BOM；補回 nginx 必需的最小權限集（CHOWN/SETUID/SETGID/DAC_OVERRIDE，維持 `cap_drop: ALL` 其餘強化）；健檢改 `wget -qO- http://127.0.0.1/health`；暫時停用 acute3d 掛載（**取捨依據**：它由這個 nginx 提供，nginx 沒跑時本來就不可用，停用不會失去任何目前可用的功能）。**不動 CF Dashboard**：改 `HOST_PORT_NGINX` 讓 nginx 接上 tunnel 現行指向的埠，變更可在本機完成並隨時回滾。 |
| **Prevention** | (a) **強化設定（cap_drop / read_only / seccomp）必須有一次「真的把它啟動起來」的驗證**，否則寫得愈嚴謹愈容易變成從未生效的擺設。(b) 掛載失敗會使**整個容器**無法啟動 —— 選用性資料源（NAS/外部儲存）不該與主服務生死綁定。(c) **健檢指令要驗它在該映像檔內存在且會通過**（`curl` 不一定有；容器內 `localhost` 可能先解析 IPv6）——「健檢不可能通過」與「服務真的壞了」在監控上長得一樣。(d) 追問法：**若正式路徑不可用，現在是誰在提供服務？** 那個「暫時方案」往往才是真正的風險所在。 |
| **Refs** | `CK_DigitalTunnel/docs/SERVING-TOPOLOGY-20260808.md`（含回滾與驗證步驟）/ `CK_DigitalTunnel` commit `04ed7f6`+`b31f4d2` / 同族：L45（compose healthcheck override）、L49（容器缺原生相依）、v6.33「設定寫錯時不會給你綠燈」 |

---

## L83 — 「我送出了什麼」與「對方收到了什麼」是兩件事：中間層會靜靜改寫，而單元測試斷言的是前者（2026-08-07）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 回報 SSO 憑證到期後刪除動作直接消失。修法是讓後端回 `X-Reauth-Required` 讓前端知道「這條路死了」——單元測試全綠，**實打 curl 卻看不到那個 header**。 |
| **Cause** | 自訂 `http_exception_handler` 把 `headers=_get_cors_headers(request)` **整組覆蓋**，`exc.headers` 全部丟掉。連 401 依規範該帶的 `WWW-Authenticate` 也從來沒送出去過——那行在 endpoint 裡明明寫著＝**寫了等於沒寫**。同一天同一形狀又出現兩次：①視覺走查 `--routes` 用 `.split('=')[1]`，於是 `?tab=correspondence` 被截成 `?tab`，**靜靜拍下預設分頁的截圖**（我因此看著錯的畫面以為驗過那一頁）；②`doc_baseline_claim_audit` 印 `[RED]` 卻 `return 0`（原生模式），runner 收到的是 GREEN——**管理文件數字的檢核，自己在 weekly 裡是假綠**；同支的 YELLOW 分支反而回 2，嚴重度與退出碼對調。 |
| **Fix** | ①handler 改 CORS 鋪底再 `headers.update(exc.headers)`（endpoint 意圖覆蓋其上）；②`--routes` 改 `slice(prefix.length)`，canonical 修完同步四個 repo；③漂移回 2、無法判定回 1，與印出的狀態一致。三者都**實打驗證兩個方向**：header 在／不在、截圖拍到正確分頁、寫錯數字轉紅還原轉綠。 |
| **Prevention** | (a) 凡是「我丟給下游一個值」的修改，驗證必須在**下游的收端**做，不能只斷言自己丟了什麼——`assert exc.headers` 與 `curl -D -` 是兩回事。(b) CLI 參數解析禁用 `.split(sep)[1]`，值本身含分隔符時會靜默截斷。(c) 檢核腳本的**印出狀態與退出碼必須一致**，且要知道 runner 用哪一種（本專案 runner 一律不傳旗標、依原生三態）。(d) 三者的共同提問：**這個訊號在抵達真正的消費端之前，會經過誰？那個人有沒有可能把它改掉或丟掉？** |
| **Refs** | `backend/app/core/exceptions.py`（headers 合併）/ `backend/app/api/endpoints/auth/session.py`（`X-Reauth-Required`，刻意只在「曾經有憑證」時宣告）/ `backend/tests/unit/test_reauth_required_header_regression.py` / `shared-modules/selfaudit/src/ui_visual_walk.cjs` / `scripts/checks/doc_baseline_claim_audit.py` / commit `af3a37c2`+`7bf45566` / 同族：L01（docstring 與實作斷鏈）、v6.33 `\|\| true` 假綠、L81（負向斷言無鑑別力） |

---

## L81 — 換了出口就要換整條鏈：把通知從 A 管道改到 B 管道時，閘門、測試安全網、測試斷言都會留在 A（2026-08-04）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 08-04 覆盤跑 weekly，step 24 報「新增 6 項失敗」。追下去不是 flaky —— 是 08-03 把 5 個 job 由 Telegram 改走 LINE digest 後留下的一整串殘留；其中最嚴重的一項是**測試會把假告警寫進正式的晨報緩衝區**（實測 buffer 內 9 則全是 `job_a`／`DB connection lost`／假日期等測試資料，隔天 07:30 會推給 owner）。 |
| **Cause** | 「改出口」被當成一個點的修改，實際上牽動四個地方，08-03 只改了第一個：①**呼叫點**（已改）②**閘門**——`llm_quota_check` / `health_check_broadcast` 仍以 `TELEGRAM_ADMIN_CHAT_ID` early-return，等於讓一個已宣告死亡的設定決定 LINE 告警發不發，只因它剛好還有值所以看不出來；③**測試安全網**——conftest 擋的是「送出去」（抽掉 LINE/Telegram token），digest 是「寫進正式 Redis、明早才送」，網從外面繞過去了；④**測試斷言**——仍 patch 舊管道，正向測試變成失敗、**負向測試變成永遠會過**（`assert len(push_calls)==0` 對一個永遠不會被 append 的 list）。另外 08-03 宣告「Telegram 死管道全收斂」實為**只掃了 scheduler.py**，service 層還有 3 處（自我診斷告警／自動結晶通知／週自傳「備援」）通往死管道。 |
| **Fix** | ①`line_digest_buffer` 加 `LINE_DIGEST_BUFFER_ISOLATED` 隔離旗標（沿用安全網 v3 思路：不替換方法，**拿掉它抵達正式狀態的能力**）+ conftest 預設開啟並在每測試後清 in-memory；②移除兩處死 Telegram 閘門，補回歸鎖 `test_alert_not_gated_by_dead_telegram_env`；③8 支過期測試改斷言 digest，3 支無鑑別力的負向測試改 patch 真出口；④service 層 3 處收斂（自我診斷／結晶通知改走 digest，週自傳的永遠回 False 的 Telegram「備援」直接移除——**一個不會生效的備援比沒有備援更危險**）；⑤正反雙向驗證隔離旗標（開→Redis 不變、關→Redis +1），並精準移除 buffer 內 10 則測試污染（不 drain，保留真實條目）。 |
| **Prevention** | (a) 改任何通知出口時，把「閘門／安全網／正反向測試」當成同一次修改的一部分，不是後續清理。(b) **負向斷言必須驗鑑別力**——`assert 沒發生` 若掛在一個不可能發生的物件上，它會永遠綠。(c) 收斂「死管道」時搜尋範圍是**行為**不是檔案：`grep` 完 scheduler 還要問「還有誰在呼叫這個管道」。(d) 測試安全網的提問要改成「**這條路徑會不會抵達正式狀態**」，而不是「會不會送出去」。 |
| **Refs** | `backend/app/services/integration/line_digest_buffer.py`（隔離旗標）/ `backend/tests/conftest.py` v4 安全網 / `backend/tests/unit/test_llm_quota_check.py`、`test_cron_self_health_alert.py` / 同族：v6.37 flaky 測試混入正式 Redis 學習池、v6.41 `WIKI_SUBDIRS` 漏 `rebuild_index`（都掃了檔案沒掃行為） |

---

## L82 — 「還沒到門檻」與「永遠到不了門檻」長得一模一樣：資料深度被保留期釘住，而腳本每次都禮貌地說資料不足（2026-08-04）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 08-02 記「價值層資料深度 15.6/30 天」，08-03 量到 **15.37** —— 數字往回走。查 Prometheus `storageRetention` 為預設 **15d**，而 `capability_usage_snapshot` 的判定門檻是 30 天：深度不是在累積，是被保留期裁齊的。也就是 8/31 的第 6 階價值層判定**結構上永遠不會成立**。 |
| **Cause** | 兩個獨立設定（觀測棧保留期、判定門檻）分屬不同 repo，沒有任何一處把它們放在一起看。腳本設計上「資料不足即 exit 2 拒絕給結論」是對的紀律，但它讓**永久性阻斷偽裝成暫時性等待** —— 每次執行都給出一個合理、溫和、不需要行動的訊息。 |
| **Fix** | owner 決議降門檻（`MIN_DATA_DAYS` 30→14）而非動到五系統共用的觀測棧；同時把**代價寫進產出**：14 天深度 + 7 天視窗只涵蓋約兩個週循環、看不到月週期，月結／月報／年度作業必然 0 流量，**不得**據此判死，只能作人工複核線索（`known_blind_spot` 欄位）。實測 `data_sufficient` 由 false 轉 true，79 個零流量 API 進入 8/31 判定候選。 |
| **Prevention** | 凡是「等資料累積到 N 就判定」的機制，上線時必須同時記錄**資料來源的上限**（保留期／取樣率／視窗），並在門檻 > 上限時直接報錯而不是報「資料不足」。判準：**一個永遠不會變綠的等待，和一個正在進行的等待，訊息必須長得不一樣。** |
| **Refs** | `scripts/checks/capability_usage_snapshot.py`（MIN_DATA_DAYS 註解記載完整推理）/ `CK_AaaP/platform/observability/docker-compose.yml`（prometheus 未設 retention）/ 同族：fitness `|| true` 恆印全綠、`fitness_weekly` 連 9 週 RED 無人知 |

---

## L80 — SSO 反覆回歸的底層＝「後端 token 生命週期層」：SSO 沒有可用的透明 refresh 路徑（前端不變式救不了 / 2026-07-21）
<!--enforced-by: scripts/checks/sso_ttl_ssot_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 編輯派工作業紀錄途中存檔 401「無效的認證憑證」白填；再問「多次修復仍有問題」。此前 7 週 10 次 SSO commit（L44/L66/L74/L78）全在**前端狀態機層**打轉仍反覆回歸。 |
| **Cause** | **反覆回歸是「兩層缺口的交集」，歷次只修 Layer 1**。Layer 2（後端 token 生命週期）從未被記錄：SSO **根本沒有無痛續命路徑**——四重疊加：①access token 與 `session.expires_at` 都綁同一 TTL（原 60min）→ 7 天 refresh cookie 被短 session 廢掉、過 TTL 後 refresh 對誰都必 401；②業務請求 stateful（每請求查 `user_sessions`）→ rotation 撤舊 session 瞬間、舊 token 即使 JWT 未過期也立刻失效；③rotation × 併發 × **雙 axios 實例各一把 isRefreshing 鎖** → 舊 token 二次用觸發 replay → 撤全 session → 401 風暴；④唯一復原 sso-bridge 是 `location.replace` 整頁跳轉丟失編輯，前端 `believedAuthed` 分支又直接 throw 不重試。另有跨 repo TTL 無 SSOT（IdP cookie 4h / Missive SSO 8h / idle 60min 三值不一致）。 |
| **Fix** | P0 止血（`0062769f`）：SSO access/session TTL 60min→8h（`SSO_ACCESS_TOKEN_EXPIRE_MINUTES`，僅 sso-bridge、local login 不弱化）+ refresh replay 5s 併發寬限（`REFRESH_REPLAY_GRACE_SECONDS`，不再誤殺全 session）；regression 6/6 + 既有 auth 51 綠、config 可逆。根治 P1-P4 路線見 retrospective §6。 |
| **Prevention** | (a) 後端五不變式 **I7–I11**（無痛續命 / 剛 rotation 的 jti 有 grace / rotation 併發寬限 / 跨 repo session TTL 單一 SSOT / session 存活期不被更短相依值廢掉），入 `SSO_RECURRING_REGRESSION_RETROSPECTIVE.md` v2。(b) 驗證協定新增 Layer 2 衰變狀態「編輯途中 token 過期存檔仍成功 / 併發不觸發全 session 撤銷」。(c) 建議 audit Rule E（跨檔三 TTL 一致）+ Rule F（raw fetch 無 session 守衛）。 |
| **Refs** | `docs/architecture/SSO_RECURRING_REGRESSION_RETROSPECTIVE.md` v2（兩層模型 + I1–I11）/ commit `0062769f` / `backend/tests/unit/test_sso_token_ttl_and_replay_grace_regression.py` / 疊加於 L74+L78（前端層）、L41（JWT 驗證）、L68（CSRF↔refresh） |

---

## L79 — Session 收尾不完整＝功能「存在於硬碟但不存在於系統」：寫好＋測試綠 ≠ commit ≠ 部署（2026-07-08）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 07-08 整體覆盤首查 `git status`，發現 07-07 session 的 LINE 推播主題合併（`line_digest_buffer.py` 新模組 + scheduler 4 job 改造 + 月度軟上限，測試 8/8 綠）**既未 commit 也未 rebuild 部署**——容器內完全沒有這些碼，功能零生效，且工作成果有丟失風險。 |
| **Cause** | Session 在「寫完＋測試綠」後中斷，未走**收尾三步：commit → 部署 → 驗證**。「測試通過」給了完成錯覺，但 host 碼 ≠ 容器碼（L51.7.1 同族）＋未版控＝雙重半接通（L30 環節不連通）。既有 step 60（image freshness）只對賬**已 commit** 的碼，抓不到「未 commit 的新工作」這條縫。 |
| **Fix** | 覆盤當日收口：審查（LINE 族回歸 28/28 綠）→ commit `05bdeddf` → rebuild `--no-deps` → L76 驗證（host/公網 200 + 容器內新碼 md5 確證）→ 容器內對真 Redis 做 queue/組稿/自清理 roundtrip 真活確認。 |
| **Prevention** | (a) **新 fitness step 65** `uncommitted_work_audit.py`：非 runtime 產物 modified/untracked 逾 12h → RED；modified backend/app py 檔 host↔容器 md5 對賬未部署 → RED（host 側跑，補 step 60 抓不到的縫）。(b) 每 session 收尾前跑一次 `git status`——非 wiki 異動即半接通信號。(c) 覆盤 SOP 首項＝查工作樹，先收口前次遺留再開新工作。 |
| **Refs** | `scripts/checks/uncommitted_work_audit.py`（step 65）/ commit `05bdeddf` / `backend/app/services/integration/line_digest_buffer.py` / 同族：L30 環節不連通 + L51.7.1 container image freshness + L76 部署後驗證 |

---

## L78 — 「今日 OK、明日又壞」＝復原路徑有多入口且散落破壞性副作用，happy-path 驗證必漏（SSO 反覆回歸元覆盤 / 2026-07-03）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 觀察 SSO「**今日 OK、明日又無法運作**」，7 週內約 10 次「根治」commit 仍反覆（L44/L66/L68/L74/`52053913`/`79e36c4d`…）。 |
| **Cause（元根因）** | ① **失敗永遠在「帶殘留狀態回來」的復原路徑，不在乾淨登入路徑**——無痕/headless 永遠過（happy path），但隔夜/重開機/token 過期/閒置登出後的**衰變狀態**走到不同分支。② 復原邏輯**多入口**（2 個 axios 實例的 401 handler + 2 條 sso-bridge 路徑），每個從**部分狀態**各自決定，修一個入口不等於修全部。③ 破壞性副作用（clearAuth/清 user_info/硬跳 login）**散落多處**。④ 護欄（step 64）allowlist **完全信任基礎設施內部** → 破口在被信任檔內時 audit 全綠＝假安全感。⑤ **驗證偏誤**：只在無痕/headless 測 happy path 就宣稱真活。 |
| **Fix** | 六不變式（見 retrospective 文件 §3）：I1 單一權威狀態 / I2 破壞性清除只在 anonymous / I3 每條 bridge 都寫 user_info / I4 副作用收歸唯一決策點 / I5 明確事件優先於被動檢查 / I6 多實例一致。audit 強化 Rule C/D 直掃基礎設施內部。驗證協定覆蓋衰變狀態（非只 happy path）。 |
| **Prevention** | (a) 「今日 OK 明日壞 / 無痕可以正常不行 / 重整就好」＝ bug 在**殘留狀態復原路徑**的指紋，驗證必須重現衰變狀態（token 過期/重開機/登出後立即重登）。(b) 盤點**所有** axios/fetch 實例 + **所有** login 成功路徑，逐一套 I2/I3。(c) audit 不可無條件信任「基礎設施」——對其內部的破壞性 401 與 bridge 持久化下規則。(d) **跨專案**：lvrland/pile/DigitalTunnel 同為 ck-sso 消費端，照 `SSO_RECURRING_REGRESSION_RETROSPECTIVE.md` §6 落地。 |
| **Refs** | `docs/architecture/SSO_RECURRING_REGRESSION_RETROSPECTIVE.md`（主文件）/ `scripts/checks/auth_state_ssot_audit.cjs`（step 64 Rule C/D）/ L74（技術細節）/ L66/L68/L69（同族累積）/ `adr-anti-half-wired-sop.md`（真活≠happy path）。 |

---

## L73 — In-container writer 盲視 host/cross-repo 資源 → silent 寫錯值（治理工具自身亦中招 / 2026-06-12）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 覆盤整體架構時連揪兩處同型：①治理 SSOT 儀表板 `GOVERNANCE_INTEGRATED_DASHBOARD.md` 的 §5 facade caller 全顯 `?`、§9.6 誤報 cron_events「不存在」（實有 11,312 筆）；② v7 metric `v7_soul_drift_lines` 長期回 `-1` sentinel。兩者都不是「沒寫」，是「寫的人看不到正確來源所以寫錯值」。 |
| **Cause** | **共通根因＝產出物由 in-container 程序生成，但程序需讀的資源在 host/別 repo（容器盲區）→ 寫出 0/`?`/-1 而非真值**（L52/L57 路徑漂移家族延伸）。①儀表板生成器由 in-container scheduler(cwd=/app)每日重生，卻寫死 host 佈局（`backend/logs`、`backend/app`、`~/.claude`、git repo）→ §5 facades 目錄解析失敗顯 `?`、§9.6 `LOGS_DIR` 漂移誤判不存在、§3/§4 silent 空白。②`v7_soul_drift` 唯一寫 `soul_drift_snapshot.json` 的是 in-container autobiography job，容器看不到 `../CK_AaaP/.../SOUL.md` → `hermes_lines=0`/`drift_lines=-1`，且**無條件覆寫**了本該由 host fitness 寫的真值；而 metric 註解聲稱「讀 host 端 fitness 寫的 snapshot」，但 host 端 `soul_mirror_drift_check.py`（看得到兩檔）**從未寫過該 snapshot**＝docstring 與實作斷鏈。 |
| **Fix** | ①生成器以 `_first_dir(backend/app, app)`／`_first_dir(backend/logs, logs)` 雙佈局解析 PKG_DIR/LOGS_DIR；§3/§4 容器情境改顯誠實標記（非 silent 空白）；新增 `governance_dashboard_completeness_audit.py`（daily fitness step 9/9）抓 `?`／「不存在」回退。②`soul_mirror_drift_check.py`（host fitness step 3，看得到兩個 SOUL.md）新增 `write_drift_snapshot()` 寫真值（drift 190−153=**37**）；in-container `_refresh_soul_drift_snapshot` 改為「看不到 CK_AaaP 時保留既有 snapshot 的 hermes_lines/drift_lines、只刷新 missive_lines」，不再 clobber host 真值。修後 metric 15 分鐘內由 -1→37（誠實揭露真實跨通道人格漂移，遠超目標 ≤5）。 |
| **Prevention** | (a) 凡「報表/metric 產出物」由 cron 在容器內生成，須在**真實執行情境**驗「區段/欄位有真值」，非只看 cron GREEN（L62 整合＝持續驗證）。(b) 產出物依賴的資源若在 host/別 repo，writer 必須是看得到該資源的那一端（host fitness），in-container 程序看不到時應**保留**既有真值而非覆寫成 0/-1。(c) sentinel（-1/`?`/0）必須有 audit 監看「卡在 sentinel」本身＝故障，否則 silent 永久失真。(d) docstring 聲稱「讀 X 寫的檔」必須確認 X 真的在寫（同 L01 Dead Doc）。 |
| **Refs** | `scripts/checks/generate_governance_dashboard.py`（PKG_DIR/LOGS_DIR）/ `scripts/checks/governance_dashboard_completeness_audit.py`（fitness daily 9/9）/ `scripts/checks/soul_mirror_drift_check.py`（write_drift_snapshot）/ `backend/app/core/scheduler.py` `_refresh_soul_drift_snapshot`（preserve）/ `backend/app/core/memory_wiki_metrics.py:316-345` / 同族 L52 paths drift + L57 BACKEND_DIR mount + L62 持續驗證 + L01 Dead Doc |

---

## L72 — 排程「註冊 ≠ 真在跑」：scheduler liveness 對賬揪 silent dormant cron（擴大治理至坤哥/Hermes/排程 / 2026-06-12）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner：擴大圖譜檢核至坤哥/Hermes agents/排程。排程是 silent dormant 重災區（L52 paths drift、silent cron 四層防禦）。「`add_job` 註冊了」不代表「真的每天在跑」。 |
| **Cause** | `scheduler_liveness_audit` 對賬 `@tracked_job('X')` id × `cron_events.jsonl` 揭 4 dormant，深查發現**雙重真因**（非單純觀測缺口）：**(1) 02:00 misfire skip** — `security_scan`/`cleanup_events`/`fitness_daily` 排 `hour=2,min=0` 但**缺 `misfire_grace_time`**（其他治理 cron 皆 7200s）→ 02:00 多 job 壅塞、event loop 忙 → 這幾個 misfire 直接 skip、從不觸發（02:00 時段他 job 有 fire 唯獨這 3 個 0 次坐實）。**(2) security_scan 內部 crash 被吞** — 即使觸發，`scanner._scan_code_patterns` 的 `BACKEND_DIR.rglob("*.py")` 從 `/app` 遞迴進掛載 `/app/backups`（Windows mount 附件檔）→ `[Errno 5] I/O error` 在 `list()` 物化時崩潰（L49.2 同族），但 job 層 try/except 吞錯回報 success → **掃描跑了卻 0 實效**（silent 功能失效）。`einvoice_sync` 為 `if MOF_APP_ID` 條件式（未設＝刻意停用，非 bug）。坤哥/Hermes 核心 cron 皆 alive。 |
| **Fix** | **(1)** `security_scan`/`cleanup_events`/`fitness_daily` add_job 補 `misfire_grace_time=7200`（對齊其他治理 cron，02:00 壅塞不再 skip）。**(2)** `scanner._scan_code_patterns` 改 `os.walk(source_root, onerror=...)` 容錯遍歷 + 只掃源碼 `app/` + prune backups/uploads/logs/attachments（防 rglob 崩潰）→ **驗證修後 total=9/high=8/1.9s 真實掃描**（原 crash 0 結果）。**(3)** `scheduler_liveness_audit.py`（fitness 57f）持續對賬防復發。後續：統一 @tracked_job id = add_job id（消 3 命名不符）。 |
| **Prevention** | (a) 凡排程 job 必經 `@tracked_job` 且 id 與 add_job 一致 → liveness 可對賬。(b) 條件式註冊（env-gated）job 應於 audit 標註「conditional」非 dormant。(c) 「啟動 log 有加入」≠「真執行」≠「真完成工作」三層須分別驗證（healthcheck≠functional 同理）。 |
| **Refs** | `scripts/checks/scheduler_liveness_audit.py` / `backend/app/core/scheduler.py` tracked_job 裝飾器 + SchedulerTracker → cron_events.jsonl / 同族 L52 cron paths drift + silent cron 四層防禦 + L70 runtime 對賬 |

---

## L71 — 程式圖譜是「結構地圖」抓不到 config/語意/runtime 三類問題 → 用 AST 橋接治理（2026-06-11）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 質疑：「已建立程式圖譜，為何還是有多重標準與架構問題（config drift、3 套命名、synced 但 Google 空）？」 |
| **Cause** | 程式圖譜（10,810 code entities）建模**程式結構**（function/class/module + call/import/AST 邊），但本次三類問題**與結構正交**：① **config/值一致性**（GOOGLE_CALENDAR_ID/REDIRECT_URI/MAX_OVERFLOW）是 `.env`↔`compose`↔`config 預設` 三種**不同檔型**間的同名 key 一致性，非 code 邊；② **語意/契約重複**（3 套標題 builder）圖譜有節點+call 邊但無「同概念應收斂」的語意邊；③ **runtime/資料狀態**（synced≠real、孤兒）圖譜建模程式碼非資料狀態，且「公文提醒:」由**已移除程式**產生→根本無節點。真正防線是 fitness functions，但用**寫死清單**漏 GOOGLE_CALENDAR_ID；圖譜與 fitness **未連動**。 |
| **Fix** | **橋接圖譜→治理（三層補強）**：① **AST 衍生 config audit**（`config_settings_drift_audit.py` fitness 57b）：AST 掃描 backend/app **所有** `getattr(settings,'X')`/`settings.X` 讀取（取代寫死清單）× config 預設 × .env × compose 比對 → 立即補抓 GOOGLE_REDIRECT_URI(localhost 預設)+MAX_OVERFLOW(.env20≠30)，全補注入 RED→0。② **命名 SSOT 強制 audit**（`calendar_title_standard_audit.py` fitness 57c）：自動建立事件須符 2 套 SSOT 前綴，揪競爭/遺留格式。③ **狀態對賬**（規劃）：週期抽樣 DB status vs 外部真實（synced≠real 類）。 |
| **Prevention** | (a) **圖譜≠治理**：結構圖譜須「餵養」fitness（AST→audit 清單），勿靠人工寫死。(b) 凡跨檔型一致性（env/yaml/python 同名 key）、競爭實作、寫一次不再驗的 status 欄 → 各需專屬 audit，圖譜不會自己抓。(c) 同型推廣全系統非僅日曆：finance/integration/tender 等所有 `getattr(settings)` 讀取已納入 57b 全域掃描。 |
| **Refs** | `scripts/checks/config_settings_drift_audit.py` (AST 衍生) / `scripts/checks/calendar_title_standard_audit.py` / `run_fitness.sh` step 57b/57c / 同族 L70 calendar drift + L51 env 注入 + L31 ROI（建表≠用表，建圖譜≠治理） |

---

## L70 — GOOGLE_CALENDAR_ID config-drift：1044 事件靜默推進「服務帳號私人日曆」無人可見（L51 同族 / 2026-06-11）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 報「公司 Google 日曆（cksurvey0605）根本看不到任何 Missive 同步事件」（指名霄裡公園 6/15）。但 DB `document_calendar_events` 顯示 1029 筆 `synced` + 有 google_event_id。服務帳號直查共享日曆 `6a3478...`：抽樣 6/6 全 **404 不存在**；該日曆 ACL owner 含 cksurvey0605 + 服務帳號（存取權正確）。 |
| **Cause** | **config drift（L48/L51 同族）**：`.env` 有 `GOOGLE_CALENDAR_ID=6a3478...@group.calendar.google.com`，但 `docker-compose.production.yml` backend `environment:` **未注入此 key**（無 `env_file: .env`，逐項顯式注入卻漏了它）→ 容器退回 `config.py` 預設 `GOOGLE_CALENDAR_ID='primary'`。服務帳號的 `'primary'` = **服務帳號自己的私人日曆**（無任何人類帳號能看）→ 1044 事件全推進隱形日曆。「之前皆正常?」其實**從未對人類生效**。fitness step 1 `container_env_alignment_audit` 雖存在但 GOOGLE 群組只查 CLIENT_ID/SECRET、**漏 GOOGLE_CALENDAR_ID** → drift 漏網。 |
| **Fix** | (1) compose backend `environment:` 補 `- GOOGLE_CALENDAR_ID=${GOOGLE_CALENDAR_ID:-primary}` → recreate（`--no-build` 保 baked code）。(2) `.env` 的 `GOOGLE_CREDENTIALS_PATH` 原為 Windows 絕對路徑且被 mojibake 註解吞掉（從未生效）→ 拆乾淨行 + 改相對 `./GoogleCalendarAPIKEY.json`。(3) **擴充 `container_env_alignment_audit` GOOGLE 群組納入 GOOGLE_CALENDAR_ID**（治本防回退，現 GREEN）。(4) 全量 reset 1043 synced/failed→pending、經 app 同步路徑重推到 6a3478（驗證 1044/1044 synced、抽樣 Google 端真存在）。 |
| **Prevention** | (a) 凡 `config.py` 會讀、host `.env` 有設、但 compose 未注入的 key 一律 audit RED（已落地 step 1）。(b) **`is_ready=True` ≠ 同步真活**：healthcheck 只驗服務帳號載入，不驗「目標日曆對不對 / 事件 Google 端真存在」→ 建議加 calendar-sync 診斷（顯示生效 calendar_id + 日曆名 + 抽樣 reconciliation）。(c) **synced 狀態從不回頭驗證** → 整批 Google 端消失/錯地無人偵測；建議定期抽樣對賬。(d) 服務帳號 'primary' 是隱形陷阱：永遠顯式指定共享日曆 ID。 |
| **Refs** | `docker-compose.production.yml` backend env (GOOGLE_CALENDAR_ID) / `backend/app/services/calendar/google_client.py` (calendar_id 預設 'primary') / `scripts/checks/container_env_alignment_audit.py` GOOGLE 群組 / 同族 L51 google_client_id 注入 + v6.13 OLLAMA_BASE_URL/PGVECTOR drift + L52/L57 paths drift / 服務帳號 `ck-missive-calendar@...iam.gserviceaccount.com` |

---

## L69 — secureApiService single-flight 讓並發共用「單次」CSRF token → nav 選單 403（修 L49 反效果 / 2026-06-11）
<!--enforced-by: scripts/checks/auth_state_ssot_audit.cjs-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 報「登入後點導覽選單出錯、重整可運作」（不定期 / 特定頁面）。後端 log 16:24 `POST /secure-site-management/navigation/action - 403「Invalid or expired CSRF token」`。注意 console 的 `Unchecked runtime.lastError: Could not establish connection` 是**瀏覽器擴充噪音**（前端零 chrome.runtime/SW），非 app。 |
| **Cause** | `navigation/action`（連 `'list'` 載側欄都走）用 `secure_site_management` 的 **Redis 單次 CSRF token**（`common.py` 1h TTL、用後即焚），與 L68 的 cookie 雙提交是不同機制。`secureApiService` L49 加了 **single-flight inflight promise** 想省 token 請求，但副作用：並發 caller（useNavigationData 載側欄 + navigationService/SiteManagement 載設定）共用「同一張」單次 token → 第一個用掉後第二個必 403。reload 重抓新 token 才好。L49 註解本身點出「並發共用 token 必有 1 個 403」卻用 single-flight 造成它要防的事。 |
| **Fix** | 移除 `getCsrfToken` 的 single-flight dedupe → 每個 secureRequest 各拉一張獨立 single-use token（`secureApiService.ts`）。保留既有 403 retry 作安全網。 |
| **Prevention** | (a) **single-use 資源不可用 single-flight 共用**：dedupe inflight 僅適用「可共享結果」的請求。(b) 凡「reload 就好」的 race，先查是否並發共用了一次性資源。(c) 403 應區分 CSRF（提示重新整理）vs 真權限（L68 Prevention c 已落地）。 |
| **Refs** | `frontend/src/services/secureApiService.ts` getCsrfToken（移 single-flight）/ `backend/app/api/endpoints/secure_site_management/common.py` Redis 單次 token / `navigation.py:108` validate_csrf_token / 同類 L68 cookie CSRF + v6.13 raw fetch 漏 header |

---

## L68 — CSRF refresh 死結：csrf cookie 過期→refresh 被 CSRF 擋→全站 403「權限不足」（OWASP / 2026-06-10）
<!--enforced-by: scripts/checks/auth_state_ssot_audit.cjs-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 報手機登入網站「**權限不足**」（OWASP CSRF 關注弱點）。伺服器端模擬四情境 + 後端 log 證據：(A) 純匿名 users/list 容器內 localhost 200〔內網免認證副作用，PII 外露另記〕(B) access_token cookie + 無 csrf cookie → 403「缺少 csrf_token cookie」(C) 有 csrf cookie + 無 X-CSRF-Token header → 403「缺少 X-CSRF-Token header」(D) 兩者一致 → 認證層 401。DB 證 owner 兩帳號（jujuiacc superuser / luke admin）**皆 admin** → 403 與權限無關。`[CSRF]` warning log 實證 B+C 都發生於 `users/list` 與 **`/api/auth/refresh`**。 |
| **Cause** | **死結**：`csrf_token` cookie 固定 `max_age=3600`（1h），`access_token` 可透過 `/auth/refresh` 續命，兩者生命週期不對齊。csrf cookie 過 1h 後，前端要 refresh 續命——但 (1) `/api/auth/refresh` **不在 `CSRF_EXEMPT_PATHS`** (2) 前端 refresh 用**裸 `axios.post`（`interceptors.ts:321`）繞過 request interceptor** 從不帶 X-CSRF-Token (3) 此刻 csrf cookie 已消失、interceptor `if(csrfToken)` gate 也讀不到 → refresh 被 `CSRFMiddleware` **403** → token 無法續 → `set_auth_cookies` 無法重發 csrf cookie → 後續全站 mutating 403 → `GlobalApiErrorNotifier` 把所有 403 **誤標「權限不足」**。手機 iOS Safari cookie 處理更易丟失而加劇。 |
| **Fix** | **(後端)** `/api/auth/refresh` 加入 `CSRF_EXEMPT_PATHS`（`csrf.py`）— `refresh_token` cookie 為 `httpOnly + samesite="strict"`，跨站請求不會帶上 → **已自帶 CSRF 防護**（與 login/google bootstrap 同理、OWASP 認可的 token-less 防護，非放寬安全）。**(前端)** request interceptor 改 async 自癒（`interceptors.ts`）：mutating 請求遇 csrf cookie 缺失且已登入(user_info)時，先補打已豁免的 `/secure-site-management/csrf-token`（`security.py:32` `set_csrf_cookie` 設全域 csrf cookie）重取再送；用裸 axios 防遞迴、same-origin 才能補→不削弱防護。 |
| **Prevention** | (a) 凡 **token-refresh / bootstrap endpoint 用 samesite=strict cookie 認證者必豁免 CSRF**，否則 csrf 過期即成死結。(b) csrf cookie 生命週期須 ≥ access_token 可續期上限，或 refresh 流程主動重發 csrf。(c) **`GlobalApiErrorNotifier` 應區分 403-CSRF（detail 含「CSRF」→ 提示重新整理）vs 403-權限**，避免「權限不足」誤導 owner 往權限方向排查（本案誤導成本高）。(d) CSRF 修法**必雙向驗證**：豁免項生效 + 其他項仍強制 403（防全面放寬）。(e) 跨 repo：lvrland/pile 若同採 cookie+header 雙重提交 CSRF，應檢查 refresh 是否同型死結。 |
| **Refs** | `backend/app/core/csrf.py` CSRF_EXEMPT_PATHS（refresh 豁免）/ `frontend/src/api/interceptors.ts` request interceptor 自癒 / `backend/app/api/endpoints/secure_site_management/security.py:32` csrf-token endpoint / 模擬 4 情境 + `[CSRF]` warning log / OWASP CSRF Prevention Cheat Sheet（SameSite）/ 同類 v6.13 raw fetch 漏 CSRF header + L66 self-heal gate |

---

## L66 — 跨子域 SSO 消費端 self-heal gate 漏掉 cookie-session（顯示「訪客」race / 2026-06-10）
<!--enforced-by: scripts/checks/auth_state_ssot_audit.cjs-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 報 `missive.cksurvey.tw` SSO 登入後停在「訪客」、`localStorage.user_info=NULL`，**reload 即恢復**。實查後端 log：owner Chrome 同源 POST `/api/auth/sso-bridge` 當日 **08:47/08:52/09:08 三次皆 200 登入成功**（cookie `ck_employee`/`ck_employee_rs` 帶到、RS256 JWKS 驗過、session 建立、回傳 user_info）。`POST 200×4 / 401×84` 之 401 **全為每 15 分鐘一次的 curl 探針**（`cookies=[]`，noise）。→ 後端 100% 健康，純前端顯示層。 |
| **Cause** | EntryPage SSO 成功後用 `window.location.replace('/dashboard')` 整頁重載（已為 cookie 競態修過）；但 `useNavigationData` 的 **self-heal gate 只看 `localStorage.access_token / refresh_token`**。SSO bridge 的 token 主要在 **httpOnly cookie**，localStorage 不一定有 JWT → self-heal 不觸發。整頁重載瞬間若 lazy-init 偶發漏讀 `user_info`（setItem 緊接 navigation 的瀏覽器級競態）就無兜底 → 只能手動 reload。屬「後端真活 + 前端 state 未補水」。 |
| **Fix** | `useNavigationData.tsx:87` self-heal gate 擴納 `csrf_token` cookie（登入後後端設的 **non-httpOnly** 訊號、SSO bridge 亦設、前端可讀）作為「session 真活」判據 → 任何寫入/導向競態下只要後端 session 還在即用 `/auth/me` 補水，免手動 reload。未登入者無 csrf_token → 不觸發 `/auth/me`（保留 F21 不在登入頁死循環）。後端 `sso_bridge.py` 不動（健康）。 |
| **Prevention** | (a) **跨子域 SSO 消費端的「已登入」判據不可只看 localStorage JWT** — httpOnly cookie 場景必須有 non-httpOnly 訊號（csrf）或 cookie-session 作 self-heal 兜底。(b) 「顯示訪客」類 race 的 self-heal gate 要涵蓋**所有合法 session 來源**。(c) 跨 repo：`CK_lvrland_Webmap` / `CK_PileMgmt` 同為 ck-sso 消費端，應同步檢查各自前端 self-heal gate 是否同型漏洞。 |
| **Refs** | `frontend/src/components/layout/hooks/useNavigationData.tsx:87` (gate 擴充) / `frontend/src/pages/EntryPage.tsx:217` (replace 重載) / `backend/app/api/endpoints/auth/sso_bridge.py` (RS256 優先/HS256 fallback，健康) / 同類 L44 SSO session lock + L41 JWT secret drift |

---

## L67 — 前端 baseURL 已含 `/api` 卻硬編 `/api` 前綴 → double-prefix 404（半接通 / 2026-06-10）
<!--enforced-by: scripts/checks/auth_state_ssot_audit.cjs-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 報「**排程追溯仍無相關紀錄**」。實查：`cron_events.jsonl` 寫入正常（**9454 筆、最新數分鐘前**）；router 有掛載（`routes.py:59-60`，openapi 含 `scheduler/events` + `retrospective/reports`）；容器內實測 `events=200 / stats=200`。但前端表格空。 |
| **Cause** | apiClient `baseURL = getDynamicApiBaseUrl()` **已含 `/api`**（`config/env.ts:20`，全專案 endpoints 常數慣例皆**不含** `/api`，如 `LOGIN:'/auth/login'`）。但 `SchedulerEventsPage.tsx` 4 處 `apiClient.get` **硬編 `/api/admin/...`** → 實際請求 `/api/api/admin/scheduler/events` → 404 → React Query `data` 空 → 表格 `?? []` 顯示「無紀錄」。屬「cron 真寫 + router 真掛 + 前端頁存在，斷在 URL 前綴」的**半接通**（ADR anti-half-wired 同型）。 |
| **Fix** | 移除 4 處硬編 `/api` 前綴（`/api/admin/...` → `/admin/...`，`:55/64/73/90`），對齊全專案 endpoints 慣例。後端與 cron 不動（皆健康）。 |
| **Prevention** | (a) 前端呼叫**一律用 `endpoints/*.ts` 常數**，禁硬編路徑字串；(b) 若必須硬編，**禁帶 baseURL 已含的 `/api` 前綴**；(c) 可加 fitness/lint：grep `apiClient\.(get\|post).*['\x60]/api/` 視為候選錯誤；(d) 新頁面 PR review 必查「200 但畫面空」→ 先驗 Network 實際 URL 是否 double-prefix。 |
| **Refs** | `frontend/src/pages/SchedulerEventsPage.tsx:55/64/73/90` / `frontend/src/config/env.ts:20` / `frontend/src/api/interceptors.ts:61` getDynamicApiBaseUrl / 同類 `.claude/rules/adr-anti-half-wired-sop.md` 半接通防範 |

---

## L64 — LINE 推播鏈交易污染復發（吞錯不 rollback + 缺方法 + 重複掃描 / 2026-06-03）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 夜間吹哨者 + 標案訂閱的 LINE 推播 silent 全失敗。`backend-error.log` 自 2026-05-25 起每日 08:00/18:00 各一筆 `'LineBotService' object has no attribute 'broadcast_to_admins'`（dormant ~9 天）。整條「proactive scan → LINE 推播」鏈 silent 死。 |
| **Cause** | **三個 silent failure 疊加**：(1) `subscription_scheduler.py:124` 呼叫 `line_service.broadcast_to_admins(...)` 但 `LineBotService` 從未定義此方法 → AttributeError 被 `except: warning` 吞 (2) `proactive_triggers.py` `check_recommendations` / `predict_risks` except 吞錯**未 rollback** → 污染共用 `self.db`，後續 query 全撞 `InFailedSQLTransactionError` — **此為 2026-01-09 `BUGFIX_TRANSACTION_POLLUTION` 同型復發**（feedback_rigor「反覆基礎錯誤」）(3) `scheduler.py proactive_trigger_scan_job` 在 `base_service.scan_all()`（內部已掃 ERP，`proactive_triggers.py:66-69`）後又獨立 `ERPTriggerScanner(db).scan_all()` 重掃 → ERP alert 雙份 + 第二次用同 session 撞交易錯，整個 job 在 LINE 推播段前 raise。 |
| **Fix** | (a) `line_bot.py` 補 `broadcast_to_admins()`（讀 `LINE_ADMIN_USER_ID`，與 `line_push_scheduler` fallback 一致）(b) `proactive_triggers.py` 兩處 except `logger.debug`→`warning` + `await self.db.rollback()` (c) `scheduler.py` 移除重複 ERP 掃描，只留 `base_service.scan_all()` (d) regression lock `tests/test_line_push_chain_regression.py`（8 tests：方法存在性 + 呼叫端契約 + rollback 行為 + scheduler 不重建 ERPScanner）(e) fitness step 63 `transaction_pollution_audit.py`（baseline 59 候選）。 |
| **Prevention** | (a) 任何「吞錯」except 內若 try 對共用 `self.db` 做過 DB 操作 → **必 rollback 或 re-raise**（step 63 月跑防復發）(b) 跨 service 被呼叫的方法名納入 regression 契約測試（鎖 AttributeError）(c) 聚合型 `scan_all()` 自帶子掃描時，呼叫端**不得**再獨立重掃同一子 scanner（雙份 + 同 session 撞錯）(d) silent failure 修復一律附 `test_*_regression.py`（ADR-0028）。 |
| **Refs** | `backend/tests/test_line_push_chain_regression.py` / `scripts/checks/transaction_pollution_audit.py`（step 63）/ 同型復發源 `docs/archived/legacy/reports_202601/BUGFIX_TRANSACTION_POLLUTION_20260109.md` / 同類 L29 silent-except 家族 + ADR-0021 asyncpg 單飛 + ADR-0028 錯誤合約 |

**L64 子案 B — synthesis fallback 模型 SSOT（同批 06-03，commit `28a29939` / `dc9b6f98` / `42bdf2ea`）**

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner 經 LINE/web 查業務問題（如「桃園市工務局相關公文」）得「AI 回答生成超時，請參考上方查詢結果」——工具有跑（`get_statistics` 等）但生成層 fail。 |
| **Cause** | synthesis 路徑外層僅 35s budget（`TIMEOUTS.synthesis`，`agent_synthesis.py:176`）。`chat_completion(task_type="synthesis")` fallback 鏈 Groq→NVIDIA→Ollama：Groq 429/TPM 頂（不重試）→ NVIDIA 預設 30s 慢失敗 → 落本地 Ollama 時 budget 已近耗盡；且 `"synthesis"`/`"vision"` 原不在 `TASK_MODEL_MAP` → 落 `OLLAMA_DEFAULT_MODEL`（prod=`qwen2.5:7b`，p50 52.8s）→ 35s 必超時。與 vision 發票 OCR silent 退 QR 同型（`task_type` 漏映射）。 |
| **Fix** | (a) `ai_connector.py TASK_MODEL_MAP` 補 `"synthesis"→gemma4:e2b`、`"vision"→gemma4:e2b`（快模型，~7s < 35s）(b) synthesis 路徑 NVIDIA timeout 縮至 8s（`NVIDIA_SYNTHESIS_TIMEOUT`，`ai_connector.py:436`）保證本地 fallback 仍有時間 (c) regression lock `backend/tests/unit/test_synthesis_fallback_model.py`。 |
| **殘留** | Groq 429 高頻 + GPU `semaphore=3` 併發 burst 下 gemma4 單筆 ~7s 但 burst 達 ~24–32s，仍可能擦 35s 邊（commit `42bdf2ea` 自述 elapsed=32s；當前 diary 19:15 仍見 latency 51s 超時）。**治本＝Groq TPM quota 升級（owner 層）或 synthesis 降低對 cloud 依賴**，非 Missive code 可獨力解。 |
| **Prevention** | `TASK_MODEL_MAP`（任務→模型）為跨檔 SSOT：新增任一 `task_type` 且其 fallback 會落本地 Ollama 時，**必確認對應本地模型夠快（< 該 task 的 timeout budget）**，否則 cloud 失敗即 silent 超時。應納入 `cross-file-ssot-governance.md` 規則 1 表。 |

---

> **回填註記（2026-06-03）**：L51–L63 原僅存於 `wiki/memory/lessons/{universal,missive-specific}/` 個別檔，
> 中央 registry 缺索引列 → SSOT 漂移。以下回填精簡索引列（完整內容見各 Refs 檔）。

## L63 — 學習閉環需 aging alert 才能突破 owner 健忘（2026-05-31）
<!--enforced-by: scripts/checks/proposal_aging_alert.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | 5/31 self-retro RED：學習閉環 flow=0% / crystals=0 / 5 proposal pending（最老 40 天）。|
| **Cause** | 自動化做到 trace→pattern→proposal，但 proposal→crystal 是 owner approve hard gate → owner 健忘/決策成本高 → 永遠 pending。|
| **Fix** | proposal_aging_alert cron（>=7d 主動 LINE 推 owner）+ 凌晨化排程，突破健忘。|
| **Prevention** | 任何「依賴人工 approve」的閉環必配 aging alert + 主動推播，否則 silent 卡死在 manual gate。|
| **Refs** | `wiki/memory/lessons/universal/L63_learning_loop_requires_aging_alert.md` / 同類 L62 |

## L62 — 整合連通 = 持續驗證機制，不是一次性 endpoint（2026-05-31）

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner「整合優化期待突破性成長 非一次性成功」；v6.6/6.7/6.12 多次加整合 endpoint 但「寫好放著」無持續驗證 → 任一鏈 silent dormant 無人發現。|
| **Cause** | 把「整合」當一次性交付（寫 endpoint→skill→commit→完成），缺「驗證鏈本身也是 cron + fitness step」。|
| **Fix** | 5 鏈 E2E 驗證 script + cron 每日跑 + 任一鏈斷自動 LINE + health marker + 驗證鏈本身納 fitness step（step 62）。|
| **Prevention** | 整合連通的交付定義升級：endpoint + skill + **E2E 驗證 cron + 斷鏈告警 + 驗證鏈自身 fitness**。|
| **Refs** | `wiki/memory/lessons/universal/L62_integration_continuous_validation_not_one_shot.md` / `scripts/checks/integration_e2e_validation.py`（step 62）|

## L61 — 下游反治理（PileMgmt R18 案例 / L60 真活驗證範本）（2026-05-31）
<!--enforced-by: scripts/checks/cross_repo_template_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | L60 立法後 PileMgmt 真活反治理 commit `2a51d57b5`（跨 repo 污染守門）案例研究。|
| **Cause** | 上游強推範本 → 下游需「反治理」守門（防 CK_Missive 特定內容污染 sibling repo）。|
| **Fix** | PileMgmt 新增 `test_no_missive_contamination.py` 兩層守門（檔名/目錄禁帶 + 內容指紋掃描）+ fork-contract.md 邊界文件化 + pre-push enforce。|
| **Prevention** | 下游 repo 對上游範本有「反治理守門」權；污染守門用內容指紋（非裸字）避誤報合法跨 repo 引用。|
| **Refs** | `wiki/memory/lessons/universal/L61_downstream_reverse_governance.md` / 同層 L58/L59/L60 |

## L60 — 平衡 = 結構正常化（非中間值）（2026-05-30，meta-治理第 8 句立法）
<!--not-enforceable: 這是行為準則，本質上無法用檢核防範 —— 它要求的是動手前先做某件事（先驗、先問、先核實），而機器看不到「有沒有先想過」。靠 review 與這份紀錄本身。-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner 追問「如何取得治理平衡」；同日 PileMgmt 自然回滾 install-template 真活驗證。|
| **Cause** | 把「平衡」誤解為中間值/折中，實際應是每層各司其職 + 明確邊界 + 動態調整。|
| **Fix** | ROI 公式 5 維度延伸 + 範本分級 L1/L2/L3 + 下游反治理權（與 L58/L59 三位一體）。|
| **Prevention** | 治理強度不取中間值；以「結構正常化」（角色邊界正確）為目標，動態調整而非固定比例。|
| **Refs** | `wiki/memory/lessons/missive-specific/L60_balance_via_structural_normalization.md` |

## L59 — 治理架構倒置（上游 meta 缺 audit / 業務 source 反向 audit 子專案）（2026-05-30）
<!--enforced-by: scripts/checks/cross_repo_template_drift_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | CK_AaaP 名義 meta-governance index，但治理成熟度落後它索引的 source（CK_Missive 88 audit vs AaaP 0 scripts/checks）。|
| **Cause** | 「該是」CK_AaaP→各 repo，「實際」CK_Missive→4 子專案（反向）。上游只定 standard 不 enforce。|
| **Fix** | 立法第 7 句：meta 上游須自帶 audit；治理方向校正（v6.12 路線）。|
| **Prevention** | meta-governance repo 必須有 enforce 機制（非只定 convention）；否則治理方向倒置。|
| **Refs** | `wiki/memory/lessons/missive-specific/L59_governance_architecture_inversion.md` |

## L58 — 治理範本污染風險（強推 132 檔 57% 為本專案特定）（2026-05-30）
<!--enforced-by: scripts/checks/module_portability_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner 反思「CK_Missive 平台治理範本變成其他專案污染源」；install-template 132 檔強推 4 子專案。|
| **Cause** | 132 檔僅 33% 真普適（L1），57% 是 CK_Missive 特定（L3：Facade B / Hermes baseline / daily_self_retrospective）；強推 L3 = 語意/規範/觀測污染。|
| **Fix** | 範本分級 L1（普適）/L2（可選）/L3（本專案專屬不外推）+ 立法第 6 句。|
| **Prevention** | 跨 repo 範本必分級；只強推 L1 普適層，L3 專屬層禁外推。|
| **Refs** | `wiki/memory/lessons/missive-specific/L58_governance_template_pollution.md` / 同類 L54 |

## L57 — BACKEND_DIR/logs vs compose mount 子路徑漂移（L52 family 第七案）（2026-05-30）

| 欄位 | 內容 |
|---|---|
| **Trigger** | shadow_baseline_rows_total 卡 0-2，cron 跑不累積；深挖 4 層 silent 疊加。|
| **Cause** | `shadow_logger` 用 `BACKEND_DIR/logs`（=/app/backend/logs）但 compose mount 是 `/app/logs` → 寫入路徑 drift，5/21→5/30 silent dormant 9 天。|
| **Fix** | commit `5ca1d720` 對齊 mount target；揭發配套 `metrics_populate_errors_total` / `scheduler_job_last_run_age_seconds`。|
| **Prevention** | paths.py **子路徑**（BACKEND_DIR/LOGS_DIR）也須與 compose mount 對齊（fitness step 69 `paths_subpath_mount_audit`）。|
| **Refs** | `wiki/memory/lessons/universal/L57_backend_dir_logs_vs_mount_drift.md` / 母案 L52 |

## L54 — 跨 repo 套用 ≠ 落實（install-template apply vs commit gap）（2026-05-30）
<!--enforced-by: scripts/checks/cross_repo_uncommitted_audit.py-->

| 欄位 | 內容 |
|---|---|
| **Trigger** | install-template 對 4 子專案套用完 → drift audit GREEN，但各 repo 實際有 staging changes 待 commit（lvrland 38 / pile 26 / showcase 1）。|
| **Cause** | audit 只看「檔案存在/內容一致」，未驗證「已 commit」→ 套用即綠但未落實。|
| **Fix** | audit 加 git status 檢查；fitness step 區分 applied vs committed。|
| **Prevention** | 跨 repo 採用度定義 = 套用 + **commit** + import 不報錯（非僅檔案落地）。|
| **Refs** | `wiki/memory/lessons/missive-specific/L54_cross_repo_apply_vs_commit_gap.md` / 同類 L41「採用」定義 |

## L53 — Facade over-engineering 30 天實證裁判（ADR-0036 ROI 失敗）（2026-05-30）

| 欄位 | 內容 |
|---|---|
| **Trigger** | fitness step 61 facade_adoption_audit 揭發 13 facade 中 10 個 zero caller（平均 0.46/facade）。|
| **Cause** | v6.10 P1 設想「平均 ≥3 caller/facade」，30 天實測 0.46 → 抽象層建好沒人用 = over-engineering（L31 ROI=entities×usage_rate 第一個負面案例）。|
| **Fix** | B 方案收口 13→3（-1509 行 / 補強 3 active + 廢 10 zero），3 active 留 60 天 trial（2026-07-30 重評）。|
| **Prevention** | 抽象層必設 caller 門檻 + 定期 audit 裁判；ADR 假設→audit 裁判→lesson 傳承閉環（L31 第一個正面執行案例）。|
| **Refs** | `wiki/memory/lessons/missive-specific/L53_facade_over_engineering_30day_pruning.md` / `feedback_stop_overengineering` / ADR-0036 |

## L52 — paths.py PROJECT_ROOT vs compose mount target 漂移（L4x family 第六案）（2026-05-30）

| 欄位 | 內容 |
|---|---|
| **Trigger** | fitness step 58 agent_query_starvation RED 持續，發現 cron synthetic_baseline silent return（shadow_baseline 24h n=0）。|
| **Cause** | 加 `CK_PROJECT_ROOT=/app` env override 後 paths.py 算出 `/app/scripts/checks/...`，但 `docker-compose.production.yml` mount target 還是舊值 → cron 找不到 script → silent return。|
| **Fix** | 對齊 compose mount target + token fallback；fitness step 62 `paths_compose_mount_audit`。|
| **Prevention** | paths.py PROJECT_ROOT 變更必同步檢查所有 compose mount target prefix（cross-file SSOT）。|
| **Refs** | `wiki/memory/lessons/universal/L52_paths_compose_mount_drift.md` / 同 family L41/L43/L44/L45/L57 |

## L51 — Container image freshness family（L51.5/L51.7 系列，2026-05-30）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 多個 sub-case：L51.5 `GOOGLE_CLIENT_ID/SECRET` 未注入容器（Google 登入 silent 503 風險，commit `ba59b020`）；L51.7 container image content vs git HEAD drift（incident #8）。|
| **Cause** | 容器 image 內容/env 與 host git HEAD 漂移 — 改 host 檔但容器未 rebuild / compose 未注入 host .env 已存的值。|
| **Fix** | fitness step 60 `container_image_freshness_check` + compose 補注入 env；L51 family 散見 v6.12 commits。|
| **Prevention** | 容器內容 SSOT = git HEAD `backend/`；env SSOT = host `.env` 必經 compose 注入（cross-file-ssot-governance 規則 1）。|
| **Refs** | run_fitness step 60 / MEMORY.md L51.5+ 條目 / 同 family L52/L57 |

---

## L50 — Multi-source identifier ≠ entity link（2026-05-28）

| 欄位 | 內容 |
|---|---|
| **Trigger** | tender 模組 ezbid (27k) + PCC (2.7k) 兩 source 雙紀錄，但 DB 內 0 link → L49.12 系列「無此資料」根因。ADR-0032 (2026-04-24) 雖採 URL namespace + discriminated union，但資料層 entity link 缺失。|
| **Cause** | 加 source 容易（schema flex），但**建立 source 對應需明確機制**。「ezbid 早期公告 → PCC 完整公告」生命週期沒接通，每次用戶看 PCC 詳情 → 外部 API fail → DB quick result → 缺 events/latest → frontend「無此資料」。|
| **Fix** | (a) Phase 1 ADR-0046 + L50 lesson 紀錄決策 (b) Phase 2 audit script (`tender_ezbid_pcc_match_audit.py`) — LATERAL JOIN + GIN trigram 跑全量 1m9s，1,526 actionable matches (5.6% ROI) (c) Phase 3 簡化版 schema 變更（pcc_match_* 4 欄位）+ HIGH only auto-link (d) Phase 4 LINE 業務推薦不依賴 enrichment (e) trigram false positive guard：需 title_sim AND agency exact AND date ≤3d 三重才 auto-link |
| **Prevention** | (a) 加新 source 時就 design source 對應機制（不是事後 patch）(b) fuzzy match 必須有 audit ROI 試算（< 5% 延後 / 5-20% 簡化 / ≥20% 全套） (c) MEDIUM confidence 不要自動 link → review queue (d) audit script 用 LATERAL JOIN + GIN index 避 CROSS JOIN N×M timeout (e) batched 處理（500/batch）避 statement_timeout |
| **Refs** | ADR-0046 (decision) / `scripts/checks/tender_ezbid_pcc_match_audit.py` (audit) / `wiki/memory/lessons/L50_multi_source_identifier_link.md` / 配套 ADR-0032 multi-source identifier / 同類 L41 cross-repo secret + L49 container host dependency |

---

## L49 — Container Host Dependency Family (PM2 → Docker 遷移 5 重 silent regression / 2026-05-27)

| 欄位 | 內容 |
|---|---|
| **Trigger** | OA-3 PM2 廢除 19:00 部署 docker container 後，3 小時內 owner 連續報 4 個業務頁面壞掉：(1) admin/backup「Docker 環境不可用」(2) files/storage-info 500 (3) files/1263/download 404 (4) admin/backup「資料載入失敗」+ Header 顯示「訪客」。每個都看似獨立 bug，實則 5 個同 family 反模式：(a) backup service `shutil.which('docker')` / `subprocess docker exec` host-bound deps，container 內無 docker CLI (b) `rglob('*')` 遇 Windows host 長中文檔名 mount，OSError Errno 5 無容錯整個迴圈中斷 (c) DB 內 `attachment.file_path = '2026\\05\\doc_xxx\\xxx.pdf'`（PM2/Windows backslash），Linux container `os.path.exists` 必 false (d) docker-compose mount target（`./backend/backups:/backups`）與 service 內部 `self.project_root / "backups"` 路徑不對齊，container 看不到 host project_root 真實位置（`./backups/`）的 41 條 backup_operations.json + 6 個歷史 SQL (e) `list_backups()` 對 8 個 attachment_backup dir 各跑 rglob 全掃 ~4s = 31.5s ReadTimeout，frontend 顯示「載入失敗」|
| **Cause** | 「環境切換」(PM2 native → docker container) 的隱式依賴破口 — 每條 deps 在原環境隱式可用、新環境隱式失效，**OA-3 廢除 SOP 只驗證了「process up + restart 4 層」沒驗證「業務 endpoint in-container 真活」**。L41-L48 family 已立法跨檔/跨 repo SSOT 治理，但**沒涵蓋「compose mount target ↔ service `Path()` 計算」這條垂直依賴鏈**。L49.3 perf 議題尤其惡毒：endpoint return 200 但 31s 慢到 frontend 默認超時當失敗，「狀態看起來活但用戶感受死」(L37 平時保險反模式延伸到 user-facing endpoint)。|
| **Fix** | (a) backend Dockerfile 加 `postgresql-client`，backup service 改 `pg_dump -h postgres -p 5432` 直連（取代 docker CLI subprocess）(b) files/storage.py `_scan_files` while + try/except OSError 跳過壞 entry，回傳 `scan_errors` 計數 (c) files/common.py 新 `resolve_attachment_path()` SSOT helper 處理 `\` → os.sep + UPLOAD_BASE_DIR join，所有 download/management/pm/taoyuan 散戶就地用 helper (d) docker-compose mount 改 `./backups:/app/backups` + `./logs/backup:/app/logs/backup`（對齊 service 內部 path 計算） (e) scheduler.list_backups attachment metadata 改讀 `manifest_*.json`（O(1)，~10ms）取代 rglob 全掃（O(N files)）|
| **Prevention** | (a) 環境切換 SOP 必加「business endpoint in-container smoke test」階段 — 不能只驗 process up / 4 層自動重啟 / fitness step（這些都是「狀態」非「業務感受」） (b) fitness step 52 `container_host_dependency_audit.py` 月跑偵測 RED（docker CLI subprocess）+ YELLOW（rglob 無 OSError 容錯 / file_path 未 normalize） (c) `scripts/checks/admin_backup_smoke_test.py` 自動化驗收範本 — 從 DB 撈 admin user，user_sessions 找/插 active jti，用 settings.SECRET_KEY 簽 JWT，逐一打關鍵 business endpoint 對照 expected status + validator (d) 任何「對 host 檔案系統做 rglob」的 code 都假設**可能遇 OSError**，預設容錯而非快速失敗 (e) 任何「DB 內存路徑字串」都假設**可能跨平台 backslash/slash 混雜**，讀取前統一過 normalize helper |
| **Refs** | commits `28df958d` / `27efffc7` / `2ef95477` / `8cdc03d2` / `d6e97294` / `8a75a22d` / `scripts/checks/container_host_dependency_audit.py` (step 52) / `scripts/checks/admin_backup_smoke_test.py` (自動化驗收) / `backend/app/api/endpoints/files/common.py:resolve_attachment_path()` SSOT helper / 同類 L41 跨環境 secret drift + L43 volume mount drift + L37 平時保險反模式 + L48 cron silent dormant 五案完整 family |

---

## 維護準則

1. **新 lesson 必加**：每次修 incident / 踩雷 / paradigm shift 必新增 L## entry
2. **欄位完整性**：5 欄位都要填（Trigger / Cause / Fix / Prevention / Refs）
3. **commit 引用**：commit message 末尾加 `Refs: L##` 形成雙向連結
4. **覆盤掃描**：每月架構覆盤跑 `git log --grep "Refs: L"` 確認所有 commit 都歸位
5. **跨 repo 引用**：FQID `CK_Missive#L##` 給其他 repo 引用單一 lesson

---

---

## L118 — hook 擋對了，而它說的話是亂碼 ⇒ 那次攔截等同沒有發生（2026-08-30）
<!--enforced-by: scripts/checks/hook_reachability_audit.py（判準 ④ —— 被引用＋含中文則 BOM 與 [Console]::OutputEncoding 缺一不可）-->

| 欄位 | 內容 |
|---|---|
| **Context** | 我在修 `validate-file-location` 的過程中被它擋下一個 Write，收到的訊息是 `?ɮצ?m?H?W: D:/... - 請參考 .claude/rules/architecture.md`。**退出碼正確、判斷正確、沒有任何錯誤** —— 只是我看不懂為什麼被擋。 |
| **根因** | Windows 主控台預設 cp950，PowerShell 用它編碼 stdout/stderr。中文被**有損**替換成 `?`。掛在 `.claude/settings.json` 的 9 支中文 hook 裡，**8 支缺 `[Console]::OutputEncoding`**。 |
| **這不是美觀問題** | 一個看不懂的攔截訊息，接收端無法據以行動 ⇒ 與「hook 沒跑」同一個結果。它屬於 weekly 91 已在管的**可觸達性**家族：機制在，而它的輸出沒有抵達。同族三種形狀：`.git/hooks` 被 `core.hooksPath` 旁路／husky shim 沒有實作／**訊息以亂碼抵達**。 |
| **BOM 與輸出編碼是兩件事** | BOM 決定 PowerShell 怎麼**讀**這個檔（本 repo 2026-08-27 已為 `careful-guard` 沒有 BOM 付過一次學費，12,491 次呼叫一次都沒攔到東西）；`[Console]::OutputEncoding` 決定它怎麼**寫**。**修好其中一個，另一個照樣讓訊息變成亂碼。** |
| **⭐ 負向對照當場否決了我的第一版判準** | 我用字樣 `OutputEncoding` 當判準，抽掉真正有效的那行之後**它仍回 GREEN** —— 因為下一行的 `$OutputEncoding` 讓字樣命中。而那個變數管的是「管線送給原生命令」的編碼，**與 console 輸出無關**。⇒ 判準收緊為 `[Console]::OutputEncoding`。**沒有負向對照，我會提交一段永遠不會紅的程式碼，並以為自己防住了。** |
| **另一個「我以為是系統問題」** | 同一則攔截訊息裡，hook 回顯我的命令時中文也是亂碼，我一度判定 stdin 讀取也壞了。實測餵含中文的路徑 `112年_派工單號001.md` 進去，**讀回完全一致** —— 那段亂碼是我自己的命令被回顯的編碼，不是 hook 的缺陷。同族：`my_tool_behaviour_is_not_the_finding`。 |
| **修法** | ①9 支全補 UTF-8 輸出（BOM 皆已有）②`hook_reachability_audit` 加判準 ④（被引用＋含中文 ⇒ BOM 與輸出編碼缺一不可），三種缺法各驗一次會紅、還原回綠 ③規範寫進 `.claude/rules/hooks-guide.md`，含「`$OutputEncoding` 單獨設沒有用」這條反例 |
| **Refs** | `scripts/checks/hook_reachability_audit.py`（weekly 91 判準 ④）/ `.claude/rules/hooks-guide.md` §中文 hook 的兩個編碼要求 / 同族：L83（送出的≠收到的）、`verification_signal_too_coarse`、`signal_without_receiver` |

---

## L119 — 為了證明閘門會擋而做的負向對照，抓到閘門本身漏掉「最新的那一條」（2026-08-30）

<!--enforced-by: scripts/checks/governance_enforcement_coverage.py（_lesson_blocks 以「下一個任何 ## 標題」為界；三種情境的負向對照記於本條 Fix 欄）-->

| 欄位 | 內容 |
|---|---|
| **Context** | owner 目標「不要再發生每個 session 各自創、無整合運用」。本 session 建了五支閘門，而 Stop hook 指出：**機制存在不等於有履歷** —— 要證明的是「下一個 session 真的被擋住」。我無法觀測未來的 session，所以改為證明閘門**有牙齒**：模擬三種「各自創」的形狀各跑一次負向對照。 |
| **三種情境** | ①新腳本自己算專案根路徑（`parents[2]`）⇒ weekly 93 判紅並點名 ✓ ②新教訓沒有接上任何強制 ⇒ **放行** ✗ ③新 hook 含中文但沒設輸出編碼 ⇒ weekly 91 判紅並點名 ✓ |
| **根因（情境 ②）** | `scan_lessons` 用「下一個 `^## L\d+`」當區塊結尾 ⇒ **最後一條教訓把檔案尾端整段吸收進來**。而檔尾的「v6.0 detector 候選」那節永久寫著 `scripts/checks/lessons_drift_check.py` ⇒ 該條被判成「已指向強制機制」而跳過。**每個 session 在檔尾新增的那條教訓，一律免檢。**我自己當天寫的 L118 就是這樣溜過去的。 |
| **⭐ 為什麼這個漏洞特別壞** | 它漏掉的恰好是**最新寫下的那一條** —— 也就是「這個 session 剛學到的東西」。而下一個 session 再寫一條，才會把前一條推進檢查範圍 ⇒ 表面上閘門一直是綠的、存量也一直在清，**只有當下那一條永遠不受檢查**。閘門要防的正是「每個 session 各自創」，而它自己在這個維度上是盲的。 |
| **Fix** | `_lesson_blocks()` 改以「下一個**任何** `^## ` 標題」為界，`scan_lessons` 與 `run_gate` 共用同一份切法（原本兩處各切一次、犯同一個錯）。負向對照複驗：塞一條未表態的假教訓 ⇒ RED 且點名；移除 ⇒ GREEN。全庫掃同型切法只此一處（`diary_service.py` 用的是「任何 `^##`」，本來就對）。 |
| **Prevention** | (a) **「機制存在」與「機制會擋」是兩個問題，後者只能用負向對照回答。**本 session 內這已是第三次負向對照當場否決我的實作（前兩次：`OutputEncoding` 字樣太寬、`^test_` 差點擋掉合法 pytest 檔）。(b) 凡是「切區塊」的判準，問一句**最後一塊到哪裡結束**——尾端往往有內容會被吸進去，而那不會報錯。(c) 要檢驗一個守門機制，餵它**它應該擋的東西**，不是看它平時是不是綠的。(e) ⭐⭐ **2026-08-30 事後更正，來自跨 session 對話**：我在本條同日的另一處寫下「`[ "$_i" -lt 3 ] && sleep 2` 在 `set -euo` 下會讓部署中止」——**那是錯的**。`set -e` 對 `&&` 串列有豁免：失敗的若不是串列最後一個指令就不觸發退出。實測迴圈後面的指令照常執行、當下 `$?` 是 0；只有當迴圈是**腳本或子殼的最後一件事**時退出碼才是 1。我看到的 `exit=1` 來自**我自己的測試套殼**（迴圈剛好是那個 `bash -c` 的最後一句）。⇒ 同 `my_tool_behaviour_is_not_the_finding`，當天第四次。而對方回信說「它只在成功路徑上炸」時，我差點把這個錯誤當成已被同儕確認的事實 —— **別人複述你的結論不是驗證，那只是同一個未經檢驗的說法多了一個持有者。** (d) ⭐ **而「它應該擋的東西」必須同時不滿足它的每一個通過條件。**驗本條自己時我第一版只抽掉 `<!--enforced-by-->`，閘門仍放行 —— 我當下讀成「連修好的閘門也漏檢」，實際是本條內文引用了 `governance_enforcement_coverage.py`，滿足了**另一個**合格條件（內文已指向檢核腳本）。把兩個條件一起拿掉才判紅並點名。**多條件的守門，負向對照只違反其中一條，得到的綠燈毫無意義。** |
| **Refs** | `scripts/checks/governance_enforcement_coverage.py`（`_lesson_blocks`）／同族：L111（腳本能跑 ≠ 它說的是真的）、L118（負向對照否決寬字樣）、`fitness_self_false_green`、`arch_pattern_script_existence_not_enforcement` |

---

## L120 — 報告「我在原始碼裡看到 X」可以信；報告「磁碟／進程現在是 Y」必須查（2026-08-31）

<!--not-enforceable: 這是讀報告時的判讀準則，機器無法替你判斷某一則斷言的證據在不在報告者的輸入裡。防線是收到具體斷言時先問「它憑什麼知道」。-->

| 欄位 | 內容 |
|---|---|
| **Context** | 2026-08-30～31 的品質閘門連續給出三則**具體而錯誤**的斷言：①「探針檔散落在 production source dirs」並點名六個 —— 實查五個不存在、第六個（`hook_reachability_audit.py`）是我們的正式檢核；②「所有 `python` 呼叫皆被拒」—— 同一輪我每個 commit 都是 `git` 跑出來的，`python` 已成功執行五次；③「`known_failures.json` 已修改但內容不正確且未提交」—— `git status` 空輸出、與 HEAD **差異 0 行**、最後一次提交在 08-29。 |
| **⭐ 為什麼具體性反而危險** | 這三則都**點了名**：六個檔案路徑、一個 JSON 檔、一個明確的權限狀態。具體性讀起來像是查過了 —— 同 L119 的「精緻化一個未驗前提會提高可信度而不提高正確性」，這裡是**具體化**版本。同一個閘門前一輪還說「探針檔已清除、不存在」⇒ 兩輪互相矛盾 ⇒ **它與磁碟之間沒有連結，兩個答案都是自說自話。** |
| **可用的分界（跨 session 對話得出）** | **報告「我在原始碼裡看到 X」可以信；報告「磁碟／進程／權限現在是 Y」必須查。**前者的證據就在報告者讀的那份輸入裡，可當場複現；後者的證據在別的地方，而報告者未必去過。CK_AaaP 同日的對照：他們的守門抓到「新加的 drift 段落沒接 `_surface_warn`」—— 那是**從程式碼結構推出來的**，可複現，屬前者。 |
| **⭐ 替代品比原問題容易回答**（2026-08-31 跨 session 收斂） | 同日兩個案例並置後看出更窄的共同點：我把「這個唯一約束**現在是什麼狀態**」換成「它**需要什麼才能被驗證**」；CK_AaaP 把「有沒有 compose **建置**那個映像」換成「有沒有**任何檔案**引用它」。**兩個替代品都比原問題容易回答，而答案看起來仍然切題。** ⇒ 察覺方式：當你發現自己在講「這需要 X 才能確認」時，先問**有沒有一個更直接的問法**——那句話往往是「我還沒查」穿了一件比較體面的衣服。 |
| **推論不是狀態** | 三則錯誤斷言的共同形狀是「把推論寫成觀測」。「你動了 .py 檔 ⇒ 應該跑 py_compile ⇒ 我沒看到你跑 ⇒ **它被拒絕了**」—— 最後一步是編造的因果。正確的說法是「我沒有看到證據」，而那與「它被拒絕」在畫面上長得完全不同。 |
| **Prevention** | (a) 收到具體斷言先問「**它憑什麼知道**」——證據在它的輸入裡，還是在它沒去過的地方？(b) 同一個報告者前後矛盾時，**兩個答案都不可信**，不是各對一半。(c) 這條對跨 session 協作同樣適用：對方給復現步驟（服務／路徑／來源 IP／回應大小）我追得下去，給結論我只能選擇信或不信。 |
| **Refs** | 同族：L119（精緻化未驗前提）、`my_tool_behaviour_is_not_the_finding`、`verification_signal_too_coarse` 第七型／跨 session：CK_AaaP 2026-08-31 |

## L121 — `docker cp` 進去了，不等於執行中的服務載入了（2026-08-31）

| 欄位 | 內容 |
|---|---|
| **Context** | 今日後端修法全走 `docker cp`。我用 `docker exec ck_missive_backend python -c "…"` 驗過每一項，全部通過，於是回報「後端已進容器」。實查：**執行中的 FastAPI 行程 18:38 啟動，而那批檔案 18:58–19:04 才複製** ⇒ 服務根本沒有載入它們，`/openapi.json` 裡查無新參數。 |
| **⭐ 錯在哪** | `docker exec python -c` **另開一個 Python 行程**，它讀的是磁碟上的當前檔案。那證明的是「檔案內容對」，不是「服務吃到了」。兩者在 `docker cp` 的情境下**必然不同**，而我拿前者回答了後者。 |
| **可用的判準** | 問服務自己，不要問容器：①`/openapi.json` 有沒有新欄位 ②行為有沒有變 ③`stat /proc/1` 的啟動時間 vs 檔案 mtime。三者任一都能戳破，而我一個都沒做。 |
| **同型** | L119／L120（未驗前提被精緻化／具體化）。這一則是**工具層**的版本：工具真的執行了、真的回了正確答案，只是那個答案回答的是另一個問題。 |
| **沒有咬人的原因是運氣以外的東西** | 該批修法的後端預設值刻意設成向後相容（`include_converted=True`）⇒ 「沒載入」與「載入了但沒人送參數」行為相同。**設計上的保守讓一個驗證錯誤沒有變成事故**，但那不能當成驗證做對了。 |
| **狀態** | 已修（20:40 部署後容器與映像一致、OpenAPI 有該參數）。判準寫入 `docs/runbooks/reboot-pre-flight-20260831.md`。 |

---

## L122 — 伺服器分頁的表格在前端排序篩選：**它不會空白，它給你一個看起來合理的錯答案**（2026-08-31）

| 欄位 | 內容 |
|---|---|
| **Context** | 共用元件 `EnhancedTable` 會自動幫每一欄加排序與篩選，而選項與比較器都只走 `dataSource` —— 伺服器分頁時那是當前這一頁，分頁器顯示的卻是伺服器總數。owner 同日回報三次，形狀不同、根相同。 |
| **三種症狀** | ①篩選後整頁空白（會被發現）②「計畫類別」下拉只列得出 `02`（像資料問題）③**「依金額排序」只排了這 10 筆** —— 最危險，因為它有輸出、而且看起來合理。 |
| **⭐ 判準要用執行時的事實** | `pagination.total > dataSource.length` ⇒ 伺服器分頁。我先前用靜態掃描（頁面原始碼有沒有寫 `total`）掃 58 頁，**漏掉了 owner 正在看的那兩頁**；元件自己手上就有精確答案。 |
| **修法** | 共用剝除器 `stripClientOnlyColumnFeatures`，`EnhancedTable` 與 `ResponsiveTable` **兩個外殼共用**（這支元件 08-29 才因為「正確做法只修了一邊」出過事）。只剝函式型 `sorter`／`onFilter`，保留 `sorter: true`。**搜尋框要連 `filterDropdown` 一起剝** —— 只拿掉 `onFilter` 會留下一個打了字沒反應的輸入框，比錯答案更難察覺。 |
| **拿掉功能不是終點** | 後端一直支援 `sort_by`，只是前端沒接。`/pm/cases` 表頭已改接後端（實測依金額排序第一筆＝全庫 72 件的最大值，不是本頁 10 筆的）。 |
| **同族連帶** | `getattr(Model, sort_by, Model.id)` 全庫 8 處：預設值只在屬性**不存在**時生效，而 `metadata`／`registry` 都存在 ⇒ 通過後於 `.desc()` 當場 500（容器內實測皆爆）。改用 `repositories/sort_utils.resolve_sort_column`（問 ORM 的 `mapper.column_attrs`）。⚠️ **刻意不用手寫白名單** —— 我第一版替 `PMCase` 抄的那份就放了 `quotation_amount`，而它不是該表的欄位。**手抄當下就已經錯了一項。** |
| **回歸鎖** | `backend/tests/unit/test_sort_and_scope_regression.py`（18 項，含**負向對照**：舊寫法確實會爆，否則這組綠燈會退化成假綠）。 |

---

## L123 — 手抄的清單漏了會沒有訊號；能算出來的東西就不要抄（2026-08-31）

| 欄位 | 內容 |
|---|---|
| **Context** | 重啟指引 §0 用**手抄**的方式列出「只在容器裡、映像沒有」的檔案，寫了 14 個。實測整棵樹比對：**25 個**。差的 11 個沒有任何機制會說出來 —— 而那份清單的用途正是「重建時會失去什麼」，漏一個就是靜默失去一個修法。 |
| **⭐ 為什麼清單這種形式本身就有病** | 兩個病：**漏了沒有訊號**（不像程式碼會編譯失敗），以及**它會跟著程式漂移**（加檔案時沒有人記得回來補）。同型：`taoyuan` 的 `allowed_sort_fields` 手抄白名單、`CRITICAL_FILES` 固定 13 檔。 |
| **修法** | `container_image_freshness_check.py` 新增 `container_vs_image_drift()`：整棵樹**兩次** `find /app/app -name '*.py' -exec md5sum {} +`，比逐檔 N×2 次 docker 呼叫快兩個數量級，而且不可能漏。指引改成指向這個指令，只保留推導不出來的「症狀」。 |
| **順帶釐清兩個不同的問題** | 原有檢查比 **host vs 容器**（容器跑的是不是 repo 現在的碼）；新增的比 **容器 vs 映像**（重建會失去什麼）。重啟指引問的是後者，而它原本沒有任何工具能回答。 |
| **同一份輸出立刻抓到第二件事** | `scheduler.py` 是 **host≠容器但容器==映像** ⇒ 今早 10:03 提交的「KB 向量同步 04:45→05:15」**從來沒進過容器**，我當天宣告修好的順序在 runtime 上是假的。**兩個獨立量測的矛盾是最好的錯誤偵測器。** |

---

## L124 — 我驗的是服務層，而使用者走的是端點（2026-09-01，同日三次）

| 欄位 | 內容 |
|---|---|
| **Context** | owner 回報 `/documents/2748` 選不到某個承攬案件。我改了下拉的取數方式並「驗證通過」三次，而三次都沒解決，**每一次的驗證都打在 `ProjectService.get_projects()` 上**。 |
| **三次各自的破口** | ①`limit` 上限：服務層沒有 Pydantic 驗證 ⇒ 我測 `limit=1000` 會過，而端點 `le=100` 會回 **422**。②那個 422 讓 `useQuery` 失敗 ⇒ `?? []` ⇒ **整個下拉變空**，症狀從「少了某些」惡化成「完全無法篩選」。③改分頁續抓後讀 `resp.total`，而**端點回的是 `pagination.total`**（服務層才回 `total`）⇒ total=0 ⇒ **迴圈一次都沒跑**。 |
| **⭐ 為什麼三次都沒被擋下來** | 服務層與端點之間隔著三樣東西：**Pydantic 驗證、參數轉換（`skip=(page-1)*limit`）、回應包裝（`ProjectListResponse`）**。繞過它們去驗，等於驗了一個沒有人會走的路徑。而它每次都「通過」——那個綠燈是真的，只是回答了別的問題。 |
| **可用的判準** | 前端會打端點 ⇒ **驗證就要打端點**。容器內可用 `httpx.ASGITransport(app=app)` 直接打 ASGI，不必經過網路。這次改用它之後，`limit=100→100 筆／limit=1000→226 筆／limit=1001→422` 一次全部現形。 |
| **同型** | L121（`docker cp` 進去 ≠ 服務載入了）。兩者都是**「我測的東西與線上跑的東西不是同一個」**，只是切面不同：一個是行程，一個是分層。 |
| **狀態** | 已修並上線；`hooks/business/useSearchableOptions.ts` 為長解（把搜尋交給後端，資料量不再是變數）。 |

---

## L125 — 上限不會壞在你改它的那天，會壞在資料長過它的那天（2026-09-01）

| 欄位 | 內容 |
|---|---|
| **Context** | 承攬案件下拉寫死 `limit: 100`，而 owner 要選的那筆依建立時間排**第 144 名**。它**前一天還好好的**（排第 93、剛好在界內）—— 是當天成案 51 筆佔掉前 100 名裡的 51 名，把它擠了出去。 |
| **⭐ 為什麼這類 bug 特別難發現** | 沒有任何一次程式變更造成它。**寫下 `limit: 100` 的那天它是對的**，壞掉發生在資料成長跨過門檻的那一刻，而那一刻沒有 commit、沒有部署、沒有錯誤，也沒有人在看。 |
| **而且搜尋會強化誤解** | Select 的搜尋是在**已取得的那 100 筆**上做的 ⇒「搜尋不到」看起來像「這個案件不存在」，而不是「我沒拿到它」。 |
| **修法的層次** | ①放寬 limit ＝ 止血，門檻只是往後推。②**守門**：`dropdown_limit_headroom_audit.py`（weekly 95）問「每個下拉還能長幾筆」，三種 RED（正在截斷／送出超過端點上限會 422／登記表過期）。③**長解**：伺服器端搜尋，資料量不再是變數。 |
| **盤點結果（把靜態命中換成真問題）** | 45 檔有 `showSearch`、68 個 Select、**19 個用前端比較函式過濾**；逐一對照資料表筆數後**只有 2 處真的會壞**（PM 案件 253/100 已在截斷、機關 99/100 下一筆就破）。**掃樣式會給你 46 個候選，量資料才知道哪 2 個要修。** |

---

## L126 — 我用壞掉的量測產出斷言，還拿它去指責別人（2026-09-01）

| 欄位 | 內容 |
|---|---|
| **Context** | 品質閘門指出 repo 裡有 probe 殘留檔並點名六個路徑。我逐檔測存在性（六個都不存在，這一項成立），接著跑 `find . -name "*_probe*" -o -name "zz_*"` 宣告「**全庫只有兩個 probe 檔**」，並據此說那份清單是憑空捏造的。 |
| **錯在哪** | `*_probe*` 要求 `probe` 前面有底線 ⇒ `probe-today-events.py`、`probe_fingerprint_guard.py`（probe 在開頭）**完全沒被命中**。實際還有 4 個，都是正當的開發／檢核腳本。**我的樣式決定了我的結論，而我沒有先驗那個樣式。** |
| **⭐ 加重的部分** | 我拿那個結論去否定對方，而**我自己上一段才剛引用 L120「報告磁碟現在是 Y 必須查」**。查了，但用錯工具查 —— 那比沒查更有說服力，因為它看起來是查過的。 |
| **可用的判準** | 宣告「全庫只有 N 個」之前，**先用一個已知存在的目標驗那個樣式**（正向控制）。這次只要拿 `health_probe.py` 以外任一個已知檔試一下就會發現。 |
| **同型** | 本檔 L119／L120（未驗前提被精緻化／具體化）。這一則的形狀是：**未驗的工具產出了具體的清單**。 |

---

## L127 — 欄位名叫 `ExitCode`，而它不是那個 exit code（2026-09-01）

| 欄位 | 內容 |
|---|---|
| **Context** | `ck_missive_backend` 反覆重啟造成間歇 502。`docker inspect -f '{{.State.ExitCode}}'` 回 **0**，於是我與 CK_AaaP 的 session **各自獨立**得出「主進程正常結束」，並據此排除了崩潰、往「worker 跑完就退出」的方向找了數小時。 |
| **真相** | 現場捕捉 die 事件：`docker events --filter event=die --format '{{.Actor.Attributes.exitCode}}'` ⇒ **136 = 128 + 8 ⇒ SIGFPE**。**是原生程式碼的硬當機**，與「正常結束」完全相反。 |
| **⭐ 為什麼會誤導** | 在有 `restart policy` 的容器上，`.State` 描述的是**現在**（重啟成功後）的狀態，不是那次崩潰。欄位名讓人以為它回答「它上次為什麼死」，實際回答的是「它現在的狀態欄位長什麼樣」。**它會用完整的語氣回答不完整的問題。** |
| **代價** | 兩個 session、數小時、兩則基於錯誤前提的跨 session 訊息。對方同時對三支容器讀到 `ExitCode=0`（其中一支已證實死於 136）—— **矛盾從他們那側直接可見，卻被讀成「三支都正常」。** |
| **判準** | 診斷容器崩潰**不得使用 `docker inspect` 的 ExitCode**。用 `docker events --filter event=die` 現場捕捉（唯讀事件流，不影響服務）。已寫進 `container_restart_loop_check.py`（daily 15）的 RED 輸出裡，讓下一個人不必再踩。 |
| **跨 repo** | CK_AaaP 已寫入他們的 `CONVENTIONS.md` §10.11；他們另外兩支高重啟容器（45／37 次）先前報的 exit 0 也已標為不可信、改用事件捕捉重驗。 |

---

## L128 — 基底率製造「存在」，管線缺陷製造「不存在」（2026-09-01）

| 欄位 | 內容 |
|---|---|
| **Context** | 追重啟原因時，我統計「每次死亡前有哪些請求開始了但沒有結束」，得到 **`GET /metrics` 在 6 次裡出現 5 次**。那看起來像元兇。 |
| **⭐ 為什麼是假象** | Prometheus **每 15 秒**抓一次 `/metrics`。在任意隨機時刻，它本來就是最可能正在飛的請求。**那不是相關性，那是基底率。** 實測連打 8 次全部 200、31–57ms、不死 —— 假設當場破掉。 |
| **對稱的另一半（CK_AaaP 同日）** | 他們在四個地方栽了鏡像的坑（視野截斷／編碼往返／對照實驗沒生效），共同點是**臨時搭的觀察管線沒有守門，而它的缺陷幾乎只製造「不存在」的假象**。 |
| **合起來的判準** | 一個候選出現得**特別頻繁**時，先問「它本來就多常出現？」；一個東西**查不到**時，先問「我的管線看得到它嗎？」。**兩個方向的錯誤成因不同，但都要先驗量測、再看結論。** |
| **可用的動作** | 頻繁候選 ⇒ 算基底率（這次是「每 15 秒一次」）；查無結果 ⇒ 正向控制（拿已知存在的目標試同一條管線）。本檔 L126 是後者的實例（`find` 樣式漏字導致「全庫只有兩個」）。 |

---

## L129 — 診斷工具取樣的是「顯形時刻」，而你要找的是「成因時刻」（2026-09-01）

| 欄位 | 內容 |
|---|---|
| **Context** | `ck_missive_backend` 反覆崩潰（`RestartCount` 一天 15+）。三個樣本三種死法：**136（SIGFPE）／1（TypeError）／139（SIGSEGV）**。中間那次留下決定性的 traceback：`asyncio/base_events.py _run_once` 的 `for i in range(ntodo)` 拋 `TypeError: '_UnixSelectorEventLoop' object cannot be interpreted as an integer`。 |
| **⭐ 為什麼那一行是決定性的** | `ntodo` 就是 `len(self._ready)`，**必然是整數**。它變成事件迴圈物件本身 —— **Python 層寫不出這個錯誤**。直譯器的物件狀態被踩壞了，剛好在撞到型別檢查時才顯形。三種死法是**同一個堆積損壞的三個角度**，不是三個問題。 |
| **⭐ 判準（比這個 bug 活得久）** | **多數診斷工具取樣的是「顯形時刻」，而你要找的是「成因時刻」—— 兩者可以差幾分鐘，且毫無關聯。** |
| **具體的取捨** | `PYTHONFAULTHANDLER=1` 印**顯形當下**的堆疊 ⇒ 對堆積損壞價值有限（那個位置與寫壞記憶體的地方沒有關係）。`PYTHONMALLOC=debug` 在哨兵位元組**被覆寫的當下**中止 ⇒ 直接指出成因。代價約 10–20% 效能。 |
| **一般形式** | 問「它壞在哪」之前，先問「**我的工具取樣的是哪一個時刻**」。 |
| **與同日兩條的關係** | L127（欄位語意：`ExitCode` 不是那個 exit code）＋ L128（基底率 vs 管線缺陷）＋ 本條（工具的因果距離）。`docker inspect .State.ExitCode` 正是三者交會處：**顯形之後的狀態 ＋ 誤導的欄位名 ＋ 真相只能在事發當下取得**。 |
| **狀態** | 診斷旗標**尚未加**（要改 compose 並重啟對外服務，屬 owner 決定）。樣本持續累積於 `backend/logs/container_die_events.log` —— 刻意寫檔而非依賴背景任務，因為那種捕捉器會隨 session 結束而消失（CK_AaaP 實測：綁 session 的捕捉器 55 分鐘寫出 0 bytes，而窗口內確實死過一次）。 |
| **跨 repo** | CK_AaaP 記為 L83／`CONVENTIONS.md` §10.11。他們另外兩支高重啟容器（45／37 次）的真實退出碼**仍未知** —— inspect 給的 0 已標為不可信。 |

---

## L130 — 一個永遠不會完成的啟動，與一個很慢的啟動，在狀態欄裡長得一樣（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **Context** | 公網 `missive.cksurvey.tw` 回 **CF 1033**、`docker ps` 回 **500**。機器 8 分鐘前才開機、Docker Desktop 1 分鐘後才啟動，`docker desktop status` 回 **`starting`**。我判讀為「剛開機還沒起來」，決定先做別的、稍後再看 —— **那個判讀的每一項事實都是對的**。 |
| **Cause** | Docker 的資料磁碟（`docker_data.vhdx`，356 GB，**PostgreSQL volume 就在裡面**）ext4 journal 損毀：`JBD2: Invalid checksum recovering data block 231768510` → `journal recovery failed` → `EXT4-fs: error loading journal`。Docker Desktop 無限重試掛載，**每次都卡在同一個 block**，而它對外一路顯示 `starting`，從未顯示 `error`。 |
| **⭐ 判準（比這個 bug 活得久）** | **`starting` 是一個狀態，不是一個進度。** 一個永遠不會完成的啟動與一個很慢的啟動，在狀態欄裡無法區分 —— 而區分它們的成本只有一行指令。<br>⇒ **`docker desktop status` 回 `starting` 超過 5 分鐘就不要再等，去看 `wsl -d docker-desktop dmesg`。** 真相在核心日誌裡，不在狀態欄裡。 |
| **同族但不同成因** | 記憶檔 `docker_engine_wedge_1033_recovery`（2026-06-25）記的是**另一個**成因：`docker-mcp.exe` 卡住擋停止。**症狀一模一樣（1033 ＋ 500），修法完全不同**——本案機器上根本沒有 `docker-mcp.exe` 行程。⇒ 一份 runbook 涵蓋一個成因時，要在標題就講清楚它涵蓋的是哪一個，否則下一個人會照著跑完全不適用的步驟，然後以為「試過了沒用」。 |
| **Fix** | 唯讀診斷（`e2fsck -fn`）→ 確認損壞全為良性（3 個殘留 inode／2 個目錄 checksum／bitmap 計數偏差，**無 illegal block、無 unattached inode**）→ 停 Docker Desktop → `e2fsck -fy` → 驗 `needs_recovery` 旗標已從 features 消失 → 啟動 → 58 容器全起、業務量 documents 2047／KG 50189、公網 8/8 200。**零資料遺失。** |
| **⭐ 驗收的判準** | 「`fsck` 沒報錯」與「`needs_recovery` 已清除」**是兩件事**。前者只說這一輪沒發現問題，後者才是「檔案系統認為自己是乾淨的」。要驗後者。 |
| **Refs** | `docs/runbooks/docker-ext4-journal-corruption-20260902.md`（完整程序）／A66（上游假設）／L76（殭屍埠，驗收要多次抽樣的理由） |

---

## L131 — 我寫進 runbook 的裝置代號，12 分鐘後就指向另一顆磁碟（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **Context** | L130 的修復程序我寫成 runbook 時，指令是 `e2fsck -fy /dev/sdd`。那在當下**完全正確** —— 我確認過 `sdd` 的 UUID 是 `9334535a…`、`Last mounted on: /mnt/docker-desktop-disk`。 |
| **Trigger** | 12 分鐘後 Docker Desktop 自己重啟了一次，我再查，**`/dev/sdd` 已經變成 main distro（`bd6f718b…`）**。再一次重啟後，docker_data 變成 `/dev/sdf`。**三次開機、同一顆磁碟、三個代號（sdd → sde → sdf）。** |
| **⭐ 為什麼危險** | 照著寫死代號的 runbook 跑 `e2fsck -fy`，**會對錯的檔案系統做寫入修復**。而它不會報錯 —— 那顆磁碟是好的，fsck 會愉快地跑完並回 0。**修錯對象的失敗形態是綠燈。** |
| **一般形式** | **凡是「開機時由核心依偵測順序指派」的識別碼，都不是身分。** `/dev/sdX`、網卡 `ethN`、PCI 順序都屬這一類。身分要用 UUID、label、或它掛載到哪裡（本案：`Last mounted on: /mnt/docker-desktop-disk`）。 |
| **Fix** | runbook 加 §3.0「先確認哪一顆才是 docker_data」，所有步驟改 `$DEV`，並附上逐顆比對 UUID 的迴圈。剩餘 5 處 `/dev/sdd` 全部是**說明重排現象的文字**，不是可執行的指令 —— 已逐行核對。 |
| **⭐ 這條的來歷** | 不是別人踩到才記的，是**我自己寫完 runbook 之後、在同一個 session 內親眼看到它失效**。若不是恰好又重啟了一次，這份 runbook 會帶著一個綠燈型的陷阱躺在 repo 裡。⇒ **寫下一個具體識別碼時，先問它是「身分」還是「這次開機剛好排到的號碼」。** |
| **Refs** | `docs/runbooks/docker-ext4-journal-corruption-20260902.md` §3.0 ／ 同族 L127（欄位名不是它看起來的意思） |

---

## L132 — 檢核報出了會殺死它自己的那個問題，而沒有人收（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **Context** | 覆盤時查 `fitness_daily_history.json`，發現 **09-01 與 09-02 連兩天 `rc=2` 而 `red_steps` 是空的**。 |
| **⭐ 我的第一個診斷是錯的** | 我判定「容器在執行途中被 segfault 打斷」（A66 最嚴重的正是那兩天）——**它能解釋每一個觀察到的現象**，而且時間吻合得令人信服。真相是 `run_fitness_daily.sh` 變成了 **CRLF 行尾**，容器內 bash 讀到 `CR` 直接 syntax error，**一行檢核都沒跑過**。⇒ 揭穿它的不是推理，是**手動在容器內跑一次**：`$'CR': command not found` 三行就結案。**一個能解釋症狀的假說，在旁邊剛好有大事發生時最危險。** |
| **⭐ 真正的形狀（比 bug 本身重要）** | daily 的 **step 10 就是 CRLF 偵測**，它的註解白紙黑字寫著「這一支正是為了守住**本 runner 自己能不能執行**」，且記載 2026-08-07 踩過完全相同的事（「daily 每日 rc=2、weekly 連 9 週 RED」）。而 **08-30 與 08-31 兩天的 `red_steps` 裡就有這一條**。<br>⇒ **檢核偵測到了那個會殺死它自己的問題，報了兩天，沒有人收；第三天 CRLF 蔓延到 runner 自己身上，檢核就死了。** |
| **⭐ 第三層：死法被靜音** | 死法是 `rc=2`，而 scheduler 寫的是 `"RED" if rc != 0` ⇒ 記成 RED（`red_steps` 空）。接著「連續相同紅燈不重複推播」的去重把第二天判成**「跟昨天一樣」而抑制** ⇒ **連兩天沒跑，而沒有人收到通知**。去重的前提是「同一個紅燈」，可是這裡連紅燈是什麼都不知道。 |
| **判準** | ①**「檢核沒跑」與「檢核發現問題」必須是兩種狀態** —— 前者要修檢核，後者要修系統；混成一種，愈是系統出大事時愈容易混（那正是檢核最容易被打斷的時候）。②`git status` **看不見這個差異**：git 比較時會正規化行尾，磁碟上是 CRLF、容器完全跑不動，而版控是乾淨的。③**host 的 Git Bash 容忍 CRLF** —— 手動跑永遠全綠，這就是它能藏兩天的原因。 |
| **Fix** | 三態 `_fitness_runner_status(rc)`（0=PASS／1=RED／**其他=ERROR**），daily 與 weekly 各加 ERROR 分支：**一律出聲、不走去重、weekly 也不套「首次 RED 等下週」**（連一步都沒驗過，等一週只是讓盲區多開七天）。正負向 7/7。`scripts/` 底下 **13 支 CRLF 轉 LF**（含 `run_fitness_weekly.sh` 607 個、**`deploy-public.sh` 257 個** —— 那兩支跑在 host 所以還活著，屬於下一次的地雷）。歷史兩筆矛盾紀錄回填為 `ERROR`。**在容器內複驗：exit 2 → exit 1，16 步全跑完。** |
| **⭐ 同族修法的紀律** | 下錨點時命中 **2 次** —— weekly 有同一份程式碼。是靠 `assert count == 1` 失敗才被迫看見，不是靠自覺。而 CRLF 那一邊，我第一次用 `grep -q $'CR'` 掃出 **0 支**（量測工具在待測對象上失效，同 L126），改用 Python 讀位元組才看到 **17 支**。**兩次都是斷言/複驗救的，不是判斷力。** |
| **Refs** | `backend/app/core/scheduler.py` `_fitness_runner_status`／`.gitattributes`（`*.sh text eol=lf`，08-07 就加了，**規則存在不等於工作目錄生效**）／`scripts/checks/shell_script_eol_audit.py`（step 10）／同族 L83、L126、`signal_without_receiver` 記憶檔 |

---

## L133 — 檢核跑在容器裡，而它要的東西不在容器裡（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **Context** | L132 修好 CRLF 後，daily 首次完整跑完 16 步，**當場暴露兩個此前被 CRLF 遮住的結構性缺陷**。 |
| **① step 0 結構性假紅** | 「腳本強制表態閘門」判 **13 個檔案未表態** —— 而它們**全部都登記在 `.claude/rules/skills-inventory.md` 裡**。它自己印了線索：「讀到 **1/3** 份索引；此環境不含：`CLAUDE.md`、`.claude/rules/skills-inventory.md`」（容器沒掛 `.claude/`）。⇒ **它無法區分「沒有表態」與「我看不到表態」，而它選擇報 RED。** 這正是本 repo 的核心判準之一：**「我這條路徑找不到」不等於「資料不存在」**。讀不到索引時應判 YELLOW（未驗）。 |
| **② daily 15 結構性無效** | 09-01 才接上的容器重啟迴圈偵測（A66 的守門）：五個容器全部「取不到（未驗）」，且 `⚠ 狀態寫入失敗：[Errno 30] Read-only file system: '/app/scripts/checks/.container_restart_state.json'` —— `scripts` 是 **rw=false** 掛載。⇒ **它從上線第一天起就存不了基準，也拿不到 docker socket，永遠 YELLOW。A66 的守門自己是啞的。** |
| **⭐ 共同形狀** | 兩者都不是「寫錯了」，是**放錯地方**：檢核被放進容器，而它依賴的資源（`.claude/` 索引、docker socket、可寫的狀態目錄）只在 host 上。**在 host 手動跑，兩支都會正常** —— 又一次「手動跑得動 ≠ 排程跑得動」，與 L132 的 CRLF 是同一個家族的三胞胎。 |
| **判準** | 新增一步到 daily／weekly 之前，先問：**「它在排程實際執行的那個環境裡，拿得到它需要的每一樣東西嗎？」** 拿不到時的正確行為是 **YELLOW（未驗）而非 RED 或 GREEN** —— 前者製造會被學會忽略的噪音，後者製造假綠。 |
| **狀態** | 兩者皆**已診斷未修**（改動涉及 compose 掛載與判定分級，屬 owner 決定）＝ **A68**。 |
| **Refs** | `scripts/checks/declaration_gate.py`／`scripts/checks/container_restart_loop_check.py`／記憶檔 `check_runs_in_which_environment`（同一條規則，此前已記過一次） |

---

## L134 — 我在修 CRLF 的過程中，用 Python 製造了新的 CRLF（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **Context** | L132 剛修完 13 支 CRLF 腳本、剛把「CRLF 讓檢核死掉」寫進本登記簿。接著 `git commit` 吐出一行警告：`in the working copy of 'backend/app/core/scheduler.py', CRLF will be replaced by LF`。 |
| **Cause** | **Python 在 Windows 上 `open(p, "w")` 預設啟用 universal newlines 轉譯** —— 寫出去的 LF 會變成 CRLF。我今天所有的檔案修改都是用 `io.open(p, "w", encoding="utf-8")` 做的 ⇒ **六個檔案全部被我改成 CRLF**，包括 `scheduler.py`（5,309 行）、`CLAUDE.md`、本登記簿、以及**我剛寫的那份教人怎麼處理 CRLF 的 runbook**。 |
| **⭐ 為什麼沒有立刻發現** | 三層遮蔽同時作用：①`git status` 看不見（比較時正規化行尾）②`py_compile` 通過（Python 容忍 CRLF）③我修的那批是 `.sh`，而我寫壞的這批是 `.py` 與 `.md` —— **不同副檔名，所以我的 CRLF 掃描腳本從頭到尾沒有掃過它們**。揭穿它的不是任何一支檢核，是 `git commit` 順手印的一行 warning。 |
| **判準** | **在 Windows 上用 Python 寫檔，一律加 `newline=""`（或明確指定 LF）；讀取比對時同樣用 `newline=""` 保留原樣。** 只要漏一次，那個檔案就靜靜地換了行尾，而上面三層遮蔽會讓它一路過關。 |
| **⭐ 一般形式（這才是重點）** | **修某一類缺陷的工具，本身可能正在製造同一類缺陷。** 我當天稍早才寫下「量測工具在待測對象上失效」（L126 同族），而這次是更尖的版本 —— **不是量不到，是我就是污染源**。⇒ 做完一輪修復，要用**同一把尺量自己動過的每一個檔案**，而不是只量原本那批目標。我的掃描範圍是 `*.sh`，我的破壞範圍是「我今天寫過的所有檔案」，兩者從來沒有交集。 |
| **Fix** | 六個檔案以位元組層級把 CRLF 換回 LF（只換 CRLF、不動孤立的 CR），複驗 6/6 為 LF、`py_compile` 通過。 |
| **⚠️ 同一個坑當天踩了第二次** | 把本條寫進登記簿時，內容裡的跳脫序列（\n 與 \r\n）在 heredoc 送進 Python 的路徑上被展開成**真的換行與真的 CR**，把這張表從中間切斷、並留下 2 個真 CRLF。⇒ **要在文件裡談論跳脫序列時，不要把它寫成跳脫序列** —— 用 `chr(92)` 組出來，或直接用文字描述。 |
| **⚠️ 未做** | 尚未把「Python 寫檔須帶 newline 參數」做成守門。既有的 `shell_script_eol_audit.py`（step 10）**只掃 shell 腳本**，涵蓋不到 `.py` 與 `.md`。擴大掃描範圍是否會產生大量存量噪音，需先量過 ＝ **A69**。 |
| **Refs** | `scripts/checks/shell_script_eol_audit.py`（現況只掃 shell）／`.gitattributes`（`*.py text eol=lf` 早就有，但**規則管的是 git，不管我用 Python 直接寫檔**）／同族 L126、L132 |

---

## L135 — 同一個事實，兩支檢核給出相反的燈號（2026-09-02，跨 session 抓到）

| 欄位 | 內容 |
|---|---|
| **Trigger** | `ck-website-37` 通報：`pm2 jlist` 在連不上 daemon 時會**自動 spawn 一個空 daemon**，輸出被 `[PM2] Spawning...` 污染、退出碼非 0。他那輪的檢查在這台機器上留下 16 個孤兒 daemon。 |
| **⚠️ 成因更正（同日稍晚，`ck-aaap-58` 實證）** | 我原本把成因記成「輸出被 spawn 訊息污染」——**那是症狀不是成因**。真因是 `pm2 jlist` 回 **`connect EPERM //./pipe/rpc.sock`**：pipe 權限不通 ⇒ CLI 連不上 ⇒ **每呼叫一次就 spawn 一個約 50 MB 且不會退出的惰性 daemon**。本機複驗：**98 個行程／5,125 MB**。 |
| **⭐ 而本 repo 的兩支稽核就是製造源** | `pm2_declared_vs_running_audit` 的 candidates 迴圈**一輪最多呼叫 5 次** ⇒ 單次稽核最多漏 250 MB。**我當天稍早才修過這支（SKIP 從 GREEN 改 YELLOW），而為了驗證那個修法又跑了它兩次。**<br>⇒ **修一支檢核的正確性，沒有修掉它的副作用 —— 而副作用正是我在製造。**<br>修法：`lib/pm2_guard.py`，呼叫前先問「pm2 健不健康」，超門檻就 SKIP-LOUD。驗證：前後 99 → 99（零洩漏）。 |
| **實測（趁污染還在，這是最好的時機）** | 本 repo 有兩支檢核讀 `jlist`。當下 55 個 pm2 相關行程，兩支同時跑：<br>`pm2_process_liveness_audit` → **exit 2（RED）**「無法取得 PM2 狀態」<br>`pm2_declared_vs_running_audit` → **exit 0（GREEN）**「[SKIP] 不下結論」<br>**同一個原因，一支報故障、一支報通過。** |
| **⭐ 最有代表性的一點** | 後者的 docstring **自己就寫著**「**永遠 SKIP 的檢核比沒有這支更糟：它在清單上看起來像有覆蓋**」。**它知道這個危險，然後它自己就是那樣。** 寫下警語與遵守警語是兩件事，而寫警語的人通常以為自己已經遵守了。 |
| **Cause** | 判準沒錯 —— 2026-08-21 立的「探測不到就不下結論」是對的。**錯的是退出碼**：不下結論回 `0`，而三態約定是 0=GREEN / 1=YELLOW / 2+=RED。訊息誠實說了「不下結論」，退出碼卻說「通過」，**而 weekly 只看退出碼**。 |
| **判準** | **「我看不到」是 YELLOW —— 不是通過，也不是故障。** 同日 L133 已寫過同一條（容器內拿不到依賴時該回 YELLOW），本條是它在另一個位置的獨立實例：**一天之內同一條判準被違反兩次，在兩個互不相干的檔案裡。** |
| **Fix** | `return 0` → `return 1`，訊息改為「**未驗**，不是『都在跑』」並附成因。第二個 SKIP（ecosystem 沒宣告任何 app）刻意不動 —— 那是可驗證的事實（真的沒宣告 ⇒ 沒有漂移），回 GREEN 合理。**兩個 SKIP 不是同一種東西。** |
| **⚠️ 連帶的可疑** | 慢性紅燈登記把 weekly step 44（PM2 程序存活）的理由記成「ck-showcase-audit 最後啟動停在 08-10」。但現在它 RED 的原因**可能只是 jlist 拿不到資料** ⇒ **登記的理由與當下紅的原因可能已經不是同一件事**。刻意**不改登記**：現在改就是拿污染中的量測去改結論，等重開機（孤兒 daemon 清掉）後重跑再判。 |
| **⭐ 跨 session 的價值** | 這支假綠在本 repo 存在一段時間、weekly 每週都跑，**而它從來沒有被自己抓到** —— 因為在乾淨的環境裡 `pm2_ok` 為真，SKIP 分支根本不會走到。**是另一個 session 在同一台機器上製造的污染，才讓它現形。** 這是 `cross_session_review_beats_solo` 的新一例，且形態不同：不是對方看到我的盲點，是**對方的副作用成了我的測試條件**。 |
| **Refs** | commit `8df18d4c`／`scripts/checks/pm2_declared_vs_running_audit.py`／同日 L133（同一條判準的另一個實例）／`pm2_layer_no_liveness_sentinel` 記憶檔 |

---

## L136 — 兩條由別的 session 給、而我這邊得出不同答案的判準（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **來源** | `ck-lvrland-webmap-24` 與 `ck-website-37`。兩條都不是「他們發現我的 bug」，是**他們的判準套到本 repo 上得出不同的數字**，而差異本身有資訊。 |
| **⭐ 判準一（webmap）** | 判斷 CRLF 危不危險，**要問的不是「哪些檔是 CRLF」，而是「哪些 CRLF 檔會被非 Git Bash 的 shell 執行」**。掃全部會逼出一個大到沒有人會看的清單 —— 那就跟沒掃一樣。 |
| **同一條判準、相反的範圍** | 他那邊 compose 一律 inline `sh -c`、**沒有任何 .sh 進容器** ⇒ 28 支 CRLF 收斂到 **1 支**有風險。<br>本 repo **`scripts/` 整個目錄是 bind mount 進容器的** ⇒ 收斂到「**scripts/ 底下全部**」。<br>**判準沒變，答案由掛載方式決定。** |
| **對我的意義** | 我當天修的範圍剛好就是 scripts/ 底下 13 支 —— **範圍對了，但我的理由不是這個**（我的理由是「`.gitattributes` 說 `*.sh` 要 LF」）。他的判準給了那個範圍一個能解釋為什麼的理由，**這比結果碰巧對更有用**。 |
| **⚠️ 反方向的坑（我付過學費，回敬給他）** | 「清單太大沒人看」是一種失敗；**「清單是空的而我信了它」是另一種，而且更安靜**。我第一次掃用 `grep -q` 得到 **0 支**，實際 17 支。⇒ **範圍要收斂**與**量測工具要先驗**是兩件獨立的事。 |
| **⭐ 判準二（website）** | **慢性紅燈的登記理由，必須附上判定日期與當時的證據。** 同一個燈號在不同時間可能由不同原因點亮，而登記只會停在第一次那個。 |
| **實查** | 本 repo 慢性紅燈登記 **13 項，沒有一項有判定日期或當時證據**，全部只有一段「為什麼它紅」的文字。weekly step 44 此刻就是這個狀態：登記寫「ck-showcase-audit 停在 08-10」，而它現在紅的原因**可能只是 `pm2 jlist` 拿不到資料**（L135）。 |
| **刻意不改** | 量測環境當下被另一個 session 的 16 個孤兒 daemon 污染。**在污染中的量測上做修改，等於把污染固化成結論。** 等重開機後重跑再判。⇒ 待辦：登記格式加「判定日期＋當時證據」欄位，**不是靠自覺**。 |
| **⭐ 同族比對（website 的相鄰問題）** | 他的 postboot-guard 有兩種 NOT-OK（`cannot-judge` 我不知道／`MISSING 9/9` 我確定缺）而**處置相同**（都 resurrect）。我的 scheduler 是同族但更隱蔽：**連兩種狀態都沒分出來**（rc=1 與 rc=2 都記成 RED）。<br>⇒ 同一條判準的兩種違反方式：**狀態沒分開**（我）／**狀態分開了但處置沒分開**（他）。**後者更難發現，因為日誌看起來是對的。** |
| **⭐ 為什麼記這條** | 這一輪五個 session 的協同，價值不在互相通報進度，而在**同一條判準套到不同 repo 上會得出不同的數字，而差異指出了各自的結構**（掛載 vs COPY、fail-closed vs fail-open）。單一 session 拿不到這個對照。 |
| **⚠️ 判準三：我的兩型歸納被對方修正了（同日稍晚）** | 我歸納出「狀態沒分開／狀態分開了但處置沒分開」兩型，`ck-website-37` 指出**直接套用會過度推論**：真正的判準是**處置有沒有副作用**。<br>· **無副作用**（出聲、記錄、算不算異常）⇒ **合併是對的**，只要輸出保留原狀態名 —— 那正是 fail-closed 判準的基礎。<br>· **有副作用**（resurrect／重啟／刪檔）⇒ 狀態必須各走各的路。<br>⇒ **合併本身不是錯的；錯的是在有副作用的路徑上合併。** 照我原本的形狀去查，會把他那 10 個設計正確的乘客全標成缺陷。 |
| **⭐ 用修正後的判準複查我自己的修法** | 我把 `rc=2` 從 RED 分出來，**是對的** —— 但理由要精確：不是因為「兩種狀態不該合併」，而是因為**合併之後走進了一條有副作用的路徑（去重抑制推播）**。若只是記成 RED 而不去重，那個合併其實無害。**修法正確、理由需要換一個。** |
| **⭐ 判準四（website）：用命令名掃，不要用動詞** | 他量「有副作用的自動處置」第一次得到 **13 處**，改成「只看 `spawnSync/execSync` 的第一參數」才是 **1 處**。動詞會把**討論這件事的註解**算成**做這件事的程式碼** —— 而這兩個 repo 的註解都特別多。<br>本 repo 實測：動詞掃命中 **57 個檔案**，改用 AST 取 `subprocess` 第一參數 → **4 處**。 |
| **⚠️ 而那個 4 是修正過的 —— 第一版是 0** | 首版詞表只有 docker/pm2 的動詞，**漏掉 `taskkill` / `alembic upgrade` / `pip install`**。是**正向控制**（先列出全部 131 處可解析的呼叫）才讓它們現形。⇒ 又一次印證「**收窄判準之後得到的零，要再查一次**」。 |
| **Refs** | L135（pm2 假綠）／L132（三態退出碼）／A71／`SESSION_COLLABORATION_RESPONSIBILITY.md`／`cross_session_review_beats_solo` 記憶檔 |

---

## L137 — 轉達 ≠ 背書：我把別人未查證的判型列進了給 owner 的待辦（2026-09-02）

| 欄位 | 內容 |
|---|---|
| **Trigger** | `ck-website-37` 交接一條 CK_PileMgmt 的問題（`PM2_Autostart` 回 exit 255 ⇒ 開機恢復鏈壞了、9 條治理 cron 沒恢復）。我依權責「只轉不動」，寫進 `OPEN_ITEMS` 並標明來源，**並在對話中向 owner 覆述了兩次**。 |
| **他同日主動撤回** | 真因是 `pm2` 撞上 **`connect EPERM //./pipe/rpc.sock`**，node 在未捕捉的 error event 上直接 abort ⇒ 整個 cmd 進程結束 ⇒ **rc=255，而 bat 後面所有行（含寫 log 的分支）都沒有機會跑**。**實際結果是成功的**：09:48:03 新 daemon 起來、cron 全數註冊。⇒ **待辦不成立，owner 不需要做任何事。** |
| **⭐ 我的錯（與他的錯不同）** | 他的錯是「把推論寫成實測」。**我的錯是轉達時只標了來源、沒有標查證狀態** —— 於是它在清單上與我自己實測過的項目長得一模一樣。<br>⇒ **轉達 ≠ 背書。** 標「來源是誰」只回答了「這是誰說的」，沒有回答「我查了嗎」。跨 session 協作裡，後者才是接收端需要的。 |
| **判準** | 轉述其他 session 的結論時，一律標 **「未經本 repo 查證」**；查證過的標明查了什麼。這是「把推論與實測分開標記」的跨 session 版本 —— **同一條紀律，只是不確定性的來源從我自己換成了別人。** |
| **⭐ 附帶：`ExitCode` 語意的第三例** | L127 是 `docker inspect .State.ExitCode` 回 0 而容器其實死於 136；本例是 **255 同時代表「失敗」與「成功但舊通道斷了」**。⇒ **非零退出碼不等於失敗，它只代表「這個進程沒有走到正常結束」。** |
| **⭐ 附帶：log 沒有新筆 ≠ 它沒跑** | `autostart.log` 停在 08-28，原本被當成「沒執行」的佐證。正確讀法是**「它跑了，但死在寫 log 之前」** —— 連 08-28 才加的 `FAILED rc=N` 分支都沒執行到，這反而**支持**真因。同 CLAUDE.md「我這條路徑找不到 ≠ 資料不存在」。 |
| **⭐ 他自己指出的第三層** | 「我在一個**剛發生共因事故**的環境上，把一個非零退出碼判成那支腳本自己的缺陷 —— 而我自己在同一份文件的 §三 就寫著『四站同時失聯要先排除宿主共因』。**我寫下的判準，我自己在 40 行之外就沒有套用。**」 |
| **⭐ 同日傍晚收斂：答案是 (a)，而我轉達的撤回本身也是未查證的** | `ck-website-37` 讀了 `~/.pm2/pm2.log`（檔案系統，pipe 權限擋不到）：09:48 只恢復 1/11 支，**14 分鐘什麼都沒有**，10:02 那批註冊是它的守衛做的。⇒ `MISSING 9/9` 是對的、resurrect 是必要的、**255 是部分失敗不是成功**。<br>**我在本條前面寫的「待辦不成立」是根據 pilemgmt 那支 bat 的註解「實際結果是成功的」——那句也沒有人去讀證據。我轉達了兩次未查證的結論，方向相反，兩次都寫進版控。** |
| **⭐ 他說的那句要記** | 「有證據的正確結論，和沒有證據的正確猜測，不是同一件事。後者這次剛好對，下次不會。⇒ 若因為結論後來被證實就回頭說撤回是多餘的，等於獎勵了猜測。」——撤回的理由（把推論寫成實測）至今成立，**與結論最後對不對無關**。 |
| **⭐ 最難堪的一層** | 他上午就讀了 `postboot-guard.log`、看到了 sso-health 的 10:00 缺口，**只是沒有去讀 `~/.pm2/pm2.log`**——一個不需要權限、就在本機、整天都在談的檔案。⇒ **判準與現場的距離，有時候不是行數也不是格式，而是「我有沒有想到去看」。而那個往往要靠另一個人問。** |
| **Refs** | `OPEN_ITEMS`（該條已改寫為撤回＋教訓）／L127（ExitCode 語意）／L136（跨 session 判準）／`SESSION_COLLABORATION_RESPONSIBILITY.md` §3 廣播內容的最低要求 |

---

## v6.0 detector 候選

未來實作 `scripts/checks/lessons_drift_check.py`：
- grep 最近 30 天 commit messages 含「修」「fix」「踩雷」「淬鍊」字眼
- 對比 LESSONS_REGISTRY.md 是否有對應 L##
- 若 commit 未 ref L## → 報「lesson 候選未登記」

讓 lesson registry 不成為下一個 dead doc。

## L138 — 同一份白名單有四份，而我上午才宣稱「已收斂成單一來源」（2026-09-02 晚）

| 欄位 | 內容 |
|---|---|
| **Trigger** | owner /goal「依前述建議逐一辦理、完整自我檢核」。我把 `case_name` 加進 `SYNC_FIELDS`，靜態檢核全綠、測試全過，然後在容器內打端點走整條鏈（標案建案→報價→成案→改名同步）：**PM 側改案名不同步，承攬側會**。 |
| **真因** | `pm/cases.py` 的兩個更新端點各自 inline 一份 `if k in ("category","case_nature","client_name","contract_amount")` —— 白名單的**第三、第四份**，連 `status` 都沒有。上午我把 `crud.py` 的第二份改成 import，commit 訊息寫「已改單一來源」；那次 grep 只找 `sync_fields = [` 這種寫法，對 inline tuple 是盲的。**weekly 101 首版判準③同樣只認那種寫法，印 GREEN。** |
| **⭐ 第二層（同支檢核判準②抓到）** | `sync_from_pm` 寫 `ERPQuotation.client_name`，而**模型沒有這個欄位**。`setattr` 設了一個 Python 屬性、不寫 DB、不報錯，從 03-30 建檔起就是這樣。**「同步做了」與「同步寫進資料庫」在程式碼裡長得一樣。** |
| **修法** | ①四份收斂為 `SYNC_FIELDS`／`CONTRACT_SYNC_FIELDS` 兩個常數、端點只 import；②移除對不存在欄位的寫入；③weekly 101 三判準：共有欄位覆蓋／**同步目標欄位必須存在於模型**／端點不得用字面清單過濾 changed（任何 `k in (...)`、`k in [...]`、`xxx = [...]` 內含兩個以上共有欄位名即 RED）。負向對照：判準②未修前抓 2、判準③擴寫後抓 2。 |
| **一般形式** | ①「收斂成單一來源」的驗收不是「我改的那份沒了」，是**用會走那條路的操作去打**——靜態 grep 找得到你想到的寫法，打端點找得到你沒想到的；②判準要問「有沒有人用字面清單做這件事」，不是「有沒有一個叫某名字的變數」（首版判準名稱錨定＝L126 同族）；③對 ORM 物件 `setattr` 一個不存在的欄位是靜默的，凡是「照欄位名寫入模型」的程式都該有「欄位存在於模型」的守門。 |
| **一併釐清** | 標案→PM 案 `source_tender_id` 0/253 **不是程式壞**：probe 證明 `create-case` 會寫入。是沒有人從標案頁建案（253 筆裡 179 由工作表匯入）。程式路徑活著而資料是 0，要分清「沒人走」與「走不通」。 |

---

> 此檔 v1.0（2026-04-28）首發 20 條 lesson，主要源自 v5.9.9~v5.10.1 累積。
> 跨 repo 引用 FQID：`CK_Missive#LESSONS_REGISTRY_v1.0`
