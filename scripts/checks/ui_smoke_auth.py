# -*- coding: utf-8 -*-
"""為 UI 自我檢核簽發臨時 admin session（2026-07-31）

比照 `admin_backup_smoke_test.py` 的既有模式：從 DB 取 admin、插一筆 active
`user_sessions`、用 SECRET_KEY 自簽合法 JWT，再向後端換一枚 csrf_token。

why：UI 檢核必須看「登入後的畫面」，但不該碰 owner 的 session、也不該把
真人密碼放進腳本。此法產生的 session 有效期短（20 分鐘）且可辨識（jti 前綴
`ui-smoke-`），事後可安全清除。

輸出（供 ui_flow_smoke.cjs 使用）：
    COOKIE=access_token=...; csrf_token=...
    USER_INFO={...}

用法（容器內執行，因為要連 DB 與讀 SECRET_KEY）：
    docker exec ck_missive_backend python /app/scripts/checks/ui_smoke_auth.py
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

for _cand in (Path("/app"), Path(__file__).resolve().parents[2] / "backend"):
    if (_cand / "app" / "db" / "database.py").exists():
        sys.path.insert(0, str(_cand))
        break

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SESSION_MINUTES = 20
JTI_PREFIX = "ui-smoke-"


async def main() -> None:
    import jwt as pyjwt
    from sqlalchemy import select, text

    from app.core.config import settings
    from app.db.database import AsyncSessionLocal
    from app.extended.models import User

    async with AsyncSessionLocal() as db:
        admin = (await db.execute(
            select(User).where(User.is_admin.is_(True)).order_by(User.id)
        )).scalars().first()
        if not admin:
            raise SystemExit("ERROR: DB 內沒有 admin 使用者")

        jti = f"{JTI_PREFIX}{uuid.uuid4().hex[:12]}"
        expires = datetime.utcnow() + timedelta(minutes=SESSION_MINUTES)
        await db.execute(
            text(
                "INSERT INTO user_sessions (user_id, token_jti, is_active, expires_at, created_at) "
                "VALUES (:u, :j, true, :e, NOW())"
            ),
            {"u": admin.id, "j": jti, "e": expires},
        )
        await db.commit()

        token = pyjwt.encode(
            {
                "sub": str(admin.id), "email": admin.email, "jti": jti,
                "exp": expires, "iat": datetime.utcnow(), "type": "access",
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        if isinstance(token, bytes):
            token = token.decode()

        # 換 csrf_token —— 前端所有 API 皆為 POST，缺此 cookie 會滿頁 CSRF 錯誤
        csrf = ""
        try:
            import httpx
            base = os.getenv("MISSIVE_INTERNAL_URL", "http://localhost:8001")
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{base}/api/secure-site-management/csrf-token",
                    cookies={"access_token": token},
                )
                if r.status_code == 200:
                    csrf = r.json().get("csrf_token", "")
        except Exception as e:  # noqa: BLE001
            print(f"# WARN 取得 csrf_token 失敗（部分檢查可能受影響）: {e}", file=sys.stderr)

        cookie = f"access_token={token}"
        if csrf:
            cookie += f"; csrf_token={csrf}"

        print("COOKIE=" + cookie)
        print("USER_INFO=" + json.dumps({
            "id": admin.id, "email": admin.email, "username": admin.username,
            "is_admin": True, "is_superuser": bool(admin.is_superuser),
            "role": admin.role,
        }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
