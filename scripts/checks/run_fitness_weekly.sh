#!/bin/bash
# ============================================================
# Fitness Tier 2 Weekly — 12 trend tracking step (~3 min)
#
# v6.12 治理進化 #2 完整落地 (2026-05-30)
# 對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md §4
#
# 包含 step (趨勢追蹤 + governance metric):
#   - 3 SOUL.md mirror drift
#   - 4 Wiki↔KG link audit
#   - 5 KG pgvector embedding 覆蓋率
#   - 7 Agent evolution health
#   - 10 Memory Wiki metrics alive
#   - 11 SOUL evolution alive
#   - 21 alias_rls_audit
#   - 51 tender_freshness_audit
#   - 53 tender_subscription_watchdog
#   - 55 tender_enrichment_freshness
#   - 59 diary density audit
#   - 61 facade adoption audit
#
# 用法:
#   bash scripts/checks/run_fitness_weekly.sh           # warning mode
#   bash scripts/checks/run_fitness_weekly.sh --strict  # 任一 RED exit 1 (cron 用)
#
# 失敗動作 (--strict 模式):
#   - 連續 2 週同 step RED → 推 LINE 提示 owner 排 sprint
# ============================================================

set -uo pipefail

STRICT=false
if [[ "${1:-}" == "--strict" ]]; then
    STRICT=true
fi

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TOTAL_STEPS=$(grep -cE '^[[:space:]]*run_step "' "$0")
echo -e "${CYAN}===========================================${NC}"
echo -e "${CYAN} Fitness Tier 2 Weekly — ${TOTAL_STEPS} trend step  ${NC}"
echo -e "${CYAN}===========================================${NC}"
echo ""

FAIL_COUNT=0
FAIL_STEPS=()
# 2026-08-13：逐步結果歷史。原本只記整體 rc，於是無法回答兩個問題 ——
# 「哪些檢核從來沒紅過」（要嘛防的事不會發生，要嘛它根本不會紅）
# 與「哪些紅了但沒人處理」（那是噪音，會稀釋真訊號）。
# 這兩個數字才是「檢核機制健不健康」的真實指標，不是步數。
STEP_RESULTS=()
WARN_COUNT=0
WARN_STEPS=()

# 註（2026-08-03）：**刻意不傳 --strict 給子腳本**。
# 各 audit 的 --strict 語意是「任何 warning 也 exit 2」，會把 YELLOW 升級成 RED——
# 例如 tender_freshness 的「3 天 stale」其中 2 天是週末（政府不發標），
# 傳 --strict 就變成每個週末都告警。不傳旗標時各腳本回原生三態
# （0=GREEN / 1=YELLOW / 2+=RED），由本腳本自己決定哪一級才 exit 1。
#
# 前一版曾用 detect_flag() 依 --help 偵測該傳哪個旗標，那是為了解決
# 「23 步只有 5 支認得 --strict、其餘 argparse 直接報錯」的問題（連 9 週假紅）。
# 現在改為一律不傳，那個問題自然消失，偵測函式也就不需要了。

# 2026-08-05：總步數改為**自我推導**，不再寫死。
# 原本表頭寫死總數，加了步驟卻沒改它 —— daily 實際 9 步印「/8」、
# weekly 實際 28 步印「/27」。兩個數字描述同一件事就會漂，
# 而這種漂移剛好出現在「用來檢查別人漂移」的腳本上。
# ─────────────────────────────────────────────────────────────────────────
# 自我完整性檢查（2026-08-29）：**本檔自己壞掉時，後面的步驟一步都不會跑。**
#
# 實例：我加 `--ci` 時把註解插進「步驟名」與「腳本路徑」之間，路徑掉到
# 下一行變成獨立語句 ⇒ `run_step "64" "名稱"` 只有兩個參數 ⇒
# `set -u` 下 `$3` unbound 直接致命 ⇒ **第 64~86 步一步都沒跑**，
# 而那包含我當天新增的全部 8 支檢核。
#
# 更糟的是它**看起來像跑完了**：前 63 步逐一印 GREEN、退出碼 0，
# 只有輸出末尾一句 `line 76: $3: unbound variable`。
# ⇒「訊號存在但沒有接收者」的自身版本。而它**已經被提交進版控**，
#   若不是我實跑一次完整 weekly，不會發現。
_self_check() {
    local bad=""
    while IFS= read -r line; do
        # 每個 run_step 必須有三個帶引號的參數（編號／名稱／腳本路徑）
        local q
        q=$(printf '%s' "$line" | tr -cd '"' | wc -c)
        if [ "$q" -lt 6 ]; then bad="$bad$line"$'
'; fi
    done < <(grep -nE '^[[:space:]]*run_step ' "$0")
    if [ -n "$bad" ]; then
        echo -e "${RED}✗ run_fitness_weekly.sh 自身損壞：以下 run_step 缺少參數${NC}"
        printf '%s' "$bad"
        echo -e "${RED}  set -u 下這會讓 runner 從該行起全部中止 —— 後面一步都不會跑。${NC}"
        exit 2
    fi
}
_self_check

run_step() {
    local step_num="$1"
    local step_name="$2"
    local script="$3"

    # 2026-08-17：`$3` 可能帶參數（如 "xxx.py --gate"），
    # 而 `-f` 是拿整串去比對檔案 → 判成「腳本不存在」＝**假紅**。
    # step 51 就是這樣連紅的：腳本明明在，只是名字後面多了一個旗標。
    # 取第一個 token 當檔名，其餘原樣傳給 python。
    local script_file="${script%% *}"

    echo -e "${CYAN}[$step_num/${TOTAL_STEPS}] $step_name${NC}"
    if [[ ! -f "$script_file" ]]; then
        # 腳本不見了要算失敗 —— 原本只印一行 warning 就 return，
        # 等於「檢查消失」與「檢查通過」同樣是綠（alias_rls_audit 正是這個狀況）。
        echo -e "  ${RED}✗${NC} script not found: $script"
        FAIL_COUNT=$((FAIL_COUNT+1)); FAIL_STEPS+=("$step_num $step_name (腳本不存在)")
        echo ""
        return
    fi

    # 計數與「是否 exit 1」必須分離。
    # 2026-08-02 修：原本非 --strict 分支是 `|| true`，FAIL_COUNT 恆為 0
    # → 結尾**永遠印「✅ all passed」，不管實際紅幾步**。當日實跑：中間明明
    # tender_freshness（48 天陳舊）與 cross-repo template drift 兩步 RED，結論卻是全綠。
    # 子腳本不帶 --strict 時本來就會回非 0（實測 2 / 1），資訊一直都在，是被 `|| true` 丟掉。
    # warning mode 的語意是「不阻斷」，不是「不報告」。
    # 三態：0=GREEN / 1=YELLOW / 2+=RED（見上方「刻意不傳 --strict」說明）
    local rc=0
    # 不加引號：`$script` 可能是 "xxx.py --gate"，加引號會整串被當成檔名。
    # 這裡的路徑與旗標都不含空白，展開是安全的。
    # shellcheck disable=SC2086
    PYTHONIOENCODING=utf-8 python $script 2>&1 || rc=$?
    STEP_RESULTS+=("$step_num|$step_name|$rc")
    if [[ $rc -eq 1 ]]; then
        WARN_COUNT=$((WARN_COUNT+1)); WARN_STEPS+=("$step_num $step_name")
    elif [[ $rc -ne 0 ]]; then
        FAIL_COUNT=$((FAIL_COUNT+1)); FAIL_STEPS+=("$step_num $step_name")
    fi
    echo ""
}

