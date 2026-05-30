"""cron 真活快照 — 透過 /health/scheduler 取 SchedulerTracker + APScheduler 合併狀態

執行：
  docker exec ck_missive_backend python scripts/checks/cron_liveness_snapshot.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")


async def main() -> int:
    from jose import jwt
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.extended.models import User
    from app.extended.models.system import UserSession
    from app.core.config import settings
    import httpx

    async with AsyncSessionLocal() as db:
        admin = (
            await db.execute(select(User).where(User.role == "admin").limit(1))
        ).scalar_one_or_none()
        if not admin:
            print("NO_ADMIN")
            return 1
        sess = (
            await db.execute(
                select(UserSession)
                .where(UserSession.user_id == admin.id, UserSession.revoked_at.is_(None))
                .limit(1)
            )
        ).scalar_one_or_none()
        if not sess:
            print("NO_SESSION")
            return 1
        now = datetime.utcnow()
        token = jwt.encode(
            {
                "sub": str(admin.id),
                "email": admin.email,
                "exp": now + timedelta(minutes=5),
                "iat": now,
                "jti": sess.token_jti,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    async with httpx.AsyncClient() as cli:
        r = await cli.get(
            "http://localhost:8001/api/health/scheduler",
            headers={"Authorization": f"Bearer {token}"},
        )
    if r.status_code != 200:
        print(f"STATUS {r.status_code}: {r.text[:200]}")
        return 1
    raw = r.text
    if not raw.strip():
        print(f"EMPTY BODY (content-length={r.headers.get('content-length')})")
        print(f"headers: {dict(r.headers)}")
        return 1
    try:
        data = r.json()
    except Exception:
        print(f"NON-JSON ({len(raw)} chars): {raw[:300]}")
        return 1
    print(
        f"running={data.get('scheduler_running')} "
        f"total={data.get('total_jobs')} "
        f"healthy={data.get('healthy')} "
        f"failed={data.get('failed')} "
        f"never_run={data.get('never_run')}"
    )
    print()
    jobs = sorted(data.get("jobs", []), key=lambda x: x.get("id", ""))
    h_icon, h_id, h_last, h_next, h_sf = "Icon", "JobID", "LastRun", "NextRun", "S/F"
    print(f"{h_icon:5} {h_id:38} {h_last:19} {h_next:19} {h_sf}")
    print("-" * 100)
    never_run_jobs = []
    for j in jobs:
        jid = j.get("id", "?")[:38]
        last = (j.get("last_run") or "NEVER")[:19]
        nxt = (j.get("next_run_time") or "NEVER")[:19]
        stat = j.get("last_status") or "-"
        succ = j.get("success_count", 0)
        fail = j.get("failure_count", 0)
        if stat == "success":
            icon = "OK"
        elif stat == "failure":
            icon = "ERR"
        else:
            icon = "---"
            never_run_jobs.append(jid)
        print(f"{icon:5} {jid:38} {last:19} {nxt:19} {succ}/{fail}")

    print()
    if never_run_jobs:
        print(f"⚠ {len(never_run_jobs)} cron NEVER run since last restart:")
        for j in never_run_jobs:
            print(f"    - {j}")
    else:
        print("✓ all cron have run at least once since restart")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
