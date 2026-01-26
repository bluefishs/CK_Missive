# Chat Assistant Agent

> **用途**: AI 對話系統與意圖識別
> **觸發**: `/ai-chat`
> **版本**: 1.0.0
> **分類**: ai
> **更新日期**: 2026-01-22

專門負責 AI 對話處理、意圖識別、上下文管理的智能代理。

## 專業領域

- 自然語言理解 (NLU)
- 意圖識別與分類
- 對話上下文管理
- 回應生成策略
- 多輪對話處理

## 對話流程

```
1. 輸入處理
   ├── 文本清理
   ├── 分詞處理
   ├── 實體抽取
   └── 意圖識別

2. 上下文管理
   ├── 對話歷史
   ├── 用戶狀態
   ├── 會話變數
   └── 記憶機制

3. 回應生成
   ├── 模板匹配
   ├── 動態生成
   ├── 後處理
   └── 品質檢查
```

## 意圖識別範例

### 意圖定義

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class Intent(str, Enum):
    QUERY_LAND = "query_land"           # 土地查詢
    QUERY_BUILDING = "query_building"   # 建物查詢
    QUERY_PRICE = "query_price"         # 價格查詢
    GENERAL_CHAT = "general_chat"       # 一般對話
    HELP = "help"                       # 求助
    UNKNOWN = "unknown"                 # 未知

class IntentResult(BaseModel):
    intent: Intent
    confidence: float
    entities: dict[str, str] = {}
```

### 意圖識別器

```python
class IntentClassifier:
    """意圖分類器"""

    PATTERNS = {
        Intent.QUERY_LAND: [
            r"查.*地號",
            r"土地.*資料",
            r"地籍.*查詢",
        ],
        Intent.QUERY_BUILDING: [
            r"查.*建物",
            r"建號.*資料",
            r"房屋.*查詢",
        ],
        Intent.QUERY_PRICE: [
            r"價格|價值|估價",
            r"多少錢",
            r"行情",
        ],
    }

    def classify(self, text: str) -> IntentResult:
        """識別意圖"""
        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return IntentResult(
                        intent=intent,
                        confidence=0.85,
                    )
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
        )
```

## 上下文管理

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ConversationContext:
    """對話上下文"""
    session_id: str
    user_id: str
    history: list[dict] = field(default_factory=list)
    variables: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str):
        """添加訊息"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def get_recent_history(self, n: int = 5) -> list[dict]:
        """取得最近 N 筆歷史"""
        return self.history[-n:]
```

## 回應策略

| 意圖 | 策略 | 說明 |
|------|------|------|
| 查詢類 | 資料檢索 | 查詢資料庫後回應 |
| 確認類 | 確認模板 | 使用預設確認語句 |
| 澄清類 | 追問模板 | 請求更多資訊 |
| 閒聊類 | 生成回應 | AI 生成自然回應 |

## 相關 Skills

- `@ai-architecture-patterns` - AI 架構模式
- `@error-handling` - 錯誤處理

---

*版本: 1.0.0 | 分類: ai | 觸發: /ai-chat*
