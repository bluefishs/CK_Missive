#!/bin/bash
# ============================================================
# Fitness Tier 1 Daily — 8 critical step (~1 min)
#
# v6.12 治理進化 #2 落地 (2026-05-30)
# 對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md §3
#
# 包含 step:
#   - 38 docker_compose_volume_consistency
#   - 40 compose/dockerfile healthcheck SSOT
#   - 47 startup race condition
#   - 57 container env alignment
#   - 58 agent_query starvation
#   - 60 container image freshness
#
# 用法:
#   bash scripts/checks/run_fitness_daily.sh           # warning mode
#   bash scripts/checks/run_fitness_daily.sh --strict  # 任一 RED exit 1 (cron 用)
#
# 失敗動作 (--strict 模式):
#   exit 1 → cron job 抓住 → 推 LINE
# ============================================================

set -uo pipefail

# --strict 接受但不再改變任何行為（2026-08-11）：
# 退出碼已一律依 RED 決定、子腳本一律不傳旗標。
# 保留參數只為相容既有呼叫端（scheduler 的 fitness_daily_job 帶著它）——
# 但不留一個看起來有作用、其實沒有的變數，那會讓人以為 warning mode 存在。
if [[ "${1:-}" == "--strict" ]]; then
    :
fi

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}=========================================${NC}"
TOTAL_STEPS=$(grep -cE '^[[:space:]]*run_step "' "$0")
echo -e "${CYAN} Fitness Tier 1 Daily — ${TOTAL_STEPS} critical step ${NC}"
echo -e "${CYAN}=========================================${NC}"
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
SKIP_STEPS=()

# ------------------------------------------------------------------
# 這一組需要 host 環境，容器內執行是零效力（2026-08-11 查證）
# ------------------------------------------------------------------
# daily 由**容器內** APScheduler 驅動，而容器只掛 scripts/ backend/ wiki/ docs/
# —— 沒有 repo 根的 .env、沒有 docker-compose*.yml、沒有 docker CLI。
# 實測這五支在容器內的輸出：
#
#   container env alignment      → [SKIP] .env not found at /app/.env
#   container image freshness    → [SKIP] docker not available
#   volume consistency           → YELLOW: No docker-compose*.yml found
#   healthcheck SSOT             → no docker-compose*.yml found
#   startup dependency race      → no docker-compose*.yml found
#
# 而 runner 把這些一律算成通過 —— **「沒檢查」與「檢查通過」長得一模一樣**，
# 於是「daily 12 步全過」實際只有 7 步真的判定過。
#
# 處置：改由 host 的 weekly 執行（那裡 .env／docker／compose 都在），
# 容器內明確標為未判定並印出負責的執行者。五支都是 compose/env/image 這類
# **變更觸發型**風險（不是自然劣化），週級足夠；而且從「每天 0 次有效檢查」
# 變成「每週 1 次有效檢查」是提升，不是下降。
HOST_ENV_AVAILABLE=false
if [[ -f docker-compose.production.yml ]]; then
    HOST_ENV_AVAILABLE=true
fi

skip_host_only() {
    local step_num="$1"
    local step_name="$2"
    echo -e "${CYAN}[$step_num/${TOTAL_STEPS}] $step_name${NC}"
    echo -e "  ${YELLOW}⊘${NC} 此環境無 docker-compose*.yml／.env／docker CLI —— 不判定"
    echo "     負責執行者：host 排程 CK_Missive-Fitness-Weekly（同一支腳本在那裡有效）"
    SKIP_STEPS+=("$step_num $step_name")
    echo ""
}

# 腳本不存在**不得**靜靜跳過。
# 2026-08-02 已在 weekly 修過同型（alias_rls_audit.py 檔名寫錯 → 那一步從未執行、
# 卻一路綠燈）；daily 當時沒改，於是今天又抓到一個：step 5 找
# startup_race_condition_audit.py，實際檔名是 startup_dependency_race_audit.py。
require_script() {
    local step_num="$1"
    local step_name="$2"
    local path="$3"
    if [[ -f "$path" ]]; then
        return 0
    fi
    echo -e "${CYAN}[$step_num/${TOTAL_STEPS}] $step_name${NC}"
    echo -e "  ${RED}✗${NC} 腳本不存在：$path —— 檢查消失不得與檢查通過同色"
    FAIL_COUNT=$((FAIL_COUNT+1)); FAIL_STEPS+=("$step_num $step_name（腳本不存在）")
    echo ""
    return 1
}

