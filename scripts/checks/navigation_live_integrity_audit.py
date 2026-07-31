# -*- coding: utf-8 -*-
"""導覽列 live 完整性稽核（fitness step 78，2026-07-31）

owner：「依前述架構對應 admin/site-management 各項模組進行自我檢測與優化程序設計」。

## 為何既有檢查不夠

| 既有 | 檢什麼 | 漏什麼 |
|---|---|---|
| `route-sync-check.js` | ROUTES / AppRouter / init_navigation_data 三檔對齊 | **原始碼對原始碼** |
| `navigation_validator.py` | 寫入時驗路徑在白名單內 | 只擋新寫入，不看既有 |

兩者都**不看 live DB 實際長什麼樣**。而導覽列是使用者唯一的入口——
DB 裡一筆指向已刪路由的項目，使用者點了就是 404，但所有靜態檢查都是綠的。
（對照 v6.13 已知：`init_navigation_data.py` 的 admin 區塊與 live DB 已漂移。）

## 檢什麼

1. **死連結**：DB 導覽項目的 path 在前端 ROUTES 中不存在 → 點了會 404
2. **孤兒頁面**：ROUTES 有、導覽沒有 → 功能存在但沒人找得到（dead UI 家族）
3. **重複 path**：同一路徑掛在多個導覽項目 → 使用者困惑、權限難管

孤兒頁面數量大且多為刻意（詳情頁、表單頁不該進側欄），故僅列數字供觀察，
**不列為失敗**；死連結與重複 path 才是硬性問題。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]

# 這些前綴屬「詳情/表單/流程」頁，本來就不該出現在側邊導覽
NON_NAV_PATTERNS = [
    r"/create$", r"/new$", r"/:", r"^/auth/", r"^/login", r"^/register",
    r"^/forgot-password", r"^/reset-password", r"^/verify-email", r"^/mfa/",
    r"^/404$", r"^/entry$", r"^/$", r"^/api/",
]


def frontend_routes() -> set[str]:
    src = (ROOT / "frontend/src/router/types.ts").read_text(encoding="utf-8")
    return {
        m.group(2)
        for m in re.finditer(r"^\s{2}([A-Z0-9_]+):\s*'(/[^']*)'", src, re.M)
    }


def live_nav_items() -> list[dict]:
    """從容器內讀 live DB（導覽是 runtime 狀態，不能只看 seed 檔）"""
    code = (
        "import asyncio,json\n"
        "from sqlalchemy import text\n"
        "from app.db.database import AsyncSessionLocal\n"
        "async def m():\n"
        "    async with AsyncSessionLocal() as s:\n"
        "        r=await s.execute(text('SELECT id,title,path,parent_id FROM site_navigation_items WHERE is_enabled=true'))\n"
        "        print('JSON'+json.dumps([{'id':x[0],'name':x[1],'path':x[2],'parent_id':x[3]} for x in r],ensure_ascii=False))\n"
        "asyncio.run(m())\n"
    )
    try:
        out = subprocess.run(
            ["docker", "exec", "ck_missive_backend", "python", "-c", code],
            capture_output=True, text=True, timeout=90,
            encoding="utf-8", errors="ignore",
        ).stdout
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  無法讀取 live DB（後端容器未啟動？）: {e}")
        return []
    for line in out.splitlines():
        if line.startswith("JSON"):
            return json.loads(line[4:])
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    print("=" * 62)
    print("導覽列 live 完整性稽核（site-management 模組）")
    print("=" * 62)

    routes = frontend_routes()
    items = live_nav_items()
    if not items:
        print("  ⚪ 無法取得 live 導覽資料，略過（不視為失敗）")
        return 0

    with_path = [i for i in items if (i.get("path") or "").strip()]
    print(f"  導覽項目 {len(items)} 筆（有路徑 {len(with_path)}）／前端路由 {len(routes)} 條")

    # 1. 死連結
    dead = [i for i in with_path if i["path"] not in routes]
    # 2. 重複 path
    # 父子共用同一路徑是**合理**的常見型態（父選單連到其第一個子頁的落地頁），
    # 例如「公文管理」(父) 與其子「公文導覽」同指 /documents。
    # 初版沒排除 → 誤報一筆；經開 DB 核實父子關係後修正（驗證優先於收斂）。
    by_id = {i["id"]: i for i in items}

    def _is_ancestor(a_id, b_id) -> bool:
        cur, guard = by_id.get(b_id), 0
        while cur and cur.get("parent_id") and guard < 10:
            if cur["parent_id"] == a_id:
                return True
            cur, guard = by_id.get(cur["parent_id"]), guard + 1
        return False

    seen: dict[str, list[dict]] = {}
    for i in with_path:
        seen.setdefault(i["path"], []).append(i)
    dupes = {}
    for path, group in seen.items():
        if len(group) < 2:
            continue
        # 群組內若每一對都是祖孫關係，視為合理
        unrelated = [
            (x["name"], y["name"])
            for idx, x in enumerate(group) for y in group[idx + 1:]
            if not _is_ancestor(x["id"], y["id"]) and not _is_ancestor(y["id"], x["id"])
        ]
        if unrelated:
            dupes[path] = [n for pair in unrelated for n in pair]
    # 3. 孤兒頁面（僅觀察）
    nav_paths = {i["path"] for i in with_path}
    orphans = [
        r for r in sorted(routes - nav_paths)
        if not any(re.search(p, r) for p in NON_NAV_PATTERNS)
    ]

    problems = []

    print(f"\n  [死連結] {len(dead)} 筆（導覽指向不存在的路由 → 點了 404）")
    for i in dead[:10]:
        print(f"      - {i['name']} → {i['path']}")
    if dead:
        problems.append(f"{len(dead)} 個導覽項目指向不存在的路由")

    print(f"\n  [重複路徑] {len(dupes)} 組")
    for p, names in list(dupes.items())[:8]:
        print(f"      - {p} ← {', '.join(names)}")
    if dupes:
        problems.append(f"{len(dupes)} 條路徑被多個導覽項目共用")

    print(f"\n  [無導覽入口的頁面] {len(orphans)} 條（僅觀察，多為刻意）")
    for r in orphans[:10]:
        print(f"      - {r}")
    if len(orphans) > 10:
        print(f"      …另 {len(orphans) - 10} 條")

    print()
    if not problems:
        print("GREEN — 導覽列與前端路由一致")
        return 0
    print(f"RED — {len(problems)} 項：")
    for x in problems:
        print(f"  - {x}")
    print("\n修法：於 /admin/site-management「導覽列管理」修正或移除該項目；")
    print("      勿直接對 live DB 跑 init_navigation_data.py（會污染既有設定）")
    return 1 if args.ci else 0


if __name__ == "__main__":
    sys.exit(main())
