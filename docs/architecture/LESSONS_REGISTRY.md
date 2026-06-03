# Governance Lessons Registry — 治理教訓單點 SSOT

> **建立**：2026-04-28（v5.10.1）
> **目的**：解決「對策散落 commit/ADR/PLAYBOOK，新人需從 git log 重建脈絡」痛點
> **狀態**：accepted（單點查詢 SSOT，每月覆盤時更新）
> **適用對象**：當前/未來 Claude session、新進 owner、跨 repo 引用者
>
> **Why this exists（v5.10.1 owner 觀察）**：
> > 「我做了 R1→R7，每輪都是『發現 → 對策』，但對策都散落在 commit messages，
> > 沒有一個單點查詢的 lessons SSOT。下次 Claude session 接手，得從 git log 重建脈絡。」

每條 Lesson 含 5 欄位：
- **Trigger**：什麼情境會踩到（What to look for）
- **Cause**：根因（Why it happened）
- **Fix**：當時怎麼修（How it was fixed）
- **Prevention**：未來怎麼防（Don't repeat）
- **Refs**：commit / ADR / PLAYBOOK / FQID

跨 repo 引用 FQID：`CK_Missive#LESSONS_REGISTRY_v1.0`

---

## L01 — SSOT 聲明 vs 實作斷鏈（Dead Doc 反模式）

| 欄位 | 內容 |
|---|---|
| **Trigger** | ADR / 設計文件承諾「將實作 X」但實際從未建檔；scanner 報 dead config |
| **Cause** | PR 拆分後文件先 merge code 後做，PR 卡住 → ADR 變 dead doc |
| **Fix** | v5.9.9：補建 `backend/app/core/timeouts.py` SSOT（兌現 ADR-0028 承諾） |
| **Prevention** | ADR 必附 commit hash 證明已落地；ADR Lifecycle Check 加「文件提到的檔案不存在」detector |
| **Refs** | ADR-0028 / commit `284ef07e` / PLAYBOOK §4.9 |

## L02 — Yaml config 聲明卻 0 reader（Dead Config）

| 欄位 | 內容 |
|---|---|
| **Trigger** | yaml schema 寫了某欄位但 production code 0 呼叫點，scanner 報 dead |
| **Cause** | feature 設計時想到要支援，但實作 fallback 仍走 hardcoded |
| **Fix** | 兩種：(a) 真接線（`should_prefer_local` 案例）(b) 標 deferred marker（`inference_profiles` 案例） |
| **Prevention** | scanner v3 識別 `Status: pending integration` docstring → SKIP；新增 yaml 欄位需附 integration test 鎖定鏈路 |
| **Refs** | ADR-0030 patch A 案例 / commit `f0a3dc5a` / PLAYBOOK §4.9 |

## L03 — Mock.patch 路徑遷移（Wave 1 sub-batch B）

| 欄位 | 內容 |
|---|---|
| **Trigger** | service 從 `services/foo_service.py` 搬到 `services/foo/core.py` 後，test 內 `patch("services.foo_service.X")` 完全失效 |
| **Cause** | mock.patch 替換的是「使用該名稱的 namespace」，不是定義位置 |
| **Fix** | sed 批次更新所有 patch 字串到新路徑 |
| **Prevention** | 每個 sub-batch 完成 git mv 後立即 `rg --multiline 'patch\(\s*["\x27]app\.services\.<old>\.'` 預掃 + 修 |
| **Refs** | commit `173230f1` / PLAYBOOK §4.3 |

## L04 — Multi-line patch sed 失效（Wave 4 tender）

| 欄位 | 內容 |
|---|---|
| **Trigger** | sed 替換 patch 路徑後，test 仍 fail；`grep` 同行模式找到 0 處但實際有殘留 |
| **Cause** | Python 慣用法 `patch(\n  "..."\n)` 跨行，sed line-based 漏抓 |
| **Fix** | 必用 `rg --multiline`，殘留逐個 manual Edit（不用 sed） |
| **Prevention** | PLAYBOOK §4.3 補強 — 兩種格式都掃 |
| **Refs** | commit `74b3d262` / PLAYBOOK §4.8 |

## L05 — Class name collision（Wave 1 sub-batch C notification）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 子包多個模組定義同名類別（`notification.service.NotificationType` vs `notification.template.NotificationType`），`__init__.py` wildcard re-export 互相覆蓋 |
| **Cause** | 不同 service 各自演化出同名 type，未察覺衝突 |
| **Fix** | `__init__.py` 改 explicit re-export 主類別，子類型從具體 submodule import |
| **Prevention** | sub-batch C 設計時先 grep `^class ` 找重名 |
| **Refs** | commit `b106cc3a` / PLAYBOOK §4.4 |

## L06 — 內部循環 import → relative import（Wave 1 sub-batch A document）

| 欄位 | 內容 |
|---|---|
| **Trigger** | sub-batch 包含互相 lazy import 的 service（如 Facade pattern），stub 載入時造成循環死鎖 |
| **Cause** | stub 機制 + lazy circular import 互動 — stub 載入觸發 __init__.py 載入 import_facade，import_facade 又 lazy import stub → 死鎖 |
| **Fix** | 子模組間互引用必改 relative import (`from .core import X`)，完全不經過 stub |
| **Prevention** | sub-batch git mv 後跑 `grep -rn "from app\.services\.<old>" backend/app/services/<context>/` 找出所有內部 stub 引用，批次改 relative |
| **Refs** | commit `33d23776` / PLAYBOOK §4.5 |

## L07 — Private function (`_` 開頭) re-export（Wave 2 ERP）

