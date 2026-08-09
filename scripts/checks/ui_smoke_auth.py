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

# 2026-08-09：候選路徑改為容錯求值。
#
# 原本直接寫 `Path(__file__).resolve().parents[2]`，而共用 runner 是把本檔
# **經 stdin** 送進容器執行（`docker exec -i ... python - < 本檔`）——
# 那時 `__file__` 是 `<stdin>`，`parents[2]` 直接 IndexError，
# 而症狀是「憑證取不到 → 87 頁全 SKIP」，看起來像認證壞了。
#
# 用 stdin 是刻意的：各 repo 容器掛載結構不同（lvrland 的 /app 不是 backend/、
# DT 的程式在 /app/src），寫容器內路徑會在每次移植時重踩（L52 家族）。
# 所以該讓 adapter 不依賴 __file__，而不是讓 runner 為這一個 repo 開分支。
def _candidates():
    yield Path("/app")
    try:
        yield Path(__file__).resolve().parents[2] / "backend"
    except (NameError, IndexError):
        pass  # stdin 執行時沒有 __file__，容器內 /app 已足夠


for _cand in _candidates():
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

        # 2026-08-07：每跑一次走查就留下一列，且沒有任何人清 —— 實測自 07-31 起
        # 累積 222 列**全部已過期卻仍標為 is_active**。數量本身無害，但它污染了
        # user_sessions：任何看「目前有幾個有效 session」的人都會被誤導，而這是檢核
        # 自己造出來的雜訊（同 08-04 負向測試汙染正式晨報、走查寫入空白業務紀錄）。
        #
        # 在簽發前順手清掉**自己簽的舊列**（前綴比對），不碰任何真實 session。
        # 放在這裡而不是另做一支排程：清理的觸發時機就是產生的時機，不會漏掉。
        #
        # ⚠️ 用 created_at 而**不是** expires_at：這張表的兩個時間欄位基準不同 ——
        # created_at 走 NOW()（DB 本地），expires_at 走 datetime.utcnow()（UTC）。
        # 實測同一列 created_at=19:12 而 expires_at=11:32，於是 `expires_at < NOW()`
        # 恆為真，會把**剛簽發、正在用**的 session 一起刪掉（並行跑兩支走查時就會互殺）。
        # 第一版就是這樣寫的，靠實際比對欄位值才發現。
        await db.execute(
            text(
                "DELETE FROM user_sessions "
                "WHERE token_jti LIKE :p AND created_at < NOW() - INTERVAL '1 day'"
            ),
            {"p": f"{JTI_PREFIX}%"},
        )

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
