# CODEWIKI 程序規範

**技能名稱**：系統文件管理
**用途**：確保重要系統變更與議題有完整記錄
**適用場景**：功能開發、問題修復、架構變更

---

## 一、CODEWIKI 更新時機

### 1.1 必須記錄的情境

| 類別 | 情境 | 記錄位置 |
|------|------|----------|
| **重大修復** | P0/P1 問題修復 | CLAUDE.md、相關 skill |
| **架構變更** | API 路徑、資料庫結構變更 | CONTEXT.md |
| **配置變更** | 環境變數、端口配置變更 | config-management.md |
| **安全更新** | 安全弱點修復、依賴更新 | code-standards.md |
| **新功能** | 新增 API 端點、元件 | CONTEXT.md、相關 skill |

### 1.2 記錄格式

```markdown
## [日期] 變更標題

**類型**：修復 / 功能 / 架構 / 安全
**影響範圍**：前端 / 後端 / 資料庫 / 全系統

### 問題描述
- 簡述問題或需求

### 解決方案
- 具體的修改內容

### 預防措施
- 如何避免類似問題
```

---

## 二、文件維護規範

### 2.1 核心文件

| 文件 | 用途 | 更新頻率 |
|------|------|----------|
| `CLAUDE.md` | Claude Code 主要規範 | 每次重大變更 |
| `CONTEXT.md` | 專案背景與架構 | 架構變更時 |
| `.claude/skills/*.md` | 特定領域規範 | 發現新問題時 |

### 2.2 Skill 文件結構

```
.claude/skills/
├── code-standards.md          # 程式碼規範
├── config-management.md       # 配置管理
├── dangerous-operations-policy.md  # 危險操作
├── database-admin-procedures.md    # 資料庫管理
├── startup-requirements.md    # 啟動要求
└── codewiki-procedures.md     # 本文件
```

---

## 三、問題追蹤與分類

### 3.1 優先級定義

| 優先級 | 描述 | 回應時間 |
|--------|------|----------|
| **P0** | 系統無法運作、編譯失敗 | 立即處理 |
| **P1** | 功能受損、測試失敗 | 當天處理 |
| **P2** | 警告、潛在風險 | 本週處理 |
| **P3** | 技術債、優化建議 | 規劃處理 |

### 3.2 常見問題類型

#### TypeScript 相關
- Hook 順序問題（useCallback 必須在 useEffect 之前）
- 類型定義缺失
- 未使用變數警告

#### 後端相關
- 環境變數未設定
- 配置檔案語法錯誤
- 資料庫連線問題

#### 配置相關
- 端口衝突
- API 路徑重複
- CORS 配置問題

---

## 四、變更記錄範例

### 2026-01-01 P0-P3 系統修復

**類型**：修復
**影響範圍**：全系統

### 修復內容

1. **TypeScript Hook 順序** (P0)
   - 問題：`Block-scoped variable used before declaration`
   - 修復：調整 useCallback 定義順序
   - 檔案：`CreateFromTranscriptModal.tsx`, `StatisticsFilterPanel.tsx`

2. **後端測試配置** (P0)
   - 問題：`ValidationError: JWT_SECRET_KEY required`
   - 修復：在 conftest.py 加入環境變數設定
   - 檔案：`backend/tests/conftest.py`

3. **Flake8 配置語法** (P0)
   - 問題：`Error code '#' does not match pattern`
   - 修復：移除 extend-ignore 的行內註解
   - 檔案：`backend/.flake8`

4. **資料庫索引清理** (P3)
   - 問題：中英文命名重複索引
   - 修復：移除 4 個重複索引，節省 10MB
   - 檔案：新增遷移腳本

### 預防措施

- 更新 `code-standards.md` 加入相關規範
- 執行 `npm run typecheck` 驗證
- 執行 `python scripts/validate_config.py` 驗證

---

### 2026-01-01 API 路由整合 - 底圖管理

**類型**：架構
**影響範圍**：後端 API

### 問題描述

- 底圖管理存在兩個重複的 API 端點模組
- `basemap.py` (JSON 配置版本) 與 `basemap_db.py` (資料庫版本) 並存
- 前端使用 `/basemaps` 端點，但讀取的是測試用 JSON 配置檔
- 導致底圖列表只顯示 3 個測試項目，而非資料庫中的 23 個

### 解決方案

1. **合併 API 端點至 `basemap_db.py`**
   - 新增 `/basemaps` (前端相容端點)
   - 新增 `/basemap/layers/list` (前端相容端點)
   - 新增 `/basemap/categories/list` (前端相容端點)

