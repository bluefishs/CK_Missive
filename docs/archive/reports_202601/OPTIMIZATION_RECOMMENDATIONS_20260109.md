# 系統優化作業安排與建議

**日期**: 2026-01-09
**依據**: 交易污染 (Transaction Pollution) 問題修復經驗
**目標**: 提升系統穩定性、可維護性與開發效率

---

## 一、問題根因分析

| 層面 | 問題 | 影響 |
|------|------|------|
| **架構設計** | 審計/通知與主業務邏輯耦合 | 次要操作失敗影響核心功能 |
| **錯誤處理** | 缺乏完整的異常隔離機制 | 錯誤擴散至連接池 |
| **監控機制** | 無即時錯誤監控與告警 | 問題發生後才被發現 |
| **開發規範** | Session 管理規範不明確 | 開發者容易引入類似問題 |
| **測試覆蓋** | 缺乏異常情境測試 | 無法提前發現潛在問題 |

---

## 二、優化作業安排

### Phase 1: 緊急修復 (已完成)
| 項目 | 狀態 | 說明 |
|------|------|------|
| 交易污染修復 | ✅ 完成 | 獨立 session 隔離 |
| SQL 語法修正 | ✅ 完成 | CAST 語法替換 |
| 文檔更新 | ✅ 完成 | 開發指引新增章節 |
| 資料庫備份 | ✅ 完成 | 修復前後備份 |

### Phase 2: 短期優化 (✅ 已完成 2026-01-09)

#### 2.1 審計服務重構 ✅
```
優先級: 高
預估工時: 4-6 小時
狀態: ✅ 已完成
```

**目標**: 將審計功能封裝為獨立服務，統一管理 session

**建議實作**:
```python
# backend/app/services/audit_service.py
class AuditService:
    """獨立的審計服務，自動管理 session 生命週期"""

    @staticmethod
    async def log_change(
        table_name: str,
        record_id: int,
        action: str,
        changes: dict,
        user_id: Optional[int] = None,
        user_name: str = "System"
    ) -> bool:
        """
        記錄變更審計日誌
        - 使用獨立 session
        - 自動處理異常
        - 失敗不影響調用方
        """
        from app.db.database import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as db:
                await log_document_change(db, ...)
                await db.commit()
                return True
        except Exception as e:
            logger.warning(f"審計記錄失敗: {e}", exc_info=True)
            return False
```

**影響範圍**:
- `documents_enhanced.py`
- `projects.py`
- `agencies.py`
- 其他有審計需求的 endpoint

#### 2.2 通知服務改進 ✅
```
優先級: 高
預估工時: 3-4 小時
狀態: ✅ 已完成
```

**目標**: 通知服務獨立化，支援失敗重試

**已實作**:
1. ✅ 新增 `safe_notify_critical_change()` - 使用獨立 session
2. ✅ 新增 `safe_notify_document_deleted()` - 使用獨立 session
3. ✅ 統一 SQL 參數綁定風格（使用 CAST 語法）

#### 2.3 全域錯誤處理強化 ✅
```
優先級: 中
預估工時: 2-3 小時
狀態: ✅ 已完成
```

**目標**: 統一異常處理，防止錯誤擴散

**已實作** (`backend/app/core/decorators.py`):
```python
@non_critical           # 非關鍵操作裝飾器，失敗不影響主流程
@retry_on_failure       # 失敗重試裝飾器（指數退避）
@log_execution          # 執行日誌裝飾器
```

### Phase 3: 中期優化 (建議 2-4 週)

#### 3.1 背景任務架構
```
優先級: 中
預估工時: 8-12 小時
```

**目標**: 將審計/通知改為異步背景任務

**技術選項**:
| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **FastAPI BackgroundTasks** | 簡單、無需額外依賴 | 無持久化、重啟丟失 | 輕量級通知 |
| **Celery + Redis** | 成熟穩定、支援重試 | 架構複雜度增加 | 大量異步任務 |
| **資料庫佇列** | 簡單、可靠 | 效能較低 | 可靠性優先 |

