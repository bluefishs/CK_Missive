# API 端點一致性檢查 (API Endpoint Consistency Check)

執行前後端 API 端點一致性檢查，確保路由定義匹配。

## 檢查項目

### 1. 後端路由檢查
檢視所有已註冊的路由前綴。

```bash
# 查看路由註冊
grep -n "include_router" backend/app/api/routes.py
```

### 2. 前端端點檢查
檢視集中式端點定義。

```bash
# 查看端點常數
cat frontend/src/api/endpoints.ts
```

### 3. 對照驗證
依據 `docs/specifications/API_ENDPOINT_CONSISTENCY.md` v2.0.0 規範檢查：

| 模組 | 後端前綴 | 前端常數 | 狀態 |
|------|----------|----------|------|
| 公文管理 | `/documents-enhanced` | `API_ENDPOINTS.DOCUMENTS` | 待確認 |
| 行事曆 | `/calendar` | `API_ENDPOINTS.CALENDAR` | 待確認 |
| 機關管理 | `/agencies` | `API_ENDPOINTS.AGENCIES` | 待確認 |
| 專案管理 | `/projects` | `API_ENDPOINTS.PROJECTS` | 待確認 |
| 廠商管理 | `/vendors` | `API_ENDPOINTS.VENDORS` | 待確認 |

### 4. 常見錯誤檢查

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

### 發現路由不一致時
1. 確認後端 `routes.py` 的 prefix 為正確來源
2. 更新前端 `endpoints.ts` 匹配後端
3. 更新使用到的 API Client

### 發現硬編碼路徑時
1. 在 `endpoints.ts` 新增對應常數
2. 替換硬編碼為常數引用

## 相關文件
- `docs/specifications/API_ENDPOINT_CONSISTENCY.md` - API 端點一致性規範
- `frontend/src/api/endpoints.ts` - 前端端點定義
- `backend/app/api/routes.py` - 後端路由註冊