| 欄位 | 內容 |
|---|---|
| **Trigger** | test 嘗試 `from app.services.<old> import _parse_head_qr` 等私有函數失敗，wildcard 不 export |
| **Cause** | Python `from module import *` 預設不 import 底線開頭名字 |
| **Fix** | stub 補 explicit re-export 私有函數清單 |
| **Prevention** | stub 建立後，grep `from app.services.<old> import _` 找出所有私有 import，補 explicit |
| **Refs** | commit `e1641e05` / PLAYBOOK §4.6 |

## L08 — Production caller 路徑同步（Wave 3 integration）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 大量 mock.patch 的 service（如 line_bot），即使 patch 路徑改了，仍多個 regression — 因 production caller 仍走舊 stub |
| **Cause** | stub 機制下 patch 失效 — patch 命中 `integration.line_bot.X` 但 dispatcher import 走 stub namespace 的 reference |
| **Fix** | sub-batch 完成後**production code 也批次 sed 改用新路徑**（不再走 stub） |
| **Prevention** | Wave 3+ 必做 `grep -rl "from app\.services\.<old>" backend/app/ backend/main.py` + sed |
| **Refs** | commit `bd5baeba` / PLAYBOOK §4.7 |

## L09 — Async mock 斷鏈（pre-existing test failures）

| 欄位 | 內容 |
|---|---|
| **Trigger** | pytest 報 `'coroutine' object is not iterable` / `StopAsyncIteration` |
| **Cause** | test 用 `MagicMock` 而非 `AsyncMock` 包 async function；或 side_effect iterator 被消耗完 |
| **Fix** | 個案修；本 session 多為 pre-existing，stash 對比證實非新 regression |
| **Prevention** | 每個 sub-batch git stash + 跑同套 test，確保 baseline 失敗清單與遷移後完全相同 |
| **Refs** | 多處：test_case_code / test_pm_case / test_agency_statistics 等 |

## L10 — Dead UI（後端實作但前端缺 UI）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶反映「某功能仍無法操作」，但 grep 後發現後端 endpoints 早已實作 |
| **Cause** | 後端先做 PoC + ADR 寫 routes 但前端 PR 卡住、或 ADR 沒寫 UI 需求 |
| **Fix** | v5.10.1：建 `AliasIntegrationDrawer` + 加 endpoints 常數 + UserManagementPage 觸發按鈕 |
| **Prevention** | 規劃 dead_ui_detector.py（cross-check `routes.py` 後端 endpoints vs `frontend/src/api/endpoints/`）；ADR 模板加 `## UI Integration` 段 |
| **Refs** | commit `03963499` / PLAYBOOK §6.5 |

## L11 — React Query staleTime + 0 invalidate = 60s 不刷新

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶反映「狀態更新後頁面沒及時刷新」 |
| **Cause** | useQuery `staleTime: 60_000` + 沒有任何 mutation `invalidateQueries(queryKey)` |
| **Fix** | 雙管齊下：(a) `refetchOnMount: 'always'` + 短 staleTime (b) 所有相關 mutation 加 invalidate |
| **Prevention** | 每個 useQuery 設計時即列「哪些 mutation 會影響此 cache」清單；invalidate 集中於 mutation hook（非 caller） |
| **Refs** | commit `244593d0` / 派工總覽 morning-status 案例 |

## L12 — Stub 算散戶 → entropy 短期不會降

| 欄位 | 內容 |
|---|---|
| **Trigger** | DDD 遷移 N 檔到子包後，service entropy 短期沒降反升 |
| **Cause** | scanner 把頂層 stub 也算 orphan；entropy = top_level / total，stub 仍佔分子 |
| **Fix** | 預期接受短期不降；待 v6.0 stub 移除後（grep 確認 0 caller）才會大幅降 |
| **Prevention** | retrospective / CHANGELOG 明確寫「stub 算散戶 → entropy 短期不變是預期」避免誤判 |
| **Refs** | PLAYBOOK §6 / WAVE_1_RETROSPECTIVE.md / 整體 entropy 29.4% → 23.5% 軌跡 |

## L13 — sed 替換漏掃 cross-cutting test 檔（Wave 8）

| 欄位 | 內容 |
|---|---|
| **Trigger** | sub-batch sed 跑完跑 target service 的 test 全綠，但全套件 pytest 報 N 個 regression |
| **Cause** | sed 只掃對應 test file（如 `test_system_health_service.py`），漏掃跨服務的 test（如 `test_agent_tools.py`）|
| **Fix** | sed 後跑 `grep -rln "app\.services\.<old>\." backend/tests/` 全掃 |
| **Prevention** | sub-batch 完成必跑全套件 pytest（不只跑 target test） |
| **Refs** | commit `bf69487c` |

## L14 — GitHub Actions 自動觸發產生雲端費用

| 欄位 | 內容 |
|---|---|
| **Trigger** | GitHub Actions push trigger 自動跑，每月累積費用 |
| **Cause** | CI workflows 預設綁 push event |
| **Fix** | 全 workflow 改 `workflow_dispatch` 唯一觸發 |
| **Prevention** | 所有檢查走本地 hook + monthly cron；新 workflow 預設手動 |
| **Refs** | feedback memory `feedback_no_github_actions_cost.md` / `.github/workflows/ci.yml` |

## L15 — Telegram 個人號當主推播通道（ADR-0027）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 主推播通道突然全斷（Telegram 個人號封禁） |
| **Cause** | admin push 全靠 Telegram 個人號 |
| **Fix** | 切 LINE；Telegram 維被動 bot；加 PII sanitizer |
| **Prevention** | 通道應**多供應**設計，從 day 1 用 `notification_dispatcher` 抽象至少 2 通道 |
| **Refs** | ADR-0027 / `telegram_content_sanitizer` |

## L16 — 一個 dataclass 塞 100+ 設定欄位