# Step 1-12
run_step "1" "SOUL.md mirror drift"           "scripts/checks/soul_mirror_drift_check.py"
run_step "2" "Wiki↔KG link audit"             "scripts/checks/wiki_kg_link_audit.py"
run_step "3" "KG pgvector embedding 覆蓋率"   "scripts/checks/kg_embedding_coverage_check.py"
run_step "4" "Agent evolution health"         "scripts/checks/agent_evolution_health.py"
run_step "5" "Memory Wiki metrics alive"      "scripts/checks/memory_metrics_alive_check.py"
run_step "6" "SOUL evolution alive"           "scripts/checks/soul_evolution_alive_check.py"
# 2026-08-02 修檔名：原引用 alias_rls_audit.py（不存在），實際是 step 21 的 coverage 版。
# 原本「腳本不存在」只印 warning 不計失敗 → 這一步等於從未執行過而沒人知道。
# ⚠️ 2026-08-29 補 --ci：基線鎖（禁淨增）**只在 --ci 模式生效**，而這裡原本沒帶 ⇒
#   自 2026-05-19 建立起從未被執行過。帶 --ci 的 run_fitness.sh 是手動月度觸發、
#   非排程 ⇒ 三個月來它允許淨增 29 個未稽核 user filter 而不會有人知道。
run_step "7" "alias_rls coverage audit（含基線鎖）" "scripts/checks/alias_rls_coverage_audit.py --ci"
run_step "8" "tender_freshness"               "scripts/checks/tender_freshness_audit.py"
run_step "9" "tender_subscription_watchdog"   "scripts/checks/tender_subscription_watchdog_audit.py"
run_step "10" "tender_enrichment_freshness"   "scripts/checks/tender_enrichment_freshness_audit.py"
run_step "11" "diary density audit"           "scripts/checks/diary_density_audit.py"
run_step "12" "facade adoption audit（僅報告·不判紅）"         "scripts/checks/facade_adoption_audit.py"
run_step "13" "paths.py vs compose mount"     "scripts/checks/paths_compose_mount_audit.py"
run_step "14" "governance alignment audit"    "scripts/checks/governance_alignment_audit.py"
run_step "15" "cross-repo template drift"     "scripts/checks/cross_repo_template_drift_audit.py"
run_step "16" "cross-repo uncommitted audit"  "scripts/checks/cross_repo_uncommitted_audit.py"
run_step "17" "hermes baseline gate audit"    "scripts/checks/hermes_baseline_gate_audit.py"
run_step "18" "paths sub-path mount audit"    "scripts/checks/paths_subpath_mount_audit.py"
run_step "19" "repository coverage audit"     "scripts/checks/repository_coverage_audit.py"
run_step "20" "cross-domain link audit"       "scripts/checks/cross_domain_link_audit.py"
run_step "21" "knowledge dedup audit"         "scripts/checks/knowledge_dedup_audit.py"
run_step "22" "graph domain tagging audit"    "scripts/checks/graph_domain_tagging_audit.py"
# 2026-08-02：docs/architecture 累積 102 份文件卻無任何檢核在問「還算數嗎」
run_step "23" "doc reference integrity"       "scripts/checks/doc_reference_integrity_audit.py"
run_step "26" "文件宣稱數字納管"             "scripts/checks/doc_baseline_claim_audit.py"
run_step "27" "憑證存活稽核（提請複查）"       "scripts/checks/credential_liveness_audit.py"
# 2026-08-05：15 支跑在 host 的 Windows 排程（三個 repo 的自我走查、能力快照、
# 異地備份、Hermes tick）**沒有任何人在看**。既有 scheduler_liveness_audit 管的是
# 容器內 APScheduler。「排程註冊了不等於排程會跑」已踩過三次，且手動呼叫都會過。
run_step "28" "Windows 排程存活"             "scripts/checks/windows_task_liveness_audit.py"
# 2026-08-27：ecosystem.config.js 宣告三支 PM2 服務（health-watchdog /
# synthetic-baseline / invoice-watcher），而 pm2 上**一支都沒有在跑**。
# 其中 health-watchdog 的「假死自動復原」沒有等價物 ——
# Docker 不會因為 unhealthy 就重啟容器，restart:always 只在程序結束時作用。
# 與 step 28 同一個家族（宣告 vs 實際），刻意放在一起。
# ⚠️ 編號 71 而非 70：2026-08-27 我與同 repo 另一個 session 同時加步驟，
#    兩邊都取了 70（對方的「廠商身分源頭一致」在檔案後段）。
#    改我這支而不是對方的 —— 動自己加的東西不會撞到別人正在編輯的檔案區段。
#    編號因此不隨檔案順序遞增，那是可接受的（本檔本來就有 23→26 的跳號）。
run_step "71" "PM2 宣告 vs 實際在跑"          "scripts/checks/pm2_declared_vs_running_audit.py"

