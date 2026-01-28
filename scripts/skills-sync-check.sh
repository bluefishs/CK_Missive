#!/bin/bash
# Skills Sync Check Script (Cross-platform)
# Version: 1.0.0
# Date: 2026-01-28

set -e

VERBOSE=${1:-""}
ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Skills Sync Check${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 1. Check Skills files
echo "1. Checking Skills files..."

EXPECTED_SKILLS=(
    "document-management.md"
    "calendar-integration.md"
    "api-development.md"
    "database-schema.md"
    "testing-guide.md"
    "frontend-architecture.md"
    "error-handling.md"
    "security-hardening.md"
    "type-management.md"
    "api-serialization.md"
    "python-common-pitfalls.md"
    "unicode-handling.md"
    "database-performance.md"
    "development-environment.md"
)

SKILLS_PATH=".claude/skills"
MISSING_SKILLS=0

for skill in "${EXPECTED_SKILLS[@]}"; do
    if [ ! -f "$SKILLS_PATH/$skill" ]; then
        echo -e "   ${RED}[FAIL] Missing: $skill${NC}"
        ((ERRORS++))
        ((MISSING_SKILLS++))
    elif [ "$VERBOSE" == "-v" ]; then
        echo -e "   ${GREEN}[PASS] $skill${NC}"
    fi
done

if [ $MISSING_SKILLS -eq 0 ]; then
    echo -e "   ${GREEN}[PASS] All ${#EXPECTED_SKILLS[@]} Skills files exist${NC}"
fi

# 2. Check Commands files
echo ""
echo "2. Checking Commands files..."

EXPECTED_COMMANDS=(
    "pre-dev-check.md"
    "route-sync-check.md"
    "api-check.md"
    "type-sync.md"
    "dev-check.md"
    "data-quality-check.md"
    "db-backup.md"
    "csv-import-validate.md"
    "security-audit.md"
    "performance-check.md"
    "superpowers/brainstorm.md"
    "superpowers/write-plan.md"
    "superpowers/execute-plan.md"
)

COMMANDS_PATH=".claude/commands"
MISSING_COMMANDS=0

for cmd in "${EXPECTED_COMMANDS[@]}"; do
    if [ ! -f "$COMMANDS_PATH/$cmd" ]; then
        echo -e "   ${RED}[FAIL] Missing: $cmd${NC}"
        ((ERRORS++))
        ((MISSING_COMMANDS++))
    elif [ "$VERBOSE" == "-v" ]; then
        echo -e "   ${GREEN}[PASS] $cmd${NC}"
    fi
done

if [ $MISSING_COMMANDS -eq 0 ]; then
    echo -e "   ${GREEN}[PASS] All ${#EXPECTED_COMMANDS[@]} Commands files exist${NC}"
fi

# 3. Check Hooks files
echo ""
echo "3. Checking Hooks files..."

EXPECTED_HOOKS=(
    "typescript-check.ps1"
    "python-lint.ps1"
    "validate-file-location.ps1"
    "route-sync-check.ps1"
    "api-serialization-check.ps1"
    "link-id-check.ps1"
    "link-id-validation.ps1"
    "performance-check.ps1"
)

HOOKS_PATH=".claude/hooks"
MISSING_HOOKS=0

for hook in "${EXPECTED_HOOKS[@]}"; do
    if [ ! -f "$HOOKS_PATH/$hook" ]; then
        echo -e "   ${RED}[FAIL] Missing: $hook${NC}"
        ((ERRORS++))
        ((MISSING_HOOKS++))
    elif [ "$VERBOSE" == "-v" ]; then
        echo -e "   ${GREEN}[PASS] $hook${NC}"
    fi
done

if [ $MISSING_HOOKS -eq 0 ]; then
    echo -e "   ${GREEN}[PASS] All ${#EXPECTED_HOOKS[@]} Hooks files exist${NC}"
fi

# 4. Check Agents files
echo ""
echo "4. Checking Agents files..."

EXPECTED_AGENTS=(
    "code-review.md"
    "api-design.md"
    "bug-investigator.md"
)

AGENTS_PATH=".claude/agents"
MISSING_AGENTS=0
INVALID_AGENTS=0

for agent in "${EXPECTED_AGENTS[@]}"; do
    if [ ! -f "$AGENTS_PATH/$agent" ]; then
        echo -e "   ${RED}[FAIL] Missing: $agent${NC}"
        ((ERRORS++))
        ((MISSING_AGENTS++))
    else
        # Validate agent structure
        AGENT_FILE="$AGENTS_PATH/$agent"
        HAS_TITLE=$(grep -c "^# " "$AGENT_FILE" || true)
        HAS_PURPOSE=$(grep -c "用途" "$AGENT_FILE" || true)
        HAS_TRIGGER=$(grep -c "觸發" "$AGENT_FILE" || true)

        if [ "$HAS_TITLE" -eq 0 ] || [ "$HAS_PURPOSE" -eq 0 ] || [ "$HAS_TRIGGER" -eq 0 ]; then
            echo -e "   ${YELLOW}[WARN] $agent missing required fields (title/purpose/trigger)${NC}"
            ((WARNINGS++))
            ((INVALID_AGENTS++))
        elif [ "$VERBOSE" == "-v" ]; then
            echo -e "   ${GREEN}[PASS] $agent (structure OK)${NC}"
        fi
    fi
done

if [ $MISSING_AGENTS -eq 0 ] && [ $INVALID_AGENTS -eq 0 ]; then
    echo -e "   ${GREEN}[PASS] All ${#EXPECTED_AGENTS[@]} Agents files exist and valid${NC}"
elif [ $MISSING_AGENTS -eq 0 ]; then
    echo -e "   ${GREEN}[PASS] All ${#EXPECTED_AGENTS[@]} Agents files exist${NC}"
fi

# 5. Check settings.json
echo ""
echo "5. Checking settings.json..."

SETTINGS_PATH=".claude/settings.json"
if [ -f "$SETTINGS_PATH" ]; then
    # Check inherit paths using grep
    if grep -q "_shared/shared" "$SETTINGS_PATH"; then
        echo -e "   ${GREEN}[PASS] inherit: _shared/shared${NC}"
    else
        echo -e "   ${RED}[FAIL] Missing inherit: _shared/shared${NC}"
        ((ERRORS++))
    fi

    if grep -q "_shared/backend" "$SETTINGS_PATH"; then
        echo -e "   ${GREEN}[PASS] inherit: _shared/backend${NC}"
    else
        echo -e "   ${RED}[FAIL] Missing inherit: _shared/backend${NC}"
        ((ERRORS++))
    fi
else
    echo -e "   ${RED}[FAIL] settings.json not found${NC}"
    ((ERRORS++))
fi

# 6. Check README files
echo ""
echo "6. Checking README files..."

README_FILES=(
    ".claude/skills/README.md"
    ".claude/hooks/README.md"
)

for readme in "${README_FILES[@]}"; do
    if [ -f "$readme" ]; then
        echo -e "   ${GREEN}[PASS] $readme${NC}"
    else
        echo -e "   ${YELLOW}[WARN] $readme not found${NC}"
        ((WARNINGS++))
    fi
done

# Summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Summary${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

TOTAL_CHECKS=$((${#EXPECTED_SKILLS[@]} + ${#EXPECTED_COMMANDS[@]} + ${#EXPECTED_HOOKS[@]} + ${#EXPECTED_AGENTS[@]}))
FAILED_CHECKS=$((MISSING_SKILLS + MISSING_COMMANDS + MISSING_HOOKS + MISSING_AGENTS))
PASSED_CHECKS=$((TOTAL_CHECKS - FAILED_CHECKS))

echo "Total checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Errors: $ERRORS${NC}"
else
    echo -e "${GREEN}Errors: 0${NC}"
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
else
    echo -e "${GREEN}Warnings: 0${NC}"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS] Skills sync check passed!${NC}"
    exit 0
else
    echo -e "${RED}[FAILED] Skills sync check failed!${NC}"
    exit 1
fi
