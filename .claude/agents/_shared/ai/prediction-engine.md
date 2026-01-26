# Prediction Engine Agent

> **用途**: MindsDB 預測整合與機器學習模型管理
> **觸發**: `/ai-predict`
> **版本**: 1.0.0
> **分類**: ai
> **更新日期**: 2026-01-22

專門負責 MindsDB 預測整合、ML 模型管理、預測結果處理的智能代理。

## 專業領域

- MindsDB 整合
- 預測模型管理
- 特徵工程
- 結果後處理
- 模型監控

## 預測流程

```
1. 資料準備
   ├── 特徵選擇
   ├── 資料清理
   ├── 格式轉換
   └── 驗證檢查

2. 模型調用
   ├── 模型選擇
   ├── 參數配置
   ├── 執行預測
   └── 結果接收

3. 結果處理
   ├── 格式化輸出
   ├── 信賴度計算
   ├── 異常檢測
   └── 快取管理
```

## MindsDB 整合範例

### 連線配置

```python
import mindsdb_sdk

# 連線 MindsDB
server = mindsdb_sdk.connect(
    url='http://localhost:47334',
    login='admin',
    password='password'
)

# 取得專案
project = server.get_project('land_prediction')
```

### 預測模型

```python
class LandPricePredictor:
    """土地價格預測器"""

    def __init__(self, project):
        self.project = project
        self.model = project.get_model('land_price_model')

    def predict(
        self,
        city: str,
        district: str,
        area: float,
        land_use: str
    ) -> dict:
        """預測土地價格"""
        result = self.model.predict({
            'city': city,
            'district': district,
            'area_sqm': area,
            'land_use_type': land_use,
        })

        return {
            'predicted_price': result['price'],
            'confidence': result['confidence'],
            'price_range': {
                'low': result['price_lower'],
                'high': result['price_upper'],
            }
        }
```

### 批次預測

```python
async def batch_predict(
    predictor: LandPricePredictor,
    items: list[dict]
) -> list[dict]:
    """批次預測"""
    results = []

    for item in items:
        try:
            prediction = predictor.predict(**item)
            results.append({
                'input': item,
                'prediction': prediction,
                'status': 'success',
            })
        except Exception as e:
            results.append({
                'input': item,
                'error': str(e),
                'status': 'failed',
            })

    return results
```

## 模型管理

```python
class ModelManager:
    """模型管理器"""

    def list_models(self) -> list[dict]:
        """列出所有模型"""
        return [
            {
                'name': model.name,
                'status': model.status,
                'accuracy': model.accuracy,
                'updated_at': model.updated_at,
            }
            for model in self.project.list_models()
        ]

    def retrain_model(self, model_name: str, data_query: str):
        """重新訓練模型"""
        self.project.create_model(
            name=f"{model_name}_v2",
            predict='price',
            query=data_query,
        )

    def get_model_metrics(self, model_name: str) -> dict:
        """取得模型指標"""
        model = self.project.get_model(model_name)
        return {
            'accuracy': model.accuracy,
            'r2_score': model.r2,
            'mae': model.mae,
            'training_time': model.training_time,
        }
```

## 預測類型

| 類型 | 模型 | 輸出 |
|------|------|------|
| 價格預測 | `land_price_model` | 預測價格 + 區間 |
| 趨勢預測 | `price_trend_model` | 未來走勢 |
| 分類預測 | `land_type_model` | 用地類型 |
| 異常檢測 | `anomaly_model` | 異常分數 |

## 相關 Skills

- `@ai-architecture-patterns` - AI 架構模式
- `@error-handling` - 錯誤處理

---

*版本: 1.0.0 | 分類: ai | 觸發: /ai-predict*
