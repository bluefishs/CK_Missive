# API 端點一致性檢查 (API Endpoint Consistency Check)

執行前後端 API 端點一致性檢查，確保路由定義匹配並符合 POST-only 安全規範。

## 檢查項目

### 1. POST-only 合規檢查 (v2.1.0 新增)
確保所有 API 端點僅使用 POST 方法。

```bash
# 檢查後端是否有非 POST 端點
grep -n "@router\.\(get\|put\|delete\|patch\)" backend/app/api/endpoints/*.py

# 預期結果：無輸出或僅有 deprecated 標記的端點
# 若有非 POST 端點，需轉換為以下格式：
# POST /xxx/list          # 取得列表 (原 GET /xxx)
# POST /xxx/{id}/detail   # 取得詳情 (原 GET /xxx/{id})
# POST /xxx/{id}/update   # 更新資料 (原 PUT /xxx/{id})
# POST /xxx/{id}/delete   # 刪除資料 (原 DELETE /xxx/{id})
```

### 2. 後端路由檢查
檢視所有已註冊的路由前綴。

```bash
# 查看路由註冊
grep -n "include_router" backend/app/api/routes.py
```

### 3. 前端端點檢查
檢視集中式端點定義。

```bash
# 查看端點常數
cat frontend/src/api/endpoints.ts
```

### 4. 對照驗證
依據 `docs/specifications/API_ENDPOINT_CONSISTENCY.md` v2.1.0 規範檢查：

| 模組 | 後端前綴 | 前端常數 | POST-only | 狀態 |
|------|----------|----------|-----------|------|
| 公文管理 | `/documents-enhanced` | `API_ENDPOINTS.DOCUMENTS` | ✅ | 待確認 |
| 行事曆 | `/calendar` | `API_ENDPOINTS.CALENDAR` | ✅ | 待確認 |
| 機關管理 | `/agencies` | `API_ENDPOINTS.AGENCIES` | ✅ | 待確認 |
| 專案管理 | `/projects` | `API_ENDPOINTS.PROJECTS` | ✅ | 待確認 |
| 廠商管理 | `/vendors` | `API_ENDPOINTS.VENDORS` | ✅ | 待確認 |
| 使用者管理 | `/admin/user-management` | `API_ENDPOINTS.ADMIN_USER_MANAGEMENT` | ✅ | 待確認 |

### 5. 常見錯誤檢查

#### 非 POST 方法呼叫
```bash
# 搜尋前端使用 GET/PUT/DELETE 的呼叫
grep -r "method:\s*['\"]GET['\"]" frontend/src/
grep -r "method:\s*['\"]PUT['\"]" frontend/src/
grep -r "method:\s*['\"]DELETE['\"]" frontend/src/
# 應全部改為 method: 'POST'
```

#### 路由前綴錯誤
```bash
# 搜尋可能錯誤的路由
grep -r "document-calendar" frontend/src/
# 應該使用 /calendar 而非 /document-calendar
```

#### 硬編碼路徑
```bash
# 搜尋未使用 API_ENDPOINTS 的呼叫
grep -r "apiClient.*'/api" frontend/src/
# 應使用 API_ENDPOINTS.XXX
```

## 修復指南

### 發現非 POST 端點時
1. 後端端點改為 `@router.post("/xxx/action")`
2. 前端呼叫改為 `method: 'POST'`
3. 更新 `endpoints.ts` 路徑 (如 `/list`, `/detail`, `/update`, `/delete`)

### 發現路由不一致時
1. 確認後端 `routes.py` 的 prefix 為正確來源
2. 更新前端 `endpoints.ts` 匹配後端
3. 更新使用到的 API Client

### 發現硬編碼路徑時
1. 在 `endpoints.ts` 新增對應常數
2. 替換硬編碼為常數引用

## 相關文件
- `docs/specifications/API_ENDPOINT_CONSISTENCY.md` - API 端點一致性規範 v2.1.0
- `frontend/src/api/endpoints.ts` - 前端端點定義
- `backend/app/api/routes.py` - 後端路由註冊
