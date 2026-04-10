# CK_Missive 開發指引

> **本檔僅記錄「現在仍會觸發的陷阱」與「正在執行的規則」。**
> 歷史 bug 修復請查 `git log` 與 `.claude/CHANGELOG.md`；完整架構規範見 `docs/DEVELOPMENT_STANDARDS.md` 與 `.claude/rules/`。

**最後整併**: 2026-04-10 (v5.5.4 baseline)
**目標**: 簡潔、可執行、只保留未過期的反模式清單。

---

## 🔗 規範來源索引 (強制載入)

`.claude/rules/` 底下所有檔案於對話啟動時自動載入。開發前請先查 CLAUDE.md 的規範索引。**本檔不重複 rules/ 的內容**，只補充尚未入規範或實戰發現的陷阱。

關鍵規範:
- `rules/development-rules.md` — API 端點/型別 SSOT/服務層/DI
- `rules/architecture.md` — 目錄結構與分層
- `rules/auth-environment.md` — 環境檢測與認證
- `MANDATORY_CHECKLIST.md` — 開發前強制檢查清單 (A~X)

---

## ⚡ 修改後自檢 (必須)

```bash
# TypeScript 編譯
cd frontend && npx tsc --noEmit

# Python 語法
cd backend && python -m py_compile app/main.py

# 後端 str(e) 洩漏掃描
grep -rn "str(e)" backend/app/api/endpoints/ --include="*.py" | grep -v __pycache__ | grep -v logger
```

自檢通過才提出複查。未通過時先自行修復。

---

## 🚨 當前仍活躍的反模式 (Anti-Patterns)

以下為經實戰驗證、仍會在新程式碼中反覆出現的陷阱。依嚴重度排序。

### A1. 🔴 `str(e)` 洩漏到客戶端

**規則**: API 端點禁止將 `str(e)` 放入 `HTTPException.detail` 或 JSON response。

```python
# ❌
raise HTTPException(status_code=500, detail=f"操作失敗: {str(e)}")

# ✅
logger.error(f"操作失敗: {e}", exc_info=True)
raise HTTPException(status_code=500, detail="操作失敗，請稍後再試")
```

### A2. 🔴 交易污染 (Session Pollution)

**規則**: `db.commit()` 後不得再以同一 session 執行新操作 (審計/通知必須用獨立 session)。

```python
# ❌ 同一 session 做審計會污染連線池
await db.commit()
await log_audit(db, ...)

# ✅ 使用 AuditService (內部開獨立 session)
await db.commit()
await AuditService.log_document_change(document_id=doc_id, ...)
```

可用安全服務: `AuditService`, `NotificationService.safe_*()`, `AuditableServiceMixin`

### A3. 🔴 useEffect 依賴包含 API 回應值 → 無限迴圈

**規則**: useEffect 依賴陣列只放「使用者主動變更」的值，禁止放 API 回應衍生值 (total / data.length / loading)。

```typescript
// ❌ total 會因 API 回應改變 → 再觸發 → 無限迴圈
useEffect(() => { fetchStats(); }, [filters, total]);

// ✅
useEffect(() => { fetchStats(); }, [filters.search, filters.doc_type]);
```

**更好的做法**: 直接用 `useQuery`，不要自己寫 useEffect + apiClient (見 MANDATORY_CHECKLIST 清單 T)。

### A4. 🔴 錯誤時清空列表 (Error Clears List)

**規則**: `catch` 區塊禁止 `setItems([])`。API 暫時失敗時應保留既有資料。

```typescript
// ❌
} catch (error) {
  setItems([]);  // 用戶已看到的資料會消失
}

// ✅
} catch (error) {
  message.error('載入失敗，請重新整理頁面');
  // 不清空
}
```

**例外**: 切換實體 (換專案) 或頁面初始載入時可清空。

### A5. 🟡 slowapi `@limiter.limit` 參數命名衝突

**規則**: 套用 `@limiter.limit` 的端點，Pydantic body 參數**不可**命名為 `request`。

```python
# ❌ body 搶了 request 這個名稱 → 500
@limiter.limit("5/minute")
async def create_backup(http_request: Request, request: CreateBackupRequest):

# ✅
@limiter.limit("5/minute")
async def create_backup(request: Request, body: CreateBackupRequest):
```

強制: `request: Request` + `response: Response` + `body: XxxRequest`。

### A6. 🟡 硬編碼 API 路徑

**規則**: 禁止在前端直接寫死 URL 字串，一律用 `api/endpoints/` 常數。動態路徑用函數型端點。

```typescript
// ❌
apiClient.post('/projects/list', params);
apiClient.post(`${AI_ENDPOINTS.ANALYSIS}/${id}`);  // 字串拼接也算

// ✅
apiClient.post(PROJECTS_ENDPOINTS.LIST, params);
apiClient.post(AI_ENDPOINTS.ANALYSIS_GET(id));
```

### A7. 🟡 Endpoint 內本地 BaseModel 違反 SSOT

**規則**: `api/endpoints/` 中不得定義 Pydantic BaseModel，必須從 `schemas/` 匯入。

```bash
# 檢查
grep -rn "class.*BaseModel" backend/app/api/endpoints/ --include="*.py" | grep -v __pycache__
```

### A8. 🟡 Antd Modal + Form.useForm 警告

**規則**: Modal 內用 `Form.useForm()` 時必須加 `forceRender`，否則 `open=false` 時 hook 已執行但 DOM 未掛載。

