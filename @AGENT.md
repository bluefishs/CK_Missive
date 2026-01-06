# Agent Build Instructions

## Project Setup
```bash
# Install dependencies (example for Node.js project)
npm install

# Or for Python project
pip install -r requirements.txt

# Or for Rust project  
cargo build
```

## Running Tests
```bash
# Node.js
npm test

# Python
pytest

# Rust
cargo test
```

## Build Commands
```bash
# Production build
npm run build
# or
cargo build --release
```

## Development Server
```bash
# Start development server
npm run dev
# or
cargo run
```

## Key Learnings

### 型別一致性 (Type Consistency)
- **單一真實來源**: Database → Backend Model → Schema → Frontend Types
- 新增欄位時必須同步更新: `models.py` → `schemas/*.py` → `*Api.ts` → `types/index.ts`
- 前端 API Interface 應與後端 Response Schema 完全對應
- 詳見: `@TYPE_CONSISTENCY_SKILL_SPEC.md`

### TypeScript 嚴格模式最佳實踐 (2026-01-06 更新)
- **介面繼承**: 跨檔案共用介面時，使用 `extends` 擴展基礎介面，避免重複定義
  ```typescript
  // ✅ 正確：擴展基礎介面
  import { NavigationItem as BaseNavItem } from '../hooks/usePermissions';
  interface NavigationItem extends BaseNavItem { additionalField?: string; }

  // ❌ 避免：重複定義相同名稱介面
  interface NavigationItem { /* 重複欄位... */ }
  ```
- **泛型元件**: Ant Design 泛型元件使用時明確指定型別
  ```typescript
  // ✅ InputNumber 指定數值型別
  <InputNumber<number> formatter={...} parser={(v) => Number(v!.replace(...))} />
  ```
- **RangePicker 日期範圍**: 處理可能為 null 的日期值
  ```typescript
  onChange={(dates) => setFilters({
    dateRange: dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null
  })}
  ```
- **陣列索引**: TypeScript 陣列索引可能回傳 undefined
  ```typescript
  // ✅ 使用 nullish coalescing
  const value = array.split(':')[0] ?? '';
  const item = exportData[0]!; // 非空斷言在確認非空後使用
  ```
- **ID 型別**: 開發模式的 mock user 使用 `id: 0` (number)，非 `'dev-user'` (string)

### 前後端整合
- POST-only API 設計避免敏感資料暴露於 URL
- API 端點回傳關聯資料 (如 `contract_project_name`) 需在後端明確填充
- 前端接收資料時使用預設值防禦 undefined: `doc.field || 'default'`

### UI 風格規範
- 表格欄位參考 `/documents` 頁面的 `DocumentList.tsx`
- 發文形式 Tag 顏色: 電子交換=green, 紙本郵寄=orange, 電子+紙本=blue
- 收發單位前綴: 收文="來文："(綠色), 發文="發至："(藍色)

### 常見錯誤避免
- 變數在 try 區塊外宣告避免 ReferenceError
- HTTP Method 前後端必須一致 (均使用 POST)
- TypeScript Interface 缺欄位會導致編譯警告

### SKILL 規範文件
| 文件 | 用途 |
|------|------|
| `@TYPE_CONSISTENCY_SKILL_SPEC.md` | 型別一致性與 UI 風格規範 |
| `@SCHEMA_VALIDATION_SKILL_SPEC.md` | Model-Database 一致性驗證 |
| `@CSV_IMPORT_SKILL_SPEC.md` | CSV 匯入模組開發規範 |
| `@PROJECT_CODE_SPEC.md` | 專案編號產生規則 |
| `@SYSTEM_ARCHITECTURE_REVIEW.md` | 系統架構審查與優化規劃 |

## Feature Development Quality Standards

**CRITICAL**: All new features MUST meet the following mandatory requirements before being considered complete.

### Testing Requirements

