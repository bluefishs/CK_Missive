# /security-audit - 資安審計檢查

> **版本**: 1.0.0
> **建立日期**: 2026-01-15
> **用途**: 自動化資安合規檢查

---

## 執行項目

執行此指令時，請依序完成以下資安檢查：

### 1. POST-only API 合規性檢查

```bash
# 搜尋後端仍使用 GET 方法的業務端點
grep -rn "@router.get" backend/app/api/endpoints/ --include="*.py" | grep -v "health\|debug\|public\|monitoring"
```

**檢查標準**:
- ✅ 所有業務查詢 API 必須使用 POST 方法
- 🟡 例外: `/health/*`, `/debug/*`, `/public/*`, `/monitoring/*`

### 2. 敏感資料曝露檢查

```bash
# 檢查是否有硬編碼的密鑰或密碼
grep -rn "password\|secret\|api_key\|token" --include="*.py" --include="*.ts" --include="*.tsx" | grep -v ".env\|test\|mock\|example"
```

**檢查項目**:
- [ ] 密碼未硬編碼在程式碼中
- [ ] API 金鑰使用環境變數
- [ ] JWT Secret 未使用預設值
- [ ] 資料庫連線字串在 .env 中

### 3. SQL 注入風險掃描

```bash
# 搜尋可能的 SQL 注入風險
grep -rn "execute\|raw\|text(" backend/app/ --include="*.py" | grep -v "alembic"
```

**檢查標準**:
- ✅ 使用 SQLAlchemy ORM 進行查詢
- ❌ 禁止使用 `execute(text(f"..."))` 拼接用戶輸入
- ✅ 參數化查詢: `execute(text("SELECT * FROM x WHERE id = :id"), {"id": value})`

### 4. 認證配置驗證

**後端檢查** (`backend/.env`):
```
JWT_SECRET_KEY=<必須是隨機生成的強密鑰>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=<建議 30-60>
```

**前端檢查** (`frontend/src/config/env.ts`):
- [ ] `isAuthDisabled()` 僅在開發環境返回 true
- [ ] 內網 IP 判斷邏輯正確
- [ ] Google OAuth Client ID 已配置

### 5. CORS 配置檢查

```python
# backend/app/core/cors.py 或 main.py
# 生產環境應限制 origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://192.168.50.210:3000",
    # 不應包含 "*"
]
```

### 6. 檔案上傳安全

**檢查項目**:
- [ ] 檔案類型白名單驗證
- [ ] 檔案大小限制
- [ ] 檔案名稱消毒 (sanitize)
- [ ] 上傳目錄不可執行

### 7. 環境變數檢查

```bash
# 確認敏感檔案不在版本控制中
cat .gitignore | grep -E "\.env|credentials|secret"
```

**必須忽略**:
- `.env`
- `.env.local`
- `.env.production`
- `credentials.json`
- `*secret*`

---

## 輸出格式

執行完成後，輸出資安審計報告：

```markdown
## 資安審計報告 - [日期]

### 檢查結果摘要

| 項目 | 狀態 | 說明 |
|------|------|------|
| POST-only 合規 | ✅/❌ | 業務 API 遷移狀態 |
| 敏感資料保護 | ✅/❌ | 硬編碼密鑰檢查 |
| SQL 注入防護 | ✅/❌ | ORM 使用狀況 |
| 認證配置 | ✅/❌ | JWT 設定安全性 |
| CORS 配置 | ✅/❌ | 跨域設定安全性 |
| 檔案上傳 | ✅/❌ | 上傳安全措施 |
| 環境變數 | ✅/❌ | .gitignore 設定 |

### 發現問題

[列出需要修正的項目]

### 建議措施

[提供修正建議]
```

---

## 自動化腳本

可搭配 PowerShell 腳本執行：

```powershell
# .claude/hooks/security-audit.ps1
# 執行自動化資安掃描
```

---

## 相關文件

- `.claude/MANDATORY_CHECKLIST.md` - 強制性開發檢查清單
- `docs/PRODUCTION_SECURITY_CHECKLIST.md` - 生產環境安全清單
- `docs/specifications/API_ENDPOINT_CONSISTENCY.md` - API 端點一致性規範

---

*此指令為 P0 優先級資安措施的一部分*