| 欄位 | 內容 |
|---|---|
| **Trigger** | 修一個 config 值找半天；dataclass 行數失控 |
| **Cause** | `AIConfig` 累積 50+ 欄位涵蓋 LLM / search / agent / pattern / compaction |
| **Fix** | （規劃）按 bounded context 拆 config — `AIConfig` / `SearchConfig` / `AgentConfig` |
| **Prevention** | 新 repo 從 day 1 即按 context 拆 config |
| **Refs** | TEMPLATE_EXTRACTION.md §3.6 |

## L17 — DDD 遷移看職責邊界不看行數

| 欄位 | 內容 |
|---|---|
| **Trigger** | service 行數 > 600 line 觸發拆分提醒，但內容單一 domain 完整實作 |
| **Cause** | 早期定義「行數驅動拆分」規則 |
| **Fix** | 改「職責驅動」— 1074 行單一 domain 不拆，200 行混三 domain 必拆 |
| **Prevention** | feedback memory 永久標 `feedback_ddd_over_line_count.md`；service-line-count-check.py 改僅警告不阻擋 |
| **Refs** | feedback memory / WAVE_1_RETROSPECTIVE.md |

## L18 — Wiki dispatch backfill 不需 fuzzy match

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

| 欄位 | 內容 |
|---|---|
| **Trigger** | `agent_evolution_history` 14d+ 0 新增；`crystals/` 持續空 |
| **Cause** | **2026-04-29 v5.10.2 根因確認 — 兩個 silent failure 疊加**：(1) `agent_post_processing.py:144` 用 `from app.core.redis import get_redis`，正確 module 是 `app.core.redis_client` → ImportError → 被 `except Exception: pass` 吞掉（違反 ADR-0028）→ `redis=None` → `should_evolve()` line 92 直接 return False → counter 永不 incr → evolution 永不跑 (2) `agent_evolution_health.py:44` 寫 `agent:evolution:query_counter`（多 `er`），scheduler 實際用 `agent:evolution:query_count` → health script 永遠報 counter=0 誤導 owner 判斷。crystallizer 鏈路（pattern→proposal）正常跑因為走別的路徑 |
| **Fix** | **v5.10.2** (1) `agent_post_processing.py:144` 改用 `app.core.redis_client` + silent `except` 改 `logger.error(exc_info=True)`（ADR-0028 合規）(2) `agent_evolution_health.py:44` 修 key 名稱對齊 scheduler。**實證**：fix 後送 1 次 agent query → counter `0 → 1` ✓，`agent:evolution:signals` + `eval_history` keys 出現 ✓ |
| **Prevention** | (a) Module 名稱以 string import 時加 unit test 驗 module 真實存在（避免 ImportError 被當例外吞）(b) Redis key 常數**集中到單一 const module** 供 scheduler + health script 共用，避免 typo 漂移(c) ADR-0028 守護擴大：silent `except: pass` 在 fitness 加 lint(d) Integration test 鎖定 `should_evolve()` 鏈路（avoid dead integration） |
| **Refs** | v5.10.2 fix commit pending / `agent_post_processing.py:144` / `agent_evolution_health.py:44` / `agent_evolution_scheduler.py` / 同類 L01 dead integration / **這是「silent failure × silent failure」疊加經典反例**（ADR-0028 教材） |

## L24 — Self-evaluator 標準過鬆 / Pattern 門檻過緊（雙重失衡）

| 欄位 | 內容 |
|---|---|
| **Trigger** | v5.10.2 #4 evolution 修復後審 Redis pattern 分布：53 個 pattern 全部 success_rate ≥ 0.95（無一例外），但 hit 分布偏低（23 筆 hit 1-2 / 5 筆 hit 3-4），結晶 candidates 累積太慢 |
| **Cause** | (a) `MIN_HIT_FOR_CRYSTAL=5` + `MIN_SUCCESS_RATE_FOR_CRYSTAL=0.95` 雙閘設計，預期「高成功 + 高頻」才結晶。實測 success_rate 全卡頂 → success 閘形同虛設，hit 閘變成唯一瓶頸 (b) self_evaluator 給分過鬆：每次 query 後評，但「能回應 = 高分」沒區分 hallucination / 找不到 / 完美回答（04-23 列無關公文 hallucination 仍評高分案例佐證） |
| **Fix** | （v5.10.2 評估記錄，未即刻 apply）門檻 5→3 立即解鎖 5 筆候選（+10%）。但更根本是修 self_evaluator 區分度 — 增加 negative-test hallucination 偵測規則 |
| **Prevention** | (a) Pattern 門檻調整前 dry-run，評估「會新增多少 promotion」(b) self_evaluator 應有 calibration test：人工標注 20 筆 query，看評分 vs 標注一致率，<70% 即報警 (c) success_rate 分布 entropy 監測 — 若全卡 1.0 即評分機制失效信號 |
| **Refs** | v5.10.2 Phase 4.1 評估 / `agent_evolution_scheduler.py:78-79` 門檻常數 / synthetic-baseline-inject.py 修正後仍 100% 高分問題 |

## L25 — 鏈路驗證 vs 鏈路盤點（grep 關鍵字陷阱）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 驗證「坤哥自我學習進化」鏈路 2（Failure → Defense rule → Planner prompt）時，初判 `load_active_defenses` 0 caller 即斷定 dead integration |
| **Cause** | 用了原始函式名稱關鍵字 grep，但實際 export 是包裝過的便捷函式 `get_defensive_rules_block`（agent_planner.py 用後者，不直接用 load_active_defenses）。「grep 找不到 caller」≠「沒有 caller」 |
| **Fix** | v5.10.2 KUNGE_LEARNING_VERIFICATION 救：補做 Phase C 直接呼叫該模組任一 export 函式看輸出，**1136 chars defense block 證實鏈路活著**。原判斷 dead 改為閉環 ✓ |
| **Prevention** | (a) 鏈路驗證**必跑實際呼叫**（asyncio.run + module call），不能只靠 grep (b) grep 時應掃整個模組所有 public export，不只 1 個關鍵字 (c) 對 dead integration 判斷加二次驗證——真試呼叫看輸出 |
| **Refs** | KUNGE_LEARNING_VERIFICATION.md §1 鏈路 2 / `auto_defense.py:97 get_defensive_rules_block` / 同類 L01（dead integration 判斷需證據而非假設） |