# 2026-08-27：四支「強制規範的守門腳本」先前**沒有任何東西在跑它們**。
#
# 鏈斷在三個地方，而每一段看起來都像已經接好了：
#   ① `scripts/checks/README.md` 把它們列在「⏰ 後端排程（scheduler.py）」底下 ——
#      而 `scheduler.py` **一次都沒提到它們**（實測 grep -c 全為 0）。
#   ② 真正的執行者設計上是 `.git/hooks/pre-commit`，而那支 hook 裡**一支都沒有**
#      （檔案自 2026-05-27 未再更動）。
#   ③ orchestrator 有一步 `_precommit_hook_probe` 正是要抓②，
#      **但它跑在容器裡，而 `.git/` 刻意不 mount** ⇒ 它回 `info: skipped`，
#      自 2026-05-31 起每天都是這個結果。**能抓到的地方它不跑，跑的地方它抓不到。**
#
# `async_session_race_guard` 守的是 `development-rules.md` §5.1／ADR-0021
# （asyncio.gather 不得共用 db session）—— 規範寫著**強制**。
#
# 接到 weekly 而不是加回 pre-commit：host 端、進版控、不增加每次提交的延遲
# （08-26 才因為同樣的理由把 tsc 從 PostToolUse 拿掉）。
# ⚠️ 實測四支目前**全部通過**（一個 WARN）—— 這是把潛伏缺口補上，
#    不是修一個正在發生的問題。
run_step "72" "並行 DB session 競態（ADR-0021 強制規範）" "scripts/checks/async_session_race_guard.py"
run_step "73" "SSE 端點必須顯式 identity 編碼"        "scripts/checks/sse_headers_guard.py"
run_step "74" "Schema 不得觸發 ORM lazy-load"          "scripts/checks/schema_lazy_load_guard.py"
run_step "75" "pattern YAML id-like 欄位型別"          "scripts/checks/pattern_yaml_type_guard.py"

# 2026-08-27：本表自己的守門人。
# `declaration_gate`（本表的另一個守門人）只驗「這支腳本有沒有被宣告」，
# **宣告是不是真的先前沒有人驗** —— 首跑就抓到 7 支宣告錯了，
# 其中四支（含 ADR-0021 強制規範）宣告的執行者一次都沒提到它們。
run_step "76" "README 宣告的執行者是不是真的在跑它" "scripts/checks/declared_runner_truth_audit.py"

# 2026-08-27 owner 立案：「前述成案程序的問題就是核心要管控」
# 「如同政府標案一鍵建案 也是相同歷程」。
# 兩條入口（邀標報價／標案一鍵建案）走同一條鏈，而它在同一個地方斷：
# 已承攬 176 件無成案編碼、報價 1,273 萬、請款與帳本各 0；
# 有編碼的 51 件則 48 件有請款。48/51 對 0/175。
# ⚠️ 只對「惡化」報紅，存量不報紅 —— 否則它第一天就是紅的（今日已付過這個學費）。
run_step "77" "成案程序管控（承攬→編碼→金流）" "scripts/checks/case_award_pipeline_audit.py"
# 2026-08-05 owner：「有資安風險皆不應該公開」。掃全 portfolio 當下發現
# lvrland 與 digitaltwin 把完整 API schema 放在公網（1.5MB／196 端點），
# 且沒有任何機制在問「我們對外開了什麼」—— 修一次不代表不會再開。
run_step "29" "公網暴露稽核"                 "scripts/checks/public_exposure_audit.py"
# 2026-08-05：視覺走查是唯一能抓「斷言全過但畫面是錯的」那一類的機制，
# 但判讀需要人在場、不能掛 cron —— 不能自動執行的流程最容易悄悄停掉且無訊號。
# 這一步只問「這件事還在做嗎」，逾期回 YELLOW 不回 RED。
run_step "30" "視覺走查新鮮度"               "scripts/checks/visual_walk_freshness.py"

# 2026-08-07：這支稽核 2026-07-21 就寫好了，卻**從沒接進任何 runner**（原記「step 71
# 待接」），所以 IdP 的 cookie TTL 從 4h 改成 8h 也沒有任何人知道 —— 又一個「機制存在
# 但沒有接收者」。它比對三處 SSO 存活期是否對齊；不對齊時使用者會在工作中被登出，
# 而且是靜默失敗（owner 2026-08-07 因此丟失一次刪除動作）。
run_step "31" "SSO 存活期跨 repo 對齊"       "scripts/checks/sso_ttl_ssot_audit.py"

# 2026-08-07：owner 回報「時序亂了」，追出 13 筆錯誤前序關聯、橫跨 4/5/7 三個月
# —— 錯了四個月而無人知道。因為這類缺陷不拋錯、不改變任何數字、不影響任何清單，
# 頁面渲染也完全正常（連瀏覽器走查都全過），它**只**改變縮排與分組。
# 唯一的偵測器一直是「人打開頁面覺得不對」；這一步就是要取代那個人。
run_step "32" "作業紀錄鏈語意"               "scripts/checks/work_record_chain_semantics_audit.py"

# 2026-08-03：測試套件本身的健康從來沒有任何一階在看 —— 整套長期不能執行，
# 是 owner 記在待辦裡而不是系統發現的；同期 ezbid parser 重寫後兩天無回歸保護。
# 比對的是「測試 id 集合 vs 基線」，不是要求全綠（現有 41 項測試債會讓它天天紅，
# 那就變成沒人看的告警）。跑全套約 9 分鐘。
run_step "24" "測試套件健康（vs 基線）"     "scripts/checks/test_suite_health.py"

# 2026-08-03：系統有五份「有哪些 API」的清單、三種不同的 key，其中三份用 URL
# 可以互相對照卻沒有任何一支在對照。首跑即揪出 12 條前端常數指向不存在的後端
# （其中 2 條還被測試斷言保護著）。
run_step "25" "程式×頁面×服務 對應完整性"  "scripts/checks/api_contract_alignment_audit.py"

# 2026-08-09：引擎有 drift 稽核，**入口腳本卻沒有任何 gate**。
# 實測 lvrland 與 pile 的入口去註解後差異 0 行（兩份相同副本各自維護），
# 而 canonical 原生 repo 那份反而最舊。收斂後若無閘門，下次必然再長回來。
run_step "33" "走查入口委派（防 copy 式復發）" "scripts/checks/selfaudit_entry_delegation_audit.py"

# 2026-08-09（owner：「跨專案 repo 或 session 導致紀錄或待辦事項遺失，
# 是否也應導入自我檢核修復與自我進化」）。同一輪就有六個實例，全是同一個形狀：
# **在某個 repo/session 完成的事沒有傳播出去，而且沒有任何機制會發現** ——
# lvrland 推送被別人未提交的變更擋住數週、DT 前端落後 21 個 commit 3.5 週、
# 檢核腳本寫好卻沒有任何 runner 引用（lvrland 6 支、pile 至今 1 支）。
# 這些都不是「程式壞了」，所以沒有任何既有檢核會紅。
run_step "34" "跨 repo 工作連續性"          "scripts/checks/cross_repo_work_continuity_audit.py"

