# CK_Missive 強制性開發規範檢查清單

> **版本**: 1.0.0
> **建立日期**: 2026-01-11
> **狀態**: 強制執行 - 所有開發任務啟動前必須檢視

---

## 重要聲明

**本檢查清單為強制性文件。任何開發任務開始前，必須先完成相關規範檢視。**

違反規範可能導致：
- 程式碼審查不通過
- 前後端資料不同步
- 系統運行異常
- 維護成本增加

---

## 一、開發任務類型判斷

根據任務類型，選擇對應的檢查清單：

| 任務類型 | 必讀規範 | 對應檢查清單 |
|---------|---------|-------------|
| **新增前端路由/頁面** | 路由同步規範 | [清單 A](#清單-a前端路由頁面開發) |
| **新增後端 API** | API 開發規範 | [清單 B](#清單-b後端-api-開發) |
| **新增導覽項目** | 路由同步規範 | [清單 C](#清單-c導覽項目變更) |
| **修改認證/權限** | 前端架構規範 | [清單 D](#清單-d認證權限變更) |
| **資料匯入功能** | 服務層規範 | [清單 E](#清單-e資料匯入功能) |
| **資料庫變更** | 資料庫規範 | [清單 F](#清單-f資料庫變更) |
| **Bug 修復** | 通用規範 | [清單 G](#清單-g-bug-修復) |

---

## 清單 A：前端路由/頁面開發

### 必讀文件
- [ ] `docs/DEVELOPMENT_STANDARDS.md` 第九節（前端開發規範）
- [ ] `.claude/skills/frontend-architecture.md`
- [ ] `frontend/src/router/types.ts`（現有路由定義）

### 開發前檢查
- [ ] 確認路由路徑在 `ROUTES` 常數中定義
- [ ] 確認使用 `VITE_API_BASE_URL` 從 `config/env.ts` 取得
- [ ] 確認認證檢測使用 `isAuthDisabled()` 函數

### 開發後檢查
- [ ] TypeScript 編譯通過：`cd frontend && npx tsc --noEmit`
- [ ] 同步更新 `backend/app/scripts/init_navigation_data.py`
- [ ] 執行路由一致性檢查（見清單 C）

---

## 清單 B：後端 API 開發

### 必讀文件
- [ ] `docs/DEVELOPMENT_STANDARDS.md` 第二至四節
- [ ] `docs/specifications/API_ENDPOINT_CONSISTENCY.md`
- [ ] `.claude/skills/api-development.md`

### 開發前檢查
- [ ] 確認使用 `ServiceResponse` 回應結構
- [ ] 確認使用 POST 方法進行資料修改操作
- [ ] 確認輸入使用 Pydantic Schema 驗證

### 開發後檢查
- [ ] Python 語法檢查通過
- [ ] 同步更新前端 `API_ENDPOINTS` 定義
- [ ] API 端點文件更新（若需要）

---

## 清單 C：導覽項目變更

### 必讀文件
- [ ] `.claude/commands/route-sync-check.md`
- [ ] `.claude/skills/frontend-architecture.md`（六、導覽系統架構）
- [ ] `backend/app/scripts/init_navigation_data.py`
- [ ] `frontend/src/router/types.ts`

### ⚠️ 重要架構須知

**主佈局元件是 `Layout.tsx`，非 `DynamicLayout.tsx`**

```
AppRouter.tsx → Layout.tsx → 側邊導覽列
                    ↓
             secureApiService.getNavigationItems()
                    ↓
             convertToMenuItems() → Ant Design Menu
```

**導覽更新事件機制：**
- `SiteManagementPage` 觸發：`window.dispatchEvent(new CustomEvent('navigation-updated'))`
- `Layout.tsx` 監聽：`window.addEventListener('navigation-updated', handler)`

### 同步檢查項目

**新增導覽項目時，必須同步更新四處：**

| 序號 | 位置 | 檔案 | 說明 |
|------|------|------|------|
| 1 | 前端路由定義 | `frontend/src/router/types.ts` | ROUTES 常數 |
| 2 | 前端路由實作 | `frontend/src/router/AppRouter.tsx` | Route 元素 |
| 3 | 後端路徑白名單 | `backend/app/core/navigation_validator.py` | VALID_NAVIGATION_PATHS |
| 4 | 後端導覽定義 | `backend/app/scripts/init_navigation_data.py` | DEFAULT_NAVIGATION_ITEMS |

### 路徑一致性規則
- 前端 ROUTES 定義的路徑 **必須** 與後端導覽的 `path` 完全一致
- 後端路徑白名單會在 API 層面驗證路徑合法性
- 圖標名稱使用 Ant Design 格式：`XxxOutlined`

### 自動化驗證機制 (2026-01-12 新增)

| 機制 | 說明 |
|------|------|
| 後端 API 驗證 | `navigation/action` 的 create/update 會驗證路徑 |
| 前端下拉選單 | SiteManagementPage 路徑欄位使用下拉選單 |
| 初始化腳本 | `--force-update` 參數可強制同步路徑 |
| PowerShell 腳本 | `.claude/hooks/route-sync-check.ps1` |

### 開發後驗證
```bash
# 執行路徑同步檢查
/route-sync-check

# 或使用 PowerShell 腳本
.\.claude\hooks\route-sync-check.ps1

# 強制同步資料庫導覽路徑
cd backend && python app/scripts/init_navigation_data.py --force-update
```

---

## 清單 D：認證/權限變更

### 必讀文件
- [ ] `.claude/skills/frontend-architecture.md`
- [ ] `frontend/src/config/env.ts`
- [ ] `frontend/src/hooks/useAuthGuard.ts`
- [ ] `frontend/src/hooks/usePermissions.ts`

### 強制規範

**認證相關函數唯一來源：**
```typescript
// 正確 - 從 config/env.ts 匯入
import { isAuthDisabled, isInternalIP, detectEnvironment } from '../config/env';

// 禁止 - 重複定義或直接讀取環境變數
const isInternal = window.location.hostname.startsWith('192.168.');  // ❌
```

**環境類型判斷：**
| 類型 | 條件 | 認證行為 |
|------|------|---------|
| localhost (DEV) | localhost + DEV=true | 免認證，自動 admin |
| internal | 內網 IP | 免認證，自動 admin |
| localhost (PROD) | localhost + DEV=false | Google OAuth |
| public | 其他 | Google OAuth |

### 開發後檢查
- [ ] 不得新增 `isInternalIP` 或類似函數的重複實作
- [ ] `ProtectedRoute` 正確處理 `authDisabled` 狀態
- [ ] 側邊欄正確顯示對應權限的選項

---

## 清單 E：資料匯入功能

### 必讀文件
- [ ] `docs/DEVELOPMENT_STANDARDS.md` 第七節
- [ ] `.claude/DEVELOPMENT_GUIDELINES.md`（交易安全檢查）
- [ ] `backend/app/services/base/import_base.py`

### 強制規範

**必須繼承 ImportBaseService：**
```python
from app.services.base.import_base import ImportBaseService

class NewImportService(ImportBaseService):
    async def import_from_file(self, ...): ...
    async def process_row(self, ...): ...
```

**必須使用共用驗證器：**
- `DocumentValidators.validate_doc_type()` - 公文類型驗證
- `StringCleaners.clean_string()` - 字串清理
- `DateParsers.parse_date()` - 日期解析

### 開發後檢查
- [ ] 使用 `ServiceResponse` 回應結構
- [ ] 匯入前呼叫 `reset_serial_counters()`
- [ ] 使用智慧匹配：`match_agency()`, `match_project()`

---

## 清單 F：資料庫變更

### 必讀文件
- [ ] `docs/DATABASE_SCHEMA.md`
- [ ] `.claude/skills/database-schema.md`
- [ ] `backend/app/extended/models.py`

### 強制規範

**欄位命名一致性：**
- 模型欄位名稱 = 資料庫欄位名稱
- 初始化腳本欄位名稱 **必須** 與模型一致

**範例錯誤：**
```python
# 模型定義
class SiteConfiguration(Base):
    key = Column(String(100))  # 欄位名稱是 'key'

# 錯誤的初始化腳本
DEFAULT_CONFIGS = [
    {"config_key": "site_title", ...}  # ❌ 應該用 'key'
]
```

### 開發後檢查
- [ ] 確認模型欄位與初始化腳本一致
- [ ] 必要時建立資料庫遷移
- [ ] 更新 Schema 定義

---

## 清單 G：Bug 修復

### 必讀文件
- [ ] `docs/ERROR_HANDLING_GUIDE.md`
- [ ] `.claude/DEVELOPMENT_GUIDELINES.md`

### 開發前檢查
- [ ] 確認問題根因，不只是修復表面症狀
- [ ] 檢查是否為架構性問題（需要通盤考量）
- [ ] 檢查是否有其他地方存在相同問題

### 開發後檢查
- [ ] TypeScript 編譯通過（前端變更）
- [ ] Python 語法檢查通過（後端變更）
- [ ] 相關測試通過
- [ ] 不引入新的技術債

---

## 二、通用開發後檢查清單

**所有開發任務完成後，必須執行：**

### 程式碼檢查
```bash
# 前端 TypeScript 編譯
cd frontend && npx tsc --noEmit

# 後端語法檢查
cd backend && python -m py_compile app/main.py
```

### 一致性檢查
- [ ] 前後端型別定義一致
- [ ] API 端點路徑一致
- [ ] 導覽路由一致

### 文件更新
- [ ] 必要時更新規範文件
- [ ] 必要時更新 CHANGELOG

---

## 三、違規處理流程

### 發現違規時
1. 停止當前開發工作
2. 閱讀相關規範文件
3. 修正違規項目
4. 重新執行檢查清單
5. 確認通過後繼續

### 常見違規類型

| 違規類型 | 說明 | 修正方式 |
|---------|------|---------|
| 路由不同步 | 前端路由與後端導覽不一致 | 執行清單 C |
| 認證重複實作 | 在多處定義 isInternalIP | 統一使用 config/env.ts |
| 欄位名稱錯誤 | 初始化腳本欄位名與模型不符 | 對照模型修正腳本 |
| 缺少驗證 | 未使用共用驗證器 | 改用 DocumentValidators |

---

## 四、快速參考

### 關鍵檔案位置

| 用途 | 檔案路徑 |
|------|---------|
| 前端路由定義 | `frontend/src/router/types.ts` |
| 前端路由實作 | `frontend/src/router/AppRouter.tsx` |
| 後端導覽定義 | `backend/app/scripts/init_navigation_data.py` |
| 後端路徑白名單 | `backend/app/core/navigation_validator.py` |
| 認證配置 | `frontend/src/config/env.ts` |
| 服務基類 | `backend/app/services/base/` |
| 驗證器 | `backend/app/services/base/validators.py` |
| 開發規範 | `docs/DEVELOPMENT_STANDARDS.md` |

### 常用指令

```bash
# 路由一致性檢查
/route-sync-check

# API 端點檢查
/api-check

# 型別同步檢查
/type-sync

# 開發環境檢查
/dev-check
```

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.2.0 | 2026-01-12 | 新增導覽路徑自動化驗證機制（白名單、下拉選單、強制同步） |
| 1.1.0 | 2026-01-12 | 新增導覽系統架構說明（Layout.tsx vs DynamicLayout.tsx） |
| 1.0.0 | 2026-01-11 | 初版建立 |

---

*本文件為強制性規範，所有開發人員必須遵守*