## L20 — Lessons 散落 commit/ADR/PLAYBOOK → 需 SSOT

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner / 新 Claude session 接手時，需從 git log + 7 份 doc 重建 incident 脈絡 |
| **Cause** | 對策淬鍊散在 commit messages（R1~R7）+ ADR 章節 + PLAYBOOK §4.x + RETROSPECTIVE 等 |
| **Fix** | v5.10.1：建本檔 `LESSONS_REGISTRY.md` 為單點查詢 SSOT |
| **Prevention** | 任何「發現 → 對策」必新增 L## entry 在本檔；commit message 末尾加 `Refs: L##`；`lessons_drift_check.py` (commit `2cee9943`) detector 月度跑防 dead doc |
| **Refs** | 本檔自身 / commit `3fd04734` / `lessons_drift_check.py` |

## L23 — 領域驅動拆分 vs 行數驅動拆分（拒拆判準）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 維護者看到「1000 行檔案」直覺反應「該拆」，提案把 morning_report_service.py (1,074L) / agent_orchestrator.py (642L) 拆成多檔 |
| **Cause** | 行數本身不是 DDD 邊界依據（feedback_ddd_over_line_count）：「1000 行單一領域不拆，200 行混三領域必拆」。但人對「大檔案」有本能厭惡，容易誤把行數當拆分理由 |
| **Fix** | **v5.10.2 評估後拒拆**（兩件案例驗證判準）：(1) `morning_report_service.py` 1,074L — 4 主題 sections（派工/會議/現勘/遺漏建檔）是「晨報生成」**單一領域內的層次分解**，`_get_*` (queries) / `_format_*` (formatting) / `_compute_*` (純函數) 是領域內 helper，不是混多領域。`morning_report_queries.py` (27L) 是 Phase 1 標記檔已預留 future 遷移路徑，但時機應在「新增領域邏輯時自然發生」(2) `agent_orchestrator.py` 642L — 7 個 method 全是 agent loop 不可分割環節（stream/tool loop/wiki ingest/trace flush）。原規劃「抽 plugin contract」評估後不必要：plugin pattern 已分散在 `agent_tools/` 子包、`agent_self_evaluator.py`、`agent_pattern_learner.py` 等別處 |
| **Prevention** | (a) 提案拆分時必先回答 3 個問題：① 內部方法是否屬不同 bounded subdomain？② 拆完後跨檔呼叫多還是單檔內呼叫多？③ 是否有外部消費者目前需要的 pattern？三題若無一個 yes → 不拆 (b) 對比範例：v5.10.2 #1 拆 `ai_stats.py` 692L (混 7 領域 → 拆) vs 本 lesson 不拆 morning_report 1,074L (單一領域) — 領域邊界才是判準 (c) 「行數是結果，不是目標」每次拆分後 commit message 要說明「拆出哪 N 個 bounded subdomain」 |
| **Refs** | v5.10.2 #6 評估 / `morning_report_service.py` (kept 1,074L) / `agent_orchestrator.py` (kept 642L) / 對比 `ai_stats.py` (拆 692L → 7 檔) / `feedback_ddd_over_line_count.md` |

## L26 — Half-Wired Anti-Pattern Stacking（多層 bug 疊加遮蔽）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶報告「一般使用者看到不該看的選單」，連續 3 次「修了 → 仍可看 → 再修」；單一現象背後 4 層獨立 bug 疊加（P-57 backend schema / P-58 frontend dev mode / P-59 NavTree UX / P-60 DB 資料漂移）。任一層沒修都看到「以為修了仍復現」假象。 |
| **Cause** | 多層獨立 bug 同時存在時，外層 bug 會 mask 內層 bug。修第一層後外觀沒變不代表沒修，而是被第二層遮住。維護者容易誤判為「上一個 fix 沒生效」而回滾，反而退步。 |
| **Fix** | v6.8+：建立「**穿透式驗證**」debug 邏輯。每修完一層，以 query「這層的修法在 unit test 通過了嗎」確認 → 若通過但用戶仍復現 → **下一層必有 bug**，繼續挖。將 `failure-sidebar-perm-4layer-stack.md` 立成範本案例。 |
| **Prevention** | (a) 大 incident debug 必有 task list 標記每層修法獨立 (b) 每修完一層立即 unit test + 文字描述「這層改了什麼會 affect 用戶看到什麼」(c) 用戶仍復現時不要回滾，假設「下一層仍有 bug」繼續挖 (d) 任一層修法都附 regression test 防回退 |
| **Refs** | `wiki/memory/failures/failure-sidebar-perm-4layer-stack.md` / commits P-57~P-60 / 同類 ADR-0025 13-day dormant |

## L27 — Dev Mode Override Trap（VITE_AUTH_DISABLED 強制覆蓋真實用戶）

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

