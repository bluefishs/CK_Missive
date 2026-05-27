#!/usr/bin/env python3
"""
Admin Backup Smoke Test (L49 配套 — owner 要求「自我瀏覽器複查」)

在 backend container 內：
1. 從 DB 撈 admin user
2. Sign 合法 JWT
3. 逐一打 backup / files / auth 關鍵 endpoint
4. 對照預期報告 PASS / FAIL

執行：
  docker exec ck_missive_backend python scripts/checks/admin_backup_smoke_test.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

import httpx
from jose import jwt
from sqlalchemy import select

# 確保能 import app.*
sys.path.insert(0, "/app")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


async def get_admin_jwt() -> tuple[str, dict]:
    """從 DB 撈 admin 的 active session 用其 jti 簽合法 token
    （backend get_current_user_from_token 會驗 user_sessions 表 jti 必須 active）"""
    from app.db.database import AsyncSessionLocal
    from app.extended.models import User
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        # 找 admin user
        result = await db.execute(
            select(User).where(User.is_admin.is_(True)).order_by(User.id)
        )
        admin = result.scalars().first()
        if not admin:
            raise SystemExit("ERROR: no admin user in DB")

        # 撈該 admin 最新的 active session jti
        session_q = await db.execute(
            text("""
                SELECT token_jti, expires_at FROM user_sessions
                WHERE user_id = :uid AND is_active = true AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """),
            {"uid": admin.id}
        )
        session_row = session_q.fetchone()

        if not session_row:
            # 沒有 active session — 插一筆新的給 smoke test 用
            import uuid
            new_jti = f"smoke-test-{uuid.uuid4().hex[:12]}"
            expires = datetime.utcnow() + timedelta(minutes=15)
            await db.execute(
                text("""
                    INSERT INTO user_sessions (
                        user_id, token_jti, is_active, expires_at, created_at
                    ) VALUES (
                        :uid, :jti, true, :exp, NOW()
                    )
                """),
                {"uid": admin.id, "jti": new_jti, "exp": expires}
            )
            await db.commit()
            jti = new_jti
            print(f"[setup] inserted new user_sessions row jti={jti[:20]}...")
        else:
            jti = session_row.token_jti
            print(f"[setup] using existing active session jti={jti[:20]}...")

        secret = os.environ.get("SECRET_KEY", "")
        if not secret:
            from app.core.config import settings
            secret = settings.SECRET_KEY
        if not secret:
            raise SystemExit("ERROR: SECRET_KEY env missing")

        now = datetime.utcnow()
        payload = {
            "sub": str(admin.id),
            "email": admin.email,
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "jti": jti,  # 對應 user_sessions 真實 row
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token, {"id": admin.id, "email": admin.email, "role": getattr(admin, "role", "?")}


async def call(client: httpx.AsyncClient, method: str, path: str, jwt_tok: str, body=None) -> tuple[int, str, int]:
    """Returns (status_code, FULL_body, body_size_bytes) — 不再 truncate（validator 需 parse 完整 JSON）"""
    headers = {
        "Authorization": f"Bearer {jwt_tok}",
        "Content-Type": "application/json",
    }
    try:
        if method == "POST":
            r = await client.post(f"http://localhost:8001{path}", headers=headers, json=body or {})
        else:
            r = await client.get(f"http://localhost:8001{path}", headers=headers)
        body_text = r.text
        return r.status_code, body_text, len(body_text)
    except Exception as e:
        return -1, f"EXCEPTION: {type(e).__name__}: {e!r}", 0


async def main():
    print("=" * 78)
    print("Admin Backup Smoke Test (L49 配套)")
    print("=" * 78)
    print()

    token, admin = await get_admin_jwt()
    print(f"Admin JWT signed for: id={admin['id']} email={admin['email']} role={admin['role']}")
    print(f"Token length: {len(token)}")
    print()

    test_cases = [
        # (label, expected_status, method, path, body, validator)
        ("auth/me",                200, "POST", "/api/auth/me", {}, None),
        ("backup/environment-status", 200, "POST", "/api/backup/environment-status", {},
         lambda j: j.get("pg_dump_available") is True or j.get("docker_available") is True),
        ("backup/list",            200, "POST", "/api/backup/list", {},
         lambda j: j.get("statistics", {}).get("database_backup_count", 0) >= 1),
        ("backup/status",          200, "POST", "/api/backup/status", {},
         lambda j: j.get("status") == "active"),
        ("backup/config",          200, "POST", "/api/backup/config", {},
         lambda j: "backup_directory" in j),
        ("backup/scheduler/status", 200, "POST", "/api/backup/scheduler/status", {},
         lambda j: j.get("running") is True),
        ("backup/remote-config",   200, "POST", "/api/backup/remote-config", {},
         lambda j: "sync_enabled" in j),
        ("backup/logs",            200, "POST", "/api/backup/logs", {"limit": 5}, None),
        ("files/storage-info",     200, "POST", "/api/files/storage-info", {},
         lambda j: "total_files" in j),
        ("files/1263/download",    200, "POST", "/api/files/1263/download", {},
         lambda body_or_dict: True),  # binary response — just check 200
    ]

    pass_n = 0
    fail_n = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        for idx, (label, exp_status, method, path, body, validator) in enumerate(test_cases):
            # L49 smoke: 每個 backup/* endpoint 都 `@limiter.limit("5/minute")` —
            # 9 個 backup hits 連續打會撞 limit。每兩個 hit 之間隔 1 秒避免 429。
            if idx > 0:
                await asyncio.sleep(1.2)

            status, body_text, size = await call(client, method, path, token, body)

            status_ok = status == exp_status
            data_ok = True
            data_note = ""

            if status_ok and validator and status == 200:
                try:
                    if path.endswith("/download"):
                        # binary blob — just check non-empty
                        data_ok = size > 1000
                        data_note = f"body_size={size}b"
                    else:
                        parsed = json.loads(body_text) if body_text.strip() else {}
                        data_ok = bool(validator(parsed))
                        data_note = f"validator_pass={data_ok}"
                except Exception as e:
                    data_ok = False
                    data_note = f"validator_err: {type(e).__name__}: {e}"

            ok = status_ok and data_ok
            mark = "✅ PASS" if ok else "❌ FAIL"
            if ok:
                pass_n += 1
            else:
                fail_n += 1

            print(f"{mark}  {label:30s} status={status:4d} (expect {exp_status})  {data_note}")
            if not ok:
                print(f"        body: {body_text[:200]}")

    print()
    print("=" * 78)
    print(f"RESULT: {pass_n} PASS / {fail_n} FAIL")
    print("=" * 78)
    sys.exit(0 if fail_n == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