# 2026-08-09（owner：「針對既有規範統整複查確認」）。
# `.claude/rules/adr-anti-half-wired-sop.md` §自查工具 明文要求「月度執行」這四支，
# 但**沒有任何 runner 或排程在跑它們** —— 寫在規範裡的規定，沒有執行者。
# 複查全部 37 份規範文件、33 支被宣告的腳本，發現 6 支有問題（1 支檔案根本不存在）。
#
# 實跑 sso_coverage_check 當場揭露：它印「[FAIL] 2 個 admin 鎖死風險」卻 exit 0
# （只有 --ci 才回 1，而本 runner 一律不傳旗標）—— 接進來之前已修為三態。
# 那個風險因此從未被任何人看見。
run_step "35" "SSO 覆蓋率（ADR-0033）"      "scripts/checks/sso_coverage_check.py"
run_step "36" "IdP 連通性（ADR-0033）"      "scripts/checks/idp_connectivity_check.py"
run_step "37" "alias RLS 端到端（ADR-0025）" "scripts/checks/alias_rls_e2e_check.py"
run_step "38" "記憶寫入鏈活體（ADR-0022）"   "scripts/checks/memory_diary_freshness_check.py"

# 2026-08-09：把「規範說要做的事，有沒有人在做」這個複查常設化。
# 首跑即揭露 adr_level_audit.py 被規範宣告但**檔案根本不存在**。
run_step "39" "規範宣告 vs 執行者"          "scripts/checks/spec_executor_audit.py"

# 2026-08-09：MODULARIZATION_STANDARDS §4.3 寫著「加 fitness step：adr_level_audit.py（待建）」
# —— 「待建」寫了就沒有下文，兩個月無人追。由 step 39 抓到「規範宣告了不存在的機制」後補建。
# ⚠️ 首版 status regex 只認英文，實跑得到「accepted 0 份」→ GREEN＝假綠
#（本 repo 寫的是 `> **狀態**: accepted`）。已補「0 份 accepted 不得判綠」守衛。
run_step "40" "ADR 接通完整度自評"          "scripts/checks/adr_level_audit.py"

# Step 41：價值層（第 6 階）**到期提醒** —— 2026-08-10 接線。
#
# 快照本身早有執行者（Windows 排程 CK_Missive-SelfAudit-CapabilityUsage 04:50，
# 經 run_capability_snapshot.sh），每天都在產出 JSON。缺的不是「有沒有跑」，
# 而是**判定時點到了會不會有人被叫醒** —— DECISION_DATE 只寫在 JSON 裡，
# 沒有任何機制在比對今天是否已經過了那一天。
#
# 同時修掉底層的退出碼混用：原本「資料還在累積」與「Prometheus 掛了」都回 2，
# 於是包裝腳本只好一律吞成 0 —— 代價是**觀測棧真的掛了也沒人知道**。
# 現改為三態（未到期 0／到期 1／依賴壞 2），才有辦法接進 runner。
run_step "41" "價值層零流量判定（到期提醒）"  "scripts/checks/capability_usage_snapshot.py"

# Step 42：服務埠暴露（2026-08-10）。
#
# 既有的 public_exposure_audit 問的是「五個公開網域的 HTTP 開了什麼」——
# 問得很好，但資料庫埠**不在那個座標系裡**，所以它再怎麼跑都不會發現
# postgres 綁在 0.0.0.0、LAN 上任一裝置都能連。這是我自己在
# BLIND_SPOT_STRATEGY 寫的 A 型盲區（座標系外）的實例。
#
# 首跑即發現 5 個專案 12 個埠對 LAN 開放，而 lvrland 早就綁 127.0.0.1 ——
# 有正確範例卻沒有擴散，那就是 drift 不是刻意分歧。
run_step "42" "服務埠暴露（資料層不得對 LAN 開放）" "scripts/checks/service_port_exposure_audit.py"

# Step 43：管理員判定 SSOT（2026-08-10）。
#
# 起因是一位員工「明明是管理員卻用不了」：role='admin' 但 is_admin=false，
# 而系統裡的判定散在四處、規則不同 —— 前端選單併看 role（看得到），
# backup / reminders / calendar 的 13 個端點只看 flag（點進去 403）。
# **看得到而用不了**是最難自行診斷的一種：使用者會以為是自己操作錯。
#
# 判定只該有一份。這支擋的是第五份出現。
run_step "43" "管理員判定 SSOT（不得有第二份規則）" "scripts/checks/admin_check_ssot_audit.py"

# Step 44：PM2 程序存活（2026-08-10）。
#
# portfolio 有三個排程層，這是最後一個補上哨兵的：
#   Windows 排程 → step 28｜容器內 APScheduler → producer watchdog｜PM2 → 本步
# 原本 PM2 只有 CK_Website 的 check-cron-coverage 在看，而那支問的是
# 「設定檔宣告的 cron 有沒有註冊」—— **註冊不等於在跑**，本專案已為這句話付過三次學費。
#
# 判讀 PM2 有兩個坑，判準都驗過：cron 型的 `stopped` 是兩次 fire 之間的正常狀態
# （誤判會一次產出 9 個假紅），而 online 型的 `exit_code` 是上一次退出的殘值。
run_step "44" "PM2 程序存活（註冊了不等於在跑）" "scripts/checks/pm2_process_liveness_audit.py"

# Step 45：異地備份完整性（2026-08-10）。
#
# owner 問「確認 NAS 有完整備份」，查下去答案是沒有：附件一份都沒有、
# 金鑰一份都沒有，而本機那份附件備份自 05-18 就停了 84 天。
# 三個缺口沒有一個會報錯 —— remote_backup.json 寫著 success、排程 LastTaskResult=0、
# NAS 檔案一天比一天多，全都是綠的。因為沒有人在問
# 「備份的東西夠不夠還原出一套能跑的系統」。
#
# 放 weekly 而非 daily：這支要讀 NAS 的 UNC 路徑，而 daily 跑在容器內看不到。
# 兩層分工 —— 當天的失敗由排程 LastTaskResult 接（weekly 28 在看），
# 本步接的是慢性腐爛（dump 截斷、附件涵蓋率漂移、金鑰過期）。
run_step "45" "異地備份完整性（四類缺一不可）" "scripts/checks/offsite_backup_completeness_audit.py"

