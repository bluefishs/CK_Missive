#!/bin/bash
# soul-fidelity-multi-baseline.sh — 多 provider × 多 model 批次 fidelity 測試
#
# 2026-04-24 建立 — 配合 docs/evaluations/qwen3-6-27b-hermes-primary.md 附錄 C
# 及 memory feedback_simplified_chinese_avoidance.md 做基線快照。
#
# 每組配置跑一次 soul-fidelity-eval.py，最後彙整 fidelity score。
#
# 使用：
#   bash scripts/checks/soul-fidelity-multi-baseline.sh
#
# 前置：需 GROQ_API_KEY 在 .env，Ollama 服務已啟動並下載 gemma4:e2b / qwen2.5:7b

set -e
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

# Load env
if [ -f .env ]; then
    export GROQ_API_KEY=$(grep ^GROQ_API_KEY .env | cut -d= -f2-)
fi

: "${GROQ_API_KEY:?GROQ_API_KEY required}"
: "${OLLAMA_BASE_URL:=http://localhost:11434/v1}"
: "${SOUL_MD_PATH:=/d/CKProject/CK_AaaP/runbooks/hermes-stack/SOUL.md}"

if [ ! -f "$SOUL_MD_PATH" ]; then
    echo "SOUL.md not found at $SOUL_MD_PATH" >&2
    exit 1
fi

echo "============================================"
echo "SOUL fidelity multi-provider baseline"
echo "============================================"
echo "SOUL: $SOUL_MD_PATH"
echo ""

OUT_DIR="$PROJECT_ROOT/scripts/checks"
TS=$(date +%Y%m%d_%H%M%S)

# 4 configurations to benchmark (將結果 append 到彙總檔)
SUMMARY="$OUT_DIR/.soul-multi-baseline-$TS.md"
cat > "$SUMMARY" <<EOF
# SOUL Fidelity Multi-Provider Baseline $TS

SOUL.md: $SOUL_MD_PATH

| # | Provider | Model | Fidelity | 備註 |
|---|---|---|---|---|
EOF

run_config() {
    local label="$1"; shift
    local provider="$1"; shift
    local model="$1"; shift
    local note="$1"; shift
    echo ""
    echo "[$label] $provider / $model"
    local TMP_OUT
    TMP_OUT=$(mktemp)
    if [ "$provider" = "groq" ]; then
        GROQ_EVAL_MODEL="$model" OLLAMA_EVAL_MODEL=DISABLED_SKIP \
            SOUL_MD_PATH="$SOUL_MD_PATH" OLLAMA_BASE_URL="$OLLAMA_BASE_URL" \
            python scripts/checks/soul-fidelity-eval.py 2>&1 | tee "$TMP_OUT" | tail -20
    else
        GROQ_EVAL_MODEL=DISABLED_SKIP OLLAMA_EVAL_MODEL="$model" \
            SOUL_MD_PATH="$SOUL_MD_PATH" OLLAMA_BASE_URL="$OLLAMA_BASE_URL" \
            python scripts/checks/soul-fidelity-eval.py 2>&1 | tee "$TMP_OUT" | tail -20
    fi
    local score
    score=$(grep -E "^\s*${provider}:" "$TMP_OUT" | tail -1 | grep -oE '[0-9]+/20 \([0-9]+%\)' | head -1)
    rm -f "$TMP_OUT"
    echo "| $label | $provider | $model | ${score:-N/A} | $note |" >> "$SUMMARY"
}

# 4 baselines
run_config "現況 P2 本地" "ollama" "gemma4:e2b" "既有主力"
run_config "候選 P2 本地" "ollama" "qwen2.5:7b" "繁中候選 🥇"
run_config "現況 P1 雲端" "groq" "llama-3.3-70b-versatile" "synthesis default"
run_config "候選 P1 雲端" "groq" "qwen/qwen3-32b" "簡體 + thinking ⚠️"

echo ""
echo "============================================"
echo "Summary -> $SUMMARY"
echo "============================================"
cat "$SUMMARY"
