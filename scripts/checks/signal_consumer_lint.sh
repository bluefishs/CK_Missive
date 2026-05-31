#!/bin/bash
#
# signal_consumer_lint.sh — Memory Signal Producer-Consumer 治理 lint
#
# 領域：consciousness signal flow governance（v5.12 Phase D）
#
# 簡化版：列出每個已知 signal 在 codebase 的引用次數
# - 若 0 引用 → 報「孤兒 signal」警報
# - 若 ≥ 2 引用（producer + consumer 都至少 1 處）→ OK
# - 註：const 變數定義也算引用，故 1 引用通常表示「只定義沒用」
#
# 用法：bash scripts/checks/signal_consumer_lint.sh
# 退出：0 = 全部 ≥ 2 / 1 = 有孤兒（0 引用）

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

# v6.13 (2026-05-31) L52 family 第 9 案修法:
# bug: container 內 PROJECT_ROOT=/app 但 host backend/* flatten 入 /app/
#      → backend/app 不存在 (應該是 app/)
# 修法: 若 backend/app 不存在 fallback app/
if [ -d "backend/app" ]; then
    SCAN_DIR="backend/app"
elif [ -d "app" ]; then
    SCAN_DIR="app"
else
    echo "[ERROR] 找不到 backend code dir (backend/app or app)" >&2
    exit 2
fi

echo "=== Memory Signal Reference Count ==="
echo "領域：signal flow governance — 偵測孤兒（0 引用）"
echo "Note: const 變數定義也算引用；≥ 2 = producer + consumer 都有"
echo ""

# 已知 signal keys（手動維護同 MEMORY_SIGNAL_FLOW.md §1.1）
SIGNAL_KEYS=(
    "agent:evolution:signals"
    "agent:evolution:query_count"
    "agent:evolution:last_run"
    "agent:critical_feedback"
    "agent:domain_scores"
    "agent:patterns:detail"
    "agent:patterns:index"
    "agent:tool_stats"
    "agent:evolution:journal"
    "agent:evolution:eval_history"
    "agent:evolution:state"
)

violations=0
suspicious=0

# 2026-05-27: 修 false positive — 同時計算 string literal + 對應 const name 使用
# 對應 const name 規律: SIGNAL_QUEUE_KEY / QUERY_COUNTER_KEY / LAST_EVOLUTION_KEY ... etc
# 邏輯: refs_string + (refs_const - 1) — 扣掉 const 定義那行避免雙算

for key in "${SIGNAL_KEYS[@]}"; do
    # 1. string literal 出現次數
    refs_string=$(grep -rn "${key}" "$SCAN_DIR" --include="*.py" 2>/dev/null | grep -v __pycache__ | wc -l)

    # 2. 找該 key 對應的 const name（從 "= \"key\"" 反推）
    const_line=$(grep -rn "= \"${key}\"" "$SCAN_DIR" --include="*.py" 2>/dev/null | grep -v __pycache__ | head -1)
    const_name=""
    if [ -n "$const_line" ]; then
        # extract LHS const name (between : and =)
        const_name=$(echo "$const_line" | sed -E 's|.*:[0-9]+:[[:space:]]*([A-Z_][A-Z0-9_]*)[[:space:]]*=.*|\1|')
    fi

    # 3. const name 使用次數（扣定義行）
    refs_const=0
    if [ -n "$const_name" ] && [ "$const_name" != "$const_line" ]; then
        refs_const=$(grep -rn "\b${const_name}\b" "$SCAN_DIR" --include="*.py" 2>/dev/null | grep -v __pycache__ | wc -l)
        # 扣掉本 audit 跑 grep 時撞到的定義行
        refs_const=$((refs_const > 0 ? refs_const - 1 : 0))
    fi

    refs=$((refs_string + refs_const))

    if [ "$refs" -eq 0 ]; then
        echo "[VIOLATION] $key: 0 references — 完全孤兒"
        violations=$((violations + 1))
    elif [ "$refs" -lt 2 ]; then
        echo "[SUSPICIOUS] $key: $refs reference — 只 1 處（可能只 const 定義沒用）"
        suspicious=$((suspicious + 1))
    else
        if [ -n "$const_name" ]; then
            echo "[OK] $key: $refs references (string=$refs_string + const=$const_name uses $refs_const)"
        else
            echo "[OK] $key: $refs references"
        fi
    fi
done

echo ""
total=${#SIGNAL_KEYS[@]}
ok_count=$((total - violations - suspicious))
echo "Summary: $ok_count/$total OK, $suspicious suspicious, $violations violations"
echo ""

if [ "$violations" -gt 0 ]; then
    echo "[FAIL] 共 $violations 個完全孤兒 signal"
    echo "Map: docs/architecture/MEMORY_SIGNAL_FLOW.md"
    exit 1
fi

if [ "$suspicious" -gt 0 ]; then
    echo "[WARN] $suspicious 個 signal 只 1 處引用（可能 const 定義沒用）"
    echo "建議檢查："
    echo "  for key in \"\${SIGNAL_KEYS[@]}\"; do grep -rn \"\$key\" backend/app; done"
    echo "Map: docs/architecture/MEMORY_SIGNAL_FLOW.md"
fi

echo "[OK] 0 完全孤兒 signal"
exit 0