2. **移除重複路由**
   - 從 `router_registry.py` 移除 `basemap_router` 註冊
   - 保留 `basemap_db_router` 作為唯一底圖 API

3. **相關檔案變更**
   - `backend/app/api/v1/endpoints/system/basemap_db.py` - 新增相容端點
   - `backend/app/api/router_registry.py` - 移除重複註冊

### 預防措施

- 新增 API 模組時，檢查是否有同功能的現有模組
- 遷移完成後立即移除或標記舊版本
- 定期清理 DEPRECATED 標記的程式碼

---

### 2026-01-01 底圖群組 API 整合

**類型**：架構
**影響範圍**：後端 API

### 問題描述

- 底圖群組存在兩個 API 來源：
  - `basemap_groups.py` (JSON 版本) - 返回數字 ID (1, 2, 3, 4)
  - `basemap_service.py` (資料庫版本) - 返回字串 ID (nlsc, osm, satellite)
- 底圖的 `group_id` 使用字串 ID，與 JSON 版本的群組 ID 不匹配
- 導致前端無法正確匹配底圖與群組，底圖影像無法顯示

### 解決方案

1. **移除 JSON 版本群組路由**
   - 從 `router_registry.py` 移除 `basemap_groups_router` 註冊
   - 保留 `basemap_db_router` 作為唯一來源

2. **新增前端相容群組端點至 `basemap_db.py`**
   - `/basemap-groups` (前端標準端點)
   - `/basemap/groups/list` (前端相容端點)

3. **驗證結果**
   - 群組 API 返回 5 筆資料：satellite, nlsc, emap, osm, opendata
   - 底圖 API 返回 23 筆資料，category 值為 nlsc, osm, satellite
   - 兩者 ID 格式一致 (皆為字串)

### 相關檔案變更
- `backend/app/api/v1/endpoints/system/basemap_db.py` - 新增群組相容端點
- `backend/app/api/router_registry.py` - 移除 basemap_groups_router

### 預防措施

- 新增 API 模組前，確認資料來源與 ID 格式一致
- 避免 JSON 配置與資料庫混用造成資料不一致

---

### 2026-01-01 GIS 底圖控制面板 API 回應解析修復

**類型**：修復
**影響範圍**：前端

### 問題描述

- GIS 平台底圖影像選擇面板顯示「沒有找到符合的底圖」
- `BasemapControlPanel.tsx` 的 API 回應解析邏輯與後端格式不符
- 後端使用 `success_response` 返回 `{ code: 200, data: { items: [...] } }`
- 前端預期 `{ success: true, data: [...] }` 或 `{ items: [...] }`

### 解決方案

1. **修復 `fetchGroups` 函數**
   ```typescript
   const groupData = response.data.data?.items  // 新格式: {code, data: {items}}
     || response.data.data                       // {success, data: [...]}
     || response.data.items                      // {items: [...]}
     || [];
   ```

2. **修復 `fetchBasemaps` 函數**
   - 同樣套用多格式相容解析邏輯

3. **相關檔案**
   - `frontend/src/modules/gis/components/BasemapControl/BasemapControlPanel.tsx`

### 預防措施

- 前端 API 回應解析應統一使用多格式相容模式
- 後端 API 回應格式應標準化文件說明
- 建議建立統一的 API 回應解析工具函數

---

### 2026-01-03 圖層管理模組化服務層

**類型**：架構
**影響範圍**：後端 / API

### 問題描述

- 圖層管理 (Basemap / GISLayer) 的業務邏輯散落在端點檔案中
- 資料庫欄位命名與 Schema 命名不一致
- Dynamic 圖層 import-from-source API 返回 501 錯誤
- `group_id` 類型混亂 (有時 int，有時 str)
- `opacity` 預設值不一致 (basemap 1.0，gislayer 0.8)

### 解決方案

1. **建立模組化服務層**
   ```
   backend/app/layer_management/
   ├── services/     # BasemapService, GisLayerService, LayerSourceService
   ├── repositories/ # 資料存取層 (欄位映射轉換)
   └── schemas/      # 統一 Pydantic 模型
   ```

2. **統一 Request 模型**
   - `ImportFromSourceRequest` 使用 `str` 類型 group_id
   - `opacity` 改為 Optional，依目標類型使用預設值
   - 新增 `LayerTargetType` Enum

3. **修正 Dynamic 圖層支援**
   - 新增 `find_dynamic_by_id()` 查詢方法
   - 更新 `find_source_by_id()` 支援 dynamic 類型

4. **端點整合服務層**
   - `gis/layers.py` 使用 GisLayerService
   - `system/basemap_db.py` 使用 ModularBasemapService

### 資料庫欄位映射