# ------------------------------------------------------------------
# Step 46-50：從 daily 移過來的五支（2026-08-11）
# ------------------------------------------------------------------
# 這五支原本掛在 daily，而 daily 由**容器內** APScheduler 驅動 ——
# 容器沒有 repo 根的 .env、沒有 docker-compose*.yml、沒有 docker CLI，
# 於是五支的實際輸出是 `[SKIP] .env not found`／`docker not available`／
# `No docker-compose*.yml found`，而 runner 把它們一律算成通過：
# **「沒檢查」與「檢查通過」長得一模一樣**，「daily 12 步全過」實際只判定了 7 步。
#
# 移到這裡是因為 weekly 跑在 host（.env／docker／compose 都在）。
# 五支都是 compose/env/image 這類**變更觸發型**風險，不是自然劣化，週級足夠；
# 而且「每天 0 次有效檢查」→「每週 1 次有效檢查」是提升，不是下降。
#
# ⚠️ step 49 的檔名：daily 原本找 startup_race_condition_audit.py（不存在），
# 實際是 startup_dependency_race_audit.py —— 那一步從建立起從未執行過。
run_step "46" "container env alignment（容器 env vs host .env）" "scripts/checks/container_env_alignment_audit.py"
run_step "47" "container image freshness（L51.7.1）"            "scripts/checks/container_image_freshness_check.py"
run_step "48" "docker compose volume 一致性（L43 防禦）"          "scripts/checks/docker_compose_volume_consistency.py"
run_step "49" "compose vs Dockerfile healthcheck SSOT（L45）"    "scripts/checks/compose_dockerfile_healthcheck_ssot.py"
run_step "50" "startup dependency race（compose depends_on）"    "scripts/checks/startup_dependency_race_audit.py"

# Step 51: 治理強制覆蓋（2026-08-13）
# ADR 與教訓都是為了「不要再犯」而寫的，但沒有機制強制的那些只是文字，
# 而文字不會在有人違反時出聲（L01 家族）。本支只回答可機器驗證的問題：
# 這條有沒有指向任何檢核腳本 —— **不判斷「該不該有」**（v6.39 已正確否決
# 自動分類：多數教訓是行為準則，區分需語意判斷會產不可信清單）。
# 覆蓋率本身不判紅，引用了不存在的腳本（斷鏈）才判紅。
run_step "51" "治理強制覆蓋＋宣告閘門（ADR／教訓）"            "scripts/checks/governance_enforcement_coverage.py --gate"

# Step 52: 檢核有效性報告（2026-08-13）
# 到目前為止沒有任何人在看兩個數字：「哪些檢核從來沒紅過」與「哪些紅了沒人處理」。
# 那兩個才是「檢核機制健不健康」的真實指標 —— 不是步數。
# 樣本不足時它會明講不足而不下結論；也不自動刪除或降級任何東西。
run_step "52" "檢核有效性報告（誰真的在保護我們）"        "scripts/checks/check_effectiveness_report.py"

# Step 53: 排程 job detail 完整度（2026-08-15）
# 2026-08-14～15 只是替既有 job 補上 detail 回傳，六次裡有六次找到藏著的問題
# （對帳報不存在的百萬差額／資安看板 48 個假紅／依賴掃描從未執行／
#  cleanup_events 空轉／soul_mirror_sync 從未同步）。
# 共通形狀＝job 算得出數字卻沒交出來，於是「做了事」與「什麼都沒做」
# 在 cron_events 裡長得一模一樣。把那個掃描變成常態，不必等人想起來再掃。
# 判 YELLOW 不判 RED：這不是故障，是可以更看得見。
run_step "53" "排程 job detail 完整度（有數字就該說出來）"    "scripts/checks/job_detail_completeness_audit.py"

# Step 54: NER 關係抽取回歸偵測（2026-08-15）
# 08-03 修好關係抽取（prompt 兩段欄位名不一致，validator 只讀前者→關係被靜默丟掉）。
# 修法前的存量公文排程「永遠不會回頭處理」——待處理判準問的是「有沒有 entities」，
# 要產出的卻是 relations（判準看的是代理指標不是產出）。
# 本支刻意**不報存量**（572 份是 owner 已知待決的事，每週報一次只會被略過），
# 只問「修法日之後有沒有又長出新的」＝修法退回才是要立刻知道的事。
run_step "54" "NER 關係抽取回歸（修法後有無新缺口）"        "scripts/checks/ner_relation_regression_check.py"


# Step 55: ERP 財務資料完整性（2026-08-15）
# 既有 ledger_reconciliation 只比「已付請款 vs 帳本」的差額 —— 問得太窄：
# 它看得到「有入帳但金額不符」，看不到「整類來源從來沒進過帳本」。
# 盤查當天：應付 36 筆全停在 unpaid（最舊 151 天）、營運支出 8 筆 approved 卻 0 入帳，
# 而差額是 0-0=0，既有對帳全綠。
# §1 判 RED（條件成立卻沒入帳＝真漏帳）；§2-4 判 YELLOW
# （填報停滯與存量斷鏈不是系統壞了，但會讓財務彙總少一整面）。
run_step "55" "ERP 財務完整性（帳本／填報／案號）"      "scripts/checks/erp_data_integrity_audit.py"

# Step 56: 前端設計規範（2026-08-15）
# owner 同一天連續指出四件事，**每一件都已經有正確範例存在於程式碼中**
# （/documents 沒有操作欄、enhanceColumns 自動加排序、ClickableStatCard、
#  TaoyuanDispatchPage 的 ?tab=），只是沒有擴散，而且沒有任何機制在問。
# 判準先驗過鑑別力：首版 44 處多為假陽性（管理診斷頁沒有詳情頁，
# 操作只能放列上），收窄成「已有 onRow 導向詳情卻還留著操作欄」後 9 處。
run_step "56" "前端設計規範（操作欄／表格能力／詳情頁模板）" "scripts/checks/frontend_design_standard_audit.py"

# 2026-08-16：owner 問「為何三條路徑 異質同工？」時查出「從標案建案」有兩份
# 各自獨立的實作，且對「邀標階段要不要建報價單」的答案相反 —— 兩邊都不報錯。
run_step "57" "業務實體建立路徑 SSOT（防第三份實作）" "scripts/checks/entity_creation_ssot_audit.py"

# 2026-08-16 owner：「分類仍有中英紛雜 如統一帳本」。
# 根因＝ledger.py 的 category 是無約束的 str（而 expense.py 註解還寫著「請同步更新
# 此處與 ledger.py」＝寫了等於沒寫），加上表單分類欄是自由輸入的 Input。
run_step "58" "列舉值儲存慣例（分類/狀態守門）" "scripts/checks/enum_storage_convention_audit.py"

# 2026-08-16：規範 §3「endpoints 禁止本地 BaseModel」寫了很久、大家大致遵守，
# 但**沒有任何機制在強制** —— 於是累積出 6 檔 18 個違規，
# 而我當天又新增了 2 個（是 stop hook 讀規範才發現的，不是檢核）。
# 存量列入 baseline 不判紅，新增的一律擋下。
run_step "59" "型別 SSOT（endpoints 無本地 BaseModel）" "scripts/checks/schema_ssot_audit.py"

# 2026-08-17 owner 回報「新增紀錄失敗」→ 追出 SAVEPOINT 內 auto_commit 家族
# （請款與發票兩支都壞著，只有 asset 是對的）。測試抓不到：它們全部 mock 掉 repo，
# 而 mock 不會 commit —— 測試一路綠而真實路徑一路壞。
run_step "60" "SAVEPOINT 內不得自行 commit" "scripts/checks/savepoint_autocommit_audit.py"

