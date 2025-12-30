# 開發流程指南

## 🎯 新開發者上手指南

### 1. 環境設置檢查清單

#### 必需軟體
- [ ] Python 3.11+
- [ ] Node.js 18+
- [ ] Docker & Docker Compose
- [ ] Git

#### 專案啟動順序
1. **啟動資料庫**
   ```bash
   docker ps | grep postgres  # 檢查 CK_Missive_postgres 是否運行
   ```

2. **啟動後端** (Port 8001)
   ```bash
   cd backend
   python main.py
   # 檢查: curl http://localhost:8001/health
   ```

3. **啟動前端** (Port 3006)
   ```bash
   cd frontend
   npm run dev
   # 訪問: http://localhost:3006
   ```

### 2. 常見開發問題與解決方案

#### ❌ 問題: API返回404錯誤
**症狀**: `GET /api/documents-years 404 Not Found`
**原因**: API路徑錯誤
**解決**:
```javascript
// ❌ 錯誤寫法
fetch('/api/documents-years')

// ✅ 正確寫法  
fetch('/api/documents/documents-years')
```

#### ❌ 問題: 資料庫表格不存在
**症狀**: `relation "official_documents" does not exist`
**原因**: 模型表名與實際表名不匹配
**解決**:
```python
# ✅ 正確模型定義
class OfficialDocument(Base):
    __tablename__ = "documents"  # 對應實際表名
```

#### ❌ 問題: 欄位名稱錯誤
**症狀**: `name 'sender_agency' is not defined`
**原因**: 使用了錯誤的欄位名稱
**解決**:
```python
# ❌ 錯誤欄位名稱
sender_agency = Column(String(200))
receiver_agency = Column(String(200))

# ✅ 正確欄位名稱
sender = Column(String(200))
receiver = Column(String(200))
```

#### ❌ 問題: Enum錯誤
**症狀**: `'str' object has no attribute 'value'`
**原因**: 在字串欄位上調用.value方法
**解決**:
```python
# ❌ 錯誤處理
"doc_type": doc.doc_type.value

# ✅ 正確處理
"doc_type": str(doc.doc_type) if doc.doc_type else ""
```

## 🏗️ 開發架構規範

### API開發模式

#### 1. 路由註冊 (app/api/routes.py)
```python
# 中央路由註冊
api_router.include_router(
    documents.router, 
    prefix="/documents", 
    tags=["公文管理"]
)
```

#### 2. API端點開發 (app/api/endpoints/)
```python
@router.get("/documents-years")
async def get_document_years(db: AsyncSession = Depends(get_async_db)):
    """取得所有公文年度列表"""
    service = DocumentService(db)
    years = await service.get_available_years()
    return {"years": years}
```

#### 3. 服務層邏輯 (app/services/)
```python
class DocumentService:
    async def get_available_years(self) -> List[int]:
        query = select(func.distinct(extract('year', Document.doc_date)))
        result = await self.db.execute(query)
        return [int(row.year) for row in result.fetchall()]
```

### 前端開發模式

#### 1. API調用規範
```typescript
// ✅ 正確的API調用
const response = await fetch('http://localhost:8001/api/documents/documents-years');

// API路徑格式: /api/{prefix}/{endpoint}
```

#### 2. 狀態管理 (Zustand)
```typescript
// 使用統一的狀態管理
import { useDocumentStore } from '../stores/documentStore';
```

#### 3. 組件規範
```typescript
// 組件應該有明確的型別定義
interface DocumentFilterProps {
  filters: DocumentFilterType;
  onFiltersChange: (filters: DocumentFilterType) => void;
}
```

## 🧪 測試與驗證

### 後端測試
```bash
# API健康檢查
curl http://localhost:8001/health

# 特定端點測試
curl "http://localhost:8001/api/documents/?skip=0&limit=5"
curl "http://localhost:8001/api/documents/documents-years"

# 檢查API文檔
open http://localhost:8001/docs
```

### 資料庫驗證
```bash
# 檢查表格結構
docker exec CK_Missive_postgres psql -U ck_user -d ck_documents -c "\dt"

# 檢查資料
docker exec CK_Missive_postgres psql -U ck_user -d ck_documents -c "SELECT COUNT(*) FROM documents"
```

### 前端測試
```bash
# 檢查前端運行狀態
curl http://localhost:3006

# 檢查瀏覽器控制台錯誤
# 開發者工具 → Console → Network
```

## 📝 程式碼提交規範

### 提交前檢查清單
- [ ] 後端服務正常啟動 (Port 8001)
- [ ] 前端服務正常啟動 (Port 3006)
- [ ] API端點測試通過
- [ ] 無 TypeScript 錯誤
- [ ] 無 ESLint 警告
- [ ] 資料庫連接正常

### Git 提交訊息格式
```
feat: 新增公文年度列表API端點

- 添加 /api/documents/documents-years 端點
- 修復前端API調用路徑錯誤
- 更新文檔說明

Fixes: #123
```

### 分支策略
- `master`: 穩定版本
- `develop`: 開發版本
- `feature/*`: 功能開發
- `bugfix/*`: 錯誤修復

## 🔧 程式碼品質工具

### 後端
```bash
# Python 程式碼格式化
black backend/

# 型別檢查
mypy backend/app

# 依賴檢查
pip-audit
```

### 前端
```bash
# TypeScript 檢查
npm run type-check

# ESLint 檢查
npm run lint

# 程式碼格式化
npm run format
```

## 📚 參考資源

- **API文檔**: http://localhost:8001/docs
- **資料庫結構**: `docs/DATABASE_SCHEMA.md`
- **專案架構**: `STRUCTURE.md`
- **系統說明**: `README.md`

---

**記住**: 遇到問題時，先檢查這些文檔，大部分常見問題都有解決方案！