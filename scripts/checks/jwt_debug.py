"""Debug JWT sign + decode inside container"""
import sys
sys.path.insert(0, "/app")
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

payload = {
    "sub": "1",
    "email": "admin@example.com",
    "exp": datetime.utcnow() + timedelta(minutes=15),
    "iat": datetime.utcnow(),
    "jti": "test-jti",
}
token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
print(f"signed token: {token[:100]}")

try:
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    print(f"decoded OK: sub={decoded.get('sub')} email={decoded.get('email')}")
except Exception as e:
    print(f"decode FAIL: {type(e).__name__}: {e}")

from app.core.auth_service import AuthService
result = AuthService.verify_token(token)
print(f"AuthService.verify_token result: {result}")