# 2026-08-17 stop hook 抓到：quotation_no 只做到 DB 與 ORM，
# Pydantic 對「model 有、response schema 沒有」的欄位是靜默丟棄 ——
# 資料在庫裡而使用者永遠看不到。判 YELLOW（有些欄位本來就不該對外）。
run_step "61" "ORM 欄位是否到達 API 回應" "scripts/checks/model_response_field_reach_audit.py"
run_step "62" "前端送出的寫入欄位 schema 收得到嗎（extra=forbid 生效範圍）" "scripts/checks/write_payload_schema_audit.py"
run_step "63" "Response schema 的欄位前端型別宣告了嗎（契約鏈第三面）" "scripts/checks/response_frontend_type_audit.py"

# 2026-08-21：公網未帶憑證可取得業務資料（實測 documents-enhanced/statistics 回 200
# 並吐出公文總數）。根因是 TUNNEL_GUARD_ENABLED=false ⇒ 沒有自帶認證的端點一律對外。
# 用 FastAPI runtime dependency 樹判定 —— 既有的 grep 規則「端點缺少認證裝飾器」
# 產生了 122 個誤判（是真問題的 6 倍），認不出 Depends(require_auth()) 這類寫法。
# ⚠️ 2026-08-29 補 --ci：不帶時**新增**的無認證端點只回 1（YELLOW）。
#   YELLOW 是「規範沒被強制」那一級，而「公網多了一個不用認證就打得到的端點」
#   是回歸不是漂移 —— 2026-08-21 那次 /api/ai/* 全裸就是這一類（別人用、我們付費）。
#   ⚠️ 這與檔頭「刻意不傳 --strict」不衝突：--strict 是把 warning 升成 error，
#   而這支的 --ci 只影響「**新增**缺口」的分級，baseline 內的存量不受影響。
run_step "64" "無認證端點（runtime dependency 樹）" "scripts/checks/public_endpoint_auth_audit.py --ci"
# C2（2026-08-24）：router 層加認證的反面風險 —— 同一個檔案裡混雜真公開端點時，公開那半會被一起擋掉，而那種失敗只有真的打開那一頁才看得見。
run_step "65" "router 層認證有沒有誤擋公開端點" "scripts/checks/router_level_auth_mixing_audit.py"
# C1（2026-08-24）：規範 §24「所有 endpoint POST」先前**沒有任何檢核在管**—— 175 支腳本沒有一支驗 HTTP 方法。散文不帶設定。
# 同上：--ci 只把「新增違反」升為 RED，baseline 存量仍是 YELLOW。
run_step "66" "端點 POST 慣例（runtime methods）" "scripts/checks/http_method_convention_audit.py --ci"
# 2026-08-24：Cloudflare 依 UA 擋請求 —— Python 預設 UA 打公網**每一條都回 403**，而那個 403 長得正好像「認證有效」。CK_AaaP 在 pile 一個進行中的 P0 外洩上重現。
run_step "67" "公網探測的客戶端指紋（403 不一定是應用層擋的）" "scripts/checks/probe_fingerprint_guard.py"
run_step "68" "管理動作有沒有給一般同仁看見（畫面不該給必然失敗的按鈕）" "scripts/checks/admin_action_visibility_audit.py"
run_step "69" "協力廠商合約經費 vs 應付分期加總（同一件事兩個數字）" "scripts/checks/vendor_contract_payable_consistency.py"
run_step "70" "廠商身分源頭一致（同一張單不得有兩個名字）" "scripts/checks/vendor_identity_ssot_audit.py"
run_step "78" "應付有沒有上限在管（報價委外經費 vs 應付合計）" "scripts/checks/payable_budget_ceiling_audit.py"
run_step "79" "設定的 LLM 模型在 provider 那邊還存不存在" "scripts/checks/llm_model_availability_audit.py"
run_step "80" "紀年契約：API 查詢參數一律西元（§2.5）" "scripts/checks/year_convention_audit.py"
# 2026-08-29：加這一步時發現 72/73/74 三個編號**各有兩支**——我前一天新增時
#   沒查既有編號就往下接。編號重複會讓「weekly 74 紅了」這句話無法定位，
#   已改到 78-80。新增步驟前請先跑：
#   grep -oE 'run_step "[0-9]+"' 本檔 | sort -n | uniq -d
run_step "81" "窄螢幕收斂判準：共用表格元件不得只看 isMobile" "scripts/checks/responsive_narrow_convergence_audit.py"
run_step "82" "統計卡分母＋年度篩選預設當年度（§2.6 ①③）" "scripts/checks/stat_card_denominator_audit.py"
# 2026-08-29：`verify_architecture.py` 的宣告是「由 pre-commit hook 與 CI 呼叫」，
# 實查 **兩邊都是 0 次**（CI 另已於 2026-03-09 全面停用）。而它自己也壞著 ——
# 根目錄推導寫成 `.parent.parent`（本檔被移進 scripts/checks/ 之後沒改），
# 一啟動就 [FATAL]。**壞掉的腳本 + 假的執行者宣告 + 文件把它列為驗證命令。**
run_step "83" "架構完整性（路由/API 前綴/型別 SSOT/Schema-ORM）" "scripts/checks/verify_architecture.py"
# 2026-08-29：L99 的下一個變形 —— **執行者存在、腳本存在、旗標存在，
#   只是呼叫時少了那個旗標**，三者分開看都是綠的。alias_rls 的基線鎖
#   就這樣三個月沒鎖過。判準刻意只抓「基線比對包在 if args.ci 裡」這一種，
#   不抓 --strict（那是本檔檔頭的既有政策，粗判準會產出 26 個假紅）。
run_step "84" "基線鎖有沒有真的被叫到（runner 漏旗標）" "scripts/checks/runner_flag_drift_audit.py"
# 2026-08-29：`run_fitness.sh`（手動月度 /arch-fitness）**獨佔 57 支檢核** ——
#   weekly 沒有的那些（dead_ui_detector／db_schema_drift／cron_health_check…）。
#   而它原本只印到終端機、不留檔案 ⇒ 「跑了全過」與「根本沒跑」事後無法區分。
#   已讓它寫 fitness-manual.json，這一步監看新鮮度。
run_step "85" "手動月度架構覆盤有沒有真的在跑" "scripts/checks/fitness_manual_freshness_audit.py"
# 2026-08-29：`dead_ui_detector` 抓「後端有端點、前端沒常數」，抓不到
#   **常數在、元件在、沒有入口** 這第三種形狀（ProfitTrendTab 只在 index.ts
#   re-export）。本 repo 記過最貴的陷阱正是「改到孤兒元件、全綠但沒人看得到」，
#   而那條教訓寫的是「動元件前先 grep 誰在用」—— 一個人要記得做的動作。
run_step "86" "元件建好了但沒有任何入口渲染它（禁淨增）" "scripts/checks/orphan_component_audit.py"
run_step "87" "測試庫 schema 不得落後正式庫" "scripts/checks/test_db_schema_drift_audit.py"
run_step "88" "postgres 調校參數跨檔 SSOT（compose×3＋規格書＋執行時）" "scripts/checks/pg_tuning_ssot_audit.py"
run_step "89" "weekly 每一步都要能紅，否則要說自己只是報告" "scripts/checks/gate_vs_report_step_audit.py"

