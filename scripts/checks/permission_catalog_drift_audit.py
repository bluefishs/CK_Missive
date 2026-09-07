#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""權限目錄漂移與「無法獨立勾選」（weekly 119，2026-09-07）。

owner 兩個回報，是同一個結構問題的兩面：

1. **「`/admin/permissions/exec?tab=by-category` 設定不同步」**
   權限管理頁有兩個分頁，而它們是**兩個來源**：
   「依選單階層」讀 `site_navigation_items`（live DB），
   「依權限分類」讀前端 `constants/permissions.ts` 的 `PERMISSION_CATEGORIES`。
   ⇒ **不在前端目錄裡的權限碼，在分類頁看不見**（頁面自己的說明就寫著這件事）。
   實測差一個：`admin:database` —— 而管理員角色正在用它。
   ⚠️ 不是資料遺失（勾選是在完整清單上加減，未知的碼會保留），是**看不見**。

2. **「委託與協力帳款仍關聯 ERP，無法正常獨立勾選」**
   權限碼與頁面是多對一：`reports:erp:view` 曾綁 11 個頁面 ⇒ 勾一個等於開 11 個。
   **粒度是權限碼的數量，不是頁面的數量。**
   owner 進一步指出：「站點路徑換階層但仍可被檢視」——把選單搬到別的父階
   不會改變它要什麼權限，共用碼的頁面搬到哪裡都還是一起開關。

## 判準

| # | 判定 | 為什麼 |
|---|---|---|
| ① | **RED** | DB 用到、前端目錄沒有 ⇒ 該權限在「依權限分類」分頁看不見也改不了 |
| ② | YELLOW（走基線） | 一個碼綁多個頁面 ⇒ 無法獨立勾選。存量是現況不是缺陷清單，**新增的耦合才要解釋** |

② 刻意不判紅：一次要求 71 個頁面各自一碼，等於把整個權限模型重寫，
而永遠是紅的訊號與沒有訊號是同一個下場。它的用途是**讓耦合看得見、逐頁減少**——
就像 09-07 把委託／協力帳款從 `reports:erp:view` 拆出來那樣。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
from lib.docker_exec import python_in  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = repo_root()
CONSTANTS = ROOT / "frontend" / "src" / "constants" / "permissions.ts"
BASELINE = Path(__file__).with_name(".permission_coupling_baseline.json")


def ui_permission_codes() -> set[str]:
    """`PERMISSION_CATEGORIES` 裡定義的權限碼。

    只認**權限項目**的 `key`（那些帶 `category:` 的物件），不認分類自己的 key ——
    分類的 key 是 `documents`／`reports` 這種沒有冒號的字，混進來會讓比對失真。
    """
    src = CONSTANTS.read_text(encoding="utf-8")
    return set(re.findall(r"key:\s*'([a-z_]+:[a-z_:]+)'", src))


def _db() -> dict | None:
    out = python_in(
        "import asyncio, json\n"
        "from sqlalchemy import text\n"
        "from app.db.database import AsyncSessionLocal\n"
        "async def m():\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        roles = (await db.execute(text(\n"
        "            \"SELECT DISTINCT v FROM role_permissions, jsonb_array_elements_text(permissions) v\"\n"
        "        ))).all()\n"
        "        navs = (await db.execute(text(\n"
        "            \"SELECT path, permission_required FROM site_navigation_items \"\n"
        "            \"WHERE is_enabled AND COALESCE(permission_required,'[]') <> '[]'\"\n"
        "        ))).all()\n"
        "    print('@@' + json.dumps({\n"
        "        'roles': [r[0] for r in roles],\n"
        "        'navs': [[n[0], n[1]] for n in navs],\n"
        "    }))\n"
        "asyncio.run(m())\n"
    )
    line = [l for l in (out or "").splitlines() if l.startswith("@@")]
    return json.loads(line[-1][2:]) if line else None


def main() -> int:
    print("=== 權限目錄漂移與獨立勾選（weekly 119）===")
    if not CONSTANTS.exists():
        print("[YELLOW] 找不到 permissions.ts，未驗")
        return 1
    ui = ui_permission_codes()
    if not ui:
        print("[YELLOW] 剖析不到 PERMISSION_CATEGORIES 的權限碼，未驗")
        return 1

    d = _db()
    if d is None:
        print("[YELLOW] 連不到資料庫，未驗")
        return 1

    role_codes = {c for c in d["roles"] if c and c != "*"}
    # 每個碼綁了哪些頁面（只算有路徑的，群組節點不是頁面）
    by_code: dict[str, list[str]] = {}
    for path, req in d["navs"]:
        if not path:
            continue
        try:
            codes = json.loads(req) if isinstance(req, str) else (req or [])
        except Exception:
            codes = [req]
        for c in codes:
            by_code.setdefault(str(c), []).append(path)

    used = role_codes | set(by_code)
    missing = sorted(used - ui)
    coupled = {c: sorted(p) for c, p in by_code.items() if len(p) > 1}

    print(f"  前端目錄 {len(ui)} 個碼／DB 實際用到 {len(used)} 個")
    print(f"  綁多頁的碼 {len(coupled)} 個（共 {sum(len(v) for v in coupled.values())} 頁無法獨立勾選）")

    rc = 0
    if missing:
        print(f"[RED] {len(missing)} 個權限碼在 DB 用著、前端目錄沒有 ⇒ "
              f"「依權限分類」分頁看不見也改不了：{'、'.join(missing)}")
        print("      修法：補進 frontend/src/constants/permissions.ts 的 PERMISSION_CATEGORIES。")
        rc = 2

    base = {}
    if BASELINE.exists():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8"))
        except Exception:
            base = {}
    known = base.get("coupled", {})
    new_coupled = {c: v for c, v in coupled.items()
                   if c not in known or len(v) > len(known.get(c, []))}
    if new_coupled:
        print(f"[YELLOW] {len(new_coupled)} 個碼的耦合是新增或變多的：")
        for c, paths in sorted(new_coupled.items()):
            print(f"    {c} ← {len(paths)} 頁：{'、'.join(paths[:4])}"
                  + ("…" if len(paths) > 4 else ""))
        print("      勾其中任何一頁都會把其餘一起打開。要獨立勾選就得給該頁自己的碼"
              "（09-07 委託／協力帳款就是這樣拆出來的：nav 宣告＋API router＋角色三處一起改）。")
        rc = max(rc, 1)
    elif coupled:
        print(f"  存量耦合 {len(coupled)} 個碼在基線內（逐頁減少，不判紅）")

    if not BASELINE.exists():
        BASELINE.write_text(json.dumps({"coupled": coupled}, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print("  已建立基線 .permission_coupling_baseline.json（存量不判紅、新增才提）")

    if rc == 0:
        print("[GREEN] 兩份目錄一致，且沒有新增的權限耦合")
    return rc


if __name__ == "__main__":
    sys.exit(main())