| 欄位 | 內容 |
|---|---|
| **Trigger** | `site_navigation_items.permission_required = TEXT` 存 JSON 字串如 `'[]'`、`'["x:y"]'`，但 `_item_to_dict` / `nav_repo.get_children_recursive` 直接回傳字串。前端 `'[]'.length === 2 ≠ 0` → filter 失效以詭異方式破壞權限過濾。 |
| **Cause** | DB 用 TEXT 存 JSON 是常見折衷（避免 JSONB 跨 DB 相容性問題），但 endpoint 沒對應 parse helper → ORM column 型別與 API 對外型別不一致。新加的 `/admin/role-permissions/nav-tree` endpoint **正確** parse，但舊 `/secure-site-management/navigation/action` 漏 parse — schema drift 在 endpoint 層產生。 |
| **Fix** | P-57（5/07）：endpoint + repo 兩端對齊新增 `_parse_permission_required` helper（None / "" / "[]" / valid JSON / list / 損壞 → 安全 fallback []）。19 unit test 含 alignment test（兩 helper 對相同輸入產出相同結果）。前端 `useNavigationData` fallback 也改為「**只**放行真正空陣列」防禦式雙保險。 |
| **Prevention** | (a) 所有 `Column(Text, comment="JSON")` 在 dict 化前都過 helper parse + 加 unit test 鎖定型別轉換 (b) 任何 TEXT-as-JSON 欄位寫進 ER diagram comment 並警告「endpoint 必 parse」 (c) Schema drift 偵測：fitness step 加「同一 column 在不同 endpoint 是否型別一致」 (d) 長期願景：能用 JSONB 就不用 Text |
| **Refs** | `failure-sidebar-perm-4layer-stack.md` §層 1 / commit P-57 / `test_nav_permission_required_parse.py` (19 tests) / 對比正確 implementation：`role_permissions_admin.py` nav-tree endpoint |

## L30 — Pipeline Integration as Priority（環節不連通就是浪費）

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

| 欄位 | 內容 |
|---|---|
| **Trigger** | install.sh 拷 N 個檔，但每個檔 `import` 的真實依賴未在 manifest 列出 → consumer build/runtime fail |
| **Cause** | manifest.yml 設計時只列「主要安裝檔」，未追蹤每檔的 transitive deps (env.ts / authService / logger / hooks / common components / utility) — install.sh 機械拷貝主檔，consumer 揭發 5 層 deps 缺失 |
| **Fix** | (a) manifest schema v1.1 加 `transitive_dependencies` 欄位（framework_deps / schema_deps / runtime_deps）(b) install.sh 加 6-stage 守門：baseline → deps check → dry-run → install → verify build → smoke test (c) step 34 transitive_deps_audit AST 解析 import 鏈交叉驗證 manifest |
| **Prevention** | (a) 任何新 ck-* package manifest 強制 list transitive_deps (b) step 34 在 fitness gate 阻擋 unlisted_dep > 0 (c) install.sh `--strict` 模式跑 consumer 端 tsc + py_compile 驗證才報 install 成功 (d) 真採用嚴格定義 4 件齊備（install + 編譯 + 啟動 + hook 通過）|
| **Refs** | LR-015 / LR-016 lvrland session feedback / ADR-0036 §Lessons / manifest.yml v2.0 ck-navigation / step 34 transitive_deps_audit.py |

## L34 — 業務 specific 不可進 shared package（lvrland LR-020 對應 / 2026-05-18）

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v1.0 ship 業務 ROUTES (DOCUMENTS / AGENCIES / DISPATCH) hardcoded 在 useMenuItems.tsx → consumer 完全無對應路由 → install 後立即 19 TS errors |
| **Cause** | 模組化過程未區分「框架可移植」vs「業務專屬」— useMenuItems 表面是 hook 但實際是業務 navigation tree builder，30+ 個 ROUTES 寫死。lvrland LR-020 揭發：shared package 內絕不可有業務 specific 內容（route / enum / API path / business magic number） |
| **Fix** | (a) ck-navigation v2.0 完全移除 useMenuItems.tsx (b) PACKAGING_PATTERN Rule 8 No Business Constants Hardcoded (c) 業務 specific items 改 consumer 端 init script seed 入 DB / config |
| **Prevention** | (a) shared-modules/ 內絕不 import `*ROUTES*` / `*API_ENDPOINTS*` / 業務 enum (b) step 30 keyword audit + step 34 transitive deps audit 雙重 gate (c) 新 package 必過 portability score ≥ 1.000（無 critical / high）才能 release (d) PR review 強制 grep 業務 keyword in shared-modules/ |
| **Refs** | lvrland LR-020 / PACKAGING_PATTERN.md Rule 8 / step 30 module_portability_audit / ck-navigation v2.0 changelog |

## L35 — 採納前必過 baseline TS check（lvrland LR-019 對應 / 2026-05-18）

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v1.0 install 標榜「14/14 100% PORTABLE 0 conflicts」→ consumer 真 install 後 19 TS errors → revert 才回 0 errors。dry-run conflicts 0 ≠ runtime 可運作 |
| **Cause** | 「真採用」評估只看 file write + conflict count，**未跑 consumer 端 build/runtime 驗證**。lvrland LR-019 揭發：採納前必須先 npx tsc / py_compile 驗證 baseline，否則 install 是半接通 |
| **Fix** | (a) ADR-0036 §Lessons 立「真採用嚴格定義」4 件齊備（install + 編譯 + 啟動 + hook 通過）(b) install.sh 加 verify build stage（6-stage 守門）(c) lvrland 揭發 Webmap TS baseline = 0 — 純基線 forward (d) ck-navigation v2.0 在 lvrland 達 TS exit 0 (件 2 通過) |
| **Prevention** | (a) install.sh `--strict` 模式跑 consumer 端 tsc + py_compile + smoke test 才報 install 成功 (b) consumers.yml `real_adoption_criteria.criteria_met` 必 4/4 才可標記 verified (c) 任何 partial < 4/4 一律標 INSTALLED_PARTIAL_N_OF_4 不可誤稱 VERIFIED |
| **Refs** | lvrland LR-019 / ADR-0036 §Lessons / consumers.yml v6.10 P1 / install.sh 6-stage 守門（待 v1.1 升級）|

## L36 — Repo Structure Assumption（install.sh 寫死目標路徑 / 2026-05-18）

