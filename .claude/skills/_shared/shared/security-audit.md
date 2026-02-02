---
name: 安全性審計
description: 檢查專案中的安全性問題與漏洞，包含定期審計與部署前檢查
version: 1.0.0
category: shared
triggers:
  - /security-audit
  - 安全掃描
  - 漏洞檢查
  - security
updated: 2026-01-28
---

# Security Audit Skill

**技能名稱**：安全性審計
**用途**：檢查專案中的安全性問題與漏洞
**適用場景**：定期安全審計、部署前檢查

---

## 執行清單

### 1. 敏感信息掃描

**檢查項目**：

- [ ] `.env` 檔案是否已加入 `.gitignore`
- [ ] 是否有 API Key 硬編碼在程式碼中
- [ ] 是否有密碼硬編碼在配置檔案中
- [ ] SECRET_KEY 長度是否 >= 32 字元
- [ ] 資料庫密碼強度是否足夠（長度 >= 16，複雜度）

**執行命令**：

```bash
# 搜尋可能的敏感信息
grep -r "SECRET_KEY" --include="*.py" --include="*.js" .
grep -r "API_KEY" --include="*.py" --include="*.js" .
grep -r "password" --include="*.env*" .

# 檢查 git 版本庫中的敏感檔案
git ls-files | grep "\.env"
```

### 2. 依賴套件安全性

**後端（Python）**：

```bash
cd backend
pip install pip-audit
pip-audit --desc
```

**前端（JavaScript）**：

```bash
cd frontend
npm audit
npm audit fix  # 自動修復
```

### 3. CORS 配置檢查

**檢查項目**：

- [ ] 生產環境是否使用萬用字元 "\*"
- [ ] CORS origins 是否只包含信任的域名
- [ ] 是否正確配置 credentials

**位置**：

- `backend/app/main.py` - CORSMiddleware 配置
- `.env.production` - CORS_ORIGINS

### 4. 認證與授權

**檢查項目**：

- [ ] JWT 令牌過期時間是否合理（建議 < 1 小時）
- [ ] 是否有臨時調試認證機制（需移除）
- [ ] 敏感 API 端點是否有認證保護
- [ ] 是否實作 refresh token 機制

**位置**：

- `backend/app/auth/security.py`
- `backend/app/core/config.py`

### 5. 輸入驗證

**檢查項目**：

- [ ] 所有 API 端點是否使用 Pydantic 驗證
- [ ] 是否有直接執行 SQL 查詢（SQL 注入風險）
- [ ] 檔案上傳是否有類型與大小限制
- [ ] 前端輸出是否有 XSS 防護

### 6. Debug 端點與日誌

**檢查項目**：

- [ ] 生產環境是否移除 /debug 端點
- [ ] DEBUG 模式是否關閉
- [ ] 日誌是否包含敏感信息
- [ ] 錯誤訊息是否暴露系統內部資訊

**執行命令**：

```bash
# 搜尋 debug 相關端點
grep -r "@app.get.*debug" backend/app/
grep -r "console.log" frontend/src/
```

### 7. HTTP 方法資安規範

**檢查項目**：

- [ ] 後端是否仍有 PUT/DELETE 方法 (應使用 POST + /update, /delete)
- [ ] 前端是否仍有 axios.put/delete 調用
- [ ] 已棄用端點是否標記 deprecated

**自動化檢查 (推薦)**：

```bash
# 使用 pre-commit hook 自動檢查 (2025-12-26 新增)
python backend/scripts/check_http_methods.py
```

**手動檢查**：

```bash
# 後端 PUT/DELETE 檢查
grep -r "@router\.\(put\|delete\)" backend/app/api/v1/

# 前端 PUT/DELETE 檢查
grep -r "\.put\|\.delete" frontend/src/api/

# 統計未遷移端點數量
grep -c "@router\.\(put\|delete\)" backend/app/api/v1/endpoints/**/*.py
```