# 2026-08-30：§7 link_id 回退。原本有 `.claude/hooks/link-id-check.ps1`（2026-01-21），
# 但**沒有任何 runner 在叫它**，而且跑起來會給錯的答案 —— `-Path "src\**\*.tsx"`
# 在 PowerShell 裡的 `**` 不是遞迴 glob，實測只掃得到 119/604 個檔（20%）而照樣印 PASS。
# 新版走 ts_source（剝註解／字串），掃 805 個檔，並豁免 React `key=`。
run_step "90" "link_id 不得回退到別的 id（§7）" "scripts/checks/link_id_fallback_audit.py"

# 2026-08-30：問的是「hook 有沒有機會被觸發」，與 weekly 39 的 spec_executor_audit
# 剛好相反 —— 那支問「規範宣告的腳本有沒有執行者」，執行者來源不含 git hook
# 與 .claude/settings.json，所以在 pre-push 從未執行、secret guard 修在死檔上的
# 情況下仍回 GREEN。存量 10 筆走基線，新增才判紅。
run_step "91" "hook 有沒有機會被觸發（不可觸達偵測）" "scripts/checks/hook_reachability_audit.py"

# 2026-08-30：四位一體（ADR × 知識地圖 × 架構圖 × 向量庫）。
# ⚠️ owner 的規範書寫「Weekly Step 88」，而 88 已被 pg_tuning_ssot_audit 佔用
#    （87/89/90/91 亦然）—— 編號要 grep 過再用，這是本檔第二次遇到同型碰撞。
# 實測首跑就抓到 42 個「地圖重生了但向量庫沒跟上」＋1 個從未進向量庫。
run_step "92" "四位一體一致性（ADR×地圖×架構圖×向量庫）" "scripts/checks/knowledge_base_consistency_check.py"

# 2026-08-30（owner 目標：不要再發生每個 session 各自創無整合運用）：
# 實測 182 支檢核裡 110 支自己算專案根路徑、39 支自己開 docker exec，
# 而共用層 scripts/checks/lib/ 早就存在、採用率只有 3.3%。
# 存量 134 支走基線，**新增一支或既有腳本增加自造處才判紅**。
run_step "93" "共用層採用率（新腳本不得自己重造）" "scripts/checks/lib_adoption_audit.py"

# 2026-08-30：長期紅燈必須有名字。
# 「無整合運用」最直接的表現不是缺機制，是**機制在響而沒有人收** ——
# 實測近 8 輪有 11 支每輪都非綠，逐一查過**沒有一支是壞掉的檢核**，
# 全是真發現且檢核自己就寫明了處置方式。問題在於「紅了 8 週」與
# 「今天才紅」在畫面上長得一模一樣。登記不是把紅燈變綠 ——
# 它們照樣各自紅著，本支只讓「有多少紅燈沒有人在收」看得見。
run_step "94" "長期紅燈必須有名字（沒有人收的訊號）" "scripts/checks/chronic_red_audit.py"

# 2026-09-01：下拉的取數上限會被資料成長追上，而它壞的那天沒有人在看。
# owner 從 /documents/2748 回報選不到某個承攬案件 —— 那筆排第 144 名，
# 而下拉寫死 limit:100。它**前一天還好好的**（排第 93），是當天成案 51 筆
# 把它擠出界的。⇒ 這支回答「每個下拉還能長幾筆才會開始靜默截斷」。
run_step "95" "下拉取數上限 vs 資料筆數（會被時間追上）" "scripts/checks/dropdown_limit_headroom_audit.py"

# 2026-09-01：設定目錄只允許 configs/（基礎設施）與 backend/config/（應用層）。
# owner：「另為設定為何散亂各處」—— 量出來是三個目錄在三個時間點各自長出來、
# 沒有人合併過，於是 remote_backup.json 有三份、內容都不同，
# 而 paths.py 一度就指向了非權威的那一份。
run_step "96" "設定目錄 SSOT（不得長出第三個）" "scripts/checks/config_directory_ssot_audit.py"

# ------------------------------------------------------------------
# 97–99（2026-09-02）：承攬案件 × 金流管控三支守門。
# 起因：實測 226 個承攬案裡 173 個在金流上看不到——承攬案件本身不掛在任何
# 一條金流上，全靠 case_code 間接推導，而帳本的 case_code 是舊制、90% 孤兒。
# 三支判準都是精確的（SQL 集合關係），不是啟發式。
# 完整分析：docs/architecture/CONTRACT_CASE_FINANCE_GOVERNANCE.md
# ------------------------------------------------------------------
run_step "97" "帳本 case_code 必須接得到主表（08-29 收斂漏了帳本）" "scripts/checks/ledger_case_code_reachability_audit.py"
run_step "98" "成案必有報價單，GN 豁免（金流全掛報價單上）" "scripts/checks/contract_case_quotation_presence_audit.py"
run_step "99" "應付必有 billing_id（橋設計了但 47 筆全空）" "scripts/checks/payable_billing_link_audit.py"
# 100（2026-09-02 owner：「無法自行檢測整個流程對應數據嗎」）：97–99 各查一個環節，
# 這一支從**案件**的角度把整條鏈走一遍。RED 只給「數字互相矛盾」（已收>請款、
# 報價多打一個 0 那種）；「執行中 >365 天 0 請款」只 YELLOW——多為小案，很可能是收了沒登。
run_step "100" "承攬案件端到端流程對應（以案件為主軸走整條鏈）" "scripts/checks/contract_case_pipeline_reconciliation.py"

# 101（2026-09-02 晚）：三表共有欄位必須在同步白名單、同步目標欄位必須存在於模型。
# 同日踩兩次同型（status 上午、case_name 晚上），第三種形狀是 sync 寫 ERPQuotation.client_name
# 而模型根本沒這欄位 —— setattr 靜默不落地。全靜態、不連 DB。
run_step "101" "三表共有欄位同步白名單（含目標欄位存在性）" "scripts/checks/case_field_sync_whitelist_audit.py"

