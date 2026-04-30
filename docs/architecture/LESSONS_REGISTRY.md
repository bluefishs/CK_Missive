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

## L22 — 範本資產缺跨 repo 引用治理規範

| 欄位 | 內容 |
|---|---|
| **Trigger** | 範本資產（playbook / lesson / detector / component）數量爆炸性增長（27+），但 consumer repo 不知如何引用、升級、回饋 |
| **Cause** | CK_AaaP/CONVENTIONS §1.3 只涵蓋 ADR FQID（`Repo#NNNN`），沒涵蓋範本資產的 FQID 命名 / 版本管理 / 引用模式 / 升級通知 / 貢獻回流規範 |
| **Fix** | v5.10.1：建 `CROSS_REPO_REFERENCE_GUIDE.md` 補完規範 — 5 大類別 FQID + 3 引用模式 + SemVer + 月度健檢 SOP + 27 範本資產目錄 + 4 個 consumer anti-pattern |
| **Prevention** | (a) 新增範本資產時必加 FQID 至 §6 目錄 (b) 升 minor/major 必更新 CHANGELOG `Note for consumers` 段 (c) `notify-consumers.py` (v6.0 規劃) |
| **Refs** | commit `b3112a9d` / `CROSS_REPO_REFERENCE_GUIDE_v1.0` / 同類 L20 dead doc 預防 |

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
