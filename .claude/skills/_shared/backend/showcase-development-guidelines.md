# CK_Showcase 開發指南

> **技能名稱**: CK_Showcase 開發指南
> **觸發**: `/showcase-dev`, `開發規範`, `development guidelines`, `coding standards`
> **版本**: 1.0.0
> **分類**: project
> **更新日期**: 2026-01-28

**用途**：CK_Showcase 專案開發規範與最佳實踐
**適用場景**：新功能開發、程式碼審查、架構決策

---

## 一、架構原則

### 1.1 SSOT (Single Source of Truth)

**核心配置檔案**: `config/ssot.yaml`

```yaml
# 所有配置的唯一真理來源
# 前端與後端皆從此檔案讀取或生成配置
meta:
  name: 'CK_Showcase'
  version: '1.0.0'
```

**類型生成流程**:

```bash
# 生成 TypeScript 類型
python scripts/generate-ssot-types.py

# 驗證配置
python scripts/validate-ssot.py
```

### 1.2 POST-Only API 設計

**強制規則**：所有 API 端點必須使用 POST 方法

```python
# ✅ 正確
@router.post("/skills/query")
async def query_skills(request: QueryRequest):
    pass

# ❌ 錯誤
@router.get("/skills")
async def get_skills():
    pass
```

**原因**：

- 資安規範要求，防止敏感資料暴露於 URL
- 統一的請求格式便於維護
- 支援複雜的查詢參數

### 1.3 Repository Pattern

**目錄結構**:

```
backend/repositories/
├── base_repository.py    # 基礎 Repository 介面
├── backup_repository.py  # 備份資料存取
├── config_repository.py  # 系統配置存取
├── overview_repository.py # 概覽資料存取
└── test_repository.py    # 測試資料存取
```

**實作範例**:

```python
from backend.repositories.base_repository import BaseRepository
from backend.database.models import SystemConfig

class ConfigRepository(BaseRepository[SystemConfig]):
    async def get_by_key(self, key: str) -> Optional[SystemConfig]:
        async with get_session() as session:
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.key == key)
            )
            return result.scalar_one_or_none()
```

---

## 二、資料庫規範

### 2.1 PostgreSQL 共用 Schema

**Schema 名稱**: `ck_shared`

**用途**: 跨專案共用資料

```sql
-- 建立 schema
CREATE SCHEMA IF NOT EXISTS ck_shared;

-- 設定搜尋路徑
SET search_path TO ck_shared, public;
```

### 2.2 SQLAlchemy 模型

**檔案位置**: `backend/database/models.py`

```python
from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class SystemConfig(Base):
    __tablename__ = 'system_config'
    __table_args__ = {'schema': 'ck_shared'}  # 指定 schema

    id = Column(UUID(as_uuid=True), primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(JSONB, nullable=False)
```

### 2.3 Alembic Migration

**位置**: `backend/database/migrations/`

```bash
# 建立新 migration
cd backend
alembic revision --autogenerate -m "Add new table"

# 執行 migration
alembic upgrade head

# 回滾
alembic downgrade -1
```

---

## 三、前端開發規範

### 3.1 API 服務層

**檔案結構**:

```
src/services/
├── core/
│   ├── index.ts              # 核心服務匯出
│   ├── createEntityApiService.ts  # 通用 Entity API 服務
│   ├── transformers.ts       # 資料轉換器
│   └── mockData/             # Mock 資料
├── skillsApi.ts              # Skills API
├── agentsApi.ts              # Agents API
└── index.ts                  # 統一匯出
```

**通用 API 服務模式**:

```typescript
import { createEntityApiService } from './core/createEntityApiService';

export const skillsService = createEntityApiService<Skill>({
  baseUrl: '/api/skills',
  entityName: 'skill',
});

// 使用
const skills = await skillsService.query({ category: 'react' });
const skill = await skillsService.getById('skill-id');
```

### 3.2 Mock 資料系統

**環境變數**:

```env
# 啟用 Mock 模式
VITE_USE_MOCK=true

# 預設使用真實 API
VITE_USE_MOCK=false
```

**Mock 資料位置**: `src/services/core/mockData/`

```typescript
// 判斷是否使用 Mock
const useMock = import.meta.env.VITE_USE_MOCK === 'true';

export async function fetchData() {
  if (useMock) {
    return mockData;
  }
  return await apiClient.post('/api/endpoint');
}
```

