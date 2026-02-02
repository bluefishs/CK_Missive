# A05 - 注入攻擊防護模式

> **OWASP 類別**: A05:2025 – Injection
> **嚴重性**: Critical
> **適用技術**: SQL, NoSQL, LDAP, OS Command, XSS

---

## 常見漏洞

| 漏洞類型          | 說明             | 影響                |
| ----------------- | ---------------- | ------------------- |
| SQL Injection     | SQL 語句被篡改   | 資料庫洩漏/刪除     |
| XSS               | 惡意腳本注入網頁 | 竊取 Cookie/Session |
| Command Injection | 系統命令被執行   | 完全控制伺服器      |
| LDAP Injection    | LDAP 查詢被篡改  | 繞過認證            |
| Path Traversal    | 檔案路徑被篡改   | 讀取敏感檔案        |

---

## 安全模式

### 1. SQL Injection 防護

```python
# ❌ 危險：字串拼接
async def get_user_by_name(name: str, db: AsyncSession):
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return await db.execute(text(query))

# 攻擊範例: name = "'; DROP TABLE users; --"

# ✅ 正確：使用 ORM
from sqlalchemy import select

async def get_user_by_name(name: str, db: AsyncSession):
    stmt = select(User).where(User.name == name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ✅ 正確：使用參數化查詢
from sqlalchemy import text

async def get_user_by_name(name: str, db: AsyncSession):
    stmt = text("SELECT * FROM users WHERE name = :name")
    result = await db.execute(stmt, {"name": name})
    return result.fetchone()
```

### 2. NoSQL Injection 防護 (MongoDB)

```python
# ❌ 危險：直接使用用戶輸入
async def find_user(username: str):
    return await db.users.find_one({"username": username})

# 攻擊範例: username = {"$ne": null}  # 返回所有用戶

# ✅ 正確：類型檢查
async def find_user(username: str):
    if not isinstance(username, str):
        raise ValueError("Username must be string")
    return await db.users.find_one({"username": username})

# ✅ 正確：使用 Pydantic 驗證
from pydantic import BaseModel, Field

class UserQuery(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')

async def find_user(query: UserQuery):
    return await db.users.find_one({"username": query.username})
```

### 3. XSS 防護

```typescript
// ❌ 危險：直接渲染 HTML
const Comment = ({ content }: { content: string }) => {
  return <div dangerouslySetInnerHTML={{ __html: content }} />;
};

// ✅ 正確：React 自動轉義
const Comment = ({ content }: { content: string }) => {
  return <div>{content}</div>;  // 安全：< > & 等字元會被轉義
};

// ✅ 如果必須渲染 HTML，使用 DOMPurify
import DOMPurify from 'dompurify';

const SafeHTML = ({ html }: { html: string }) => {
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href', 'target']
  });
  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
};
```

```python
# 後端輸出轉義
from markupsafe import escape

@router.post("/comments")
async def create_comment(content: str):
    # 儲存前轉義
    safe_content = escape(content)
    return await save_comment(safe_content)
```

### 4. Command Injection 防護

```python
# ❌ 極度危險：shell=True + 字串拼接
import subprocess

def process_file(filename: str):
    subprocess.run(f"cat {filename}", shell=True)  # 可執行任意命令

# 攻擊範例: filename = "file.txt; rm -rf /"

# ✅ 正確：使用列表參數 + shell=False
def process_file(filename: str):
    # 驗證檔名
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
        raise ValueError("Invalid filename")

    subprocess.run(["cat", filename], shell=False)

# ✅ 更好：使用 Python 原生方法
def read_file(filename: str):
    allowed_path = Path("/safe/directory")
    file_path = (allowed_path / filename).resolve()

    # 確保在允許的目錄內
    if not str(file_path).startswith(str(allowed_path)):
        raise ValueError("Path traversal detected")

    return file_path.read_text()
```

### 5. Path Traversal 防護

```python
# ❌ 危險：直接使用用戶輸入
@router.post("/files/{filename}")
async def get_file(filename: str):
    return FileResponse(f"/uploads/{filename}")

# 攻擊範例: filename = "../../../etc/passwd"

# ✅ 正確：路徑驗證
from pathlib import Path

UPLOAD_DIR = Path("/uploads").resolve()

@router.post("/files/{filename}")
async def get_file(filename: str):
    # 構建完整路徑
    file_path = (UPLOAD_DIR / filename).resolve()

    # 驗證路徑在允許目錄內
    if not str(file_path).startswith(str(UPLOAD_DIR)):
        raise HTTPException(403, "Access denied")

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path)
```

### 6. LDAP Injection 防護

```python
# ❌ 危險：字串拼接
def authenticate(username: str, password: str):
    filter_str = f"(uid={username})"
    result = ldap.search(filter_str)

# 攻擊範例: username = "*)(uid=*))(|(uid=*"

# ✅ 正確：轉義特殊字元
import ldap

def escape_ldap(value: str) -> str:
    """轉義 LDAP 特殊字元"""
    chars = ['\\', '*', '(', ')', '\0']
    for char in chars:
        value = value.replace(char, f'\\{char}')
    return value

def authenticate(username: str, password: str):
    safe_username = escape_ldap(username)
    filter_str = f"(uid={safe_username})"
    result = ldap.search(filter_str)
```

---

## 輸入驗證通用模式

```python
# backend/app/core/validators.py
import re
from pydantic import validator

class SafeString:
    """安全字串驗證器"""

    # 預定義的安全模式
    PATTERNS = {
        'alphanumeric': r'^[a-zA-Z0-9]+$',
        'username': r'^[a-zA-Z0-9_]{3,30}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'filename': r'^[a-zA-Z0-9_.-]{1,255}$',
        'uuid': r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
    }

    @classmethod
    def validate(cls, value: str, pattern_name: str) -> str:
        pattern = cls.PATTERNS.get(pattern_name)
        if not pattern:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        if not re.match(pattern, value):
            raise ValueError(f"Invalid {pattern_name} format")

        return value


# 使用範例
from pydantic import BaseModel, field_validator

class UserCreate(BaseModel):
    username: str
    email: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return SafeString.validate(v, 'username')

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return SafeString.validate(v, 'email')
```

---

## 檢查清單

- [ ] 所有 SQL 查詢使用 ORM 或參數化查詢
- [ ] 前端使用 React 自動轉義，必要時用 DOMPurify
- [ ] 後端輸出進行 HTML 轉義
- [ ] 禁止使用 shell=True 執行命令
- [ ] 檔案路徑驗證防止 Path Traversal
- [ ] 所有用戶輸入經過 Pydantic 驗證
- [ ] 使用白名單而非黑名單驗證

---

## 自動化檢測

```bash
# 搜尋潛在的 SQL Injection
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" backend/

# 搜尋潛在的 XSS
grep -rn "dangerouslySetInnerHTML" frontend/src/

# 搜尋潛在的 Command Injection
grep -rn "subprocess.*shell=True\|os.system\|os.popen" backend/
```

---

## 相關資源

- [OWASP Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)
- [DOMPurify](https://github.com/cure53/DOMPurify)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)
