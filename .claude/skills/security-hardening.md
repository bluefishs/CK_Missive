# Security Hardening Skill - 安全加固指南

> **版本**: 2.0.0
> **觸發關鍵字**: 安全, security, 防護, 漏洞, vulnerability, XSS, SQL injection, refresh token, idle timeout
> **更新日期**: 2026-02-07

---

## 概述

本 Skill 提供 CK_Missive 專案的安全加固最佳實踐，涵蓋 OWASP Top 10 防護策略。

---

## 認證與授權

### 1. JWT Token 安全

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # JWT 設定
    JWT_SECRET_KEY: str = Field(..., description="必須為強密碼")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 禁止在程式碼中硬編碼
    # ❌ JWT_SECRET_KEY: str = "my-secret-key"
```

### 2. 密碼安全

```python
from passlib.context import CryptContext

# 使用 bcrypt (成本因子 12)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 密碼強度要求
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_NUMBER = True
PASSWORD_REQUIRE_SPECIAL = True
```

### 3. 角色權限檢查

```python
from functools import wraps
from fastapi import Depends, HTTPException, status

def require_role(allowed_roles: list[str]):
    """角色檢查裝飾器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in allowed_roles and not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="權限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# 使用
@router.delete("/users/{user_id}")
@require_role(["admin", "superuser"])
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    ...
```

---

## 輸入驗證與清理

### 1. Pydantic Schema 驗證

```python
from pydantic import BaseModel, Field, validator, EmailStr
import re

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(..., min_length=8)

    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('密碼必須包含大寫字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密碼必須包含數字')
        if not re.search(r'[!@#$%^&*]', v):
            raise ValueError('密碼必須包含特殊字元')
        return v
```

### 2. SQL Injection 防護

```python
# ✅ 正確 - 使用參數化查詢 (SQLAlchemy ORM)
from sqlalchemy import select

stmt = select(Document).where(Document.id == document_id)
result = await db.execute(stmt)

# ✅ 正確 - 使用 text() 與參數
from sqlalchemy import text

stmt = text("SELECT * FROM documents WHERE id = :id")
result = await db.execute(stmt, {"id": document_id})

# ❌ 錯誤 - 字串拼接 (SQL Injection 漏洞)
query = f"SELECT * FROM documents WHERE id = {document_id}"
```

### 3. XSS 防護

```typescript
// 前端 - React 自動轉義
// ✅ 安全 - JSX 自動轉義
<div>{userInput}</div>

// ❌ 危險 - dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// 如果必須使用 HTML，先清理
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

---

## API 安全

### 1. Rate Limiting

```python
# backend/app/core/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 使用
@router.post("/login")
@limiter.limit("5/minute")  # 每分鐘最多 5 次
async def login(request: Request, ...):
    ...
```

### 2. CORS 設定

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 不要用 ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ❌ 危險 - 允許所有來源
allow_origins=["*"]

# ✅ 安全 - 明確指定來源
allow_origins=["https://yourdomain.com", "http://localhost:3000"]
```

### 3. POST-only 敏感端點

```python
# ❌ 危險 - GET 請求可被 CSRF 攻擊
@router.get("/auth/me")
async def get_current_user():
    ...

# ✅ 安全 - POST-only
@router.post("/auth/me")
async def get_current_user():
    ...
```

---

## 敏感資料保護

### 1. 環境變數

```bash
# .env (永不提交到版本控制)
JWT_SECRET_KEY=超強密碼至少32字元
DATABASE_URL=postgresql://user:password@localhost/db
GOOGLE_CLIENT_SECRET=xxx

# .gitignore
.env
.env.local
*.pem
*.key
credentials.json
```

### 2. 日誌脫敏

```python
import logging

class SensitiveFilter(logging.Filter):
    """過濾敏感資訊"""
    SENSITIVE_PATTERNS = ['password', 'token', 'secret', 'credential']

    def filter(self, record):
        message = record.getMessage()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message.lower():
                record.msg = "[REDACTED - contains sensitive data]"
        return True

# 應用過濾器
logger.addFilter(SensitiveFilter())
```

### 3. 回應資料過濾

```python
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    # 不包含敏感欄位
    # ❌ password_hash: str
    # ❌ google_id: str

    class Config:
        from_attributes = True
```

---

## 檔案上傳安全

### 1. 檔案類型驗證

```python
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_upload(file: UploadFile):
    # 檢查副檔名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不允許的檔案類型: {ext}")

    # 檢查檔案大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "檔案大小超過限制")

    # 重置檔案指標
    await file.seek(0)

    # 檢查 MIME type (magic bytes)
    import magic
    mime = magic.from_buffer(content, mime=True)
    if mime not in ['application/pdf', 'image/jpeg', 'image/png']:
        raise HTTPException(400, "檔案內容與副檔名不符")
```

### 2. 安全的檔案儲存

```python
import uuid
from pathlib import Path

def get_safe_filename(original_filename: str) -> str:
    """生成安全的檔案名稱"""
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4()}{ext}"

# 不要直接使用用戶提供的檔名
# ❌ 危險
save_path = f"/uploads/{file.filename}"

# ✅ 安全
safe_name = get_safe_filename(file.filename)
save_path = f"/uploads/{safe_name}"
```

---

## Refresh Token Rotation (v2.0.0)

### 機制說明

每次 token refresh 操作會使舊 session 失效並簽發新的 token pair，防止 token 被重播攻擊利用。

### 核心實作

```python
# backend/app/core/auth.py

async def refresh_access_token(refresh_token: str, db: AsyncSession) -> TokenResponse:
    """
    Refresh token rotation 流程：
    1. 驗證 refresh token
    2. SELECT FOR UPDATE 鎖定 session 行（防止並行 race condition）
    3. 撤銷舊 session
    4. 簽發新的 access + refresh token
    5. 建立新 session 記錄
    """
    # 使用 SELECT FOR UPDATE 防止並行刷新 race condition
    stmt = select(UserSession).where(
        UserSession.refresh_token == refresh_token
    ).with_for_update()
    session = await db.execute(stmt)

    # Token 重播偵測：若 token 已被撤銷，代表可能被竊取
    if session.is_revoked:
        # 撤銷該用戶的所有 session
        await revoke_all_user_sessions(session.user_id, db)
        raise HTTPException(401, "Token replay detected, all sessions revoked")

    # 撤銷當前 session
    session.is_revoked = True
    await db.flush()

    # 簽發新 token pair
    return await generate_login_response(user, db, is_refresh=True)
```

### 關鍵設計

| 項目 | 說明 |
|------|------|
| `SELECT FOR UPDATE` | 防止兩個並行 refresh 請求同時使用同一個 token |
| Token 重播偵測 | 已撤銷的 refresh token 被重用時，撤銷該用戶所有 session |
| `is_refresh=True` | refresh 操作不增加 `login_count`，避免統計失真 |
| 舊 session 失效 | 每次 refresh 舊的 refresh token 立即標記為 revoked |

---

## 密碼安全強化 (v2.0.0)

### 移除明文密碼 Fallback

```python
# ❌ 舊版 - 有明文密碼 fallback（已移除）
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # 危險：允許明文比對
        return plain_password == hashed_password

# ✅ v2.0.0 - bcrypt 失敗直接回傳 False
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # 只記錄異常類型，不記錄詳細訊息（避免洩露密碼資訊）
        logger.warning(f"Password verification error: {type(e).__name__}")
        return False
```

### 日誌脫敏強化

```python
# ❌ 危險 - 記錄完整異常訊息（可能含密碼片段）
logger.error(f"Auth failed: {str(e)}")

# ✅ 安全 - 只記錄異常類型
logger.warning(f"Password verification error: {type(e).__name__}")
```

---

## Session 安全 (v2.0.0)

### 1. 閒置逾時 (Idle Timeout)

```typescript
// frontend/src/hooks/useIdleTimeout.ts

/**
 * 30 分鐘無操作自動登出
 * 監聽事件：mousemove, mousedown, keypress, scroll, touchstart
 */
export function useIdleTimeout(timeoutMs: number = 30 * 60 * 1000) {
    useEffect(() => {
        let timer: NodeJS.Timeout;

        const resetTimer = () => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                authStore.logout();
                navigate('/login', { state: { reason: 'idle_timeout' } });
            }, timeoutMs);
        };

        const events = ['mousemove', 'mousedown', 'keypress', 'scroll', 'touchstart'];
        events.forEach(event => window.addEventListener(event, resetTimer));
        resetTimer();

        return () => {
            clearTimeout(timer);
            events.forEach(event => window.removeEventListener(event, resetTimer));
        };
    }, [timeoutMs]);
}
```

### 2. 跨分頁同步 (Cross-Tab Sync)

```typescript
// 監聽 storage 事件，偵測其他分頁的登出或 token 變更
useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
        if (event.key === 'auth_token' && event.newValue === null) {
            // 其他分頁已登出，同步登出本分頁
            authStore.logout();
            navigate('/login');
        }
        if (event.key === 'auth_token' && event.newValue !== event.oldValue) {
            // Token 已在其他分頁刷新，同步更新
            authStore.setToken(event.newValue);
        }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
}, []);
```

### 3. 啟動時 Token 驗證

```typescript
// ProtectedRoute 首次載入時驗證 token 有效性
const [startupValidated, setStartupValidated] = useState(false);

useEffect(() => {
    if (!startupValidated) {
        // 向 /auth/me 發送請求驗證 token
        authApi.getCurrentUser()
            .then(() => setStartupValidated(true))
            .catch(() => {
                authStore.logout();
                navigate('/login');
            });
    }
}, []);

// _startupValidated 在登出時重置，支援多用戶情境
const logout = () => {
    clearTokens();
    setStartupValidated(false);  // 下次登入會重新驗證
};
```

---

## Public Endpoint 加固 (v2.0.0)

### 資訊洩露修復

```python
# ❌ 舊版 - /public/system-info 暴露內部設定
@router.get("/public/system-info")
async def system_info():
    return {
        "version": settings.VERSION,
        "auth_disabled": settings.AUTH_DISABLED,  # 洩露認證狀態
        "debug": settings.DEBUG,                   # 洩露 debug 模式
    }

# ✅ v2.0.0 - 只回傳必要的公開資訊
@router.get("/public/system-info")
async def system_info():
    return {
        "version": settings.VERSION,
        "app_name": settings.APP_NAME,
    }
```

```python
# ❌ 舊版 - /public/calendar-status 暴露檔案系統路徑
@router.get("/public/calendar-status")
async def calendar_status():
    return {
        "enabled": settings.CALENDAR_ENABLED,
        "credentials_file": settings.GOOGLE_CREDENTIALS_FILE,  # 洩露路徑
    }

# ✅ v2.0.0 - 移除檔案路徑
@router.get("/public/calendar-status")
async def calendar_status():
    return {
        "enabled": settings.CALENDAR_ENABLED,
        "configured": bool(settings.GOOGLE_CREDENTIALS_FILE),  # 只回傳是否已設定
    }
```

### 診斷路由權限提升

以下 4 個診斷路由從公開改為需要 admin 角色：

| 路由 | 說明 | 變更 |
|------|------|------|
| `API_MAPPING` | API 映射表 | public -> admin |
| `API_DOCS` | API 文件 | public -> admin |
| `UNIFIED_FORM_DEMO` | 表單 Demo | public -> admin |
| `GOOGLE_AUTH_DIAGNOSTIC` | OAuth 診斷 | public -> admin |

```python
# ✅ 診斷路由需要 admin 權限
@router.get("/admin/api-mapping")
async def api_mapping(current_user: User = Depends(require_admin)):
    ...
```

---

## SECRET_KEY 強制檢查 (v2.0.0)

### 生產環境啟動保護

```python
# backend/app/core/config.py

def validate_secret_key(self):
    """生產環境禁止使用自動生成的 SECRET_KEY"""
    is_dev = self.DEVELOPMENT_MODE.lower() in ('true', '1', 'yes')

    if not is_dev and self.JWT_SECRET_KEY.startswith('dev_only_'):
        raise RuntimeError(
            "CRITICAL: Production environment cannot use auto-generated SECRET_KEY. "
            "Set a fixed JWT_SECRET_KEY in .env to prevent token invalidation on restart."
        )

    if is_dev and self.JWT_SECRET_KEY.startswith('dev_only_'):
        logger.warning(
            "Using auto-generated SECRET_KEY. "
            "All tokens will be invalidated on server restart. "
            "Set JWT_SECRET_KEY in .env for persistent sessions."
        )
```

### 設定要求

```bash
# .env (生產環境必須設定)
JWT_SECRET_KEY=<至少 32 字元的強密碼，不可以 dev_only_ 開頭>
DEVELOPMENT_MODE=false
```

---

## 安全檢查清單

### 每次部署前
- [ ] 環境變數已正確設定
- [ ] DEBUG 模式已關閉
- [ ] CORS 只允許必要的來源
- [ ] 所有敏感端點都需要認證
- [ ] Rate limiting 已啟用
- [ ] SECRET_KEY 已固定於 .env（非自動生成）

### 程式碼審查時
- [ ] 無硬編碼的密鑰或密碼
- [ ] 使用參數化查詢，無 SQL 拼接
- [ ] 輸入都經過驗證和清理
- [ ] 敏感資料不暴露在日誌或回應中
- [ ] 檔案上傳有類型和大小限制

### 認證與 Session 安全 (v2.0.0 新增)
- [ ] Refresh token rotation 已實作（無 token 重用）
- [ ] `SELECT FOR UPDATE` 用於並行敏感的 DB 操作
- [ ] 無明文密碼 fallback
- [ ] Public endpoints 不暴露內部設定
- [ ] 診斷頁面需要 admin 認證
- [ ] 閒置逾時已啟用於認證頁面
- [ ] 跨分頁 auth 同步已啟用
- [ ] SECRET_KEY 已固定於生產 .env

### 定期檢查
- [ ] 執行 `/security-audit` 指令
- [ ] 檢查依賴套件的安全更新
- [ ] 審查存取日誌中的異常模式
- [ ] 測試認證和授權機制

---

## 參考資源

- **資安審計指令**: `.claude/commands/security-audit.md`
- **OWASP Top 10**: https://owasp.org/Top10/
- **安全模式 (共享)**: `.claude/skills/_shared/shared/security-patterns.md`