**建議**: 目前規模採用 FastAPI BackgroundTasks，未來擴展再考慮 Celery

```python
from fastapi import BackgroundTasks

@router.post("/{document_id}/update")
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    # 主業務邏輯
    document = await update_document_in_db(db, document_id, data)
    await db.commit()

    # 背景任務 - 不阻塞回應
    background_tasks.add_task(
        AuditService.log_change,
        table_name="documents",
        record_id=document_id,
        action="UPDATE",
        changes=changes
    )

    return document
```

#### 3.2 連接池監控
```
優先級: 中
預估工時: 4-6 小時
```

**目標**: 即時監控資料庫連接池健康狀態

**監控指標**:
- 活躍連接數
- 等待連接數
- 連接錯誤率
- 平均查詢時間

**建議實作**:
```python
# backend/app/core/db_monitor.py
from sqlalchemy import event

class DatabaseMonitor:
    metrics = {
        "active_connections": 0,
        "checkout_count": 0,
        "checkin_count": 0,
        "overflow_count": 0,
        "invalidated_count": 0
    }

    @classmethod
    def setup(cls, engine):
        event.listen(engine.sync_engine, "checkout", cls.on_checkout)
        event.listen(engine.sync_engine, "checkin", cls.on_checkin)
        event.listen(engine.sync_engine, "invalidate", cls.on_invalidate)
```

#### 3.3 健康檢查端點
```
優先級: 中
預估工時: 2-3 小時
```

```python
# backend/app/api/endpoints/health.py
@router.get("/health/db")
async def database_health():
    """資料庫健康檢查"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "pool": DatabaseMonitor.get_pool_status()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )
```

### Phase 4: 長期優化 (建議 1-2 月)

#### 4.1 測試覆蓋強化
```
優先級: 高
預估工時: 16-24 小時
```

**目標**: 建立完整的異常情境測試

**測試案例**:
```python
# backend/tests/test_transaction_isolation.py

class TestTransactionIsolation:
    """交易隔離測試"""

    async def test_audit_failure_does_not_affect_main_operation(self):
        """審計失敗不應影響主操作"""
        # Mock 審計服務拋出異常
        with patch('app.services.audit_service.log_change', side_effect=Exception("DB Error")):
            response = await client.post(f"/documents/{doc_id}/update", json=data)
            assert response.status_code == 200

    async def test_notification_failure_does_not_affect_main_operation(self):
        """通知失敗不應影響主操作"""
        pass

    async def test_connection_pool_health_after_failures(self):
        """連續失敗後連接池應保持健康"""
        pass
```

#### 4.2 CI/CD 整合
```
優先級: 中
預估工時: 8-12 小時
```

**目標**: 自動化檢查防止類似問題

**Pipeline 階段**:
```yaml
# .github/workflows/code-quality.yml
stages:
  - lint:
      - pylint --load-plugins=custom_session_checker

  - test:
      - pytest tests/test_transaction_isolation.py
      - pytest tests/test_error_handling.py

  - security:
      - bandit -r app/
      - safety check
```

**自定義 Lint 規則**:
```python
# 檢測 session 傳遞給非核心操作
def check_session_usage(node):
    if is_audit_or_notification_call(node):
        if has_db_parameter(node):
            report_warning("審計/通知操作不應接收外部 session")
```

#### 4.3 開發規範制度化
```
優先級: 高
預估工時: 4-6 小時
```

**Code Review Checklist**:
- [ ] 審計/通知操作是否使用獨立 session？
- [ ] 非核心操作是否有完整異常處理？
- [ ] SQL 參數綁定是否使用正確語法？
- [ ] 是否有對應的單元測試？

---

## 三、優先順序總覽

