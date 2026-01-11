# /pre-dev-check - 開發前強制檢查

在開始任何開發任務前，執行此指令以確保遵循專案規範。

## 使用方式

```
/pre-dev-check [任務類型]
```

**任務類型**：
- `route` - 新增前端路由/頁面
- `api` - 新增後端 API
- `nav` - 新增/修改導覽項目
- `auth` - 修改認證/權限
- `import` - 資料匯入功能
- `db` - 資料庫變更
- `fix` - Bug 修復

## 執行步驟

### 步驟 1：識別任務類型

根據使用者描述的任務，自動判斷對應的檢查清單。

### 步驟 2：載入對應規範

讀取 `.claude/MANDATORY_CHECKLIST.md` 中對應的檢查清單。

### 步驟 3：檢查必讀文件

列出該任務類型需要預先閱讀的規範文件。

### 步驟 4：確認關鍵檢查項目

在開發前確認：
- [ ] 已閱讀對應規範文件
- [ ] 了解必須同步更新的位置
- [ ] 知道開發後的驗證步驟

## 任務類型對照表

| 任務類型 | 代碼 | 必讀清單 |
|---------|------|---------|
| 新增前端路由/頁面 | `route` | 清單 A |
| 新增後端 API | `api` | 清單 B |
| 新增/修改導覽項目 | `nav` | 清單 C |
| 修改認證/權限 | `auth` | 清單 D |
| 資料匯入功能 | `import` | 清單 E |
| 資料庫變更 | `db` | 清單 F |
| Bug 修復 | `fix` | 清單 G |

## 關鍵同步位置

### 導覽項目變更 (最常見問題)

新增路由時必須同步更新三處：

```
1. frontend/src/router/types.ts      → ROUTES 常數
2. frontend/src/router/AppRouter.tsx → Route 元素
3. backend/app/scripts/init_navigation_data.py → DEFAULT_NAVIGATION_ITEMS
```

### 認證相關變更

所有認證判斷必須使用：

```typescript
import { isAuthDisabled, isInternalIP, detectEnvironment } from '../config/env';
```

禁止在其他地方重複定義認證檢測邏輯。

### API 端點變更

前後端必須同步：

```
後端: backend/app/api/endpoints/*.py
前端: frontend/src/services/endpoints.ts
```

## 開發後驗證

完成開發後必須執行：

```bash
# 前端 TypeScript 編譯檢查
cd frontend && npx tsc --noEmit

# 後端 Python 語法檢查
cd backend && python -m py_compile app/main.py
```

## 相關指令

- `/route-sync-check` - 前後端路由一致性檢查
- `/api-check` - API 端點一致性檢查
- `/type-sync` - 型別同步檢查
- `/dev-check` - 開發環境檢查

## 相關文件

- `.claude/MANDATORY_CHECKLIST.md` - 強制性開發檢查清單
- `docs/DEVELOPMENT_STANDARDS.md` - 統一開發規範總綱
- `.claude/DEVELOPMENT_GUIDELINES.md` - 開發指引