| 表 | 資料庫欄位 | Schema 欄位 |
|---|-----------|-------------|
| spatial_layers | layer_name | name |
| spatial_layers | is_visible | is_enabled |
| dynamic_layers | layer_code | name |
| dynamic_layers | api_endpoint | service_url |
| dynamic_layers | is_active | is_enabled |

### 相關檔案

- `backend/app/layer_management/` - 新模組
- `backend/app/api/v1/endpoints/gis/layers.py` - 整合服務層
- `backend/app/api/v1/endpoints/system/basemap_db.py` - 整合服務層
- `docs/specs/LAYER_MANAGEMENT_ARCHITECTURE.md` - 架構設計文件

### 預防措施

- 新增 API 端點使用 Service 層封裝
- Repository 層負責欄位映射轉換
- 遵循「原地重構」策略，避免 V2 API

---

### 2026-01-06 都市更新高亮標記功能

**類型**：功能
**影響範圍**：前端

### 問題描述

- 都市更新查詢結果點擊定位後，無法確認目標位置
- 開發區已有高亮標記與 Popup，需要統一實作

### 解決方案

1. **建立高亮標記組件**
   - `UrbanRenewalHighlightMarker.tsx` - 紫色主題 (#722ed1)
   - Pulse 動畫效果
   - 自動 flyTo + openPopup
   - 15 秒自動清除

2. **建立 Map Feature Hook**
   - `useUrbanRenewalMapFeature.ts` - 統一狀態管理
   - 回傳 memoized props (panelProps, layerProps, highlightMarkerProps)

3. **整合至地圖頁面**
   - `GisPlatformPage.tsx` - 加入高亮標記狀態與組件
   - `RealEstateMap.tsx` - 同步整合

4. **匯出 Hook**
   - `hooks/index.ts` - 匯出 Hook 與型別

### 相關檔案

- `frontend/src/components/Map/UrbanRenewalHighlightMarker.tsx` (新增)
- `frontend/src/hooks/useUrbanRenewalMapFeature.ts` (新增)
- `frontend/src/components/UrbanRenewal/UrbanRenewalInfoPanel.tsx` (修改)
- `frontend/src/pages/GisPlatformPage.tsx` (修改)
- `frontend/src/components/Map/RealEstateMap.tsx` (修改)
- `frontend/src/hooks/index.ts` (修改)

### Commit

`8206aa887 feat(urban-renewal): 實作都市更新查詢結果高亮標記與 Popup 功能`

---

### 2026-01-06 清除圖徵按鈕修復

**類型**：修復
**影響範圍**：前端

### 問題描述

- 地圖導覽列「清除圖徵」按鈕失效
- 點擊後未完整清除所有套疊圖層

### 解決方案

更新 `handleClearAllFeatures` 函數，加入遺漏的清除項目：

1. 都市更新圖層與高亮標記
2. 開發區圖層與高亮標記
3. 查估案件圖層
4. 不動產交易圖層

### 預防措施

- 新增圖層功能時，必須同步更新 `handleClearAllFeatures`
- 更新 `.claude/skills/code-standards.md` 加入「清除圖徵完整性規範」

### 相關檔案

- `frontend/src/pages/GisPlatformPage.tsx` (修改)

### Commit

`f05783277 fix(map-nav): 修復「清除圖徵」按鈕未完整清除所有套疊圖層`

---

### 2026-01-06 KML 匯出功能

**類型**：功能
**影響範圍**：前端 / 後端

### 問題描述

- 開發區、都市更新、控制點需要匯出至 Google Earth / QGIS
- 中文檔名在部分瀏覽器會亂碼

### 解決方案

1. **後端 API**
   - 新增 `GeoJSONToKMLExporter` 服務
   - 開發區 `/api/v1/data/development-zones/export/kml`
   - 都市更新 `/api/v1/data/urban-renewal/export/kml`
   - 控制點 `/api/v1/spatial/control-points/export/kml`

2. **中文檔名編碼**
   - 使用 RFC 5987: `filename*=UTF-8''<encoded>`

3. **前端組件**
   - 新增統一 `KmlExportButton` 組件
   - 整合至各資訊面板

### Commit

`feat(export): 實作 KML 匯出功能 - 開發區、都市更新、控制點`

---

## 五、驗證清單

### 變更前
- [ ] 確認變更類型與影響範圍
- [ ] 備份相關資料（資料庫、配置）
- [ ] 確認測試環境正常

### 變更後
- [ ] 執行相關測試
- [ ] 更新相關文件
- [ ] 記錄變更內容

---

**建立日期**：2026-01-01
**最後更新**：2026-01-06