# 2026-08-05：總步數改為**自我推導**，不再寫死。
# 原本表頭寫死總數，加了步驟卻沒改它 —— daily 實際 9 步印「/8」、
# weekly 實際 28 步印「/27」。兩個數字描述同一件事就會漂，
# 而這種漂移剛好出現在「用來檢查別人漂移」的腳本上。
run_step() {
    local step_num="$1"
    local step_name="$2"
    local cmd="$3"

    echo -e "${CYAN}[$step_num/${TOTAL_STEPS}] $step_name${NC}"
    # 計數與「是否 exit 1」分離（2026-08-02 同型修法，三支 fitness 腳本皆中此缺陷）。
    # 原本非 --strict 走 `|| true` → FAIL_COUNT 恆 0 → 結尾恆印「all passed」。
    # warning mode 的語意是不阻斷，不是不報告。
    #
    # exit code 為三態（audit 腳本共同約定）：0=GREEN / 1=YELLOW / 2+=RED。
    # 分開計數而非一律算 RED —— 把 YELLOW 報成 RED 會讓人習慣忽略紅字，
    # 等於把訊號變回噪音。
    #
    # ⚠️ 2026-08-11 更正上面那句原本引用的例子：它寫「volume consistency 真 drift=0、
    # 只有 5 個無害 orphan volume」。查證後兩件都不成立 —— 那 5 個 orphan volume
    # 早已不存在（現在只剩 3 個且全部有容器在用），而該步在容器內 YELLOW 的真正
    # 原因是**找不到 docker-compose*.yml**，它從來沒有真的檢查過任何東西。
    # 2026-08-11：**一律不傳 --strict**（沿用 weekly 08-07 的結論）。
    #
    # 原本 cron 帶 --strict 呼叫本 runner，run_step 再把 --strict 轉傳給每一支腳本，
    # 而多數腳本的 argparse 不認識它 → `error: unrecognized arguments: --strict`
    # → exit 2 → 假紅。實測今天修好前兩個真因後，暴露出的正是這一層：
    # 手動跑（不帶旗標）全綠、cron 跑（帶旗標）step 10/11 紅，紅的原因是參數。
    # weekly 在 08-02 用 detect_flag() 繞過、08-07 改為一律不傳並移除該函式，
    # daily 當時沒改 —— 又一次「有正確範例卻沒擴散」。
    #
    # 退出碼一律依腳本原生三態（0/1/2+），嚴重度不由呼叫端的旗標決定。
    local rc=0
    eval "$cmd" 2>&1 || rc=$?
    STEP_RESULTS+=("$step_num|$step_name|$rc")
    if [[ $rc -eq 1 ]]; then
        WARN_COUNT=$((WARN_COUNT+1)); WARN_STEPS+=("$step_num $step_name")
    elif [[ $rc -ne 0 ]]; then
        FAIL_COUNT=$((FAIL_COUNT+1)); FAIL_STEPS+=("$step_num $step_name")
    fi
    echo ""
}

# Step 1/6: container env alignment (step 57)
# 2026-08-09：腳本強制表態閘門放第一步。
# 它每天印「存量待清 N」—— 這個數字不動就代表沒有人在清，
# 比一個永遠綠的閘門誠實。新增腳本不在基線裡，會被真的擋下來。
run_step "0" "腳本強制表態閘門" \
    "scripts/checks/declaration_gate.py"

if $HOST_ENV_AVAILABLE; then
    run_step "1" "container env alignment audit" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/container_env_alignment_audit.py"
else
    skip_host_only "1" "container env alignment audit"
fi

# Step 2: container image freshness (step 60, L51.7.1) — 需 host docker CLI
if $HOST_ENV_AVAILABLE; then
    run_step "2" "container image freshness check" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/container_image_freshness_check.py"
else
    skip_host_only "2" "container image freshness check"
fi

# Step 3: docker_compose volume consistency (step 38, L43) — 需 compose + docker volume ls
if ! $HOST_ENV_AVAILABLE; then
    skip_host_only "3" "docker_compose volume consistency"
elif require_script "3" "docker_compose volume consistency" \
        "scripts/checks/docker_compose_volume_consistency.py"; then
    run_step "3" "docker_compose volume consistency" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/docker_compose_volume_consistency.py"
fi

# Step 4: compose/dockerfile healthcheck SSOT (step 40, L45) — 需 compose + Dockerfile
if ! $HOST_ENV_AVAILABLE; then
    skip_host_only "4" "compose/dockerfile healthcheck SSOT"
elif require_script "4" "compose/dockerfile healthcheck SSOT" \
        "scripts/checks/compose_dockerfile_healthcheck_ssot.py"; then
    run_step "4" "compose/dockerfile healthcheck SSOT" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/compose_dockerfile_healthcheck_ssot.py"
