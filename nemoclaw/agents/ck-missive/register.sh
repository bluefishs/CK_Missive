#!/bin/bash
# 在 OpenClaw 中註冊乾坤 Skill
#
# 用法: bash nemoclaw/agents/ck-missive/register.sh
#
# 前提:
#   1. OpenClaw 已安裝在 D:\CKProject\CK_OpenClaw
#   2. 乾坤後端已啟動 (port 8001)
#   3. MCP_SERVICE_TOKEN 已設定

OPENCLAW_DIR="D:/CKProject/CK_OpenClaw"
SKILL_DIR="$OPENCLAW_DIR/skills/ck-missive"
AGENT_FILE="$(dirname "$0")/agent.md"

echo "=== NemoClaw: 註冊乾坤 Skill 到 OpenClaw ==="

# 檢查 OpenClaw
if [ ! -d "$OPENCLAW_DIR" ]; then
    echo "錯誤: OpenClaw 未找到: $OPENCLAW_DIR"
    exit 1
fi

# 檢查乾坤引擎
if ! curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "錯誤: 乾坤引擎未啟動 (port 8001)"
    exit 1
fi

echo "✓ OpenClaw 存在"
echo "✓ 乾坤引擎運行中"

# 建立 skill 目錄
mkdir -p "$SKILL_DIR"

# 複製 agent.md 作為 OpenClaw skill
cp "$AGENT_FILE" "$SKILL_DIR/SKILL.md"

echo "✓ Skill 已註冊: $SKILL_DIR/SKILL.md"
echo ""
echo "下一步:"
echo "  1. 在 OpenClaw 配置中啟用 ck-missive skill"
echo "  2. 設定 MCP_SERVICE_TOKEN 環境變數"
echo "  3. 重啟 OpenClaw gateway"