**Pre-commit Hook** (`.pre-commit-config.yaml`):

```yaml
- id: check-http-methods
  name: 'Check HTTP Method Security'
  entry: python backend/scripts/check_http_methods.py
  language: system
  files: '^frontend/src/(api|services)/.*\.(ts|tsx|js|jsx)$'
```

**參考文檔**：

- `.speckit/api-standards.md` Section 0 - HTTP 方法資安規範
- `claude_plant/HTTP_METHOD_MIGRATION_PLAN.md` - 遷移追蹤

### 8. Request ID 追蹤

**檢查項目**：

- [ ] 後端是否啟用 RequestIdMiddleware
- [ ] 前端 API 客戶端是否發送 X-Request-ID
- [ ] 錯誤日誌是否包含 Request ID

**位置**：

- `backend/app/main.py` - RequestIdMiddleware 配置
- `backend/app/core/logging_config.py` - Request ID 實作
- `frontend/src/api/client.ts` - 前端 Request ID 生成

---

## 自動化審計腳本

```bash
#!/bin/bash
# security-audit.sh

echo "=== 安全性審計開始 ==="

# 1. 檢查敏感檔案
echo "\n[1] 檢查敏感檔案..."
if git ls-files | grep -q "\.env\.production"; then
    echo "❌ 警告：.env.production 存在於 git 版本庫中"
else
    echo "✅ 通過"
fi

# 2. 檢查弱密碼
echo "\n[2] 檢查弱密碼..."
if grep -q "123456" .env.production 2>/dev/null; then
    echo "❌ 警告：發現弱密碼"
else
    echo "✅ 通過"
fi

# 3. 檢查 DEBUG 模式
echo "\n[3] 檢查 DEBUG 模式..."
if grep -q "DEBUG=true" .env.production 2>/dev/null; then
    echo "❌ 警告：生產環境 DEBUG 模式開啟"
else
    echo "✅ 通過"
fi

# 4. 依賴套件審計
echo "\n[4] 依賴套件審計..."
cd backend && pip-audit --desc --exit-code && cd ..
cd frontend && npm audit --audit-level=high && cd ..

# 5. HTTP 方法資安檢查
echo "\n[5] HTTP 方法資安檢查..."
BACKEND_COUNT=$(grep -r "@router\.\(put\|delete\)" backend/app/api/v1/ 2>/dev/null | grep -v "deprecated=True" | wc -l)
FRONTEND_COUNT=$(grep -r "\.put\(.*\)\|\.delete\(" frontend/src/api/ 2>/dev/null | wc -l)
if [ "$BACKEND_COUNT" -gt 0 ] || [ "$FRONTEND_COUNT" -gt 0 ]; then
    echo "⚠️ 警告：發現 $BACKEND_COUNT 個後端 + $FRONTEND_COUNT 個前端未遷移的 PUT/DELETE 調用"
    echo "   參見: claude_plant/HTTP_METHOD_MIGRATION_PLAN.md"
else
    echo "✅ 通過"
fi

echo "\n=== 安全性審計完成 ==="
```

---

## 修復建議

### 立即修復（嚴重）

1. **移除敏感信息**

   ```bash
   git rm --cached .env.production
   git commit -m "security: remove sensitive files"
   ```

2. **重新生成密鑰**

   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

3. **更換弱密碼**
   ```bash
   openssl rand -base64 20
   ```

### 短期修復（高優先級）

4. **移除臨時調試認證**
   - 檔案：`backend/app/auth/security.py`
   - 行動：刪除 `return TokenData(username="debug_user")` 邏輯

5. **移除 debug 端點**
   - 檔案：`backend/app/main.py`
   - 行動：移除 `/debug/routes` 端點或添加認證保護

---

## 定期審計排程

- **每週**：自動化腳本審計
- **每月**：人工全面審計
- **部署前**：必須執行完整審計
- **重大變更後**：針對性審計

---

**建立日期**：2025-10-27
**最後更新**：2025-12-26