fi

# Step 5: startup dependency race audit (step 47) — 需 compose
# 2026-08-11：檔名更正。原本找 startup_race_condition_audit.py（不存在），
# 實際是 startup_dependency_race_audit.py —— 這一步從建立起從未執行過。
if ! $HOST_ENV_AVAILABLE; then
    skip_host_only "5" "startup dependency race audit"
elif require_script "5" "startup dependency race audit" \
        "scripts/checks/startup_dependency_race_audit.py"; then
    run_step "5" "startup dependency race audit" \
        "PYTHONIOENCODING=utf-8 python scripts/checks/startup_dependency_race_audit.py"
fi

# Step 6/9: agent_query starvation (step 58, L51.7)
run_step "6" "agent_query starvation check" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/agent_query_starvation_check.py"

# Step 7/9: cron silent dormant (v6.12 #2 補完, 2026-05-30)
run_step "7" "cron silent dormant check" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/cron_silent_dormant_check.py"

# Step 8/9: dashboard freshness (v6.12 整合 SSOT 配套, 2026-05-30)
run_step "8" "dashboard freshness check" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/dashboard_freshness_check.py"

# Step 9/9: dashboard completeness (2026-06-12 覆盤 — 防區段 silent 落空 / L52·L57·L62)
# 抓「生成器在 in-container 情境寫死 host 佈局 → §5 facade `?` / §9.6 誤報不存在」回退
run_step "9" "dashboard completeness audit" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/governance_dashboard_completeness_audit.py"

# Step 10: shell script 行尾（2026-08-07）
# 這一支正是為了守住「本 runner 自己能不能執行」—— CRLF 讓 daily/weekly 在容器內
# syntax error、一行檢核都沒跑過（daily 每日 rc=2、weekly 連 9 週 RED），而在 host
# 跑同一支永遠全綠。規則已補進 .gitattributes，但規則存在不等於生效，要有人持續問。
run_step "10" "shell script 行尾（CRLF 會使容器內完全不執行）" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/shell_script_eol_audit.py"

# Step 11: DB 交易狀態（2026-08-08）
# lvrland 後端 hang 住、API 對真實使用者完全不可用而公網首頁仍回 200，
# 唯一指向真因的證據是 DB 的 idle in transaction (aborted) × 5 —— 當時沒有任何機制在看它。
# 這種故障不會自己好，只會累積到把連線池吃光；抓到就是真的，不必猜。
run_step "11" "DB 交易狀態（中止未 rollback）" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/db_transaction_health_check.py"

# Step 12: 模組匯入掃描（2026-08-13）
# 一天之內找到三個彼此無關、形狀卻完全一樣的缺陷：模組匯入即失敗，
# 但因為不在 __init__ 匯出、消費端又是函式內延遲匯入、上層再 catch 成 warning，
# 於是可以壞好幾個月而所有訊號都是綠的（tender_cache 至少 78 天、
# wiki/compiler 三個多月、pm/staff_* 自 v5.2.0）。
# py_compile／型別檢查／測試／走查全都抓不到 —— 唯一的辦法是真的匯入一次。
# 放 daily 而非 weekly：它要在應用實際執行的環境裡跑，而 daily 正是在容器內。


# Step 13: 八條生命跡象（2026-08-16）
# owner：「每週都重複檢修…還是修補不完」。當天量出原因：150 支檢核裡
# **131 支只看機制**、19 支碰業務資料，七月至今 +47／刪 0。
# 而系統存在的目的不是讓機制動，是讓公文被處理、款被收到、帳被記下。
# 機制的組合數無窮（job × 豁免 × 環境 × 重構），業務結果只有幾條 ——
# 追著機制修永遠有下一個。這一步問的是後者。
# ⚠️ 刻意**不帶 --enforce**：新機制上線當下最不該被信任（§3 #15-17/19/21
# 全是我自己新加的檢核造成的假訊號）。首月只觀測，看過幾輪真實資料再開。
run_step "12" "模組匯入掃描（匯入即失敗的模組）" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/module_import_sweep.py"

run_step "13" "八條生命跡象（模組今天活著嗎）" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/business_vital_signs.py"


