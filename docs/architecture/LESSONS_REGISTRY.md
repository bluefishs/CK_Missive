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

## L20 — Lessons 散落 commit/ADR/PLAYBOOK → 需 SSOT

| 欄位 | 內容 |
|---|---|
| **Trigger** | Owner / 新 Claude session 接手時，需從 git log + 7 份 doc 重建 incident 脈絡 |
| **Cause** | 對策淬鍊散在 commit messages（R1~R7）+ ADR 章節 + PLAYBOOK §4.x + RETROSPECTIVE 等 |
| **Fix** | v5.10.1：建本檔 `LESSONS_REGISTRY.md` 為單點查詢 SSOT |
| **Prevention** | 任何「發現 → 對策」必新增 L## entry 在本檔；commit message 末尾加 `Refs: L##` |
| **Refs** | 本檔自身 / commit `<this-commit>` |

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
