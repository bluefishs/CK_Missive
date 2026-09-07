#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色列舉 vs `role_permissions` 的漂移（weekly 118，2026-09-07）。

## 為什麼要有這一支

`role_permissions` 資料表是角色的權威來源（有中文名、權限清單、`can_login`），
而 `app/schemas/auth.py` 的 `UserRole` 是**手抄的一份**。2026-08-27 新增了
`exec`／`ops`／`finance` 三個職能角色進資料表與前端，**列舉沒有跟上**：

* `UserUpdate.role` 型別是 `Optional[UserRole]`
* ⇒ 把任何人改成高階主管／營運管理／財務 → **422，而且沒有任何訊息**
* ⇒ 角色做出來了、權限頁列得出來、**就是指派不上去**，而畫面上看不出原因

owner 2026-09-07 從 `/api/admin/user-community/users/3/update` 回報那個 422 時，
它已經卡了 11 天。**沒有任何檢核在對這兩份**。

## 判準

| 方向 | 判定 | 為什麼 |
|---|---|---|
| DB 有、列舉沒有 | **RED** | 那個角色指派不上去（本次事故的形狀） |
| 列舉有、DB 沒有 | YELLOW | 可以選、但選了沒有任何權限——是待清的殘留，不是當下故障 |

⚠️ 刻意**不**去比對前端 `constants/permissions.ts`：那一份是預設權限的範本
（建立角色時用），不是「現在有哪些角色」。拿它比會得到一支天天黃的檢核。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
from lib.docker_exec import python_in  # noqa: E402

try:  # Windows 主控台預設 cp950，中文輸出會被有損替換成 ?
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = repo_root()
AUTH_SCHEMA = ROOT / "backend" / "app" / "schemas" / "auth.py"


def enum_roles() -> set[str]:
    """讀 `UserRole` 的成員值。用文字剖析而不是 import —— 檢核跑在 host，
    而 import backend 會把整條設定鏈拉進來（且需要 DB）。"""
    src = AUTH_SCHEMA.read_text(encoding="utf-8")
    m = re.search(r"class UserRole\(str, Enum\):(.*?)(?=\n\nclass |\n\n# )", src, re.S)
    if not m:
        return set()
    return set(re.findall(r'^\s+[A-Z_]+\s*=\s*"([a-z_]+)"', m.group(1), re.M))


def main() -> int:
    print("=== 角色列舉 vs role_permissions（weekly 118）===")
    if not AUTH_SCHEMA.exists():
        print("[YELLOW] 找不到 auth.py，未驗")
        return 1

    code = enum_roles()
    if not code:
        # 剖析不到就不要回綠——「掃不到」與「沒有問題」是兩件事
        print("[YELLOW] 剖析不到 UserRole 的成員（class 形狀可能改了），未驗")
        return 1

    # 走共用的 docker_exec（weekly 93：不自己開 docker exec、不自算路徑）
    out = python_in(
        "import asyncio, json\n"
        "from sqlalchemy import text\n"
        "from app.db.database import AsyncSessionLocal\n"
        "async def m():\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        rows = (await db.execute(text('SELECT role FROM role_permissions ORDER BY role'))).all()\n"
        "    print(json.dumps([r[0] for r in rows]))\n"
        "asyncio.run(m())\n"
    )
    line = [l for l in (out or "").strip().splitlines() if l.startswith("[")]
    if not line:
        # 連不到就回 YELLOW —— 「查不到」不等於「一致」
        print("[YELLOW] 連不到資料庫，未驗")
        return 1
    import json
    db = {r.strip() for r in json.loads(line[-1]) if r}

    missing = sorted(db - code)      # DB 有、列舉沒有 ⇒ 指派不上去
    extra = sorted(code - db)        # 列舉有、DB 沒有 ⇒ 選了沒權限

    print(f"  role_permissions {len(db)} 個：{'、'.join(sorted(db))}")
    print(f"  UserRole 列舉 {len(code)} 個：{'、'.join(sorted(code))}")

    if missing:
        print(f"[RED] {len(missing)} 個角色在資料表裡有、`UserRole` 沒有 ⇒ "
              f"指派給任何人都會回 422（而且沒有訊息）：{'、'.join(missing)}")
        print("      修法：把它們補進 `backend/app/schemas/auth.py` 的 UserRole。")
        return 2
    if extra:
        print(f"[YELLOW] {len(extra)} 個角色列舉裡有、資料表沒有 ⇒ 選得到但沒有任何權限："
              f"{'、'.join(extra)}")
        return 1
    print("[GREEN] 兩份一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
