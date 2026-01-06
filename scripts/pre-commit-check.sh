#!/bin/bash
# CK_Missive Pre-commit 強制檢查腳本
# 用法: ./scripts/pre-commit-check.sh
# 或配置為 Git hook: cp scripts/pre-commit-check.sh .git/hooks/pre-commit

set -e

echo "================================================"
echo "  CK_Missive 提交前強制檢查"
echo "  參照: @DEVELOPMENT_STANDARDS.md"
echo "================================================"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# 檢查 1: TypeScript 編譯
echo -e "${YELLOW}[1/3]${NC} TypeScript 型別檢查..."
cd frontend
if npx tsc --noEmit 2>/dev/null; then
    echo -e "${GREEN}✓${NC} TypeScript 檢查通過"
else
    echo -e "${RED}✗${NC} TypeScript 檢查失敗"
    echo "  請執行: cd frontend && npx tsc --noEmit 查看詳細錯誤"
    ERRORS=$((ERRORS + 1))
fi
cd ..

# 檢查 2: 前端建置
echo -e "${YELLOW}[2/3]${NC} 前端建置檢查..."
cd frontend
if npm run build > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 前端建置成功"
else
    echo -e "${RED}✗${NC} 前端建置失敗"
    echo "  請執行: cd frontend && npm run build 查看詳細錯誤"
    ERRORS=$((ERRORS + 1))
fi
cd ..

# 檢查 3: 相對 API 路徑
echo -e "${YELLOW}[3/3]${NC} API 路徑檢查..."
RELATIVE_API=$(grep -r "fetch('/api" frontend/src --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
if [ "$RELATIVE_API" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} 發現 $RELATIVE_API 處相對 API 路徑"
    echo "  建議使用 API_BASE_URL 替代 '/api'"
    # 這是警告，不阻止提交
else
    echo -e "${GREEN}✓${NC} API 路徑檢查通過"
fi

echo ""
echo "================================================"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}✗ 檢查失敗: $ERRORS 個錯誤${NC}"
    echo ""
    echo "請修復上述錯誤後再提交"
    echo "參考文件: @DEVELOPMENT_STANDARDS.md"
    exit 1
else
    echo -e "${GREEN}✓ 所有強制檢查通過${NC}"
    echo ""
    echo "可以安全提交代碼"
    exit 0
fi