### 3.3 組件設計

**命名規範**:

- 組件: PascalCase (e.g., `SkillDetailModal.tsx`)
- Hooks: camelCase + use 前綴 (e.g., `useSkillsData.ts`)
- 服務: camelCase (e.g., `skillsApi.ts`)

**目錄結構**:

```
src/pages/skills/
├── SkillsManagementPage.tsx  # 主頁面
├── components/
│   ├── index.ts              # 組件匯出
│   ├── SkillDetailModal.tsx
│   ├── SkillsSearchPanel.tsx
│   └── AnalysisSuggestionsPanel.tsx
└── hooks/
    └── useSkillsData.ts
```

---

## 四、後端開發規範

### 4.1 Router 結構

**檔案位置**: `backend/routers/`

```python
from fastapi import APIRouter, Depends
from backend.repositories.skill_repository import SkillRepository

router = APIRouter(prefix="/api/skills", tags=["Skills"])

@router.post("/query")
async def query_skills(
    request: QueryRequest,
    repo: SkillRepository = Depends(get_repository)
):
    return await repo.query(request)
```

### 4.2 錯誤處理

```python
from fastapi import HTTPException

@router.post("/detail/{skill_id}")
async def get_skill_detail(skill_id: str):
    skill = await repo.get_by_id(skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_id}"
        )
    return skill
```

### 4.3 日誌記錄

**規範**: 使用 logging 模組，避免 print 語句

```python
import logging

logger = logging.getLogger(__name__)

# ✅ 正確
logger.info("Processing skill: %s", skill_id)
logger.error("Failed to process: %s", error)

# ❌ 避免
print(f"Processing skill: {skill_id}")
```

---

## 五、CI/CD 規範

### 5.1 Commit 訊息格式

**Conventional Commits**:

```
type(scope): description

feat(skills): add category filter
fix(api): correct response format
refactor(backend): extract repository pattern
docs(readme): update installation guide
test(skills): add unit tests for query
chore(deps): update dependencies
```

### 5.2 Pre-commit 檢查

**自動執行**:

- `lint-staged`: 前端格式化
- `flake8`: 後端 lint (僅 staged 檔案)
- Skills 驗證 (若有變更)

### 5.3 CI 流程

| Job             | 說明                |
| --------------- | ------------------- |
| lint-frontend   | ESLint 檢查         |
| lint-backend    | Flake8 檢查         |
| test-frontend   | Vitest 測試         |
| test-backend    | Pytest + PostgreSQL |
| validate-skills | Skills 格式驗證     |

---

## 六、測試規範

### 6.1 後端測試

**位置**: `backend/tests/`

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_query_skills():
    response = client.post("/api/skills/query", json={})
    assert response.status_code == 200
```

### 6.2 前端測試

**位置**: `src/**/*.test.ts`

```typescript
import { describe, it, expect } from 'vitest';

describe('SkillsService', () => {
  it('should query skills', async () => {
    const result = await skillsService.query({});
    expect(result.items).toBeDefined();
  });
});
```

---

## 七、常見問題

### 7.1 Mock 模式切換

```bash
# 開發時使用 Mock
VITE_USE_MOCK=true npm run dev

# 測試真實 API
VITE_USE_MOCK=false npm run dev
```

### 7.2 資料庫連線失敗

```bash
# 檢查環境變數
echo $DATABASE_URL

# 測試連線
cd backend
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"
```

### 7.3 Skills 驗證失敗

```bash
# 執行驗證
node .claude/scripts/validate-all.cjs

# 重新生成索引
node .claude/scripts/generate-index.cjs
```

---

## 八、重構檢查清單

### 新增功能前

- [ ] 確認 SSOT 配置是否需要更新
- [ ] 設計 API 端點 (POST-Only)
- [ ] 規劃 Repository 結構
- [ ] 準備 Mock 資料

### 程式碼審查

- [ ] 遵循 Repository Pattern
- [ ] 使用 logging 而非 print
- [ ] API 使用 POST 方法
- [ ] 有對應的測試
- [ ] 無硬編碼路徑

### 提交前

- [ ] `npm run lint` 通過
- [ ] `npm run test:run` 通過
- [ ] `python -m pytest tests/` 通過
- [ ] Commit 訊息符合格式

---

**建立日期**: 2026-01-28
**最後更新**: 2026-01-28
