# 服務依賴矩陣

> **目的**：記錄各前端功能模組對後端服務、資料庫表格、外部 API 的依賴關係
> **建立日期**：2026-01-19
> **維護要求**：新增功能時同步更新此矩陣

---

## 一、快速定位面板服務依賴

| 功能模組 | 後端端點 | 依賴資料表 | 外部服務 | 健康檢查 |
|----------|----------|------------|----------|----------|
| **座標定位** | - | - | - | N/A (純前端) |
| **地標定位** | `/spatial/facility-categories/*` | `emap_landmarks`, `emap_categories` | - | `/facility-categories/status` |
| **門牌地址定位** | `/spatial/tgos/geocode` | - | TGOS API | `/spatial/tgos/status` |
| **行政區定位** | `/spatial/admin-districts/*` | `admin_district_centers` | - | 村里 API 測試 |
| **土地地段定位** | `/spatial/land-sections/*` | `nlsc_cadastral_bounds`* | MOI WMTS | `/spatial/land-sections/status` |
| **控制點定位** | `/spatial/control-points/*` | `nlsc_control_points` | - | `/spatial/control-points/status` |
| **門牌查建號** | `/spatial/moi/building/*` | - | MOI API_036 | `/spatial/moi/building/status` |
| **公有土地查詢** | `/spatial/land-info/public-land/*` | - | MOI API_039 | `/spatial/land-info/status` |
| **地價查詢** | `/spatial/land-info/land-price/*` | - | MOI LandQueryPrice | `/spatial/land-info/status` |
| **建築執照查詢** | `/spatial/building-license/*` | - | TYCG OpenData | `/spatial/building-license/health` |

> *標註：`nlsc_cadastral_bounds` 表目前不存在，需建立

---

## 二、資料庫表格依賴詳情

### 2.1 行政區定位 (`admin_district_centers`)

| 欄位 | 類型 | 必要性 | 說明 |
|------|------|--------|------|
| `level` | varchar | 必要 | 'city', 'district', 'village' |
| `city_name` | varchar | 必要 | 縣市名稱 |
| `district_name` | varchar | 條件 | 鄉鎮市區名稱 |
| `village_name` | varchar | 條件 | 村里名稱 |
| `center_lat` | float | **必要** | 中心緯度 (不可 NULL) |
| `center_lng` | float | **必要** | 中心經度 (不可 NULL) |
| `zoom_level` | int | 建議 | 建議縮放等級 |

**資料來源與同步**：

> ⚠️ **重要**：此表資料需從圖層表同步，不會自動填充

| 圖層來源表 | 級別 | 同步狀態 | 筆數 |
|------------|------|----------|------|
| `layer_COUNTY_MOI` | city | ✅ 已同步 | 22 |
| `layer_TOWN_MOI` | district | ✅ 已同步 | 491 |
| `layer_VILLAGE_MOI` | village | ✅ 已同步 | 7956 |

**同步 SQL** (從村里圖層同步)：
```sql
INSERT INTO admin_district_centers (level, city_name, district_name, village_name, center_lat, center_lng, zoom_level)
SELECT
    'village' as level,
    "COUNTYNAME" as city_name,
    "TOWNNAME" as district_name,
    "VILLNAME" as village_name,
    ST_Y(ST_Centroid(geometry)) as center_lat,
    ST_X(ST_Centroid(geometry)) as center_lng,
    16 as zoom_level
FROM "layer_VILLAGE_MOI"
WHERE geometry IS NOT NULL
ON CONFLICT DO NOTHING;
```

**健康檢查 SQL**：
```sql
SELECT
  level,
  COUNT(*) as total,
  SUM(CASE WHEN center_lat IS NULL OR center_lng IS NULL THEN 1 ELSE 0 END) as null_coords
FROM admin_district_centers
GROUP BY level;
```

### 2.2 地籍圖服務 (`nlsc_cadastral_bounds`) - **需建立**

| 欄位 | 類型 | 必要性 | 說明 |
|------|------|--------|------|
| `lot_code` | varchar | 必要 | 地段代碼 |
| `map_name` | varchar | 必要 | 圖幅名稱 |
| `center_lat` | float | **必要** | 中心緯度 |
| `center_lng` | float | **必要** | 中心經度 |
| `wms_url` | varchar | 建議 | WMS 服務網址 |
| `west_bound` | float | 建議 | 西界 |
| `east_bound` | float | 建議 | 東界 |
| `south_bound` | float | 建議 | 南界 |
| `north_bound` | float | 建議 | 北界 |

