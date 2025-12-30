# 行事曆服務架構整理說明

## 整理目的
將行事曆功能從公文系統中抽離，建立獨立的行事曆服務，實現關注點分離。

## 新的架構結構

### 1. 後端服務層

#### 純粹行事曆服務
- **檔案**: `backend/app/services/calendar_service.py`
- **功能**: 提供基本行事曆 CRUD 操作
- **特點**: 完全獨立，不依賴公文系統

#### 純粹行事曆 API
- **檔案**: `backend/app/api/endpoints/pure_calendar.py`
- **路由**: `/api/calendar/*`
- **功能**: 提供獨立的行事曆 REST API

#### Google Calendar 整合模組
- **檔案**: `backend/app/integrations/calendar/google_calendar_integration.py`
- **功能**: 獨立的 Google Calendar 整合服務
- **特點**: 可以獨立使用，不綁定特定業務邏輯

### 2. 前端服務層

#### 純粹行事曆服務
- **檔案**: `frontend/src/services/pureCalendarService.ts`
- **功能**: 前端行事曆 API 調用封裝

#### 純粹行事曆頁面
- **檔案**: `frontend/src/pages/PureCalendarPage.tsx`
- **功能**: 獨立的行事曆界面
- **特點**: 完整的行事曆功能，包含事件管理、統計、分類等

## API 端點對照

### 原有混合端點 vs 新的獨立端點

| 原有端點 | 新獨立端點 | 說明 |
|---------|-----------|------|
| `/api/calendar/events` | `/api/calendar/events` | 純粹事件管理 |
| `/api/document-calendar/sync-event` | `/api/calendar/google-sync` | Google 同步（可選） |
| `/api/calendar/status` | `/api/calendar/status` | 服務狀態 |

### 新增功能
- `/api/calendar/categories` - 事件分類管理
- `/api/calendar/stats` - 統計資訊
- Google Calendar 雙向同步（可選啟用）

## 功能特色

### 1. 關注點分離
- 行事曆功能完全獨立
- 可以單獨使用，不依賴公文系統
- 清晰的模組界限

### 2. 可選的 Google 整合
- Google Calendar 整合是可選功能
- 可以只使用本地行事曆
- 或同時使用本地 + Google 同步

### 3. 豐富的事件管理
- 事件分類（工作、個人、會議等）
- 優先級設定（高、中、低）
- 統計功能（今日、本週、本月事件）
- 衝突檢測

### 4. 用戶友好界面
- 完整的日曆檢視
- 事件列表
- 統計卡片
- 拖拽編輯（未來可擴展）

## 與公文系統的關係

### 獨立使用
行事曆系統可以完全獨立運行，不需要公文系統。

### 公文整合（可選）
如果需要公文事件同步到行事曆：
1. 保留原有的 `document_calendar.py`
2. 讓它調用新的純粹行事曆服務
3. 實現單向或雙向同步

### 整合方式示例
```python
# 在公文創建時，可選地同步到行事曆
from app.services.calendar_service import calendar_service

async def create_document_with_calendar_sync(document_data, sync_to_calendar=False):
    # 創建公文
    document = await create_document(document_data)

    # 可選：同步到行事曆
    if sync_to_calendar and document.deadline:
        await calendar_service.create_event(
            title=f"公文截止: {document.subject}",
            description=f"公文編號: {document.document_number}",
            start_datetime=document.deadline,
            end_datetime=document.deadline + timedelta(hours=1),
            category="deadline",
            priority="high"
        )

    return document
```

## 遷移計畫

### 第一階段：獨立行事曆
- ✅ 建立純粹行事曆服務
- ✅ 建立獨立 API 端點
- ✅ 建立前端頁面
- ✅ 建立 Google Calendar 整合模組

### 第二階段：路由整合
- [ ] 將新路由加入主路由
- [ ] 更新導航選單
- [ ] 測試獨立功能

### 第三階段：公文整合（可選）
- [ ] 修改公文系統調用新的行事曆服務
- [ ] 保持向後兼容
- [ ] 逐步遷移現有功能

### 第四階段：清理
- [ ] 移除舊的混合代碼
- [ ] 文檔更新
- [ ] 性能優化

## 使用方式

### 開發者
```bash
# 啟動後端（包含新的行事曆 API）
cd backend && python main.py

# 前端會自動包含新的行事曆頁面
cd frontend && npm run dev
```

### 用戶
1. 導航到「行事曆」頁面
2. 可以創建、編輯、刪除事件
3. 查看統計和分類
4. 可選：啟用 Google Calendar 同步

## 架構優勢

1. **可維護性**: 清晰的模組邊界，easier to maintain
2. **可測試性**: 每個模組可以獨立測試
3. **可擴展性**: 容易添加新功能
4. **可重用性**: 行事曆服務可以在其他項目中使用
5. **向後兼容**: 不破壞現有公文系統功能