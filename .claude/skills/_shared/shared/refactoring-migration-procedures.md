---
name: 重構與遷移作業規範
description: 避免遷移一半造成維護地獄的重構與遷移標準作業規範
version: 1.0.0
category: shared
triggers:
  - /refactoring
  - 重構規範
  - 遷移作業
  - migration
updated: 2026-01-28
---

# 重構與遷移作業規範

> 避免「遷移一半」造成的維護地獄

---

## 1. 遷移前檢查清單

### 1.1 依賴分析

在移除或重構任何模組前，必須執行：

```bash
# 搜尋所有引用該模組的檔案
grep -r "from.*模組名稱.*import" backend/
grep -r "import.*模組名稱" frontend/src/
```

### 1.2 記錄依賴關係

```
待遷移模組: basemap.py
├── 被引用於: basemap_parser.py (load_basemap_config, save_basemap_config)
├── 被引用於: router_registry.py (router)
└── 前端呼叫: /basemap/layers/list, /basemaps
```

### 1.3 遷移影響評估

- [ ] 列出所有受影響的 API 端點
- [ ] 列出所有引用的函數/類別
- [ ] 確認前端呼叫的 URL 路徑
- [ ] 確認資料格式是否相容

---

## 2. 廢棄標記規範

### 2.1 檔案層級標記

當整個檔案即將廢棄時，在檔案頂部加入醒目標記：

```python
"""
模組名稱

╔════════════════════════════════════════════════════════════════════╗
║  ⚠️  已廢棄 - DEPRECATED (YYYY-MM-DD)                              ║
║                                                                    ║
║  此模組已遷移至: 新模組路徑                                        ║
║  預計移除日期: YYYY-MM-DD                                          ║
║                                                                    ║
║  僅保留以下導出供相容使用:                                         ║
║  - 函數/類別名稱                                                   ║
╚════════════════════════════════════════════════════════════════════╝
"""
```

### 2.2 函數層級標記

```python
import warnings
from functools import wraps

def deprecated(message: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(f"{func.__name__} is deprecated: {message}",
                         DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@deprecated("Use basemap_service.create_basemap() instead")
def save_basemap_config(config):
    ...
```

### 2.3 API 端點標記

```python
@router.post("/old-endpoint", deprecated=True)
async def old_endpoint():
    """
    ⚠️ [DEPRECATED] 請使用 /new-endpoint

    預計移除: 2025-03-01
    """
    ...
```

---

## 3. 型別一致性規範

### 3.1 ID 欄位規則

| 情境             | 型別              | 範例                         |
| ---------------- | ----------------- | ---------------------------- |
| 資料庫自動生成   | `int`             | `id: int`                    |
| 使用者定義識別碼 | `str`             | `group_id: str = "opendata"` |
| 混合支援         | `Union[int, str]` | `id: Union[int, str]`        |

### 3.2 前後端型別對應

```
Python (後端)          TypeScript (前端)
─────────────────────────────────────────
int                    number
str                    string
Optional[int]          number | null
Union[int, str]        number | string
List[str]              string[]
Dict[str, Any]         Record<string, unknown>
```

### 3.3 Pydantic 模型規範

```python
class CompatibleModel(BaseModel):
    """相容性模型 - 接受前端可能發送的所有欄位"""

    # 核心欄位
    name: str
    description: Optional[str] = None

    # 前端可能發送的額外欄位
    icon: Optional[str] = None
    metadata: Optional[dict] = None

    # 忽略未知欄位，避免 422 錯誤
    model_config = {"extra": "ignore"}
```

---

## 4. 遷移執行步驟

### 4.1 階段一：準備

1. 建立新模組（不移除舊模組）
2. 新模組實作所有功能
3. 撰寫遷移測試

### 4.2 階段二：橋接

1. 舊模組加入廢棄標記
2. 舊模組內部改為呼叫新模組
3. 保持 API 端點相容

```python
# 舊模組 (basemap.py)
@deprecated("Use basemap_db.py")
def load_basemap_config():
    # 改為呼叫新服務
    from backend.app.services.basemap_service import get_basemap_service
    service = get_basemap_service(get_db())
    return service.get_basemaps()
```

### 4.3 階段三：清理

1. 確認無任何模組引用舊函數
2. 更新 router_registry.py
3. 移除舊模組或保留最小相容導出

---

## 5. 遷移後驗證

### 5.1 端到端測試

```bash
# 測試所有 CRUD 操作
curl -X POST http://localhost:8002/api/v1/basemap/groups -d '{"name":"test"}'
curl -X POST http://localhost:8002/api/v1/basemap/groups/test/update -d '{"name":"test2"}'
curl -X POST http://localhost:8002/api/v1/basemap/groups/test/delete
```

### 5.2 前端整合測試

- [ ] 列表顯示正常
- [ ] 新增功能正常
- [ ] 更新功能正常
- [ ] 刪除功能正常
- [ ] 排序功能正常

### 5.3 日誌檢查

```bash
# 確認無廢棄警告
docker logs backend 2>&1 | grep -i "deprecated"
```

---

## 6. 常見錯誤與預防

### 6.1 422 Unprocessable Entity

**原因**: Pydantic 模型欄位與請求不符
**預防**:

- 使用 `model_config = {"extra": "ignore"}`
- 確保所有前端可能發送的欄位都有定義

### 6.2 404 Not Found

**原因**: Router 移除但前端仍呼叫舊端點
**預防**:

- 在新模組加入相容端點
- 使用 URL 別名 (alias)

### 6.3 500 Internal Server Error

**原因**: 函數被移除但仍被其他模組引用
**預防**:

- 遷移前完整搜尋依賴
- 保留 stub 函數直到確認無引用

---

## 7. 文件更新

遷移完成後必須更新：

- [ ] `CONTEXT.md` - 架構變更
- [ ] `router_registry.py` - 註解說明
- [ ] 相關 skill 文件

---

**最後更新**: 2026-01-01