| 欄位 | 內容 |
|---|---|
| **Trigger** | ck-navigation v2.0 install.sh 寫死 `backend/app/api/endpoints/`，但 lvrland 用 `backend/app/api/v1/endpoints/` → 檔放錯位置 → 件 3 runtime smoke 失敗（Missive source 內 OK 但 consumer 結構差異）|
| **Cause** | Package source repo（Missive）的 backend structure 不等於所有 consumer 結構。lvrland 用 `v1/endpoints/` 規約 (API versioning)，pile/AaaP/hermes 可能各自不同。install.sh 不能寫死單一 target path |
| **Fix** | (a) install.sh 加結構偵測（Option A）：先掃 consumer 是否有 `backend/app/api/v1/endpoints/` 否則 fallback `backend/app/api/endpoints/` (b) manifest.yml 加 `target_patterns` 可配置欄位 (c) 補登 L36 入 LESSONS_REGISTRY (d) 加 PACKAGING_PATTERN Rule 10 「Target Path 必須可配置」 |
| **Prevention** | (a) install.sh 強制偵測 consumer 結構（不再寫死路徑）(b) 新 ck-* package 必加 target_patterns 多模式 (c) step 35 manifest_drift 加偵測 target_pattern 欄位是否存在 (d) consumer 採納前 owner 確認結構符合任一 target_pattern |
| **Refs** | lvrland P220 件 3 失敗 evidence (2026-05-18) / ck-navigation v2.0 install.sh / PACKAGING_PATTERN.md Rule 10（待補） |

## L22 — 範本資產缺跨 repo 引用治理規範

| 欄位 | 內容 |
|---|---|
| **Trigger** | 範本資產（playbook / lesson / detector / component）數量爆炸性增長（27+），但 consumer repo 不知如何引用、升級、回饋 |
| **Cause** | CK_AaaP/CONVENTIONS §1.3 只涵蓋 ADR FQID（`Repo#NNNN`），沒涵蓋範本資產的 FQID 命名 / 版本管理 / 引用模式 / 升級通知 / 貢獻回流規範 |
| **Fix** | v5.10.1：建 `CROSS_REPO_REFERENCE_GUIDE.md` 補完規範 — 5 大類別 FQID + 3 引用模式 + SemVer + 月度健檢 SOP + 27 範本資產目錄 + 4 個 consumer anti-pattern |
| **Prevention** | (a) 新增範本資產時必加 FQID 至 §6 目錄 (b) 升 minor/major 必更新 CHANGELOG `Note for consumers` 段 (c) `notify-consumers.py` (v6.0 規劃) |
| **Refs** | commit `b3112a9d` / `CROSS_REPO_REFERENCE_GUIDE_v1.0` / 同類 L20 dead doc 預防 |

## L37 — 覆盤報告自身也是「真活宣告 vs 真接通」候選（2026-05-19）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 寫策略級覆盤時，自然會在 §結論 / §演進方向 提出新標準 / 新 ADR / 新原則；但覆盤本身是 day-1 產出，未經 dogfood 即標榜「策略級體檢」。如 RETRO_20260519 §5 提 3 個 ADR 候選 vs §7.4「禁做新建抽象層 / 守護腳本 / 標準文件」自相矛盾，是 LR-015 同型反模式（建好門面 + 自評通過 + 無 dogfood）。|
| **Cause** | 覆盤代理 / 寫手對自身產出無 ROI 量測機制，傾向「結論越多越專業」。Effort 估計常 3-4 倍樂觀（如 §6 列 5h 但實際 10-13h）。風險分級易用 hyperbole（如 R1「隨時觸發」缺實際 user base 量測）。ROI 量化常混淆「使用率」與「ROI」（前者是分母，後者是分子÷分母）。|
| **Fix** | v6.10 P1：(a) 覆盤報告必附 `§自我檢視` 段落，列出至少 5 個自己看到的弱點（如 RETRO_20260519 §9 列 7 缺陷）(b) Effort 估計 × 2-3x 緩衝後再對外宣告 (c) 「真活定義」不可依賴掛了的監督機制（如 capability_usage_audit JSON parse fail 期間不可用作真活判定）(d) §禁做 原則必檢查與 §策略提議 自洽 |
| **Prevention** | (a) 覆盤報告必有「P0 半天可做」清單 + Effort 估計 × 2-3x 緩衝 + 與 §禁做 原則自洽性校驗 (b) §風險 R1-R6 等級宣告必附「實際引爆率量測待補」(c) ROI 量化嚴格區分「使用率」「成本投入」「outcome 量」三維 (d) 報告產出後 7 天 owner check-in：本報告自己有沒有變 dead doc |
| **Refs** | `docs/architecture/RETRO_20260519_strategic_health_check.md` §9（自我檢視 7 缺陷）/ ADR-0036 §Lessons LR-015 / 同類 L30/L31 dead investment / 覆盤工具自身也犯反模式 = 元教訓 |

