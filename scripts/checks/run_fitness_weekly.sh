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
run_step() {
    local step_num="$1"
    local step_name="$2"
    local script="$3"

    echo -e "${CYAN}[$step_num/${TOTAL_STEPS}] $step_name${NC}"
    if [[ ! -f "$script" ]]; then
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
    PYTHONIOENCODING=utf-8 python "$script" 2>&1 || rc=$?
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
run_step "7" "alias_rls coverage audit"       "scripts/checks/alias_rls_coverage_audit.py"
run_step "8" "tender_freshness"               "scripts/checks/tender_freshness_audit.py"
run_step "9" "tender_subscription_watchdog"   "scripts/checks/tender_subscription_watchdog_audit.py"
run_step "10" "tender_enrichment_freshness"   "scripts/checks/tender_enrichment_freshness_audit.py"
run_step "11" "diary density audit"           "scripts/checks/diary_density_audit.py"
run_step "12" "facade adoption audit"         "scripts/checks/facade_adoption_audit.py"
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
