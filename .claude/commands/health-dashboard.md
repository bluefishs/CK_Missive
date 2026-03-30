# 系統健康儀表板 (Health Dashboard)

> **版本**: 1.0.0 | **用途**: 一鍵產生當前系統健康報告

執行全面健康檢查，輸出結構化報告。

## 執行項目

### 1. 前端品質指標
```bash
# TypeScript 編譯
cd frontend && npx tsc --noEmit 2>&1 | tail -5

# 超閾值頁面 (>480L)
find frontend/src/pages -name "*.tsx" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 480 {print}' | head -10

# 超閾值元件 (>480L)
find frontend/src/components -name "*.tsx" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 480 {print}' | head -10

# 超閾值 Hooks (>480L)
find frontend/src/hooks -name "*.ts" ! -path "*__tests__*" -exec wc -l {} + | sort -rn | awk '$1 > 480 {print}' | head -5
```

### 2. 後端品質指標
```bash
# Python 語法
cd backend && python -m py_compile app/main.py

# 超閾值服務 (>580L)
find backend/app/services -name "*.py" -exec wc -l {} + | sort -rn | awk '$1 > 580 {print}' | head -10

# DB 遷移 HEAD 檢查
cd backend && python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; s=ScriptDirectory.from_config(Config('alembic.ini')); heads=s.get_heads(); print(f'Heads: {len(heads)} — {\"OK (single)\" if len(heads)==1 else \"WARNING: multiple heads!\"}'); print(f'Total: {len(list(s.walk_revisions()))}')"
```

### 3. 測試統計
```bash
# 測試檔案數
echo "Backend tests: $(find backend/tests -name '*.py' | wc -l)"
echo "Frontend tests: $(find frontend/src -name '*.test.*' | wc -l)"
```

### 4. Git 活動
```bash
echo "Total commits: $(git log --oneline | wc -l)"
echo "This month: $(git log --oneline --since='$(date +%Y-%m-01)' | wc -l)"
echo "Uncommitted: $(git status --short | wc -l)"
```

### 5. 專案規模
```bash
echo "Frontend files: $(find frontend/src -name '*.ts' -o -name '*.tsx' | wc -l)"
echo "Backend files: $(find backend/app -name '*.py' | wc -l)"
echo "DB migrations: $(ls backend/alembic/versions/*.py 2>/dev/null | wc -l)"
```

## 輸出格式

產出 Markdown 格式報告，包含：

| 維度 | 指標 | 狀態 |
|------|------|------|
| TypeScript | 0 errors | ✅/❌ |
| 前端 >480L | N 個 | ✅ (0) / ⚠️ (N) |
| 後端 >580L | N 個 | ✅ (0) / ⚠️ (N) |
| 遷移 HEAD | 單一/多重 | ✅/❌ |
| 測試檔案 | N 個 | 數字 |
| 提交活動 | 本月 N | 數字 |

## 相關指令

- `/dev-check` — 開發環境檢查
- `/verify` — 綜合驗證 (Build/Type/Lint/Test)
- `/performance-check` — 效能診斷
