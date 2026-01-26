# AI Assistant Agent

> **用途**: AI 對話系統、意圖識別與 MindsDB 預測整合
> **觸發**: `/ai-chat`, `/ai-assistant`
> **版本**: 1.0.0
> **分類**: backend
> **更新日期**: 2026-01-22

負責 AI 對話系統、意圖識別與 MindsDB 預測整合的智能代理。

## 專業領域

- 自然語言意圖識別
- MindsDB 預測模型整合
- 對話上下文管理
- AI 回應視覺化

## AI 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI 助理系統                           │
├─────────────────────────────────────────────────────────┤
│  混合 AI 連接器        意圖識別            對話記憶       │
│  - Groq (主要)        - 規則匹配          - Redis        │
│  - OpenAI (備援)      - 向量相似度        - 位置歷史     │
│  - Claude            - LLM 分類          - 查詢歷史     │
│  - Ollama (本地)                                        │
├─────────────────────────────────────────────────────────┤
│              複合意圖分解與執行管線                       │
│  定位執行器 → 土地執行器 → 規劃執行器 → GIS執行器        │
└─────────────────────────────────────────────────────────┘
```

## 支援的意圖類型 (17+6 種)

### 基礎意圖
| 意圖 | 範例查詢 |
|------|----------|
| location_query | "台北市信義區在哪裡" |
| address_query | "信義路三段100號" |
| land_query | "這塊地的資訊" |
| zoning_query | "這裡是什麼分區" |
| price_query | "附近房價多少" |
| transaction_query | "最近交易紀錄" |
| urban_renewal_query | "有沒有都更案" |
| development_zone_query | "開發區資訊" |

### 新增意圖 (整合中)
| 意圖 | 說明 | 需要 MindsDB |
|------|------|:------------:|
| price_forecast | 房價預測 | ✅ |
| investment_analysis | 投資分析 | ✅ |
| heatmap_request | 熱力圖請求 | ❌ |
| trend_chart_request | 趨勢圖請求 | ❌ |
| comparison_chart_request | 比較圖請求 | ❌ |
| layer_toggle | 圖層切換 | ❌ |

## MindsDB 整合

### 預測模型
```sql
-- 房價預測
SELECT price_trend, confidence
FROM house_price_predictor
WHERE city='台北市' AND district='大安區'
  AND prediction_date='2027-01';

-- 成交量預測
SELECT volume_forecast
FROM transaction_volume_predictor
WHERE region='新北市' AND quarter='2027Q1';
```

### 服務配置
```yaml
mindsdb:
  host: mindsdb
  http_port: 47334
  mysql_port: 47335
  models_db: landvaluation_ml
```

## 意圖識別流程

```
Layer 1: 快速規則匹配 (< 5ms)
    ↓ (信心度 < 0.8)
Layer 2: 向量語意匹配 (< 50ms)
    ↓ (信心度 < 0.7 或衝突)
Layer 3: LLM 深度分析 (< 500ms)
```

### 向量嵌入配置
```yaml
embedding:
  model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  dimension: 384
  index: pgvector (ivfflat)
```

## 執行器實作模式

```python
class PredictionQueryExecutor(BaseExecutor):
    """預測查詢執行器"""

    async def execute(self, context: PipelineContext, params: dict):
        prediction_type = params.get("prediction_type")
        location = context.get_location()

        # 呼叫 MindsDB 服務
        result = await self.mindsdb_service.predict(
            model=prediction_type,
            location=location,
            time_range=params.get("time_range")
        )

        return ExecutorResult(
            success=True,
            data=result.to_dict(),
            visualization={"type": "forecast_chart"},
            natural_language_response=self._generate_response(result)
        )
```

## 視覺化整合

### 意圖到圖表映射
| 意圖 | 主要視覺化 | 次要視覺化 |
|------|------------|------------|
| price_query | stat_card | sparkline |
| trend_analysis | line_chart | area_chart |
| comparison_query | bar_chart | map_markers |
| heatmap_request | heatmap | stats_panel |
| price_forecast | forecast_chart | confidence_band |

### 前端組件
```typescript
// AIResponseVisualizer
<AIResponseVisualizer
  response={aiResponse}
  onVisualizationReady={handleVisualization}
/>
```

## 回饋學習機制

```python
# 記錄使用者回饋
await intent_learning_service.record_feedback(
    session_id=session_id,
    detected_intent=detected,
    correct_intent=actual,
    user_message=message,
    feedback_score=score  # 1-5
)

# 累積 100 筆後自動觸發模式更新
```

## 相關文件

- `.claude/skills/ai-architecture-patterns.md`
- `docs/specs/AI_GIS_INTEGRATION_ROADMAP.md`
- `backend/app/services/ai/` 目錄