## L39 — QueryKey Drift（React Query invalidate silent dead）（2026-05-20）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶報「派工 158 公文對照僅 1 筆又出現 2 筆紀錄（類似問題已多次發生）」。DB + Redis cache 都實際 1 筆，但 UI 顯示 2 筆 — frontend React Query cache stale。深掘揭發：真實 list query 用 `queryKeys.taoyuanDispatch.orders(params)` = `['taoyuan-dispatch-orders', params]`，但所有 mutation invalidate 寫 `['dispatch-orders']` —— **兩個 key 完全不重疊**！5/18 第一次案例已加 invalidate 但 silent dead（永不生效），用戶 5/20 第二次踩 = 慢性 bug 真因。|
| **Cause** | **與 L29 dict-key drift 同型反模式**：A 邏輯寫 key X、B 邏輯讀 key Y、X≠Y 但兩端都以為對齊 → silent failure 累積。React Query `invalidateQueries({ queryKey: ['dispatch-orders'] })` 對 `useQuery({ queryKey: ['taoyuan-dispatch-orders', ...] })` 不起作用（prefix 不同）。命名漂移源：早期可能用 `['dispatch-orders']`，後改 `queryKeys.taoyuanDispatch.orders()` SSOT 但 invalidate 路徑沒同步更新。5/18 第一次 fix 又再次用舊散戶 key 寫死，沒走 SSOT。|
| **Fix** | v6.10.1 (5/20): (a) `useDispatchCacheInvalidator.ts`：DISPATCH_ORDERS_KEY 改用 `['taoyuan-dispatch-orders']` + 保留 legacy `['dispatch-orders']` 防其他散戶 query (b) `useDocuments.ts:176`：invalidate 改用 `queryKeys.taoyuanDispatch.all` SSOT + 仍保留 legacy key (c) 清 Redis backend cache `cache:dispatch:list:*` (d) 用戶 Ctrl+Shift+R 後 UI 應變 1 筆。|
| **Prevention** | (a) 任何 `invalidateQueries({ queryKey: [...] })` 必引用 `queryKeys.<module>.<entity>` SSOT，**禁止散戶手寫字串陣列** (b) 加 fitness step `queryKey_drift_audit.py`：grep 全 codebase invalidate keys vs useQuery keys 做交集 — 任何 invalidate key 未對應任一 query key 即報 (c) `useCacheInvalidator` 類 helper 集中所有 invalidate 入口，禁止 component 內直接呼叫 `invalidateQueries` (d) 任何 chronic bug「類似問題已多次發生」**第一個假設就是 silent dead invalidate / drift / wiring**，不要假設 backend bug |
| **Refs** | 用戶 5/20 報案（image dispatch=158）/ `frontend/src/hooks/taoyuan/useDispatchCacheInvalidator.ts:36` / `frontend/src/hooks/business/useTaoyuanDispatch.ts:48` / `frontend/src/config/queryConfig.ts` queryKeys.taoyuanDispatch.orders / 同類 L29 dict-key contract drift + L21 redis key 名稱漂移 + L28 JSON-as-TEXT schema drift（drift 反模式三件套）|

## L38 — 平時保險（cron / 異地備份）也是 LR-015 反模式高發區（2026-05-19）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 用戶 5/19 指出「Docker Desktop 升級會清 volume．．．不可發生之錯誤」。盤點發現 CK_Missive 三重風險：(1) Windows Task Scheduler 無 `CK_Missive_Daily_Backup` 任務（5/16 後完全沒跑），但 setup_scheduled_task.ps1 寫了；(2) `backend/config/remote_backup.json` 14 天 `sync_enabled: false`，異地備份 0 次；(3) docker-compose.infra.yml 全用 named volume — Docker Desktop reset / WSL distro unregister 會**全清**。5/12 `ck_missive_backup_20260512_020000.sql` size=0（pg_dump 失敗仍 touch 檔）— 是 ADR-0028 silent failure 的備份版。|
| **Cause** | 過去討論 LR-015 都聚焦「**新建抽象層 + 自評通過**」（如 ck-navigation v1.0 標榜 portability 1.000 後爆 19 TS errors），但平時保險也是同型反模式：(a) 「排程應該在」≠「排程真在」(b) 「sync_enabled 該 true」≠「實際是 true」(c) 「named volume 可用」≠「升級後仍可用」(d) 「backup 跑完」≠「backup 檔有效」。共同病灶：機制建好後**從未驗證 wiring 真活**。|
| **Fix** | v6.10 P1（2026-05-19，1.5h 內）：(a) `scripts/backup/pre_upgrade_backup.sh`（96 行）4 層緊急備份（PG custom dump + PG SQL.gz + Redis rdb + 2 個 volume tar）+ NAS 異地同步 (b) `scripts/backup/restore_from_volume_tar.sh`（102 行）bit-perfect 還原 (c) `docs/runbooks/docker-desktop-upgrade-sop.md`（9 段）升級前 / 中 / 後 SOP (d) 立即跑 emergency backup 269MB 本機 + 272MB NAS Z 異地 — pg_dump 79MB / SQL.gz 76MB / Redis rdb 380KB / PG volume tar 193MB / Redis volume tar 149KB |
| **Prevention** | (a) 所有「保險機制」必每月跑一次 **real restore drill**（非假設）才算真活；本月 5/19 危機即 first drill (b) backup script 必加 `[[ -s "$file" ]]` 0B 檢查 + 失敗 Telegram alert（防 5/12 同類）(c) 用 `Get-ScheduledTask` / cron 真活 probe 補進 `optimization_pipeline_orchestrator` 環節（pipeline-reports JSON 每日記錄 last_run_time）(d) named volume → host bind mount 結構性升級（停機 5min，根除 Docker Desktop reset 風險）(e) `remote_backup.json sync_enabled` 改 true 後加 `sync_status alert`（連續 24h idle → red）|
| **Refs** | `scripts/backup/pre_upgrade_backup.sh` / `scripts/backup/restore_from_volume_tar.sh` / `docs/runbooks/docker-desktop-upgrade-sop.md` / `RETRO_20260519` §10 / 同類 L01 dead integration + L30 pipeline integration + L37 覆盤自身反模式 |

## L41 — JWT Secret Drift Silent Fail（4 重疊加 / 2026-05-21）

