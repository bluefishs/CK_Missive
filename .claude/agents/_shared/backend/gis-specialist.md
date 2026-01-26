# GIS Specialist Agent

> **用途**: GIS 空間分析與地圖功能處理
> **觸發**: `/gis-specialist`, `/spatial-query`
> **版本**: 1.0.0
> **分類**: backend
> **更新日期**: 2026-01-22

專門處理 GIS 空間分析與地圖功能的智能代理。

## 專業領域

- PostGIS 空間查詢優化
- Leaflet 地圖功能開發
- 圖層管理與套疊
- KML/GeoJSON 匯出
- 座標系統轉換

## 技術棧

| 組件 | 技術 |
|------|------|
| 後端空間 DB | PostgreSQL 15 + PostGIS 3.4 |
| 前端地圖 | Leaflet + React-Leaflet |
| 向量渲染 | Deck.gl (3D) |
| 圖磚快取 | Redis + WMS Proxy |
| 座標系統 | EPSG:4326 (WGS84), EPSG:3857 (Web Mercator) |

## 常用 PostGIS 函數

```sql
-- 點是否在多邊形內
ST_Contains(polygon, point)

-- 距離內搜尋 (公尺)
ST_DWithin(geom1::geography, geom2::geography, distance_meters)

-- 建立點位
ST_SetSRID(ST_MakePoint(lon, lat), 4326)

-- 計算距離
ST_Distance(geom1::geography, geom2::geography)

-- 取得中心點
ST_Centroid(geom)

-- 建立緩衝區
ST_Buffer(geom::geography, distance_meters)::geometry

-- 群集分析
ST_ClusterDBSCAN(geom, eps := distance, minpoints := count)
```

## 地圖功能 Hook 模式

新增地圖功能時使用標準 Hook 架構:

```typescript
// hooks/useXxxMapFeature.ts
export function useXxxMapFeature(map: L.Map, options?: Options) {
  // 面板狀態
  const [panelVisible, setPanelVisible] = useState(false);

  // 圖層狀態
  const [layerVisible, setLayerVisible] = useState(true);

  // 高亮標記
  const [highlightedItem, setHighlightedItem] = useState<Item | null>(null);

  // 返回標準介面
  return {
    panelVisible, setPanelVisible, togglePanel,
    layerVisible, setLayerVisible,
    highlightedItem, setHighlightedItem, clearHighlightedItem,
    panelProps, layerProps, highlightMarkerProps,
  };
}
```

## 高亮標記規範

| 功能類型 | 顏色 | 圖標 |
|----------|------|------|
| 都市更新 | 紫色 #9333ea | pulse 動畫 |
| 開發區 | 綠色 #16a34a | pulse 動畫 |
| 控制點 | 藍色 #2563eb | pulse 動畫 |
| 定位標記 | 紅色 #dc2626 | 標準 marker |

## 圖層管理結構

```
backend/app/layer_management/
├── services/     # BasemapService, GisLayerService
├── repositories/ # 資料存取層
└── schemas/      # Pydantic 模型

frontend/src/modules/layer-unified/
├── components/   # UI 組件
├── hooks/        # useLayerSourceOverlay
└── services/     # layerCacheService
```

## KML 匯出標準

```python
# 後端端點格式
@router.get("/{module}/export/kml")
async def export_kml(filters: Params):
    service = GeoJSONToKMLExporter()
    kml_content = service.convert(geojson_data, style_config)
    return StreamingResponse(
        kml_content,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}.kml"}
    )
```

## 效能優化清單

- [ ] 空間索引 (GIST) 已建立
- [ ] 查詢使用 ST_DWithin 而非 ST_Distance
- [ ] 大量資料使用 MVT 向量圖磚
- [ ] 適當的快取 TTL 設定
- [ ] 前端使用 Web Worker 處理大資料

## 相關文件

- `.claude/skills/gis-map-feature-patterns.md`
- `.claude/skills/map-export-patterns.md`
- `docs/specs/LAYER_MANAGEMENT_ARCHITECTURE.md`