# 102（2026-09-02 晚 owner「統一新制避免混淆，對應填報編碼同步檢核」）：新建承攬案不得是舊制格式、
# 成案編碼必須能回溯建案案號、報價單 project_code 必須等於承攬案的、新建報價單 quote_kind 不得 NULL。
run_step "102" "案號新制統一與填報編碼同步" "scripts/checks/case_code_format_consistency_audit.py"

# 103（2026-09-03 owner「有報價費用應收總額就自動新增第一期費用數據，以利通報與稽催」）：
# 成案、有金額的報價單必須有請款——沒有第一期，夜間吹哨者的「請款逾期」對它永遠不會響。
run_step "103" "成案即應收：第一期請款存在性" "scripts/checks/first_billing_presence_audit.py"

# 104（2026-09-03 全景覆盤 A1）：金額語意三方對帳——報價總價 × 請款額 × 發票額，依 FIELD_SEMANTICS.md。
# 100／103 判「該不該有請款」，這支判「三個地方寫的是不是同一個數」。
run_step "104" "ERP 金額語意三方對帳（FIELD_SEMANTICS）" "scripts/checks/erp_amount_semantics_audit.py"
# 105（09-04 金流複查）：匯入把「已成立」寫成 contracted 卻不建承攬案 ⇒ 16 筆在每張表上各自「正常」而整條鏈斷掉
run_step "105" "案件狀態一致性（已承攬⇔承攬案⇔project_code）" "scripts/checks/case_state_consistency_audit.py"
# 106（09-04 owner「協力廠商已增列費用但廠商帳款／應付沒列入」）：指派表與應付表沒有橋，16 案有指派 13 案無應付
run_step "106" "指派即應付（協力廠商指派⇔應付）" "scripts/checks/vendor_association_payable_audit.py"
# 107（09-04 /loop 名稱標準化）：名稱欄是快照、鍵欄才是關聯——可精確對上主檔卻沒填鍵＝RED
run_step "107" "名稱欄 vs 鍵欄一致性（id 是鍵、名稱是快照）" "scripts/checks/name_id_pair_consistency_audit.py"
# 108（09-05 owner「統計圖卡對應動態篩選為首要核心」）：卡片點了只換底色＝假互動；09-04 兩頁四張卡就是這樣
run_step "108" "統計卡是否接到篩選（假互動偵測）" "scripts/checks/stat_card_filter_wiring_audit.py"

# ------------------------------------------------------------------
# 逐步結果歷史（2026-08-13）
# ------------------------------------------------------------------
# 只記整體 rc 時，三個月後也回答不出「哪一支檢核從來沒紅過」。
# 而那正是判斷「這 158 支裡有多少真的在保護我們」的唯一依據 ——
# 從沒紅過的，要嘛防的事不會發生（可降級），要嘛它根本不會紅（假綠，更嚴重：
# 2026-08-13 一天就找到三支屬於後者）。
# skip 也要記：**「沒檢查」與「檢查通過」不得在歷史裡長得一樣**，
# 那正是這整套機制反覆踩到的東西。
_HIST="wiki/memory/fitness_step_history.jsonl"
mkdir -p "$(dirname "$_HIST")" 2>/dev/null
{
  # 2026-08-27：手動跑必須與排程跑**分得出來**。
  # 我今天為了驗新加的 step 手動全跑一次，寫進歷史的那一行與排程跑的一模一樣 ——
  # 而這份歷史唯一的用途是回答「哪一支從來沒紅過」，多一筆人為樣本就會稀釋它。
  # 同族前例：負向測試污染正式晨報、走查累積 222 列 user_sessions。
  # 用法：CK_FITNESS_MANUAL=1 bash scripts/checks/run_fitness_weekly.sh
  printf '{"ts":"%s","runner":"%s","manual":%s,"steps":{'     "$(date +%Y-%m-%dT%H:%M:%S)" "weekly"     "$([ "${CK_FITNESS_MANUAL:-0}" = "1" ] && echo true || echo false)"
  _first=1
  for _r in "${STEP_RESULTS[@]:-}"; do
    [ -z "$_r" ] && continue
    _n="${_r%%|*}"; _rest="${_r#*|}"; _name="${_rest%%|*}"; _rc="${_rest##*|}"
    [ $_first -eq 0 ] && printf ','
    printf '"%s":%s' "$_n $_name" "$_rc"
    _first=0
  done
  printf '}}
'
} >> "$_HIST" 2>/dev/null || true

# ============================================================
# Summary
# ============================================================
echo -e "${CYAN}===========================================${NC}"
if [[ $FAIL_COUNT -eq 0 && $WARN_COUNT -eq 0 ]]; then
    echo -e "${GREEN} ✅ Tier 2 weekly all passed${NC}"
else
    [[ $FAIL_COUNT -gt 0 ]] && echo -e "${RED} ✗ Tier 2 weekly: $FAIL_COUNT step(s) RED${NC}"
    for s in "${FAIL_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${RED}✗${NC} $s"
    done
    [[ $WARN_COUNT -gt 0 ]] && echo -e "${YELLOW} ⚠ YELLOW $WARN_COUNT step(s)（非故障，待確認）${NC}"
    for s in "${WARN_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${YELLOW}⚠${NC} $s"
    done
    # exit 1 只由 RED 觸發，不含 YELLOW —— 否則 cron 會因為「週末沒發標」每週報一次
    # 2026-08-07：原本 exit 1 **只在 --strict 時**觸發 —— 於是不帶旗標的呼叫端
    # 會拿到「印著 N step(s) RED、退出碼卻是 0」。我自己寫 host 執行器時就踩了：
    # 報 2 步 RED、wrapper 記 rc=0，交接給容器端就會被寫成 PASS。
    # 退出碼必須與印出的狀態一致（L83）；--strict 保留但不再是 exit 1 的前提。
    if [[ $FAIL_COUNT -gt 0 ]]; then
        # 2026-08-09：訊息改為與實際行為一致。
        # 原本寫「連續 2 週**同 step** RED 將推 LINE」，但歷史檔當時只記 rc／status、
        # 根本沒有步驟名可比 —— 條件引用了不存在的資訊（同族：宣告了一個沒實作的機制）。
        # 現在 red_steps 有記，而升級條件仍是「連紅 ≥2 週」（步驟換人也該報），
        # 差別在 digest 會**先講與上週的差異**。
        echo -e "${RED} RED → exit 1 (連紅 ≥2 週進 digest；訊息會標出本週新增的 RED)${NC}"
        exit 1
    fi
fi
echo -e "${CYAN}===========================================${NC}"