- **Minimum Coverage**: 85% code coverage ratio required for all new code
- **Test Pass Rate**: 100% - all tests must pass, no exceptions
- **Test Types Required**:
  - Unit tests for all business logic and services
  - Integration tests for API endpoints or main functionality
  - End-to-end tests for critical user workflows
- **Coverage Validation**: Run coverage reports before marking features complete:
  ```bash
  # Examples by language/framework
  npm run test:coverage
  pytest --cov=src tests/ --cov-report=term-missing
  cargo tarpaulin --out Html
  ```
- **Test Quality**: Tests must validate behavior, not just achieve coverage metrics
- **Test Documentation**: Complex test scenarios must include comments explaining the test strategy

### Git Workflow Requirements

Before moving to the next feature, ALL changes must be:

1. **Committed with Clear Messages**:
   ```bash
   git add .
   git commit -m "feat(module): descriptive message following conventional commits"
   ```
   - Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, etc.
   - Include scope when applicable: `feat(api):`, `fix(ui):`, `test(auth):`
   - Write descriptive messages that explain WHAT changed and WHY

2. **Pushed to Remote Repository**:
   ```bash
   git push origin <branch-name>
   ```
   - Never leave completed features uncommitted
   - Push regularly to maintain backup and enable collaboration
   - Ensure CI/CD pipelines pass before considering feature complete

3. **Branch Hygiene**:
   - Work on feature branches, never directly on `main`
   - Branch naming convention: `feature/<feature-name>`, `fix/<issue-name>`, `docs/<doc-update>`
   - Create pull requests for all significant changes

4. **Ralph Integration**:
   - Update @fix_plan.md with new tasks before starting work
   - Mark items complete in @fix_plan.md upon completion
   - Update PROMPT.md if development patterns change
   - Test features work within Ralph's autonomous loop

### Documentation Requirements

**ALL implementation documentation MUST remain synchronized with the codebase**:

1. **Code Documentation**:
   - Language-appropriate documentation (JSDoc, docstrings, etc.)
   - Update inline comments when implementation changes
   - Remove outdated comments immediately

2. **Implementation Documentation**:
   - Update relevant sections in this AGENT.md file
   - Keep build and test commands current
   - Update configuration examples when defaults change
   - Document breaking changes prominently

3. **README Updates**:
   - Keep feature lists current
   - Update setup instructions when dependencies change
   - Maintain accurate command examples
   - Update version compatibility information

4. **AGENT.md Maintenance**:
   - Add new build patterns to relevant sections
   - Update "Key Learnings" with new insights
   - Keep command examples accurate and tested
   - Document new testing patterns or quality gates

### Feature Completion Checklist

Before marking ANY feature as complete, verify:

- [ ] All tests pass with appropriate framework command
- [ ] Code coverage meets 85% minimum threshold
- [ ] Coverage report reviewed for meaningful test quality
- [ ] Code formatted according to project standards
- [ ] Type checking passes (if applicable)
- [ ] All changes committed with conventional commit messages
- [ ] All commits pushed to remote repository
- [ ] @fix_plan.md task marked as complete
- [ ] Implementation documentation updated
- [ ] Inline code comments updated or added
- [ ] AGENT.md updated (if new patterns introduced)
- [ ] Breaking changes documented
- [ ] Features tested within Ralph loop (if applicable)
- [ ] CI/CD pipeline passes

### Rationale

These standards ensure:
- **Quality**: High test coverage and pass rates prevent regressions
- **Traceability**: Git commits and @fix_plan.md provide clear history of changes
- **Maintainability**: Current documentation reduces onboarding time and prevents knowledge loss
- **Collaboration**: Pushed changes enable team visibility and code review
- **Reliability**: Consistent quality gates maintain production stability
- **Automation**: Ralph integration ensures continuous development practices

**Enforcement**: AI agents should automatically apply these standards to all feature development tasks without requiring explicit instruction for each task.