# Step 14: 知識文庫新鮮度（2026-08-31）
# owner：「知識文庫要與系統同步更新，不然僅是舊歷史紀錄，
#         對於系統開發檢視與維護效益低」。
#
# 為什麼放 daily 而不是只留在 weekly 92：
#   **偵測的節奏要跟得上它偵測的東西。**向量同步是每日 05:15，
#   而 weekly 92 一週才問一次 ⇒ 同步壞掉最久要七天才知道。
#
# ⚠️ 判準刻意分兩級，否則會做出一支天天紅的檢核：
#   daily 跑 02:00、同步跑 05:15，**當天改過的文件在 02:00 看必然「未同步」**，
#   那是正常待辦不是故障。
#     · 改在上次同步之後 → YELLOW（待同步，預期中）
#     · 改在上次同步之前卻還是舊的 → RED（同步跑了但沒修好）
#   取不到上次同步時間就明講無法分辨，**不猜** —— 猜錯的方向是把
#   「同步壞了」讀成「還沒輪到」。
#
# ⚠️ 用 weekly 92 的 `--freshness-only` 而不是另寫一支：判準 ③ 的實作
#   已經精確，複製出去只會產生兩份會各自演化的判準。
run_step "14" "知識文庫新鮮度（向量庫 vs docs/）" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/knowledge_base_consistency_check.py --freshness-only"


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
  printf '{"ts":"%s","runner":"%s","steps":{' "$(date +%Y-%m-%dT%H:%M:%S)" "daily"
  _first=1
  for _r in "${STEP_RESULTS[@]:-}"; do
    [ -z "$_r" ] && continue
    _n="${_r%%|*}"; _rest="${_r#*|}"; _name="${_rest%%|*}"; _rc="${_rest##*|}"
    [ $_first -eq 0 ] && printf ','
    printf '"%s":%s' "$_n $_name" "$_rc"
    _first=0
  done
  for _s in "${SKIP_STEPS[@]:-}"; do
    [ -z "$_s" ] && continue
    [ $_first -eq 0 ] && printf ','
    printf '"%s":"skip"' "$_s"
    _first=0
  done
  printf '}}
'
} >> "$_HIST" 2>/dev/null || true

# ============================================================
# Summary
# ============================================================
echo -e "${CYAN}=========================================${NC}"
# 未判定的步驟要先講、而且一定要講 —— 否則「12 步全過」會被讀成「12 步都檢查過」。
# 2026-08-11 之前正是如此：容器內 5 步零效力，摘要卻印「all passed」。
if [[ ${#SKIP_STEPS[@]} -gt 0 ]]; then
    echo -e "${YELLOW} ⊘ 未判定 ${#SKIP_STEPS[@]} 步（此環境不具備所需條件，由 host weekly 負責）${NC}"
    for s in "${SKIP_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${YELLOW}⊘${NC} $s"
    done
    echo -e "   本次實際判定 $((TOTAL_STEPS - ${#SKIP_STEPS[@]}))/${TOTAL_STEPS} 步"
fi
if [[ $FAIL_COUNT -eq 0 && $WARN_COUNT -eq 0 ]]; then
    if [[ ${#SKIP_STEPS[@]} -gt 0 ]]; then
        echo -e "${GREEN} ✅ Tier 1 daily：已判定的步驟全過${NC}"
    else
        echo -e "${GREEN} ✅ Tier 1 daily all passed${NC}"
    fi
else
    [[ $FAIL_COUNT -gt 0 ]] && echo -e "${RED} ✗ Tier 1 daily: $FAIL_COUNT step(s) RED${NC}"
    for s in "${FAIL_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${RED}✗${NC} $s"
    done
    # YELLOW 單獨列：需要看一眼，但不是「壞了」（如無害的 orphan volume）
    [[ $WARN_COUNT -gt 0 ]] && echo -e "${YELLOW} ⚠ YELLOW $WARN_COUNT step(s)（非故障，待確認）${NC}"
    for s in "${WARN_STEPS[@]:-}"; do
        [[ -n "$s" ]] && echo -e "   ${YELLOW}⚠${NC} $s"
    done
    # exit 1 的門檻**只由 RED 決定**，不含 YELLOW —— 否則 cron 會因為
    # 無害的 orphan volume 每天報一次，幾週後這個告警就沒人看了（L31 家族）。
    # 2026-08-07：原本 exit 1 **只在 --strict 時**觸發 —— 於是不帶旗標的呼叫端
    # 會拿到「印著 N step(s) RED、退出碼卻是 0」。我自己寫 host 執行器時就踩了：
    # 報 2 步 RED、wrapper 記 rc=0，交接給容器端就會被寫成 PASS。
    # 退出碼必須與印出的狀態一致（L83）；--strict 保留但不再是 exit 1 的前提。
    if [[ $FAIL_COUNT -gt 0 ]]; then
        echo -e "${RED} RED → exit 1 (cron 將觸發 LINE 推送)${NC}"
        exit 1
    fi
fi
echo -e "${CYAN}=========================================${NC}"