**建表 SQL**：
```sql
CREATE TABLE IF NOT EXISTS nlsc_cadastral_bounds (
  id SERIAL PRIMARY KEY,
  lot_code VARCHAR(20) NOT NULL UNIQUE,
  map_name VARCHAR(100),
  coordinate_system VARCHAR(20),
  map_scale INTEGER,
  center_lat FLOAT,
  center_lng FLOAT,
  west_bound FLOAT,
  east_bound FLOAT,
  south_bound FLOAT,
  north_bound FLOAT,
  wms_url VARCHAR(500),
  zoom_level INTEGER DEFAULT 17,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_nlsc_cadastral_lot_code ON nlsc_cadastral_bounds(lot_code);
CREATE INDEX idx_nlsc_cadastral_center ON nlsc_cadastral_bounds(center_lat, center_lng);
```

### 2.3 地段代碼 (`lvr_section_codes`)

| 欄位 | 類型 | 必要性 | 說明 |
|------|------|--------|------|
| `section_code` | varchar | 必要 | 地段代碼 |
| `section_name` | varchar | 必要 | 地段名稱 |
| `city_code` | char(1) | 必要 | 縣市代碼 |
| `district_code` | char(2) | 必要 | 鄉鎮區代碼 |
| `office_code` | char(2) | 必要 | 事務所代碼 |

---

## 三、外部服務依賴詳情

### 3.1 TGOS 門牌定位服務

| 項目 | 內容 |
|------|------|
| **服務名稱** | TGOS 全國門牌位置比對服務 |
| **端點** | `https://api.tgos.tw/TGOS_MAP_API/TGLocator` |
| **認證方式** | API Key |
| **環境變數** | `TGOS_API_KEY` |
| **超時設定** | 10 秒 |
| **失敗處理** | 顯示「TGOS 服務尚未設定」警告 |

### 3.2 MOI 內政部地籍服務

| 項目 | 內容 |
|------|------|
| **服務名稱** | 內政部地政司 OpenData API |
| **認證方式** | API Key |
| **環境變數** | `MOI_API_KEY` |
| **熔斷機制** | 是 (連續失敗 5 次觸發) |
| **API 清單** | |
| - MOI_API_036 | 建物標示部查詢 |
| - MOI_API_039 | 公有土地 OData |
| - LandQueryPrice | 地價查詢 |

### 3.3 TYCG 桃園市開放資料

| 項目 | 內容 |
|------|------|
| **服務名稱** | 桃園市政府建管處開放資料 |
| **端點** | `https://opendata.tycg.gov.tw/api/` |
| **認證方式** | 無 |
| **資料格式** | JSON |
| **注意事項** | 回傳陣列可能包含 null 項目 |

---

## 四、健康檢查端點規範

### 4.1 標準回應格式
```json
{
  "success": true,
  "data": {
    "is_available": true,
    "data_source": "NLSC|MOI_CACHE|EXTERNAL",
    "total_records": 12345,
    "last_updated": "2026-01-19T00:00:00Z"
  },
  "message": "服務正常"
}
```

### 4.2 不可用回應格式
```json
{
  "success": true,
  "data": {
    "is_available": false,
    "error_code": "TABLE_NOT_FOUND|EXTERNAL_SERVICE_DOWN|NO_DATA",
    "error_message": "nlsc_cadastral_bounds 表不存在"
  },
  "message": "服務不可用"
}
```

### 4.3 前端處理邏輯
```typescript
// 檢查服務狀態
useEffect(() => {
  const checkService = async () => {
    try {
      const response = await apiClient.get('/service/status');
      const data = parseApiResponse(response.data);
      setServiceAvailable(data?.is_available ?? false);
    } catch {
      setServiceAvailable(false);
    }
  };
  checkService();
}, []);

// 條件渲染警告
{serviceAvailable === false && (
  <Alert
    message="服務暫時無法連線"
    type="warning"
    showIcon
  />
)}
```

---

## 五、依賴缺失處理策略

