# Security Hardening Skill - 安全加固指南

> **版本**: 1.0.0
> **觸發關鍵字**: 安全, security, 防護, 漏洞, vulnerability, XSS, SQL injection
> **更新日期**: 2026-01-15

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

## 安全檢查清單

### 每次部署前
- [ ] 環境變數已正確設定
- [ ] DEBUG 模式已關閉
- [ ] CORS 只允許必要的來源
- [ ] 所有敏感端點都需要認證
- [ ] Rate limiting 已啟用

### 程式碼審查時
- [ ] 無硬編碼的密鑰或密碼
- [ ] 使用參數化查詢，無 SQL 拼接
- [ ] 輸入都經過驗證和清理
- [ ] 敏感資料不暴露在日誌或回應中
- [ ] 檔案上傳有類型和大小限制

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