```tsx
<Modal open={visible} forceRender>
  <Form form={form}>...</Form>
</Modal>
```

**另一類**: React Query `queryFn` 內不要呼叫 `form.setFieldsValue()`，改用 `useEffect` 等 data 就緒後再設。

### A9. 🟡 刪除/重命名函數前未全域搜尋引用

**規則**: 刪除前必須 `grep -r "function_name" backend/` 確認無殘留 import。

### A10. 🟡 link_id 回退邏輯

**規則**: 關聯記錄必須要求 `link_id` 存在，禁止 `?? item.id` 回退。詳見 `docs/specifications/LINK_ID_HANDLING_SPECIFICATION.md`。

---

## 📋 Git Commit 粒度

**原則**: 一個 commit 做一件事。多個不相關變更必須拆分。

| 情境 | 策略 |
|------|------|
| 新功能 + 測試 | 同一 commit |
| Bug 修復 + 順手重構 | **分開** commit |
| 新功能 + 無關重構 | **分開** commit |
| DB 遷移 + ORM | 同一 commit |
| 前端頁面 + 後端 API | 可同一 commit (同功能) |

**禁止**: `feat: PM重定位 + 統一模板 + 委託單位 + Code-graph` (混雜多主題)。

**好處**: `git bisect` 可定位 regression，CHANGELOG 自動生成精準，cherry-pick/revert 安全。

---

## 📐 服務行數監控 (>600L 警告)

```bash
python scripts/checks/service-line-count-check.py --threshold 600
```

當前 v5.5.4 違規清單 (2026-04-10):
- `agent_orchestrator.py` (594L — 接近閾值)
- `agent_evolution_scheduler.py` (587L)
- `dispatch_order_service.py` (550L)
- `agent_planner.py` (521L)
- `case_code_service.py` (511L)
- `agent_pattern_learner.py` (510L)
- `telegram_bot_service.py` (508L)
- `response_enricher.py` (503L)

拆分策略:
1. 提取 helper/utility → 獨立模組
2. 子功能 → sub-service (如 `tender_analytics_*.py` 的模式)
3. 策略模式分離分支邏輯

---

## 🤖 Agent 開發前置檢查

新增/修改 Agent 工具、SSE 事件、合成邏輯前：

### 新增工具
- [ ] `tool_definitions.py` 新增 TOOL_DEFINITIONS 項
- [ ] `tool_registry.py` / executor 實作 `_tool_name` 方法
- [ ] 前端 UI 的 `TOOL_ICONS` + `TOOL_LABELS` 同步
- [ ] 工具描述含使用時機 (讓 LLM 能正確選擇)
- [ ] 若屬可學習工具 → 確認 pattern_learner 已覆蓋

### SSE 事件
- [ ] thinking/tool_call/tool_result 事件含 `step_index`
- [ ] error 事件含 `code` (RATE_LIMITED/SERVICE_ERROR/TIMEOUT/VALIDATION_ERROR)
- [ ] 前端 callback 簽章與後端事件欄位對齊

### 合成品質
- [ ] `_strip_thinking_from_synthesis()` 處理新工具輸出
- [ ] 閒聊偵測不誤攔業務查詢
- [ ] 測試覆蓋: 正常/引用 [公文N]/[派工單N]/長思考鏈

---

## 🧪 Code Review Checklist (精簡版)

### 前端
- [ ] 資料取得用 `useQuery`/`useMutation`，無 useEffect + apiClient
- [ ] API 路徑用 endpoints 常數，無硬編碼
- [ ] catch 未清空列表
- [ ] Modal + useForm 有 `forceRender`
- [ ] 型別從 `types/` 匯入，api/*.ts 無本地 interface

### 後端
- [ ] `str(e)` 未洩漏
- [ ] commit 後未複用 session
- [ ] `@limiter.limit` 端點 body 不叫 request
- [ ] 端點內無本地 BaseModel
- [ ] Service 層繼承 `AuditableServiceMixin` (CRUD)
- [ ] 無 N+1 查詢 (用 `selectinload`/`joinedload`)
- [ ] 端點使用 `Depends(get_service_with_db(X))` 工廠

### 測試
- [ ] 錯誤分支有測試
- [ ] 「錯誤時保留列表」有測試 (前端載入函數)
- [ ] 邊界條件覆蓋

---

## 📚 相關文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | 強制性檢查清單 (A~X，按任務類型) |
| `.claude/CHANGELOG.md` | 完整版本更新記錄 |
| `.claude/rules/` | 自動載入的規範 (9 份) |
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 |
| `docs/ERROR_HANDLING_GUIDE.md` | 錯誤處理詳細指南 |
| `docs/specifications/` | 所有技術規範 |
| `docs/adr/` | 架構決策紀錄 (15 份) |

---

## 🛠️ 快速命令

```bash
# 前置檢查
/pre-dev-check

# 整合檢查
powershell -File scripts/checks/skills-sync-check.ps1
cd frontend && npx tsc --noEmit
cd backend && python -m py_compile app/main.py

# 路由一致性
powershell -File .claude/hooks/route-sync-check.ps1

# API 序列化
powershell -File .claude/hooks/api-serialization-check.ps1

# 服務行數
python scripts/checks/service-line-count-check.py --threshold 600

# Skills 重建索引
node .claude/scripts/generate-index.cjs
```

---

> **核心理念**: 規則要少而精，過期的陷阱清理掉才能讓真正的紅線被看見。