### 5.1 資料表不存在
1. 服務狀態端點返回 `is_available: false`
2. 前端顯示警告訊息
3. 相關功能禁用或使用備援方案

### 5.2 外部服務不可用
1. 啟動熔斷機制
2. 使用本地快取（如有）
3. 返回友善錯誤訊息

### 5.3 NULL 值處理
```python
# 後端：防禦性程式設計
items = data.get("items") or []  # 使用 or 而非 default
for item in items:
    if item is None:
        continue
    # 處理 item
```

---

## 五-B、服務層對應關係 (2026-01-19 更新)

### 已遷移的核心服務

| 端點檔案 | 服務類別 | 方法數 | 狀態 |
|---------|---------|--------|------|
| `real_estate/coordinate_validation.py` | `CoordinateValidationService` | 7 | ✅ P3-042 |
| `real_estate/land_transcripts.py` | `LandTranscriptService` | 20+ | ✅ P3-041 |
| `spatial/land_sections.py` | `LandSectionService` | 15+ | ✅ P3-001-B |
| `spatial/admin_districts.py` | `AdminDistrictService` | 8 | ✅ P3-019 |
| `system/database_info.py` | `DatabaseInfoService` | 10+ | ✅ P3-020 |
| `compensation/cases.py` | `CompensationCaseService` | 15+ | ✅ P3-001 |
| `spatial/analysis.py` | `SpatialAnalysisService` | 12 | ✅ P3-036 |
| `spatial/path_analysis.py` | `PathAnalysisService` | 10 | ✅ P3-038 |

### 新建服務詳情

#### CoordinateValidationService
```python
# backend/app/services/coordinate_validation_service.py
class CoordinateValidationService:
    def get_transactions_missing_coordinates(city, limit) -> Tuple[List, int]
    def get_transactions_with_coordinates(city, limit, exclude_cadastral) -> List
    def get_transactions_without_coordinates(city, limit) -> List
    def update_coordinate(transaction_id, latitude, longitude, source) -> int
    def diagnose_anomalous_coordinates(city, min_district_count, limit) -> Tuple
    def get_anomaly_stats_by_city(city, min_district_count) -> Tuple
    def clear_anomalous_coordinates(city, min_district_count) -> int
    def commit() / rollback()
```

#### LandTranscriptService (擴充)
```python
# backend/app/services/land_transcript_service.py - 新增方法
def get_transcript_id_by_serial_number(plot_serial_number) -> Optional[int]
def get_transcripts_for_batch(city, limit) -> List[Dict]
def get_ownership_count_by_transcript_id(transcript_id) -> int
def get_ownership_count_by_serial_number(plot_serial_number) -> int
def update_transcript_calculated_fields(transcript_id, fields) -> int
def update_transcript_field(transcript_id, field, value) -> int
def get_transcripts_for_export(city, limit) -> List[Dict]
def upsert_transcript(transcript_data) -> int
def delete_ownership_by_transcript_id(transcript_id) -> int
def insert_ownership(ownership_data) -> int
```

### 服務遷移進度統計

| 指標 | 數值 |
|------|------|
| 總端點檔案數 | 101 |
| 服務層檔案數 | 172 |
| 架構警告數 | 0 ✅ |
| ESLint 錯誤數 | 0 ✅ |

> **註**：服務層遷移已於 P3-001-B 完成，架構驗證全部通過。

---

## 六、維護指南

### 新增功能時
1. 更新本文件的依賴矩陣（第一節）
2. 若有新資料表，新增至第二節
3. 若有新外部服務，新增至第三節
4. 實作對應的健康檢查端點

### 定期檢查
- [ ] 每月執行一次完整健康檢查
- [ ] 確認所有外部服務 API Key 有效
- [ ] 檢查資料表記錄數是否正常

### 問題排查流程
```
功能異常
  │
  ├─ 檢查健康檢查端點
  │   ├─ is_available: false → 查看 error_code
  │   └─ 端點無回應 → 檢查後端服務
  │
  ├─ 檢查資料表
  │   ├─ 表不存在 → 執行建表 SQL
  │   └─ 欄位 NULL → 執行資料補全
  │
  └─ 檢查外部服務
      ├─ API Key 過期 → 更新環境變數
      └─ 服務端異常 → 啟用備援或等待恢復
```

---

**最後更新**：2026-01-19