```
緊急 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 長期

Week 1-2          Week 3-4          Month 2           Month 2+
┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
│ Phase 2 │  →   │ Phase 3 │  →   │ Phase 4 │  →   │ 持續    │
│ 短期優化│      │ 中期優化│      │ 長期優化│      │ 改進    │
└─────────┘      └─────────┘      └─────────┘      └─────────┘
    │                │                │                │
    ├─ 審計服務重構   ├─ 背景任務架構   ├─ 測試覆蓋強化   ├─ 監控調優
    ├─ 通知服務改進   ├─ 連接池監控     ├─ CI/CD 整合    ├─ 效能優化
    └─ 錯誤處理強化   └─ 健康檢查端點   └─ 規範制度化    └─ 架構演進
```

---

## 四、資源需求估算

| Phase | 預估工時 | 人力需求 | 備註 |
|-------|---------|---------|------|
| Phase 2 | 10-14 小時 | 1 開發者 | 可並行開發 |
| Phase 3 | 14-20 小時 | 1 開發者 | 需測試環境 |
| Phase 4 | 28-42 小時 | 1-2 開發者 | 可分階段進行 |
| **總計** | **52-76 小時** | - | 約 2-3 週全職投入 |

---

## 五、風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| 重構引入新 bug | 中 | 高 | 完整測試覆蓋、分階段上線 |
| 背景任務丟失 | 低 | 中 | 實作持久化佇列或重試機制 |
| 效能下降 | 低 | 中 | 效能測試、監控預警 |
| 開發資源不足 | 中 | 中 | 優先處理高優先級項目 |

---

## 六、預期效益

| 效益 | 說明 |
|------|------|
| **穩定性提升** | 消除交易污染風險，減少 500 錯誤 |
| **可維護性提升** | 統一的服務封裝，降低維護成本 |
| **問題發現加速** | 監控機制提前發現潛在問題 |
| **開發效率提升** | 明確規範減少試錯時間 |
| **系統可觀測性** | 健康檢查與指標監控 |

---

## 七、建議立即行動

### 本週內 (高優先)
1. ✅ 完成現有問題修復 (已完成)
2. ✅ 審計服務重構 (`AuditService` 類別) - 2026-01-09 完成
3. ✅ 通知服務 SQL 語法全面檢查 - 2026-01-09 完成

### 下週 (中優先)
4. ✅ 錯誤處理裝飾器實作 - 2026-01-09 完成
5. 🔲 基礎健康檢查端點
6. 🔲 單元測試補充

### 持續進行 (長期)
7. 🔲 背景任務架構評估
8. 🔲 CI/CD 整合規劃
9. 🔲 團隊培訓與規範推廣

---

## 八、Phase 2 實作摘要 (2026-01-09)

### 已建立的新檔案

| 檔案 | 說明 |
|------|------|
| `backend/app/services/audit_service.py` | 統一審計服務，自動管理獨立 session |
| `backend/app/core/decorators.py` | 通用裝飾器 (@non_critical, @retry_on_failure, @log_execution) |

### 已更新的檔案

| 檔案 | 變更 |
|------|------|
| `backend/app/services/notification_service.py` | 新增 safe_* 方法（獨立 session） |
| `backend/app/api/endpoints/documents_enhanced.py` | 改用 AuditService 和 safe_* 方法 |

### 使用方式

```python
# 審計日誌（自動使用獨立 session）
from app.services.audit_service import AuditService
await AuditService.log_document_change(
    document_id=doc_id,
    action="UPDATE",
    changes=changes,
    user_id=user_id,
    user_name=user_name
)

# 關鍵欄位變更通知（自動使用獨立 session）
from app.services.notification_service import NotificationService
await NotificationService.safe_notify_critical_change(
    document_id=doc_id,
    field="subject",
    old_value="舊主旨",
    new_value="新主旨",
    user_id=user_id
)

# 非關鍵操作裝飾器
from app.core.decorators import non_critical

@non_critical(default_return=False)
async def send_notification():
    # 此函數失敗不會影響主業務邏輯
    ...
```

---

*文件生成時間: 2026-01-09 14:10*
*Phase 2 完成時間: 2026-01-09 15:30*
*下次檢視建議: 2026-01-16*