| 欄位 | 內容 |
|---|---|
| **Trigger** | 員工 SSO Phase 1.5 整合 missive 時 `verify_ck_sso_jwt` 持續回 401，owner 花 6 小時逐項排除才找到「`.env` CK_SSO_JWT_SECRET hex 與 CF Pages JWT_SECRET 打錯一字元」。四重反模式疊加：(1) secret drift（手動 copy 失誤）(2) silent fail（`logger.debug` 在 prod INFO level 永不輸出）(3) 異常吞噬（單一 `except JWTError` 不分 SIGNATURE/EXPIRED/ISSUER/MISSING_CLAIM 四種子型）(4) 缺真 E2E（CI 用 mock JWT 全綠，從未跑「真 CF Pages 簽 → 真 backend 驗」端到端）|
| **Cause** | 每個反模式單獨都不致命，**疊加構成驗證永遠失敗、永遠靜默的死區**。與 L37 同型「平時看不到反模式」家族 — verify 失敗本是高頻事件，但被降級為 debug 後等於沒發生。與 L29 dict-key drift 同型 cross-side mismatch，但 L41 是「兩 hex string 跨環境同步」非「dict key 同 codebase 漂移」。|
| **Fix** | (a) 全 4 種 JWT exception 分別 `logger.warning` + 區分子型訊息 (b) `verify` 失敗 log 含 expected_issuer / hex_length（不漏 secret 本體）(c) `ck-sso-py/install.sh` v1.0 內建 4 acceptance check 強制 (Check 1 grep `.env`、Check 2 grep `logger.warning`、Check 3 bridge endpoint health、Check 4 owner 真 E2E) (d) Check 1+2 自動，3+4 必手動 — 自動 fail 拒絕 install，提示 owner 不可省 Check 4 |
| **Prevention** | (a) 任何「跨環境 secret 同步」流程加 hex 比對 self-test（不洩漏內容但比較 hash 前 8 chars） (b) 任何「驗證型」endpoint 預設 `logger.warning` 失敗、單元測試 cover 4+ 種失敗子型 (c) 跨 repo 共用模組必走 `install.sh` 含「真接通」自動 check + owner manual gate (d) 「採用」定義升級：程式進 repo + import 不報錯 + owner E2E pass = 真採用 |
| **Refs** | `D:/CKProject/CK_Missive/shared-modules/ck-sso-py/install.sh` v1.0 (4 acceptance check) / `D:/CKProject/CK_Website/docs/SSO-IMPLEMENTATION-STATUS.md` v1.2 / 真採用範本 `CK_lvrland_Webmap/backend/app/core/ck_sso.py` + `CK_PileMgmt/backend/app/core/ck_sso.py` / 獨立 lesson 檔 `wiki/memory/lessons/L41_jwt_secret_drift_silent_fail.md` / 同類 L37 silent-debug + L29 contract drift + L21 silent-fail 累積元教訓 |

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

| 欄位 | 內容 |
|---|---|
| **Trigger** | L60 立法後 PileMgmt 真活反治理 commit `2a51d57b5`（跨 repo 污染守門）案例研究。|
| **Cause** | 上游強推範本 → 下游需「反治理」守門（防 CK_Missive 特定內容污染 sibling repo）。|
| **Fix** | PileMgmt 新增 `test_no_missive_contamination.py` 兩層守門（檔名/目錄禁帶 + 內容指紋掃描）+ fork-contract.md 邊界文件化 + pre-push enforce。|
| **Prevention** | 下游 repo 對上游範本有「反治理守門」權；污染守門用內容指紋（非裸字）避誤報合法跨 repo 引用。|
| **Refs** | `wiki/memory/lessons/universal/L61_downstream_reverse_governance.md` / 同層 L58/L59/L60 |

## L60 — 平衡 = 結構正常化（非中間值）（2026-05-30，meta-治理第 8 句立法）

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner 追問「如何取得治理平衡」；同日 PileMgmt 自然回滾 install-template 真活驗證。|
| **Cause** | 把「平衡」誤解為中間值/折中，實際應是每層各司其職 + 明確邊界 + 動態調整。|
| **Fix** | ROI 公式 5 維度延伸 + 範本分級 L1/L2/L3 + 下游反治理權（與 L58/L59 三位一體）。|
| **Prevention** | 治理強度不取中間值；以「結構正常化」（角色邊界正確）為目標，動態調整而非固定比例。|
| **Refs** | `wiki/memory/lessons/missive-specific/L60_balance_via_structural_normalization.md` |

## L59 — 治理架構倒置（上游 meta 缺 audit / 業務 source 反向 audit 子專案）（2026-05-30）

| 欄位 | 內容 |
|---|---|
| **Trigger** | CK_AaaP 名義 meta-governance index，但治理成熟度落後它索引的 source（CK_Missive 88 audit vs AaaP 0 scripts/checks）。|
| **Cause** | 「該是」CK_AaaP→各 repo，「實際」CK_Missive→4 子專案（反向）。上游只定 standard 不 enforce。|
| **Fix** | 立法第 7 句：meta 上游須自帶 audit；治理方向校正（v6.12 路線）。|
| **Prevention** | meta-governance repo 必須有 enforce 機制（非只定 convention）；否則治理方向倒置。|
| **Refs** | `wiki/memory/lessons/missive-specific/L59_governance_architecture_inversion.md` |

## L58 — 治理範本污染風險（強推 132 檔 57% 為本專案特定）（2026-05-30）

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

## v6.0 detector 候選

未來實作 `scripts/checks/lessons_drift_check.py`：
- grep 最近 30 天 commit messages 含「修」「fix」「踩雷」「淬鍊」字眼
- 對比 LESSONS_REGISTRY.md 是否有對應 L##
- 若 commit 未 ref L## → 報「lesson 候選未登記」

讓 lesson registry 不成為下一個 dead doc。

---

> 此檔 v1.0（2026-04-28）首發 20 條 lesson，主要源自 v5.9.9~v5.10.1 累積。
> 跨 repo 引用 FQID：`CK_Missive#LESSONS_REGISTRY_v1.0`
